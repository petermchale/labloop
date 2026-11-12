# Future work

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
- **Knowledge base:** add a transactional database backend for concurrent access,
  indexed retrieval, and immutable record revisions; define whether Markdown
  remains authoritative or becomes an import/export format. Add SHACL validation
  for RDF structure and relationships, richer source and assertion provenance,
  and graph-aware retrieval alongside text search.
- **Presentations:** produce a slide narrative from knowledge-base records and
  linked plots, IGV snapshots, and other evidence: question → hypotheses →
  experiments → observations → failed approaches → lessons → uncertainties.
  Cite source records and distinguish hypotheses from supported or rejected claims.
- **Research agenda:** optionally use Russell and Norvig's
  [**problem generator**](learning-agent.md#problem-generator)
  and [Voyager's curriculum](https://arxiv.org/abs/2305.16291) to propose and
  prioritize tasks from accumulated knowledge and uncertainties. Currently lessons
  pass directly to the actor, which chooses its next actions.
- **Experiment branches and checkpoint commits:** preserve successful approaches
  and evidence against failed ones, linking branches and exact code versions to
  hypotheses, experiments, observations, and lessons. Retrieve those outcomes before
  new work, inspect diffs, restore versions for reproduction, and revisit failures
  when new evidence warrants it. Capture changes made during a run, beyond the
  starting Git state currently recorded.
