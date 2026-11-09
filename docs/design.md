# Design and limitations

## Design boundaries

See the [README](../README.md) for the learning loop,
[Codex execution](codex-backend.md) for prompt assembly, tools, sandboxes, and
invocation artifacts, and [knowledge and feedback](knowledge-base.md) for storage,
retrieval, and lesson lifecycle rules.

Packaged role prompts are invocation instructions; Codex retains its own system
instructions. The distiller proposes tests for the actor rather than running
another experiment stage. Codex permissions and account limits apply.

Work products have an identifier, description, evidence paths, and an actor-chosen
`type_name`. Domain concepts such as `CrossoverCandidate` emerge during research.

### Limits on criteria invariance

The controller loads criteria once and supplies the same text to every critic in
that run. Reports cannot replace it. The source configuration remains writable;
LabLoop does not protect it, version criteria snapshots, or verify their hashes.
Edits could therefore affect later runs. Protecting and versioning criteria is
future work.

Unchanged text does not guarantee correct LLM interpretation. Executable criteria
could be enforced by the controller; scientific judgments still require evidence
and may need scientist review.

## Verification and limits

Tests cover two-cycle handoff, knowledge retrieval, ontology extension, file
provenance, scientist feedback, input requests, schema validation, and CLI failures
and timeouts. The [execution guide](codex-backend.md) describes the test double and
its limits.

A live CLI smoke test reached the service, but this account rejected its configured
`gpt-6.1-sol` model. No fallback was selected; use `--model` with an available model.
A complete live run remains unverified. IGV was not installed during development,
so visual crossover audits remain unverified too.

Git branch, commit, and dirty state are recorded at run start; LabLoop does not
manage branches or commits.

For building this prototype, Sol is a reasonable default and Astra is not required
by the design. This is engineering judgment, not a measured model comparison.

## Future work

- **Knowledge base:** add a transactional database backend for concurrent access,
  indexed retrieval, and immutable record revisions; define whether Markdown
  remains authoritative or becomes an import/export format. Add SHACL validation
  for RDF structure and relationships, richer source and assertion provenance,
  and graph-aware retrieval alongside text search. Consider reusing
  [LabWeb](https://github.com/petermchale/labweb) infrastructure while preserving
  LabLoop's experiment, lesson, and retraction rules. These improvements are not
  implemented; structural validation would not establish scientific truth.
- **Presentations:** produce a slide narrative from knowledge-base records and
  linked plots, IGV snapshots, and other evidence: question → hypotheses →
  experiments → observations → failed approaches → lessons → uncertainties.
  Cite source records and distinguish hypotheses from supported or rejected claims.
  This would be a reporting step after a run; no exporter is implemented.
- **Research agenda:** optionally use Russell and Norvig's **problem generator**
  and [Voyager's curriculum](https://arxiv.org/abs/2305.16291) to propose and
  prioritize tasks from accumulated knowledge and uncertainties. Currently lessons
  pass directly to the actor, which chooses its next actions.
- **Experiment branches and checkpoint commits:** preserve successful approaches
  and evidence against failed ones, linking branches and exact code versions to
  hypotheses, experiments, observations, and lessons. Retrieve those outcomes before
  new work, inspect diffs, restore versions for reproduction, and revisit failures
  when new evidence warrants it. Capture changes made during a run, beyond the
  starting Git state currently recorded.
