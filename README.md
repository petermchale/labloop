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

> The clear implication is that machine-readable science should be generated at
> the point of publication, not after the fact.

Booeshaghi, Luebbert, and Pachter (2026). [*Science should be machine-readable*](https://www.biorxiv.org/content/10.64898/2026.01.30.702911v1.full.pdf)

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

### Walk through a completed run

Read the [completed crossover run](examples/crossover-walkthrough/README.md)
directly on GitHub without cloning the repository, installing dependencies, or
starting the local evidence tree server. The walkthrough links the critic's
audit, the distilled lesson, and the actor's follow-up test to their evidence.

<!-- To feature a new run, see examples/crossover-walkthrough/MAINTAINING.md. -->

## Case study: crossover discovery

LabLoop audits three candidate meiotic crossovers on chromosome 22 using trio
reads and genotype calls. The [genomics presentation](https://docs.google.com/presentation/d/1FzK2NiQOgYmQbHzjBBOBRLEBbnM_KE8p-1YNgua9t1U/edit?usp=sharing)
explains the crossover problem and follows the audit, distilled lesson, and
follow-up test.

### Run the focused crossover example

Install Codex CLI, sign in with `codex login`, and install
[IGV Desktop](https://igv.org/doc/desktop/DownloadPage/). With the environment above activated:

```bash
python -m pip install -e '.[genomics]'
```

The [focused configuration](examples/crossover-focused.json) uses the checked-in
[three-candidate fixture](trio_dev_data/focused/). See the running guide if you
need to [rebuild the fixture](docs/usage.md#rebuild-the-crossover-fixture).

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
snapshots. See [IGV setup](docs/usage.md#igv-cli-and-snapshots) for launcher
discovery, custom installations, and snapshot requirements.

LabLoop uses Codex's saved authentication and configured model. Use `--model`
to override it. See the [running guide](docs/usage.md#monitor-a-run) to find
the run manifest and follow role logs.

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
- **Share a lab vault across project checkouts.** Add an authenticated API for
  reading and writing knowledge records, with project-level access and support
  for concurrent runs. Lab members could run agents from their own Git checkouts
  on a laptop or on CHPC. With proposed options such as
  `--vault-url https://lab1.labloop.org --project crossover`, the controller
  would retrieve relevant prior findings and save new observations, lessons,
  and evidence references to the shared vault. Records could include the starting
  Git commit and CHPC file paths so collaborators with cluster access can find
  the inputs while large files stay on CHPC.
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
