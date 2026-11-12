<!-- Archived design prompt; describes the original intent, not implementation status. -->

Source: [Original development prompt to create LabLoop](https://docs.google.com/document/d/1b07T79EFHmcI7X3DAfnaBCRq3122i9MDHtsK7qyyJ3I/edit?usp=sharing).
This prompt instructed a coding agent to design and implement the LabLoop
prototype. It is not a runtime prompt for LabLoop's actor, critic, or distiller;
the subagent prompts quoted within it illustrate the intended case study.

The development prompt below is preserved from the document's Markdown export. See the
[main README](../README.md) for current behavior and
[future work](../README.md#future-work) for planned improvements.

---

# LabLoop: a learning agent for scientific research

## High-level architecture

LabLoop is an agent that comprises three LLM-based subagents: an actor, a critic, and a distiller, following the learning agent architecture of Russell and Norvig, and Tom Mitchell (both referenced at [https\://x.com/peter\_t\_mchale/status/2116657330754580829](https://x.com/peter_t_mchale/status/2116657330754580829); read all replies to the post). The user supplies domain knowledge, primarily at the start, but occasionally in response to requests from the agent, enabling the agent to automate the more routine aspects of the scientist's job. The domain knowledge is split into a goal (initial prompt for actor), evaluation criteria (“truth” that the critic compares against what the actor actually produces), and how to learn general lessons (prompt for the distiller). 

The agent, or one or more of the subagents, are connected to a compounding knowledge base server based on Tony Seale’s vault-ld ([https\://github.com/The-Knowledge-Graph-Guys/vault-ld](https://github.com/The-Knowledge-Graph-Guys/vault-ld) ) that stores facts, and distillations of those facts, pruning facts that new evidence reject, accelerating the agents work by circumventing the need to grep folders, etc. Since this is a learning agent for scientific research, the ontology should start with types for hypotheses, git elements (commits, experiment-specific branches, etc), experiments, observations, diagnoses, distilled lessons/claims/heuristics, file paths, etc., but the learning agent should be able to update/generalize the ontology as necessary. Using semantic-web standards enables vendor-neutral publishing on the web, accelerating collaboration, reproduction and peer review. 

## Case study: finding reliable genomic crossovers

To better define LabLoop, consider an approach for discovering a set of reliable genomic crossovers in a trio, formulated as prompts for the three subagents: 

Actor: “Your goal is to compute a reliable set of crossovers in the chr22 fixture (trio\_dev\_data/) using ‘whatshap –ped \--recombination-list’. You may need to run ‘whatshap unphase’ to avoid mixed phasing. Decide whether you also need to run ‘whatshap stats’ and whether you need to ‘haplotag’ the bams.”  

Critic: “Critique crossover calls by auditing the corresponding read alignments using IGV’s CLI, e.g., by asking whether the spanning alignments support the predicted crossover” 

Distiller: “Given these crossover calls, distill a heuristic based on failure modes that you hypothesize, e.g., ‘crossovers at unreliable variants are probably false’ or ‘crossovers located close to one another are probably false’, etc.” 

When the distiller proposes a new heuristic, Labloop updates the actor’s prompt with the new heuristic, so that the actor does things like first filtering the input variants on genotype quality before running whatshap, or filtering predicted crossovers that lie in genomic “exclude” regions, etc. The cycle then repeats with the output of the actor being fed into the critic, crossover by crossover, and then onto the distiller, which updates the actor. Hypothesized failure modes, observations made after testing those hypotheses, distilled heuristics, together with pointers to associated git branches and commit hashes stored in the knowledge base by one or more sub-agents, which also continually query the knowledge base to build on previous findings and avoid duplicated work and the rediscover of dead ends (e.g., a git branch that ended in failure). 

## Final thought

Develop the simplest codebase you can to prototype LabLoop along these lines. Assess whether GPT-6.1 Sol is sufficient, or whether GPT-6 Astra is required.
