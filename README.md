# LabLoop

A scientific learning loop: **actor → critic → distiller → actor → …**.
A Python controller runs each role in a fresh Codex CLI session. Lessons persist
and evolve in a compounding knowledge base; LLM weights stay unchanged
([conceptual background](docs/learning-agent.md)).
The [LabLoop presentation](https://docs.google.com/presentation/d/1FzK2NiQOgYmQbHzjBBOBRLEBbnM_KE8p-1YNgua9t1U/edit?usp=sharing)
introduces the ideas behind LabLoop and shows the learning loop in action
through a genomics case study on crossover discovery.

LabLoop is a prototype. See the [documentation index](docs/README.md) for guides
and design notes.

![LabLoop architecture: actor, critic, and distiller repeat over N cycles, sharing a knowledge base.](docs/architecture.svg)

The scientist supplies three prompts in a JSON file:

| Prompt | Role |
| --- | --- |
| `goal` | Actor: investigate and produce work products with evidence. |
| `criteria` | Critic: audit each product against the scientist's criteria. |
| `distill` | Distiller: propose lessons and suggested tests from the observations. |

Lessons remain hypotheses for the next actor to test. The critic evaluates the
resulting evidence against the same criteria throughout the run.

## Case study: crossover discovery

LabLoop audited three candidate meiotic crossovers on chromosome 22 using trio
reads and genotype calls. The critic found evidence for one paternal switch
and left two maternal candidates unresolved. The distiller proposed checking
flanking markers, and the next actor wrote a script to test that lesson.
Three child reads corroborated the paternal switch on both sides.

- [Explore the completed run on GitHub](examples/crossover-walkthrough/README.md)
- [Run the focused crossover example locally](docs/usage.md#run-the-focused-crossover-example)

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
Click a filename to preview or download it, or choose **Open in VS Code**.

For other runs, pass the same `--vault` and `--runs` paths you used to run
LabLoop. The defaults are `vault` and `runs`.

<a href="docs/evidence-tree.png">
  <img src="docs/evidence-tree.png" width="550" alt="LabLoop evidence tree showing the crossover run on Cycle 2, with the tree guide expanded and the distilled lesson collapsed.">
</a>

## Sharing knowledge across labs

Publishing knowledge bases on the Semantic Web extends the learning loop
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

<a name="future-work"></a>

## Roadmap

The roadmap starts with individual runs, then covers how labs share and
publish results and use them to plan new experiments.

1. **Move genomics support out of the core.** Keep shared role prompts, the CLI,
   the controller, and base report schemas domain-neutral. Put crossover goals,
   criteria, and scientific instructions in the example configuration, which
   enables an optional IGV integration for launcher discovery, request schemas,
   rendering, and follow-up instructions. Give the core a generic interface for
   tool requests and their evidence or errors in single-product and batch reviews.
   Test a generic task without an integration and a crossover task with IGV.
   Keep existing manifests and vault records readable and defer new crossover
   evidence until the next walkthrough update.
2. **Protect criteria from edits.** Enforce the prompts' ban on changing inputs.
   Project write access currently lets the actor or critic overwrite criteria in
   `examples/crossover-focused.json`.
3. **Introduce experiment branches and checkpoint commits.** Capture changes
   during runs alongside the starting Git state already recorded. Preserve successful approaches
   and evidence against failed ones by linking branches and exact code versions
   to hypotheses, experiments, observations, and lessons. Retrieve outcomes
   before new work, inspect diffs, restore versions to reproduce results, and
   revisit failures when new evidence warrants it.
4. **Validate the RDF graph with SHACL.** Define shapes for required properties
   and relationships, such as requiring a lesson to cite a record of type
   observation.
5. **Share a lab vault across project checkouts.** Add an authenticated read/write
   API with project-level access and a transactional database for concurrent runs,
   indexed retrieval, and immutable record revisions. Use text search to find
   records by keyword and graph queries to follow links from lessons through
   observations to evidence files. Decide whether Markdown is authoritative or
   serves as an import/export format. From their own Git checkouts on laptops or CHPC, lab
   members could run agents with `--vault-url https://lab1.labloop.org --project crossover`
   to retrieve relevant findings and save observations, lessons, and evidence
   references. Records could include the starting Git commit and CHPC paths so
   collaborators with cluster access can find inputs while large files stay on CHPC.
6. **Track provenance for auditing.** Use W3C PROV-O to link each processing
   step to its run, responsible lab member, inputs, and outputs. An auditor could
   see who processed a given file and trace the resulting files to that step.
   Record the sources supporting each research assertion.
   [W3C PROV-O](https://www.w3.org/TR/prov-o/)
7. **Publish vaults as Linked Data.** The project already owns `labloop.org` for
   its home. Optional subdomains such as `lab1.labloop.org` and `lab2.labloop.org`
   could ease adoption. Each lab could publish stable HTTPS identifiers for
   lessons, observations, and evidence, such as `https://lab1.labloop.org/id/<record-id>`.
   Serve a human-readable page or RDF description at each URL with links to
   related records. Agents could follow citations to evidence, and labs could
   link findings to records they replicate, challenge, or build upon.
   [Linked Data principles](https://www.w3.org/DesignIssues/LinkedData.html)
8. **Introduce an automatic curriculum.** Optionally use Russell and Norvig's
   [problem generator](docs/learning-agent.md#problem-generator) and
   [Voyager's curriculum](https://arxiv.org/abs/2305.16291) to propose and
   prioritize tasks from accumulated knowledge and uncertainties. Today the
   actor receives lessons directly and chooses its next actions.
