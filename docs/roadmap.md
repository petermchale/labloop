# LabLoop roadmap

1. **Move genomics support out of the core.** Keep shared prompts, the CLI,
   controller, and base report schemas domain-neutral. Put crossover goals,
   criteria, and instructions in the example config, which enables an optional
   IGV integration for launcher discovery, request schemas, rendering, and
   follow-up instructions. Use a common tool interface for requests and their
   evidence or errors. Test a generic task
   without an integration and a crossover task with IGV.
2. **Protect criteria from edits.** Enforce the prompts' ban on changing inputs.
   Project write access currently lets the actor or critic overwrite criteria in
   [`examples/crossover-focused.json`](../examples/crossover-focused.json).
3. **Introduce experiment branches and checkpoint commits.** Build on the
   recorded starting Git state by committing changes during each run. Make
   Git branches correspond to experiments so that success and failures (dead ends) can be tracked.
4. **Validate the RDF graph with SHACL.** Define shapes for required properties
   and relationships, such as requiring a lesson to cite a record of type
   observation.
5. **Share a lab vault across project checkouts.** Let agents on laptops or
   HPC read and write project records through an authenticated API. Use a
   transactional database for concurrent runs, indexed keyword search, and
   immutable revisions. Graph queries trace lessons through observations to
   evidence. Record filepaths on protected HPC environments.
6. **Track provenance for auditing.** Use W3C PROV-O to link each processing
   step to its run, responsible lab member, inputs, and outputs. An auditor could
   see who processed a given file and trace the resulting files to that step. [W3C PROV-O](https://www.w3.org/TR/prov-o/)
7. **Publish vaults as Linked Data.** The project already owns `labloop.org` which could host a project webpage.
   Labs could host subdomains, e.g., `lab1.labloop.org` and `lab2.labloop.org`,
   at which they publish stable HTTPS identifiers for
   lessons, observations, and evidence, e.g., `https://lab1.labloop.org/id/<record-id>`.
   Serve a human-readable page or RDF description at each URL with links to
   related records. Agents could follow citations to evidence, and labs could
   link findings to records they replicate, challenge, or build upon.
   [Linked Data principles](https://www.w3.org/DesignIssues/LinkedData.html)
8. **Introduce an automatic curriculum.** See [Voyager's automatic curriculum](https://arxiv.org/html/2305.16291#S2.SS1) and
   [Russell and Norvig's problem generator](learning-agent.md#problem-generator)
