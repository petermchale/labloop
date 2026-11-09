"""Role-specific Codex invocations; Codex owns the model and tool-execution loop."""
import json
import os
import shutil
import signal
import subprocess
import sys
from importlib.resources import files
from time import monotonic


def role_instructions(role, scientist_prompt):
    if role not in ("actor", "critic", "distiller"):
        raise ValueError(f"Unknown scientific role: {role}")
    prompts = files("labloop").joinpath("prompts")
    common = prompts.joinpath("common.md").read_text(encoding="utf-8").strip()
    specific = prompts.joinpath(f"{role}.md").read_text(encoding="utf-8").strip()
    return "\n\n".join((common, specific, "Scientist's task-specific instructions:\n" + scientist_prompt))


class CodexAgent:
    def __init__(self, models=None, *, executable="codex", timeout=900, effort="medium"):
        if timeout <= 0:
            raise ValueError("Codex timeout must be positive")
        self.executable = shutil.which(executable)
        if not self.executable:
            raise ValueError(f"Codex CLI not found: {executable}")
        self.models = models or {}
        self.timeout = timeout
        self.effort = effort
        self.metrics = []
        version = subprocess.run([self.executable, "--version"], capture_output=True,
                                 text=True, timeout=10, check=True)
        self.version = version.stdout.strip()

    def ask(self, role, instruction, context, schema, artifacts, trace):
        sandbox = "read-only" if role == "distiller" else "workspace-write"
        schema_path = trace.with_suffix(".schema.json")
        result_path = trace.with_suffix(".result.json")
        prompt_path = trace.with_suffix(".prompt.json")
        stderr_path = trace.with_suffix(".stderr.txt")
        schema_path.write_text(json.dumps(schema.model_json_schema(), indent=2))
        # Use the same interpreter/package as the controller for application-specific recall.
        recall = [sys.executable, "-m", "labloop.cli", "recall", "<query>",
                  "--vault", str(artifacts.vault.root.resolve()), "--research-only"]
        prompt = {"role": role, "instructions": role_instructions(role, instruction),
                  "project_root": str(artifacts.root), "context": context,
                  "knowledge_access": {"recall_argv": recall,
                                       "usage": "Replace <query> with your search; run from project_root."}}
        prompt_path.write_text(json.dumps(prompt, indent=2))
        argv = [self.executable, "exec", "--cd", str(artifacts.root),
                "--sandbox", sandbox, "--skip-git-repo-check", "--ephemeral",
                "--color", "never", "--json", "--output-schema", str(schema_path),
                "--output-last-message", str(result_path),
                "-c", f'model_reasoning_effort="{self.effort}"']
        if self.models.get(role):
            argv += ["--model", self.models[role]]
        argv.append("-")
        invocation = {"argv": argv, "role": role, "codex_version": self.version,
                      "sandbox": sandbox, "timeout_seconds": self.timeout}
        invocation_path = trace.with_suffix(".invocation.json")
        started = monotonic()
        invocation_path.write_text(json.dumps(invocation, indent=2))
        result_path.unlink(missing_ok=True)  # Never consume a stale result after a failed invocation.
        with trace.open("w") as events, stderr_path.open("w") as stderr:
            process = subprocess.Popen(argv, cwd=artifacts.root, stdin=subprocess.PIPE,
                                       stdout=events, stderr=stderr, text=True,
                                       start_new_session=True)
            timed_out = False
            try:
                process.communicate(json.dumps(prompt), timeout=self.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                raise
        invocation.update(returncode=process.returncode, timed_out=timed_out,
                          latency_seconds=monotonic() - started)
        invocation_path.write_text(json.dumps(invocation, indent=2))
        metric = {**invocation, "model": self.models.get(role) or "Codex configured model", "usage": {}}
        self.metrics.append(metric)
        if timed_out:
            raise RuntimeError(f"Codex {role} exceeded {self.timeout}s; see {stderr_path}")
        if process.returncode:
            stderr_text = stderr_path.read_text()
            runtime_blocked = (
                "attempt to write a readonly database" in stderr_text
                or ("failed to initialize in-process app-server client" in stderr_text
                    and "Operation not permitted" in stderr_text)
            )
            if runtime_blocked:
                raise RuntimeError(
                    f"Codex {role} could not initialize its local runtime. The parent "
                    "environment may block writes to Codex's home directory or local "
                    "app-server startup. Run LabLoop from a normal terminal, or grant "
                    "the LabLoop launch permission in the parent application. Changing "
                    "the role's --sandbox setting cannot remove parent restrictions. "
                    f"See {stderr_path}")
            raise RuntimeError(f"Codex {role} exited {process.returncode}; see {stderr_path}")
        events = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
        if any(event.get("type") in ("turn.failed", "thread.failed", "error") for event in events):
            raise RuntimeError(f"Codex {role} reported failure; see {trace}")
        completed = [event for event in events if event.get("type") == "turn.completed"]
        if not completed:
            raise RuntimeError(f"Codex {role} did not complete a turn; see {trace}")
        metric["usage"] = completed[-1].get("usage", {})
        if not result_path.is_file():
            raise RuntimeError(f"Codex {role} produced no final JSON result; see {trace}")
        return schema.model_validate_json(result_path.read_text())


class DemoAgent:
    """Scripted orchestration fixture, deliberately NOT a model-quality benchmark."""
    def __init__(self):
        self.metrics = []

    def ask(self, role, instruction, context, schema, artifacts, trace):
        if role == "actor":
            path = context["output"] + "/synthetic-call.txt"
            artifacts.path(path).write_text("Synthetic crossover: GQ=8; ambiguous alignment.\n")
            result = {"summary": "Synthetic orchestration test", "products": [
                {"key": "synthetic-1", "type_name": "SyntheticFinding",
                 "description": "Synthetic low-GQ call", "evidence": [path]}],
                "needs_input": None}
        elif role == "critic":
            result = {"verdict": "uncertain", "diagnosis": "Synthetic low-GQ ambiguity; no biological conclusion.",
                      "evidence": context["product"]["evidence"], "needs_input": None}
        else:
            result = {"lessons": [{"claim": "Test whether low-GQ variants inflate false crossovers.",
                                   "because": [context["observations"][0]["id"]],
                                   "test": "Compare a predeclared GQ filter on held-out labeled events."}],
                      "retract": [], "new_types": [], "needs_input": None}
        trace.write_text(json.dumps(result) + "\n")
        return schema.model_validate(result)
