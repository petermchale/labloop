"""Exercise the real subprocess boundary with a deterministic CLI test double."""
import json
import sys

import pytest
from pydantic import ValidationError

from labloop.agents import CodexAgent
from labloop.file_provenance import RunArtifacts
from labloop.knowledge import Vault
from labloop.loop import run_loop
from labloop.report_schemas import ActorReport


@pytest.fixture
def fake_codex(tmp_path):
    executable = tmp_path / "codex-test-double"
    executable.write_text("#!" + sys.executable + "\n" + r'''
import json, subprocess, sys, time
from pathlib import Path
if "--version" in sys.argv:
    print("codex-test-double 1.0")
    sys.exit(0)
argv = sys.argv[1:]
prompt = json.load(sys.stdin)
root = Path(prompt["project_root"])
context = prompt["context"]
role = prompt["role"]
mode = (root / "mode.txt").read_text() if (root / "mode.txt").exists() else "success"
with (root / "invocations.jsonl").open("a") as log:
    log.write(json.dumps({"argv": argv, "prompt": prompt}) + "\n")
if mode == "timeout":
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    time.sleep(30)
if mode == "nonzero":
    print("Deliberate test failure", file=sys.stderr)
    sys.exit(7)
result_path = Path(argv[argv.index("--output-last-message") + 1])
if mode != "missing":
    if mode == "invalid":
        result = {"wrong": "schema"}
    elif role == "actor":
        if context["cycle"] == 1:
            script = root / context["output"] / "calculate.py"
            script.write_text("import math\nprint(math.sqrt(81))\n")
        else:
            # Knowledge access uses the command supplied by the controller, not custom tools.
            recall = ["ReusableCalculator" if v == "<query>" else v
                      for v in prompt["knowledge_access"]["recall_argv"]]
            records = json.loads(subprocess.check_output(recall, cwd=root, text=True))
            assert any(r.get("text") == "ReusableCalculator" for r in records)
            assert all(r["type"] not in ("ll:Goal", "ll:Criteria", "ll:DistillInstructions") for r in records)
            assert context["heuristics"][0]["text"] == "Reuse the verified calculation"
            script = root / context["previous_cycles"][0]["actor"]["products"][0]["evidence"][0]
        output = root / context["output"] / ("answer-" + str(context["cycle"]) + ".txt")
        with output.open("w") as handle:
            subprocess.run([sys.executable, str(script)], stdout=handle, check=True)
        result = {"summary": "Computed a square root", "products": [{"key": "root",
                  "type_name": "Calculation", "description": "ReusableCalculator",
                  "evidence": [str(script.relative_to(root)), str(output.relative_to(root))]}],
                  "needs_input": None}
    elif role == "critic":
        evidence = context["product"]["evidence"]
        assert (root / evidence[-1]).read_text().strip() == "9.0"
        result = {"verdict": "supported", "diagnosis": "9 squared equals 81",
                  "evidence": evidence, "needs_input": None}
    else:
        result = {"lessons": [{"claim": "Reuse the verified calculation",
                  "because": [context["observations"][0]["id"]],
                  "test": "Compare additional inputs with independent calculations"}],
                  "retract": [], "new_types": [], "needs_input": None}
    result_path.write_text(json.dumps(result))
print(json.dumps({"type": "thread.started", "thread_id": "test-" + role}))
print(json.dumps({"type": "turn.failed" if mode == "failed-event" else "turn.completed",
                  "usage": {"input_tokens": 100, "output_tokens": 20}}))
''')
    executable.chmod(0o755)
    return str(executable)


def test_codex_runs_all_roles_and_reuses_code_across_cycles(tmp_path, fake_codex, monkeypatch):
    # The recalled package must be available from the temporary research project.
    from pathlib import Path
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1]))
    config = {"goal": "Calculate a square root", "criteria": "Check independently", "distill": "Learn"}
    vault = Vault(tmp_path / "vault")
    for kind in ("Goal", "Criteria", "DistillInstructions"):
        vault.put(kind, "ReusableCalculator archived instructions")
    agent = CodexAgent(executable=fake_codex, models={"actor": "test-model"})
    path = run_loop(config, tmp_path, agent, cycles=2)
    manifest = json.loads(path.read_text())
    invocations = [json.loads(line) for line in (tmp_path / "invocations.jsonl").read_text().splitlines()]
    assert [i["prompt"]["role"] for i in invocations] == ["actor", "critic", "distiller"] * 2
    assert manifest["state"] == "budget_exhausted"
    assert len(manifest["metrics"]) == 6
    assert all(m["usage"]["output_tokens"] == 20 for m in manifest["metrics"])
    for invocation in invocations:
        argv, prompt = invocation["argv"], invocation["prompt"]
        scientist_prompt = config[{"actor": "goal", "critic": "criteria", "distiller": "distill"}[prompt["role"]]]
        assert prompt["instructions"].endswith("Scientist's task-specific instructions:\n" + scientist_prompt)
        for role in ("actor", "critic", "distiller"):
            assert (f"You are the {role} in LabLoop's scientific learning cycle." in prompt["instructions"]) == (role == prompt["role"])
        assert "resume" not in argv
        assert "--ephemeral" in argv
        sandbox = argv[argv.index("--sandbox") + 1]
        assert sandbox == ("read-only" if prompt["role"] == "distiller" else "workspace-write")
        assert "agenda" not in prompt["context"]
        assert "--research-only" in prompt["knowledge_access"]["recall_argv"]
        schema_path = __import__('pathlib').Path(argv[argv.index("--output-schema") + 1])
        assert json.loads(schema_path.read_text())["additionalProperties"] is False
    assert "--model" in invocations[0]["argv"]
    assert "--model" not in invocations[1]["argv"]
    first, second = [cycle["actor"]["products"][0]["evidence"][0] for cycle in manifest["cycles"]]
    assert first == second
    records = Vault(tmp_path / "vault").records.values()
    assert any(r.get("path") == first and r.get("sha256") for r in records)
    assert len(list(path.parent.glob("*.prompt.json"))) == 6
    assert len(list(path.parent.glob("*.result.json"))) == 6


@pytest.mark.parametrize("mode,error", [("nonzero", RuntimeError), ("missing", RuntimeError),
                                      ("invalid", ValidationError), ("failed-event", RuntimeError)])
def test_cli_failures_are_recorded(tmp_path, fake_codex, mode, error):
    (tmp_path / "mode.txt").write_text(mode)
    agent = CodexAgent(executable=fake_codex)
    with pytest.raises(error):
        run_loop({"goal": "Test", "criteria": "Test", "distill": "Test"}, tmp_path, agent, cycles=1)
    manifest = json.loads(next((tmp_path / "runs").glob("*/run.json")).read_text())
    assert manifest["state"] == "failed"
    assert manifest["error"]


def test_timeout_kills_invocation_and_ignores_stale_result(tmp_path, fake_codex):
    (tmp_path / "mode.txt").write_text("timeout")
    artifacts = RunArtifacts(tmp_path, tmp_path / "out", Vault(tmp_path / "vault"))
    trace = artifacts.output / "actor.jsonl"
    result = trace.with_suffix(".result.json")
    result.write_text('{"summary":"stale","products":[],"needs_input":null}')
    agent = CodexAgent(executable=fake_codex, timeout=0.1)
    with pytest.raises(RuntimeError, match="exceeded"):
        agent.ask("actor", "Test", {"output": "out"}, ActorReport, artifacts, trace)
    assert not result.exists()
    assert agent.metrics[0]["timed_out"]


def test_missing_codex_has_actionable_error():
    with pytest.raises(ValueError, match="Codex CLI not found"):
        CodexAgent(executable="/nonexistent/codex")
