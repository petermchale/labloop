# LabLoop

A scientific learning loop: **actor → critic → distiller → actor → …**.
A Python controller runs each role in a fresh Codex CLI session. Lessons persist
and evolve in a compounding knowledge base; LLM weights stay unchanged
([conceptual background](docs/learning-agent.md)).

Publishing knowledge bases on the Semantic Web extends that feedback loop
within and across labs, which is the idea behind the name **LabLoop**. Lab
members can build on each other's work from a shared record of experiments,
evidence, and open hypotheses. Researchers in other labs can discover those
records, test hypotheses on their own data, and share what they find. Published
knowledge bases can also speed up peer review by helping reviewers trace
claims to their supporting evidence and see which hypotheses are still open (compare
[Paper2Agent](https://arxiv.org/pdf/2509.06917)).

LabLoop represents its knowledge base as RDF using Semantic Web standards.
To share a live vault with agents on the web, run `labloop serve` behind an
HTTPS reverse proxy. Agents can search the latest records or fetch the current
graph as Turtle or JSON-LD and query it with RDF tools.
[Knowledge-base guide for live web access](docs/knowledge-base.md#live-web-access)

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

## Browse a run's evidence tree

After the quick-start demo, start the local server from the repository root
with your virtual environment active.

```bash
python -m labloop.cli serve --vault runs/demo-vault --runs runs
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/) and choose a run and cycle.
Expand a distilled lesson to see the critic observations it cites. Each
observation branches into the critic's evidence files and the actor work product
it reviewed. Expand the work product to find the actor's evidence files.
Click a filename to preview or download it, or choose **Open in VS Code**.

For other runs, pass the same `--vault` and `--runs` paths you used to run
LabLoop. The defaults are `vault` and `runs`.

<a href="docs/evidence-tree.png">
  <img src="docs/evidence-tree.png" width="480" alt="LabLoop evidence tree showing the crossover run on Cycle 2, with the tree guide expanded and the distilled lesson collapsed.">
</a>

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

### How LabLoop audits crossover candidates

LabLoop's **actor → critic → distiller** loop automates the repeated investigation
normally done by a bioinformatician inspecting calls and revising scripts:

1. **Build the evidence.** The actor evaluates three predefined chromosome 22
   intervals using the trio's reads and genotype calls. It reports each candidate
   with evidence and specifies an initial IGV view.
2. **Audit the evidence.** The critic evaluates each reported candidate against
   the scientist's fixed criteria, inspecting alignments and IGV snapshots,
   informative markers, parental origin, and phasing context.
3. **Explain failures.** The distiller turns the audits into evidence-linked,
   testable lessons: for example, a hypothesis that a particular class of calls
   depends on unreliable genotypes, with a suggested test using a genotype filter.
4. **Iterate.** The next actor tests a proposed lesson on the same candidates,
   and the critic reviews the follow-up evidence under the same criteria.

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

### Run the focused crossover example

Install Codex CLI, sign in with `codex login`, and install
[IGV Desktop](https://igv.org/doc/desktop/DownloadPage/). With the environment above activated:

```bash
python -m pip install -e '.[genomics]'
```

The [focused configuration](examples/crossover-focused.json) uses the checked-in
[three-candidate fixture](trio_dev_data/focused/). The
[pedigree file](trio_dev_data/focused/trio.ped) records its data provenance.
To rebuild the fixture, use the preparation script with the chromosome 22 trio
inputs under `trio_dev_data/input/` and an absent `trio_dev_data/focused/` output
directory:

```bash
.venv/bin/python examples/prepare_crossover_fixture.py
```

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
snapshots. If the critic needs a different view, it sends the request to the
LabLoop controller, which runs IGV again and returns the new snapshot to the
critic automatically.

See [IGV setup](docs/usage.md#igv-cli-and-snapshots) for launcher discovery,
custom installations, and snapshot requirements.

LabLoop uses Codex's saved authentication and configured model. Use `--model`
to override it.

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

### Presentation of LabLoop to a genomics audience

https://docs.google.com/presentation/d/1FzK2NiQOgYmQbHzjBBOBRLEBbnM_KE8p-1YNgua9t1U/edit?usp=sharing

## How to summarize a run

Point your agent at a run directory (`runs/RUN_ID/`) and ask for a summary,
slides, or a short report. Have it start with `run.json` and cite the supporting
evidence and vault records for its findings.

We used this approach to produce the [crossover walkthrough](#walk-through-a-completed-run).

## Documentation

This is a prototype.

- [Running guide](docs/usage.md): CLI options and detailed monitoring instructions.
- [Knowledge and feedback](docs/knowledge-base.md): retrieval, RDF export, live vault
  access, scientist corrections, and requests for input.
- [Codex execution](docs/codex-backend.md): role invocation and experiment artifacts.
- [Original development prompt](docs/original-prompt.md): instructions to a coding
  agent to create LabLoop, distinct from its subagents' runtime prompts.
- [Source review](docs/source-review.md): research informing the design.
- [Editable architecture diagram](docs/architecture.mmd).
- [Why LabLoop kept IGV CLI](docs/why-labloop-kept-igv-cli.md).

## Future work

- **Move genomics support out of the core.** Keep the shared role prompts,
  CLI, controller, and base report schemas domain-neutral. Put crossover goals,
  criteria, and scientific instructions in the example configuration. Move IGV
  launcher discovery, request schemas, rendering, and follow-up instructions
  into an optional tool integration enabled by that configuration. The core can
  provide a generic interface for a tool request and its evidence or error, for
  both single-product and batch reviews. When implementing this, test a generic
  task with no integration and a crossover task with IGV enabled. Preserve the
  readability of existing run manifests and vault records. Defer generating new
  crossover evidence until the walkthrough is next updated.
- **Harden criteria:** The actor or critic could technically overwrite criteria in `examples/crossover-focused.json`
because they have write access to the project.
Their prompts prohibit changing inputs, but LabLoop does not enforce that restriction.
We'll want to harden that.
- **Improve knowledge base:** add a transactional database backend for concurrent access,
  indexed retrieval, and immutable record revisions; define whether Markdown
  remains authoritative or becomes an import/export format. Add SHACL validation
  for RDF structure and relationships, richer source and assertion provenance,
  and graph-aware retrieval alongside text search.
- **Publish vaults as Linked Data.** The `labloop.org` domain has already
  been purchased for the project home.
  One could give
  participating labs their own subdomains, e.g.,
  `lab1.labloop.org` and `lab2.labloop.org`. Having a subdomain of `labloop.org`
  is not required, but could facilitate adoption.
  Each lab's instance could publish stable HTTPS identifiers for
  its lessons, observations, and evidence records, such as
  `https://lab1.labloop.org/id/<record-id>`. Looking up a record's URL should
  return a human-readable page or an RDF description with links to related
  records. Agents could follow a lesson's citations to its evidence, and labs
  could link their own findings to records they replicate or challenge or build upon.
  [Linked Data principles](https://www.w3.org/DesignIssues/LinkedData.html)
- **Introduce an automatic curriculum:** optionally use Russell and Norvig's
  [**problem generator**](docs/learning-agent.md#problem-generator)
  and [Voyager's curriculum](https://arxiv.org/abs/2305.16291) to propose and
  prioritize tasks from accumulated knowledge and uncertainties. Currently lessons
  pass directly to the actor, which chooses its next actions.
- **Introduce experiment branches and checkpoint commits:** preserve successful approaches
  and evidence against failed ones, linking branches and exact code versions to
  hypotheses, experiments, observations, and lessons. Retrieve those outcomes before
  new work, inspect diffs, restore versions for reproduction, and revisit failures
  when new evidence warrants it. Capture changes made during a run, beyond the
  starting Git state currently recorded.
