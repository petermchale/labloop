# Design and limitations

## Roles, prompts, and tools

Each invocation combines [`common.md`](../labloop/prompts/common.md), the relevant
[`actor`](../labloop/prompts/actor.md), [`critic`](../labloop/prompts/critic.md), or
[`distiller`](../labloop/prompts/distiller.md) instructions, and the scientist's
JSON prompt. These packaged Markdown files are invocation instructions; Codex
retains its own system instructions.

Codex supplies file, shell, image, and configured tool access. LabLoop supplies a
`recall` command in each role's context and validates structured reports. Agents
cite results and reusable scripts; the controller records file paths and hashes.
Work products have an identifier, description, evidence paths, and an actor-chosen
`type_name`. Domain concepts such as `CrossoverCandidate` emerge during research.

Actor and critic use Codex's `workspace-write` sandbox; the distiller uses
`read-only` and proposes tests for the actor rather than running another experiment
stage. Prompts direct generated files into the current run directory and prohibit
changing inputs or the vault. These instructions do not narrow the actor's and
critic's write access beyond the project sandbox. Codex permissions and account
limits apply.

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
and timeouts. Integration tests use a Codex CLI test double; they verify
orchestration, not scientific learning.

A live CLI smoke test reached the service, but this account rejected its configured
`gpt-6.1-sol` model. No fallback was selected; use `--model` with an available model.
A complete live run remains unverified. IGV was not installed during development,
so visual crossover audits remain unverified too.

Each run saves a manifest and RDF. Each invocation saves its prompt/context,
schema, CLI version and arguments, JSONL events, stderr, result, duration, exit
status, and usage when available. Git branch, commit, and dirty state are recorded
at run start; LabLoop does not manage branches or commits.

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
