# Running LabLoop

For installation and the demo, see the [README quick start](../README.md#quick-start).
For the crossover workflow, see the [case study](../README.md#case-study-meiotic-crossover-discovery-in-trios)
or [run the focused example](#run-the-focused-crossover-example).

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

## Run the focused crossover example

Install Codex CLI, sign in with `codex login`, and install
[IGV Desktop](https://igv.org/doc/desktop/DownloadPage/). Activate the virtual
environment from the [quick start](../README.md#quick-start), then install the
genomics dependencies.

```bash
python -m pip install -e '.[genomics]'
```

The [focused configuration](../examples/crossover-focused.json) uses the checked-in
[three-candidate fixture](../trio_dev_data/focused/). It keeps trio reads and
variants overlapping each candidate and 15 kb of flanking sequence on either
side. The chr22 FASTA retains the original coordinate system. See how to
[rebuild the fixture](#rebuild-the-crossover-fixture) if needed.

Log in to macOS on the Mac where IGV Desktop is installed.

- **Terminal.app:** Open Terminal.app on that Mac, change to the LabLoop
  repository, and run
  `.venv/bin/python -m labloop.cli run examples/crossover-focused.json --cycles 2`.
- **Codex desktop:** Open this repository in Codex on the same Mac and paste
  the prompt below. Adjust the project path to match your checkout. The
  controller needs an approved launch outside the chat's sandbox so it can
  open IGV.

```text
Run LabLoop's focused crossover example for two cycles from /Users/petermchale/labloop:
.venv/bin/python -m labloop.cli run examples/crossover-focused.json --cycles 2

I explicitly authorize an escalated launch of this command outside the chat's
sandbox, use of my saved Codex authentication, and child Codex model sessions
that may transmit sensitive trio/genomic data to the configured model service.
Request escalation through the execution tool's approval mechanism. Keep
LabLoop's existing per-role sandbox settings. If approval is denied, report
the reason instead of bypassing it. Allow IGV batch execution for alignment
snapshots. Monitor this run to completion or a failure/needs_input state,
then report its manifest, results, and any remaining permission restrictions.
Do not launch another experiment against the same vault concurrently.
```

The Codex launch is subject to automatic approval review, organization policy,
and macOS GUI access controls. IGV may open windows while the controller renders
snapshots. See [IGV setup](#igv-cli-and-snapshots) for launcher
discovery, custom installations, and snapshot requirements.

LabLoop uses Codex's saved authentication and configured model. Use `--model`
to override it. See the [running guide](#monitor-a-run) to find
the run manifest and follow role logs.

To keep this experiment's artifacts and vault separate from the defaults, use
this command.

```bash
.venv/bin/python -m labloop.cli run examples/crossover-focused.json --cycles 2 \
  --runs runs/focused --vault runs/focused-vault
```

### Rebuild the crossover fixture

The [pedigree file](../trio_dev_data/focused/trio.ped) records its data provenance.
To rebuild the fixture, use the preparation script with the chromosome 22 trio
inputs under `trio_dev_data/input/` and an absent `trio_dev_data/focused/` output
directory:

```bash
.venv/bin/python examples/prepare_crossover_fixture.py
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
sandbox. See the [launch instructions](#run-the-focused-crossover-example).

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
