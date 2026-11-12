# LabLoop

A scientific learning loop: **actor → critic → distiller → actor → …**.
A Python controller runs each role in a fresh Codex CLI session. Lessons persist
and evolve in a compounding knowledge base; LLM weights stay unchanged
([conceptual background](docs/learning-agent.md)).

The scientist supplies three prompts in a JSON file:

| Prompt | Role |
| --- | --- |
| `goal` | Actor: investigate and produce work products with evidence. |
| `criteria` | Critic: audit each product against the scientist's criteria. |
| `distill` | Distiller: propose lessons and suggested tests from the observations. |

Lessons remain hypotheses for the next actor to test. The critic evaluates the
resulting evidence against the same criteria throughout the run.

![LabLoop architecture: actor, critic, and distiller repeat over N cycles, sharing a knowledge base.](docs/architecture.svg)

## Quick start

Requires Python 3.11 or later. Run a demo with synthetic evidence and no model access:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m labloop.cli run examples/demo.json --demo --cycles 2 --vault runs/demo-vault
python -m pytest -q
```

The demo uses a separate vault. `requirements-tested.txt` records tested direct
dependency versions, rather than a complete dependency lockfile.

## Case study: crossover discovery

### Why crossover discovery needs more than a caller

Bioinformaticians often need to separate biological signals from artifacts
introduced by variant calling, alignment, and inference.
Here the signal is an inherited meiotic crossover in a parent–child trio: a switch
between the two homologs of a parent along the chromosome transmitted to the child.

A predicted switch is only a candidate. Incorrect genotypes, misplaced reads, and
phasing errors can mimic a change in inheritance. Repeats and structural variation
can make several nearby markers wrong together, so a cluster of apparent switches
may reflect one difficult region. Conversely, sparse informative markers can leave
a genuine crossover localized only to a broad interval.

Filtering therefore involves a tradeoff: permissive filters retain artifacts;
strict filters can remove genuine events or the markers needed to resolve them.
The task is to discover which evidence distinguishes reliable candidates in the
dataset at hand, then turn that evidence into a reproducible filtering procedure.

| Where to filter | Examples of rules to investigate | What could be lost |
| --- | --- | --- |
| Variants | Genotype quality, depth, allele balance, difficult genomic regions | Informative markers and breakpoint resolution |
| Reads | Mapping/base quality, ambiguous alignments, support at informative markers | Coverage and haplotype connectivity |
| Crossover candidates | Flanking-marker support, phase-block boundaries and phasing confidence, suspicious clusters | Real events with weak or unusual evidence |

### How LabLoop develops a filter for crossovers

LabLoop's **actor → critic → distiller** loop automates the repeated investigation
normally done by a bioinformatician inspecting calls and revising scripts:

1. **Discover and revise.** The actor runs pedigree-aware phasing with
   `whatshap phase --ped --recombination-list`, reports individual candidates,
   and develops analysis code. In later cycles it uses prior lessons to choose
   changes, which can include filtering variants or reads before rerunning phasing,
   or filtering the resulting candidates.
2. **Audit the evidence.** The critic evaluates each reported candidate against
   the scientist's fixed criteria, inspecting alignments and IGV snapshots,
   informative markers, parental origin, and phasing context.
3. **Explain failures.** The distiller turns the audits into evidence-linked,
   testable lessons: for example, a hypothesis that a particular class of calls
   depends on unreliable genotypes, with a suggested test using a genotype filter.
4. **Iterate.** The next iteration of the actor applies and tests proposed lessons;
   the critic audits the new candidates, the distiller learns a lesson, if it exists.

For example, if audits implicate low-quality markers in an apparent cluster of
crossovers, the actor could filter those markers and rerun phasing. The follow-up
must examine whether the inheritance pattern is now better supported and what
informative evidence was removed; A smaller call set alone is not success.

The automation is the search for and testing of better analysis rules, guided by
explanatory feedback in natural language. It is an agent-directed investigation, not a
numerical optimizer. The current example defines
candidate-level audits; it does not yet supply a held-out benchmark.
Establishing improved precision and sensitivity requires an
independent truth set or validation assay.
IGV review helps diagnose artifacts but is not independent
biological proof.

### Run LabLoop to filter crossovers automatically

Install Codex CLI, sign in with `codex login`, and install
[IGV Desktop](https://igv.org/doc/desktop/DownloadPage/). With the environment above activated:

```bash
python -m pip install -e '.[genomics]'
```

Log in to macOS on the Mac where IGV Desktop is installed.

- **Terminal.app:** Open Terminal.app on that Mac, change to the LabLoop
  repository, and run
  `.venv/bin/python -m labloop.cli run examples/crossover-discovery.json --cycles 2`.
- **Codex desktop:** Open this repository in Codex on the same Mac and paste
  the prompt below. Adjust the project path to match your checkout. The
  controller needs an approved launch outside the chat's sandbox so it can
  open IGV.

```text
Run LabLoop's crossover example for two cycles from /Users/petermchale/labloop:
.venv/bin/python -m labloop.cli run examples/crossover-discovery.json --cycles 2

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
snapshots. If the critic needs a different view, it sends the request to the
LabLoop controller, which runs IGV again and returns the new snapshot to the
critic automatically.

See [IGV setup](docs/usage.md#igv-cli-and-snapshots) for launcher discovery,
custom installations, and snapshot requirements.

The example uses the chromosome 22 trio fixture in `trio_dev_data/input/`.
The actor develops analyses, the critic audits each candidate in IGV, and distilled
lessons reach the next iteration of the actor. LabLoop uses Codex's saved authentication and
configured model; use `--model` to override it.

For your own task, copy an [example configuration](examples/demo.json), edit
`goal`, `criteria`, and `distill`, and run it with a separate `--vault` per project.

By default, an experiment creates and populates `vault/` with Markdown knowledge records,
ontology classes, and a shared `context.jsonld`. Pass `--vault PATH` to use another
location; the demo above uses `runs/demo-vault/`.

Experiments save a `run.json` manifest, evidence, and per-role logs under `runs/`.
To follow the first actor in a second terminal:

```bash
tail -n +1 -f runs/RUN_ID/1-actor.jsonl
```

Replace `RUN_ID` with your experiment directory. See the [running guide](docs/usage.md)
for options, log names, and monitoring details. If an experiment stops with `needs_input`,
[record scientist feedback](docs/knowledge-base.md#answer-a-request-for-scientist-input)
and start another experiment with the same vault.

### Walk through a completed run

The [crossover walkthrough](examples/crossover-walkthrough/README.md) follows an
actual run from the critic's audit through a lesson saved in the vault and the
actor's follow-up test.

<!-- To feature a new run, see examples/crossover-walkthrough/MAINTAINING.md. -->

## Status and documentation

This is a prototype.

- [Running guide](docs/usage.md): CLI options and detailed monitoring instructions.
- [Knowledge and feedback](docs/knowledge-base.md): retrieval, RDF export, scientist
  corrections, and requests for input.
- [Codex execution](docs/codex-backend.md): role invocation and experiment artifacts.
- [Original development prompt](docs/original-prompt.md): instructions to a coding
  agent to create LabLoop, distinct from its subagents' runtime prompts.
- [Source review](docs/source-review.md): research informing the design.
- [Editable architecture diagram](docs/architecture.mmd).
- [Future work](docs/future-work.md).
- [IGV CLI and igv-reports comparison](docs/igv-reports-comparison.md): findings from the renderer experiment and the decision to retain IGV CLI.
