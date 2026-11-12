# Replace the featured crossover run

The project README links to this directory's `README.md`. Keep that path and
replace the walkthrough and its supporting files together when a new run gives
readers a clearer example of an audit leading to a follow-up test.

1. Start with `runs/<run-id>/run.json`. Use its cycle entries to match critic
   observations and evidence to the corresponding records in the run's vault.
   Check the next actor's result for what it actually tested and the next critic's
   result for what the evidence supported.
2. Rewrite the [walkthrough](README.md) around that sequence. Explain what the
   scientist asked for, what the critic found, what the vault carried forward,
   and what changed in the follow-up. Say whether the test reused the original
   cases or evaluated independent cases.
3. Update the [vault excerpts](vault-excerpts.md) with the new source run ID,
   observation and lesson IDs, statuses, and proposed test. Add the evidence
   snapshot and follow-up output that support the new story. Give readers
   relative links to the files included here. Check that the selected material
   can be shared in the repository and remove superseded example files.
4. Preview the Markdown, open its links and images, and check the reported
   outcomes against the source run. Commit the replacement as one change so the
   previous version is available in Git history.
