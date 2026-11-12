# Running LabLoop

For installation and the demo, see the [README quick start](../README.md#quick-start).
For the crossover workflow, see the [case study](../README.md#case-study-crossover-discovery).
Use the [Codex launch prompt](../README.md#run-the-focused-crossover-example)
for execution and permissions.

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

The crossover configuration enables `"igv_snapshots": true` to check IGV
before starting Codex and render snapshots from the controller. A configuration
can also declare `"required_tools": ["igv"]` to check IGV and supply the launcher
to the roles for direct use. `--igv` also enables launcher discovery, and
`--demo` skips IGV. The launcher is printed at startup and recorded in `run.json`.

Set `"critic_batch_size": 10` in a configuration to review up to ten work
products per Codex invocation, with one verdict per product. The default is one.
The focused crossover example uses the checked-in
[three-candidate fixture](../trio_dev_data/focused/). It keeps trio reads and
variants overlapping each candidate and 15 kb of flanking sequence on either
side. The chr22 FASTA retains the original coordinate system.

```bash
.venv/bin/python -m labloop.cli run examples/crossover-focused.json --cycles 2 \
  --runs runs/focused --vault runs/focused-vault
```

## Setup troubleshooting

### IGV CLI and snapshots

Install [IGV Desktop](https://igv.org/doc/desktop/DownloadPage/) with Java.
LabLoop finds `igv` or `igv.sh` on PATH, then checks macOS app bundles in
`/Applications` and `~/Applications`. Use `--igv /path/to/igv.sh` to override
discovery; supply an executable path or command name, without arguments.

The check confirms CLI batch support, not successful rendering. Snapshots still
require a GUI session and suitable permissions, and batch mode may display IGV
windows. `igvtools` cannot replace IGV for snapshots.

With controller rendering enabled on macOS, use Terminal.app while signed in
to the Mac desktop, or use an approved Codex desktop launch outside the chat's
sandbox. See the [README launch instructions](../README.md#run-the-focused-crossover-example).

The controller batches the actor's initial views before starting the critics.
In single-product mode the critic can ask for up to four additional views per
pass, with two follow-up passes. In batched mode the controller collects up to
four additional views per product into one IGV render and one follow-up pass
for the batch. The critic can adjust coordinates on the same chromosome, select
among the actor's BAM or VCF.gz tracks, and change read sorting, grouping, and coloring.
The run manifest records PNG paths or rendering errors, alongside paths to
the batch and its log when IGV was invoked.

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

The first number is the cycle. `critic-0` audits the first product, and
`critic-batch-0` audits the first batch. Additional IGV review passes add
`-view-1` or `-view-2` to the trace name.
`tail` follows one file at a time. Ctrl+C in this monitoring terminal leaves LabLoop
running. For diagnostics, follow the matching `1-actor.stderr.txt` file.
Substitute your `--runs`
directory if you changed it.
