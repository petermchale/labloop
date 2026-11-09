# LabLoop

A scientific learning loop: **actor → critic → distiller → actor → …**.
A Python controller runs each role in a fresh Codex CLI session. Lessons persist
in a knowledge base and inform the next cycle; LLM weights stay unchanged.

The scientist supplies three prompts in a JSON file:

| Prompt | Role |
| --- | --- |
| `goal` | Actor: investigate and produce work products with evidence. |
| `criteria` | Critic: audit each product against the scientist's criteria. |
| `distill` | Distiller: propose lessons and suggested tests from the observations. |

Lessons remain hypotheses for the next actor to test. The critic evaluates the
resulting evidence against the same criteria throughout the experiment.

![LabLoop architecture: actor, critic, and distiller repeat over N cycles, sharing a knowledge base.](docs/architecture.svg)

## Compounding scientific knowledge

LabLoop carries knowledge across cycles and experiments: what was tried, what the evidence
showed, which explanations remain hypotheses, and which approaches failed. The aim
is for each investigation to leave useful context for the next, reducing repeated
searches and rediscovery of dead ends.

An extensible knowledge graph links goals, criteria, experiments, work products,
observations, diagnoses, lessons, and evidence files. Lessons cite the observations
that motivated them and propose tests; the next actor receives active lessons and
retrieved context. New scientific entity types can emerge during an investigation.
Knowledge base records contain the file paths and hashes of experimental evidence,
and Git references identify the code context of an experiment.

Contradictory evidence can retire an assertion while preserving its provenance.
Rejected heuristics leave the active lesson list and cannot silently return as
identical proposals. Scientists can add corrections or domain knowledge through
[explicit feedback](docs/knowledge-base.md#supply-scientist-feedback), including
answers when a role requests input. Recorded lessons remain hypotheses to test.

The current implementation stores Markdown records in `vault/` and derives RDF for
export as Turtle or JSON-LD. These standards support portable knowledge exchange;
shared publication on the web and collaboration between scientists within labs
and between labs remain goals. Retrieval currently uses word matching, and LabLoop
does not yet manage experiment branches or checkpoint commits. See
[knowledge and feedback](docs/knowledge-base.md) and
[planned improvements](docs/design.md#future-work).

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

For a cancer genomics researcher, the familiar problem is separating a biological
signal from artifacts introduced by variant calling, alignment, and inference.
Here the signal is an inherited meiotic crossover in a parent–child trio: a switch
between the two homologs of a parent along the chromosome transmitted to the child.
This example uses germline inheritance, rather than tumor recombination or LOH.

A predicted switch is only a candidate. Incorrect genotypes, misplaced reads, and
phasing errors can mimic a change in inheritance. Repeats and structural variation
can make several nearby markers wrong together, so a cluster of apparent switches
may reflect one difficult region. Conversely, sparse informative markers can leave
a genuine crossover localized only to a broad interval. These challenges are
illustrated by [inGAP-family](https://pmc.ncbi.nlm.nih.gov/articles/PMC9801030/)
and the human-trio study [MRLR](https://pmc.ncbi.nlm.nih.gov/articles/PMC6956785/).

Filtering therefore involves a tradeoff: permissive filters retain artifacts;
strict filters can remove genuine events or the markers needed to resolve them.
The task is to discover **which evidence distinguishes reliable candidates in this
dataset**, then turn that evidence into a reproducible filtering procedure.

| Where to filter | Examples of rules to investigate | What could be lost |
| --- | --- | --- |
| Variants | Genotype quality, depth, allele balance, Mendelian consistency, difficult genomic regions | Informative markers and breakpoint resolution |
| Reads | Mapping/base quality, ambiguous alignments, support at informative markers | Coverage and haplotype connectivity |
| Crossover candidates | Flanking-marker support, parental transmission consistency, phasing context, suspicious clusters | Real events with weak or unusual evidence |

These are possible experiments, not validated LabLoop defaults. Thresholds and
combinations must be tested against the data.

### How LabLoop develops a filter

LabLoop's **actor → critic → distiller** loop automates the repeated investigation
normally done by a bioinformatician inspecting calls and revising scripts:

1. **Discover and revise.** The actor runs pedigree-aware phasing with
   `whatshap phase --ped --recombination-list`, reports individual candidates,
   and develops analysis code. In later cycles it uses prior lessons to choose
   changes, which can include filtering variants or reads before rerunning phasing,
   or filtering the resulting candidates.
2. **Audit the evidence.** The critic evaluates each reported candidate against
   the scientist's fixed criteria, inspecting alignments and IGV snapshots,
   informative markers, parental origin, and phasing context. Coverage or haplotags
   alone do not establish a crossover; missing evidence remains uncertain.
3. **Explain failures.** The distiller turns the audits into evidence-linked,
   testable lessons: for example, a hypothesis that a particular class of calls
   depends on unreliable genotypes, with a suggested test using a genotype filter.
4. **Test the next revision.** The next actor applies and tests proposed lessons;
   the critic audits the new candidates. The knowledge base retains observations,
   candidate lessons, and rejected assertions for reuse across experiments.

For example, if audits implicate low-quality markers in an apparent cluster of
crossovers, the actor could filter those markers and rerun phasing. The follow-up
must examine whether the inheritance pattern is now better supported and what
informative evidence was removed. A smaller call set alone is not success.

The automation is the search for and testing of better analysis rules, guided by
explanatory feedback. It is an agent-directed investigation, with no built-in
numerical optimizer or proven optimal filter. The current example defines
candidate-level audits; it does not yet supply a held-out benchmark or measure
missed events. Establishing improved precision and sensitivity requires an
independent truth set or validation assay, checks on excluded candidates, and
held-out evaluation. IGV review helps diagnose artifacts but is not independent
biological proof.

### Run crossover discovery

For the crossover example, install Codex CLI, sign in with `codex login`, and make
IGV Desktop's launcher available as `igv`. With the environment above activated:

```bash
python -m pip install -e '.[genomics]'
python -m labloop.cli run examples/crossover-discovery.json --cycles 2
```

The example uses the chromosome 22 trio fixture in `trio_dev_data/input/`.
The actor develops analyses, the critic audits each candidate in IGV, and distilled
lessons reach the next actor. LabLoop uses Codex's saved authentication and
configured model; use `--model` to override it.

For your own task, copy an [example configuration](examples/demo.json), edit
`goal`, `criteria`, and `distill`, and run it with a separate `--vault` per project.
Use one writer per vault.

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

## Status and documentation

This is a prototype. Tests verify orchestration with a CLI test double; scientific
learning, a complete live experiment, and visual IGV audits remain unverified. A live
smoke test reached the service but its configured model was rejected; select an
available model with `--model`.

- [Running guide](docs/usage.md): crossover workflow, CLI options, and monitoring.
- [Knowledge and feedback](docs/knowledge-base.md): retrieval, RDF export, scientist
  corrections, and requests for input.
- [Codex execution](docs/codex-backend.md): role invocation and experiment artifacts.
- [Design and limitations](docs/design.md): prompts, permissions, criteria,
  verification, and future work.
- [Original development prompt](docs/original-prompt.md): instructions to a coding
  agent to create LabLoop, distinct from its subagents' runtime prompts.
- [Source review](docs/source-review.md): research informing the design.
- [Editable architecture diagram](docs/architecture.mmd).
