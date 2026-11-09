import hashlib
import json
import subprocess
from pathlib import Path
from uuid import uuid4

from .knowledge import Vault
from .report_schemas import ActorReport, Critique, Distillation
from .file_provenance import RunArtifacts


def git_context(root):
    def read(*args):
        p = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10)
        return p.stdout.strip() if p.returncode == 0 else None
    return {"commit": read("rev-parse", "HEAD"), "branch": read("branch", "--show-current"),
            "dirty": bool(read("status", "--porcelain"))}


def run_loop(config, root, agent, *, cycles=2, vault_dir="vault", run_dir="runs"):
    root = Path(root).resolve()
    if not 1 <= cycles <= 20:
        raise ValueError("cycles must be between 1 and 20")
    # Resolve destinations through the same path policy as evidence.
    for directory in (vault_dir, run_dir):
        if not (root / directory).resolve().is_relative_to(root):
            raise ValueError("Run and vault directories must be within workspace")
    vault = Vault(root / vault_dir)
    session = uuid4().hex
    output = root / run_dir / session
    output.mkdir(parents=True)
    artifacts = RunArtifacts(root, output, vault)
    goal = vault.put("Goal", config["goal"])
    criteria = vault.put("Criteria", config["criteria"])
    git = git_context(root)
    refs = {}
    if git["commit"]:
        refs["commit"] = vault.put("GitCommit", git["commit"], gitDirty=git["dirty"])
    if git["branch"]:
        refs["branch"] = vault.put("GitBranch", git["branch"])
    manifest = {"session": session, "config": config, "git": git, "cycles": [], "state": "running"}
    manifest_path = output / "run.json"
    def save():
        manifest["metrics"] = agent.metrics
        Vault._write(manifest_path, json.dumps(manifest, indent=2))
        Vault._write(output / "graph.ttl", vault.export())
    save()
    try:
        for cycle in range(cycles):
            exp = vault.put("Experiment", f"{session}: cycle {cycle + 1}", status="running",
                            because=[goal, criteria], **refs)
            record = {"experiment": exp, "cycle": cycle + 1, "observations": []}
            manifest["cycles"].append(record)
            common = {"output": str(output.relative_to(root)),
                      "knowledge": vault.recall(config["goal"]),
                      "heuristics": vault.lessons(),
                      "feedback": [r for r in vault.records.values() if r["type"] == "ll:Feedback"][-30:],
                      "note": "Heuristics are candidate hypotheses, not evaluation truth.",
                      "cycle": cycle + 1, "previous_cycles": manifest["cycles"][:-1]}
            actor = agent.ask("actor", config["goal"], common, ActorReport, artifacts,
                              output / f"{cycle + 1}-actor.jsonl")
            record["actor"] = actor.model_dump()
            if actor.needs_input:
                manifest.update(state="needs_input", question=actor.needs_input)
                vault.put("Experiment", f"{session}: cycle {cycle + 1}", id=exp,
                          status="needs_input", because=[goal, criteria], **refs)
                break
            if len({i.key for i in actor.products}) != len(actor.products):
                raise ValueError("Actor produced duplicate work-product keys")
            max_products = config.get("max_products", 100)
            if len(actor.products) > max_products:
                raise ValueError(f"Actor exceeded max_products={max_products}; no products silently dropped")
            observations = []
            for index, item in enumerate(actor.products):
                if not item.evidence:
                    raise ValueError("Actor work product must cite evidence")
                files = [artifacts.file_record(p, exp) for p in item.evidence]
                # Scientific entity types arise from the task, rather than a core enum.
                vault.add_type(item.type_name)
                product_id = vault.put(item.type_name, item.description, experiment=exp,
                                       files=files, status="proposed")
                critic = agent.ask("critic", config["criteria"],
                                   {"output": common["output"], "product": item.model_dump(),
                                    "knowledge": common["knowledge"], "feedback": common["feedback"]},
                                   Critique, artifacts,
                                   output / f"{cycle + 1}-critic-{index}.jsonl")
                evidence = [artifacts.file_record(p, exp) for p in critic.evidence]
                if critic.verdict != "uncertain" and not evidence:
                    raise ValueError("Definite critique must cite an evidence file")
                obs = vault.put("Observation", critic.diagnosis, experiment=exp,
                                because=[product_id], status=critic.verdict, files=evidence)
                diagnosis = vault.put("Diagnosis", critic.diagnosis, experiment=exp, because=[obs])
                observations.append({"id": obs, "item": item.key, **critic.model_dump()})
                record["observations"].append({**observations[-1], "diagnosis": diagnosis})
                if critic.needs_input:
                    manifest.update(state="needs_input", question=critic.needs_input)
                    break
            if manifest["state"] == "needs_input":
                vault.put("Experiment", f"{session}: cycle {cycle + 1}", id=exp,
                          status="needs_input", because=[goal, criteria], **refs)
                break
            distilled = agent.ask("distiller", config["distill"],
                                  {**common, "observations": observations}, Distillation, artifacts,
                                  output / f"{cycle + 1}-distiller.jsonl")
            known = {o["id"] for o in observations}
            # Validate the whole proposal before making any of its changes.
            for change in [*distilled.lessons, *distilled.retract]:
                if not set(change.because) <= known:
                    raise ValueError("Distiller cited an observation outside this experiment")
            for retraction in distilled.retract:
                if not vault.can_retract(retraction.target):
                    raise ValueError("Only a known research assertion can be retracted")
                if not any(o["id"] in retraction.because and o["verdict"] == "contradicted"
                           for o in observations):
                    raise ValueError("Retraction needs a current contradictory observation")
            for name in distilled.new_types:
                import re
                if not re.fullmatch(r"[A-Z][A-Za-z0-9]{0,63}", name):
                    raise ValueError("Invalid proposed type")
            for name in distilled.new_types:
                vault.add_type(name)
            for lesson in distilled.lessons:
                # Stable claim identity avoids duplicate candidate rules across cycles/runs.
                ident = "heuristic_" + hashlib.sha256(lesson.claim.strip().lower().encode()).hexdigest()[:24]
                existing = vault.records.get(ident)
                if existing and existing.get("status") == "rejected":
                    continue  # A dead end cannot silently resurrect itself.
                because = list(dict.fromkeys((existing or {}).get("because", []) + lesson.because))
                vault.put("Heuristic", lesson.claim, id=ident, experiment=exp,
                          status="proposed", because=because, test=lesson.test)
            for retraction in distilled.retract:
                vault.reject(retraction.target, retraction.because)
                vault.put("Claim", "Retraction: " + retraction.target, experiment=exp,
                          target=retraction.target, because=retraction.because, status="rejected")
            record["distillation"] = distilled.model_dump()
            vault.put("Experiment", f"{session}: cycle {cycle + 1}", id=exp,
                      status="completed", because=[goal, criteria], **refs)
            save()
            if distilled.needs_input:
                manifest.update(state="needs_input", question=distilled.needs_input)
                break
            if not actor.products:
                manifest["state"] = "no_products"
                break
        if manifest["state"] == "running":
            manifest["state"] = "budget_exhausted"
    except Exception as exc:
        manifest.update(state="failed", error=f"{type(exc).__name__}: {exc}")
        if manifest["cycles"]:
            vault.put("Experiment", str(exc), id=manifest["cycles"][-1]["experiment"],
                      status="failed", because=[goal, criteria], **refs)
        raise
    finally:
        save()
    return manifest_path
