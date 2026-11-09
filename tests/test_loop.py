import json
from pathlib import Path

import pytest
from rdflib import Graph, RDF, OWL

from labloop.agents import DemoAgent
from labloop.knowledge import Vault, NS
from labloop.loop import run_loop
from labloop.report_schemas import Distillation
from labloop.file_provenance import RunArtifacts

CONFIG = {"goal": "Synthetic test", "criteria": "Require evidence", "distill": "Propose a test"}


def test_research_recall_filters_instructions_before_ranking_and_limit(tmp_path):
    vault = Vault(tmp_path / "vault")
    finding = vault.put("Observation", "Synthetic finding")
    for kind in ("Goal", "Criteria", "DistillInstructions"):
        for _ in range(35):
            vault.put(kind, "Synthetic test archived instructions")
    # Higher-scoring instructions must not crowd findings out of the result limit.
    assert [r["id"] for r in vault.recall("Synthetic test", limit=1, research_only=True)] == [finding]
    assert [r["id"] for r in vault.recall(research_only=True)] == [finding]
    assert vault.recall("Synthetic test", limit=1)[0]["type"] in ("ll:Goal", "ll:Criteria", "ll:DistillInstructions")
    assert len(Vault(tmp_path / "vault").records) == len(vault.records)


def test_actor_receives_findings_lessons_feedback_without_task_records(tmp_path):
    vault = Vault(tmp_path / "vault")
    vault.put("Goal", "Synthetic test old goal")
    vault.put("Criteria", "Synthetic test old audit instructions")
    vault.put("DistillInstructions", "Synthetic test old distill instructions")
    finding = vault.put("Observation", "Synthetic test prior finding")
    lesson = vault.put("Heuristic", "Synthetic test proposed lesson", status="proposed")
    feedback = vault.put("Feedback", "Scientist correction")

    class ChecksKnowledge(DemoAgent):
        def ask(self, role, instruction, context, schema, artifacts, trace):
            if role == "actor":
                assert instruction == CONFIG["goal"]
                assert all(r["type"] not in ("ll:Goal", "ll:Criteria", "ll:DistillInstructions") for r in context["knowledge"])
                assert finding in {r["id"] for r in context["knowledge"]}
                assert lesson in {r["id"] for r in context["heuristics"]}
                assert feedback in {r["id"] for r in context["feedback"]}
            return super().ask(role, instruction, context, schema, artifacts, trace)

    run_loop(CONFIG, tmp_path, ChecksKnowledge(), cycles=2)


@pytest.mark.parametrize("stop", [None, "actor", "critic", "failure"])
def test_all_task_prompts_are_archived_and_linked_across_experiment_states(tmp_path, stop):
    class StopsAtRole(DemoAgent):
        def ask(self, role, instruction, context, schema, artifacts, trace):
            if stop == "failure":
                raise RuntimeError("Test execution failure")
            result = super().ask(role, instruction, context, schema, artifacts, trace)
            if role == stop:
                result.needs_input = "Test missing input"
            return result

    if stop == "failure":
        with pytest.raises(RuntimeError, match="Test execution failure"):
            run_loop(CONFIG, tmp_path, StopsAtRole(), cycles=2)
    else:
        run_loop(CONFIG, tmp_path, StopsAtRole(), cycles=2)
    vault = Vault(tmp_path / "vault")
    prompts = {kind: [r for r in vault.recall() if r["type"] == "ll:" + kind]
               for kind in ("Goal", "Criteria", "DistillInstructions")}
    for kind, key in (("Goal", "goal"), ("Criteria", "criteria"), ("DistillInstructions", "distill")):
        assert len(prompts[kind]) == 1
        assert prompts[kind][0]["text"] == CONFIG[key]
    prompt_ids = {records[0]["id"] for records in prompts.values()}
    assert not prompt_ids.intersection(r["id"] for r in vault.recall(research_only=True))
    manifest = json.loads(next((tmp_path / "runs").glob("*/run.json")).read_text())
    for cycle in manifest["cycles"]:
        assert set(vault.records[cycle["experiment"]]["because"]) == prompt_ids
    graph = Graph().parse(data=vault.export(), format="turtle")
    assert (NS.DistillInstructions, RDF.type, OWL.Class) in graph
    for cycle in manifest["cycles"]:
        for ident in prompt_ids:
            assert (NS[cycle["experiment"]], NS.because, NS[ident]) in graph


def test_two_cycles_feed_back_and_rdf_roundtrip(tmp_path):
    class CheckingAgent(DemoAgent):
        seen = []
        roles = []
        def ask(self, role, instruction, context, schema, artifacts, trace):
            self.roles.append(role)
            assert "agenda" not in context
            if role == "actor":
                self.seen.append(context["heuristics"])
            return super().ask(role, instruction, context, schema, artifacts, trace)
    agent = CheckingAgent()
    manifest = json.loads(run_loop(CONFIG, tmp_path, agent, cycles=2).read_text())
    assert manifest["state"] == "budget_exhausted"
    assert len(manifest["cycles"]) == 2
    assert not agent.seen[0]
    assert agent.seen[1][0]["status"] == "proposed"
    assert agent.roles == ["actor", "critic", "distiller"] * 2
    assert agent.seen[1][0]["test"] == manifest["cycles"][0]["distillation"]["lessons"][0]["test"]
    vault = Vault(tmp_path / "vault")
    assert len(vault.lessons()) == 1
    assert len(vault.lessons()[0]["because"]) == 2
    assert not any(r["type"] == "ll:ResearchQuestion" for r in vault.records.values())
    graph = Graph().parse(data=vault.export(), format="turtle")
    assert (NS.Hypothesis, RDF.type, OWL.Class) in graph
    assert len(graph) == len(vault.graph)
    assert any(r["type"] == "ll:FilePath" and r["sha256"] for r in vault.records.values())


def test_invented_citation_fails_without_poisoning_memory(tmp_path):
    class BadDistiller(DemoAgent):
        def ask(self, role, instruction, context, schema, artifacts, trace):
            if role == "distiller":
                return Distillation(lessons=[{"claim": "Invented", "because": ["fake"], "test": "Test"}],
                                    retract=[], new_types=[], needs_input=None)
            return super().ask(role, instruction, context, schema, artifacts, trace)
    with pytest.raises(ValueError, match="outside this experiment"):
        run_loop(CONFIG, tmp_path, BadDistiller())
    vault = Vault(tmp_path / "vault")
    assert not vault.lessons()
    assert any(r.get("status") == "failed" for r in vault.records.values())
    manifest = json.loads(next((tmp_path / "runs").glob("*/run.json")).read_text())
    assert manifest["state"] == "failed"


def test_rejected_rule_is_retrievable_but_not_injected(tmp_path):
    vault = Vault(tmp_path / "vault")
    ident = vault.put("Heuristic", "Low GQ rule", status="proposed", because=["obs"])
    vault.reject(ident, ["counterexample"])
    assert not vault.lessons()
    assert vault.recall("Low GQ")[0]["status"] == "rejected"
    assert Vault(tmp_path / "vault").records[ident]["because"] == ["obs"]
    assert Vault(tmp_path / "vault").records[ident]["rejectedBecause"] == ["counterexample"]


def test_evidence_paths_and_missing_files(tmp_path):
    artifacts = RunArtifacts(tmp_path, tmp_path / "out", Vault(tmp_path / "vault"))
    with pytest.raises(ValueError, match="escapes"):
        artifacts.path("../secret")
    (tmp_path / "outside").symlink_to("/etc")
    with pytest.raises(ValueError, match="escapes"):
        artifacts.file_record("outside/passwd", "exp")
    with pytest.raises(ValueError, match="does not exist"):
        artifacts.file_record("missing.txt", "exp")


def test_ontology_extension_and_invalid_id(tmp_path):
    vault = Vault(tmp_path / "vault")
    vault.add_type("MappingArtifact")
    ident = vault.put("MappingArtifact", "A test artifact")
    assert (NS[ident], RDF.type, NS.MappingArtifact) in vault.graph
    with pytest.raises(ValueError):
        vault.add_type("../../bad")
    with pytest.raises(ValueError):
        vault.put("Observation", "bad", id="../bad")


def test_human_question_stops_loop(tmp_path):
    class NeedsHuman(DemoAgent):
        def ask(self, role, instruction, context, schema, artifacts, trace):
            result = super().ask(role, instruction, context, schema, artifacts, trace)
            if role == "critic":
                result.needs_input = "What independent validation assay should be used?"
            return result
    path = run_loop(CONFIG, tmp_path, NeedsHuman(), cycles=3)
    manifest = json.loads(path.read_text())
    assert manifest["state"] == "needs_input"
    assert len(manifest["cycles"]) == 1
    assert not Vault(tmp_path / "vault").lessons()


def test_scientist_feedback_retires_assertion_and_reaches_actor(tmp_path):
    from labloop.scientist_feedback import record_feedback
    vault = Vault(tmp_path / "vault")
    target = vault.put("Heuristic", "A falsifiable rule", status="proposed", because=["prior"])
    ident = record_feedback(tmp_path, "vault", {"target": target,
                            "status": "contradicted", "text": "Independent validation rejects this rule."})
    updated = Vault(tmp_path / "vault")
    assert updated.records[target]["status"] == "rejected"
    assert updated.records[target]["because"] == ["prior"]
    assert updated.records[target]["rejectedBecause"] == [ident]
    class ChecksFeedback(DemoAgent):
        def ask(self, role, instruction, context, schema, artifacts, trace):
            if role == "actor":
                assert context["feedback"][0]["id"] == ident
                assert all(h["id"] != target for h in context["heuristics"])
            return super().ask(role, instruction, context, schema, artifacts, trace)
    run_loop(CONFIG, tmp_path, ChecksFeedback(), cycles=1)


def test_work_product_type_is_learned_from_actor(tmp_path):
    run_loop(CONFIG, tmp_path, DemoAgent(), cycles=1)
    vault = Vault(tmp_path / "vault")
    assert (NS.SyntheticFinding, RDF.type, OWL.Class) in vault.graph
    assert list(vault.graph.subjects(RDF.type, NS.SyntheticFinding))
    assert not list(vault.graph.subjects(RDF.type, NS.CrossoverCandidate))

