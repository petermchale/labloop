# Codex role execution

For the learning loop and role descriptions, see the [README](../README.md).
This page describes the `codex exec` subprocess contract. Codex provides the model
conversation and its existing file, shell, image, and configured tool capabilities;
LabLoop has no direct model API client or custom tool dispatcher.

The critic reviews one work product per invocation by default. With batching
enabled, the output schema lists the allowed product keys for that invocation.
The controller checks that each product receives exactly one review. Each role
gets its previous context through records and reports.

For each invocation the Python controller:

1. Loads `prompts/common.md` and the current role's Markdown instructions from
   the package, appends the scientist's task-specific prompt, and supplies relevant
   knowledge, lessons, and evidence references as context.
2. Writes a prompt and the Pydantic-derived JSON Schema for the role's result.
3. Starts Codex and streams its JSONL events and stderr into run files.
4. Waits up to the configured timeout, terminating the CLI process group on expiry.
5. Requires a successful exit and completed turn, validates the final JSON, then
   validates evidence paths and citations before writing knowledge records.

The actual invocation has this form:

```bash
codex exec --cd PROJECT_ROOT --sandbox workspace-write \
  --skip-git-repo-check --ephemeral --color never --json \
  --output-schema RESULT.schema.json \
  --output-last-message RESULT.result.json \
  -c 'model_reasoning_effort="medium"' - < RESULT.prompt.json
```

The distiller uses `--sandbox read-only`. Actor and critic use `workspace-write`
to develop code and create research outputs. Prompts require preservation of
inputs, implementation, and the knowledge vault, with generated research files
under the run output directory. Those prompt instructions are not additional
filesystem enforcement: Codex's selected sandbox and configured permissions
provide the execution boundary. Only the controller is instructed to write
knowledge records.

Each prompt supplies a knowledge-retrieval command using the controller's Python
interpreter and exact vault path:

```bash
/path/to/python -m labloop.cli recall 'QUERY' --vault /path/to/vault
```

The controller also preloads relevant records so each role can begin with
context. Actor and critic prompts supply a `register-evidence` command for the
current run. The command verifies that each supplied path identifies an existing
file within the project and returns an evidence ID for that file. Role result
files contain the IDs. The controller resolves them to paths for manifests and
subsequent roles, and hashes the files when recording provenance in the vault.

Model overrides add `--model` to the relevant role's invocation; see
[CLI options](usage.md#cli-options). Run metadata
captures the CLI version, arguments, prompt, result schema, JSONL events, stderr,
validated final result, duration, exit status, timeout status, and reported usage.
Authentication credentials are not copied into the run files.

Integration tests use a fake CLI process; they verify the
subprocess contract, not actual model reasoning or biological accuracy.

Sources: [noninteractive execution](https://learn.chatgpt.com/docs/non-interactive-mode),
[CLI command reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli).
