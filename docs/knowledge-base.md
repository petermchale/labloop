# Knowledge base and scientist feedback

Markdown notes with YAML-LD frontmatter are authoritative; `context.jsonld` maps
them into RDF using RDFLib. The design follows
[Vault-LD](https://github.com/The-Knowledge-Graph-Guys/vault-ld) without claiming
full roundtrip conformance. Use a separate vault per project and one writer.

The controller writes records; agents read through `recall`. Retrieval uses lexical
matching over structured records. RDF is available for graph queries through
RDFLib; there is no vector index or automatic inference engine. Optional HTTP
access is read-only, bound to localhost, and is not an MCP server:

```bash
python -m labloop.cli recall 'mapping ambiguity'
python -m labloop.cli export --format turtle
python -m labloop.cli serve --port 8765
# GET http://127.0.0.1:8765/recall?q=mapping
# GET http://127.0.0.1:8765/graph.ttl
# GET http://127.0.0.1:8765/graph.jsonld
```

Each role receives its current task instructions explicitly: the actor receives
the goal, the critic receives the criteria, and the distiller receives the distill
prompt. Retrieved knowledge supplies prior findings to help with those tasks.
Previously, retrieval also returned archived task prompts. In the crossover run,
the actor received criteria directing the critic to audit candidates in IGV.
Including those instructions alongside research findings blurred the roles: the
actor could interpret the critic's audit as part of its own assignment. It performed
audit work and then requested GUI access, stopping the loop before the critic ran.
The retrieved criteria likely contributed to this behavior, although the broad
goal of producing reliable candidates also allowed substantial investigation.

The controller's injected knowledge and the recall command supplied to agents now
use research-only retrieval (`recall --research-only`). This excludes archived
`Goal`, `Criteria`, and `DistillInstructions` records before ranking and limiting
results, keeping other roles' instructions and obsolete assignments out of the
research context and leaving room for relevant findings. All three prompts remain
in the vault for provenance, are linked from each experiment's `because` references,
and are available through ordinary recall.

The actor should return its candidates and supporting evidence for the critic to
audit. For example, if the actor can produce candidates but cannot launch IGV for
the critic's visual review, it should describe that limitation in its report and
return the products with `needs_input: null`. Setting `needs_input` would stop the
controller before it invokes the critic. The critic can attempt the review and
request help if it is blocked. The actor should still set `needs_input` when a
missing tool, input, or scientific decision prevents its own work.

On first opening a vault, LabLoop initializes classes for goals, criteria, distill
instructions, experiments, work products, hypotheses, observations, diagnoses, claims, heuristics,
file paths, Git references, and scientist feedback. Learning can add classes;
new predicates require updating `context.jsonld`. Replace the example namespace
before public publication.

Lessons remain **hypotheses to test**, with observation references and suggested
tests. Retractions require current contradictory observations. Rejected assertions
remain retrievable with their provenance, but rejected heuristics leave the actor's
lesson list and cannot silently reappear as identical proposals.

### Supply scientist feedback

Save a JSON file targeting a known record ID from `recall` or a run's graph.
For feedback on an entire experiment, use its ID from `run.json` → `cycles` →
`experiment`. For example, save this as `scientist-feedback.json`:

```json
{
  "target": "REPLACE_WITH_EXPERIMENT_ID",
  "status": "context",
  "text": "Hypothesis to test: closely spaced crossover candidates arise from unreliable genotypes. Compare results before and after genotype-quality filtering and audit the read evidence. Treat this as untested.",
  "evidence": []
}
```

Statuses are `context`, `supported`, `contradicted`, or `uncertain`. Evidence paths
must identify existing project-relative files; use `[]` when none apply.
Contradictory feedback retires a targeted research assertion when eligible;
`context` neither validates a hypothesis nor retires a claim.

Record scientist feedback and start a new run with the same vault:

```bash
python -m labloop.cli feedback scientist-feedback.json --vault vault
python -m labloop.cli run examples/crossover-focused.json --cycles 2 --vault vault
```

The latest 30 scientist feedback records are automatically supplied; older ones
remain retrievable. Feedback adds context without guaranteeing priority. To make a
new hypothesis the explicit task, copy `examples/crossover-focused.json`, revise its `goal`, and run
that configuration with the same vault. Keep the criteria unless the scientific
question requires different ones.

### Answer a request for scientist input

Any role can return a question in `needs_input`. The controller saves it, stops,
and prints the manifest path, state, and question, for example:

```text
/path/to/labloop/runs/RUN_ID/run.json
needs_input
Which independent dataset should I use to validate these crossover candidates?
```

Use the scientist-feedback workflow above: target the last experiment in the
printed manifest, set `status` to `context`, and put your answer in `text`.
If supplying data, cite its existing path in `evidence`. Start another run using
the same vault. It starts from the actor with a new cycle count; it does not resume
the interrupted role.

LabLoop does not wait for terminal input or consume chat replies. In a supervising
Codex chat, you can ask the assistant to record your answer and launch the next run.
