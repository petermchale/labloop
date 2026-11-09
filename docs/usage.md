# Running LabLoop

For installation and the demo, see the [README quick start](../README.md#quick-start).
For the crossover workflow and launch command, see the
[case study](../README.md#case-study-crossover-discovery).

## CLI options

Use these options with `python -m labloop.cli run CONFIG`:

| Option | Purpose |
| --- | --- |
| `--model` | Override the model for all roles. |
| `--critic-model`, `--distiller-model` | Override individual roles. |
| `--cycles` | Number of actor → critic → distiller cycles (default 2). |
| `--timeout` | Seconds per role invocation (default 900), not per run. |
| `--effort`, `--codex` | Reasoning effort (default: `medium`) and CLI executable. |
| `--igv` | IGV CLI launcher path; overrides automatic discovery. |
| `--vault`, `--runs` | Knowledge and run directories (defaults `vault`, `runs`). |

The crossover configuration declares `"required_tools": ["igv"]` to check IGV
before starting Codex. `--igv` also enables this check; `--demo` skips it.
The resolved command is printed at startup, recorded in `run.json`, and supplied
to every role.

## Setup troubleshooting

### IGV CLI and snapshots

Install [IGV Desktop](https://igv.org/doc/desktop/DownloadPage/) with Java.
LabLoop finds `igv` or `igv.sh` on PATH, then checks macOS app bundles in
`/Applications` and `~/Applications`. Use `--igv /path/to/igv.sh` to override
discovery; supply an executable path or command name, without arguments.

The check confirms CLI batch support, not successful rendering. Snapshots still
require a GUI session and suitable permissions, and batch mode may display IGV
windows. `igvtools` cannot replace IGV for snapshots.

### Codex runtime blocked by a parent sandbox

A restricted parent process can prevent Codex from writing runtime state in
`~/.codex` or starting its local app-server client. Errors may mention a read-only
database or `Operation not permitted`; the role's stderr log contains details.
This can happen when an agent launches LabLoop from a chat in ChatGPT Desktop or
the Codex desktop app. LabLoop starts a child Codex process, which inherits the
parent launch's restrictions even though each role has its own sandbox setting.

To retry from the chat:

1. Ask the agent: "Retry the experiment with an escalated launch."
2. The agent must request execution approval for the LabLoop command outside the
   parent sandbox. A regular retry inside the sandbox will retain the restriction.
3. Approve that execution request if prompted. If the chat uses **Approve for me**,
   the request may go to automatic approval review instead. To review it yourself,
   select **Ask for approval** in the permissions control below the message box,
   if available, before requesting the retry. Available options depend on app
   version and managed policy; see the official
   [permission modes](https://learn.chatgpt.com/docs/permission-modes) and
   [automatic review](https://learn.chatgpt.com/docs/sandboxing/auto-review) guidance.

Alternatively, run LabLoop from a normal terminal after `codex login`:

```bash
cd /path/to/labloop
.venv/bin/python -m labloop.cli run examples/crossover-discovery.json --cycles 2
```

Changing the child role's `--sandbox` setting cannot lift parent restrictions.
Approval of the parent launch does not guarantee that IGV snapshots will render;
the role still needs access to a graphical desktop session.

## Monitor a run

Run LabLoop in one terminal. In a second terminal in the project directory, find
the manifest and follow the first actor's event log:

```bash
ls -lt runs/*/run.json # run.json records cycle summaries and final state
run_dir="runs/RUN_ID"  # replace with your run directory
tail -n +1 -f "$run_dir/1-actor.jsonl"
```

`-n +1` shows existing events; `-f` follows new ones, including commands, file
changes, tool activity, and messages. This is a raw log, not an interactive chat.
Files appear when their invocation starts. To switch roles, stop `tail` with
Ctrl+C, list the logs, and follow the relevant file:

```bash
ls -lt "$run_dir"/*.jsonl
tail -n +1 -f "$run_dir/1-critic-0.jsonl"
# Later, follow 1-distiller.jsonl or 2-actor.jsonl in the same way.
```

The first number is the cycle; `critic-0` audits the first product. `tail` does not
switch files automatically. Ctrl+C in this monitoring terminal leaves LabLoop
running. For diagnostics, follow the matching `1-actor.stderr.txt` file.
Substitute your `--runs`
directory if you changed it.
