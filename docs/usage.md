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
| `--vault`, `--runs` | Knowledge and run directories (defaults `vault`, `runs`). |

Each candidate gets a separate critic invocation, so runtime depends strongly on
how many candidates the actor produces.

## Monitor a run

Run LabLoop in one terminal. In a second terminal in the project directory, find
the manifest and follow the first actor's event log:

```bash
ls -lt runs/*/run.json
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
`run.json` records cycle summaries and final state. Substitute your `--runs`
directory if you changed it.
