# LabLoop

LabLoop turns what agents learn into reusable code and lessons: candidate facts
(hypotheses) that later analyses test.

You define a research goal and the criteria for judging the evidence. LabLoop
runs a loop: it performs an analysis, checks the results against your criteria,
and preserves code, evidence, and lessons with proposed follow-up tests. The next
round builds on that code and tests the lessons in a new analysis.

<a name="case-study-crossover-discovery"></a>

## Case study: meiotic crossover discovery in trios

The [LabLoop presentation](https://docs.google.com/presentation/d/1FzK2NiQOgYmQbHzjBBOBRLEBbnM_KE8p-1YNgua9t1U/edit?usp=sharing)
introduces the ideas behind LabLoop and shows the learning loop in action
through a genomics case study on crossover discovery.

LabLoop audited three candidate meiotic crossovers on chromosome 22 using trio
reads and genotype calls. The critic found evidence for one paternal switch
and left two maternal candidates unresolved. The distiller proposed checking
flanking markers, and the next actor turned that lesson into
[a reusable analysis script](runs/45e83829807b4e04b831c48a8359d7f1/trio_flank_linkage.py).
Three child reads corroborated the paternal switch on both sides. The run left
both executable code and a testable lesson for later analyses.

- [Explore the completed run on GitHub](examples/crossover-walkthrough/README.md)
- [Run the focused crossover example locally](docs/usage.md#run-the-focused-crossover-example)

## How LabLoop works

A scientific learning loop: **actor → critic → distiller → actor → …**.
A Python controller runs each role in a fresh Codex CLI session. Reusable code
persists as experiment artifacts, linked to evidence and lessons in a compounding
knowledge base; LLM weights stay unchanged
([conceptual background](docs/learning-agent.md)).

![LabLoop architecture: actor, critic, and distiller repeat over N cycles, sharing a knowledge base.](docs/architecture.svg)

The scientist supplies three prompts in a JSON file:

| Prompt | Role |
| --- | --- |
| `goal` | Actor: investigate and produce work products, including reusable code, with evidence. |
| `criteria` | Critic: audit each product against the scientist's criteria. |
| `distill` | Distiller: propose lessons and suggested tests from the observations. |

Lessons are candidate facts (hypotheses) for the next actor to test.
Code makes analysis methods reusable and the proposed tests executable. The
critic evaluates the resulting evidence against the same criteria throughout
the run.

LabLoop is a prototype. See the [documentation index](docs/README.md) for guides
and design notes.

## Quick start

Requires Python 3.11 or later. Run a demo with synthetic evidence and no model access:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m labloop.cli run examples/demo.json --demo --cycles 2 --vault runs/demo-vault
python -m pytest -q
```

After the quick-start demo, start the local server from the repository root
with your virtual environment active.

```bash
python -m labloop.cli serve --vault runs/demo-vault --runs runs
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/) and choose a run and cycle.
Expand a distilled lesson to see the critic observations it cites. Each
observation branches into the critic's evidence files and the actor work product
it reviewed. Expand the work product to find the actor's evidence files.
Follow these links to inspect the code behind an analysis as well as its results.
Click a filename to preview or download it, or choose **Open in VS Code**.

The viewer looks like this, shown here with Cycle 2 of the crossover run.

<a href="docs/evidence-tree.png">
  <img src="docs/evidence-tree.png" width="550" alt="LabLoop evidence tree showing the crossover run on Cycle 2, with the tree guide expanded and the distilled lesson collapsed.">
</a>

For other runs, pass the same `--vault` and `--runs` paths you used to run
LabLoop. The defaults are `vault` and `runs`.

## GraphRAG and the evidence graph

LabLoop uses retrieval-augmented generation (RAG) to bring prior findings into
each new analysis. Its knowledge base stores structured Markdown records, links
them to code and other evidence files, and represents their relationships as an
RDF graph.

The diagram follows one of the crossover lesson's three observation links and
shows how the lesson guides the next analysis.

```mermaid
---
config:
  themeVariables:
    fontSize: 13px
  flowchart:
    wrappingWidth: 320
    nodeSpacing: 35
    rankSpacing: 35
---
flowchart TD
    Run["Cycle 1 · Actor proposes candidates → Critic audits → Distiller proposes a test"]

    subgraph Vault["Vault · Records with typed links"]
        Lesson["Lesson · Check phased markers on both sides"]
        Obs["Critic observation · Maternal switch unresolved"]
        Product["Actor work product · Crossover candidate"]
        CriticFile["Critic evidence · IGV snapshot"]
        ActorFile["Actor evidence · Candidate JSON"]
        Code["Reusable code · Flanking-marker analysis script"]

        Lesson -->|because| Obs
        Obs -->|because| Product
        Obs -->|files| CriticFile
        Product -->|files| ActorFile
        Product -->|files| Code
    end

    Run -->|Controller saves linked records| Vault
    Vault -->|Project records to RDF| Graph["Graph queries and evidence inspection"]
    Vault -->|Keyword recall + non-rejected lessons| Next["Cycle 2 · Actor tests flanking-marker support"]
```

Each cycle retrieves records matching the research goal and gives the actor
non-rejected lessons as hypotheses to test. Agents can search further with
`recall --research-only`, which excludes archived task instructions. Retrieval
ranks records by keyword overlap and recency.
Linked code artifacts let agents inspect and build on earlier analysis methods
while testing the lessons those analyses produced.

## Evaluation and validation

LabLoop evaluates evidence in every cycle against the scientist's fixed
`criteria`. Its existing evaluation systems are:

| System | What it does |
| --- | --- |
| [Critic](labloop/prompts/critic.md) | Audits each product's evidence and returns `supported`, `contradicted`, or `uncertain`, with a diagnosis. Optional IGV views support visual review. |
| [Pydantic schemas](labloop/report_schemas.py) | Validate reports, verdicts, batch keys and counts, and allowed observation citations. |
| [Python controller](labloop/loop.py) | Requires evidence files, rejects duplicate products and invented citations, and permits retractions only with contradictory observations. |
| [Scientist feedback](docs/knowledge-base.md#supply-scientist-feedback) | Carries human assessments into later analyses and retires eligible contradicted assertions. |
| [Audit records](docs/codex-backend.md) | Preserve prompts, results, traces, usage, file hashes, and links from lessons to evidence for inspection. |
| [Pytest suite](tests/) | Checks orchestration, validation, feedback, RDF roundtrips, and integrations using fixtures. |

Pydantic runtime validation and explicit Python logic enforce these structural
and evidence checks without an RDF validator. Python type annotations alone
do not enforce them at runtime.

Valid reports and file references do not prove scientific correctness. Critic
judgments still need expert review and independent validation; the demo and
software tests do not measure model quality. LabLoop has no independent-trial
benchmark, systematic critic calibration, or production quality gates and drift
monitoring yet.

For the broader evaluation practices, see
[Anthropic's agent-evals guide](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)
and [AWS's AgentCore framework](https://aws.amazon.com/blogs/machine-learning/building-trust-in-ai-agents-a-production-ready-evaluation-framework-with-amazon-bedrock-agentcore/).

## Sharing knowledge across labs

Publishing knowledge bases on the Semantic Web would extend the learning loop
within and across labs. Members of a given lab
could build on each other's reusable code and lessons from a shared record of
experiments, evidence, and open hypotheses. Researchers across a network of labs
could discover those records, adapt linked code, use data from their own labs to
test hypotheses shared by other labs, and share their results. Published knowledge bases could also
speed up peer review by helping reviewers trace claims to their supporting
evidence and see which hypotheses are still open.

Some of these thoughts are not new.
[Paper2Agent](https://arxiv.org/pdf/2509.06917) serves research papers over MCP to AI agents.
[Booeshaghi, Luebbert, and Pachter](https://www.biorxiv.org/content/10.64898/2026.01.30.702911v1.full.pdf) went further when they argued that “machine-readable science should
be generated at the point of publication, not after the fact.” We agree.

The network could be organized like Mastodon. A lab could run its own LabLoop
server, much as a community can run its own Mastodon server. Just as a Mastodon
client connects to a home server and shows posts from other servers, a LabLoop
client could connect to a researcher's lab server and let them explore records
published by other labs.

The proposed Linked Data publication model would give each published lesson,
observation, and evidence record a stable HTTPS URL, such as
`https://lab1.labloop.org/id/<record-id>`. The URL would serve a readable page
or an RDF description with links to related records. Using coding agents,
another lab could follow a lesson to its supporting code and evidence, reuse or
adapt the analysis, and link its own replication results back to the original
record.

For example, another lab could use LabLoop's RDF vocabulary and a standard tool
such as RDFLib to follow links from lessons to observations and evidence files,
without installing LabLoop. Reading the Markdown vault directly would instead
require custom code to parse its YAML metadata and reconstruct those links,
coupling that code to LabLoop's storage conventions.

The RDF vocabulary describes record types and relationships; it does not yet
express all the validation rules in LabLoop's Pydantic models and Python
controller.

To share a live vault with agents on the web, run `labloop serve` behind an
HTTPS reverse proxy. Agents can search the latest records or fetch the current
graph as Turtle or JSON-LD and query it with RDF tools.
[Knowledge-base guide for live web access](docs/knowledge-base.md#live-web-access)

<a name="future-work"></a>

<a name="roadmap"></a>

In addition to the goal of publishing vaults as Linked Data, the [roadmap](docs/roadmap.md) also covers checkpoint commits for
reproducing experiments and authenticated access to shared lab vaults.
