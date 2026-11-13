# Sources informing LabLoop

Reviewed November 8, 2026. The X thread was supplied as
[`learning-agent.md`](learning-agent.md); videos were reviewed through
transcripts, and the linked diagrams were inspected visually. Paper review focused
on definitions, methods, evaluation, and limitations.

| Source | Implication for LabLoop |
| --- | --- |
| [McHale's thread](https://x.com/peter_t_mchale/status/2116657330754580829), [learning analogy](https://pbs.twimg.com/media/HV_gOuXasAAj9YA.png?name=orig), and [Russell & Norvig figure](https://pbs.twimg.com/media/HWfFCVCaEAAUMmJ.jpg?name=orig) | Repeat **actor → critic → distiller** for N cycles, passing lessons directly to the next actor. Learning changes context and knowledge, not model weights. |
| [Mitchell, Keller & Kedar-Cabelli: explanation-based generalization (1986)](https://link.springer.com/content/pdf/10.1007/BF00116250.pdf) | Use domain knowledge to explain examples and propose general lessons. With imperfect scientific knowledge, retain those lessons as falsifiable hypotheses with provenance. |
| [Tom Mitchell's lecture, 22:30–33:40](https://www.youtube.com/watch?v=8oQQu5e22Sk&t=1349) | Ground critiques in observed outcomes; feed distilled principles back to the actor. Record uncertainty when evidence lacks independent truth labels. |
| [Aparna Dhinakaran: prompt learning](https://www.youtube.com/watch?v=pP_dSNz_EdQ) | Preserve explanatory critiques alongside distilled lessons. Evaluate improvement on held-out tasks using a predeclared success measure. |
| [Copilot learning from outcomes](https://github.blog/changelog/2026-10-28-copilot-automations-now-learn-from-outcomes-and-self-improve/) | Capture scientist corrections and outcome feedback separately from the agents' own assessments. |
| [Voyager](https://arxiv.org/html/2305.16291v2) | Retain useful code and failed experiments for future reuse. Its automatic curriculum, together with Russell and Norvig's problem generator, suggests a possible future research-agenda extension. |
| [Gulwani's Cornell lecture](https://vod.video.cornell.edu/id/1_1mqdu9e5), [summary](https://www.linkedin.com/posts/sumit-gulwani_neurosymbolicai-agenticai-programsynthesis-share-7514045265604079617-WuQV), and [generality spectrum](https://pbs.twimg.com/media/HWnTsrubIAAM5Vh.jpg?name=orig) | Let reusable scientific code emerge during research. Keep stable orchestration in Python and use Codex for investigation, interpretation, and code development. |

These sources motivate the design; they do not validate LabLoop's scientific
performance.

## Machine-readable science

> The clear implication is that machine-readable science should be generated at
> the point of publication, not after the fact.

Booeshaghi, Luebbert, and Pachter (2026). [*Science should be machine-readable*](https://www.biorxiv.org/content/10.64898/2026.01.30.702911v1.full.pdf)
