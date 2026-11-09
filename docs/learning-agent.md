---
title: "A correspondence between learning in token space vs parameter space:"
author: "Peter McHale (@peter_t_mchale)"
source: "https://x.com/peter_t_mchale/status/2116657330754580829"
published: 2026-10-31
saved: 2026-11-08
type: thread
tags: [x, thread]
---

# A correspondence between learning in token space vs parameter space:

**Author:** Peter McHale ([@peter_t_mchale](https://x.com/peter_t_mchale))  
**Date:** October 31, 2026 at 04:23 PM  
**Source:** https://x.com/peter_t_mchale/status/2116657330754580829

---

**1/14**

A correspondence between learning in token space vs parameter space:

![Image 1](https://pbs.twimg.com/media/HV_gOuXasAAj9YA.png?name=orig)

---

**2/14**

Deep learning requires big data because the feedback signal is weak (a scalar carries little information) and the system knows nothing prior to learning.

---

**3/14**

Explanation-based learning (EBL) can be achieved with small data because the feedback signal is strong (text can be rich and carry a lot of information), which is due to the fact that the system has a pre-existing model of the world (the LLM).

---

**4/14**

Sources:  
Original EBL (1986): https://link.springer.com/article/10.1007/BF00116250  
Using LLMs to construct explanations (2025): https://youtu.be/8oQQu5e22Sk?si=E9m_oYa-MjMipikJ&t=1349

---

**5/14**

Sources (cont.):   
Prompt learning (2025): https://www.youtube.com/watch?v=pP_dSNz_EdQ

---

**6/14**

Just like learning in parameter space, learning in token space requires contact with reality (the y_i variable).

---

**7/14**

That implies some interface with users that enables the system to determine what worked and what didn't. In this way tacit knowledge locked in the mind of the user flows into structured memory in the AI system.

---

**8/14**

Sources (cont.):   
Github CoPilot Automations https://github.blog/changelog/2026-10-28-copilot-automations-now-learn-from-outcomes-and-self-improve/

---

**9/14**

In Russel & Norvig's textbook (4th global ed 2022), their "performance element" equates to my "actor", their  
"learning element" equates to my "distiller", and   
their "changes" arrow equates to my "update_actor_with_distilled_lesson".

![Image 1](https://pbs.twimg.com/media/HWfFCVCaEAAUMmJ.jpg?name=orig)

---

<a id="problem-generator"></a>

**10/14**

Additionally, they have a "problem generator" element that is very similar to the "automatic curriculum" of Voyager (https://arxiv.org/abs/2305.16291)

---

**11/14**

... which you might call a "research agenda" in the context of scientific research.

---

**12/14**

When the elements of Russell & Norvig's "learning agent" are "neural calls", it becomes an example of Sumit Gulwani's "neurosymbolic script" (19m, https://vod.video.cornell.edu/id/1_1mqdu9e5)  Also see high-level summary at https://www.linkedin.com/posts/sumit-gulwani_neurosymbolicai-agenticai-programsynthesis-share-7514045265604079617-WuQV

---

**13/14**

![Image 1](https://pbs.twimg.com/media/HWnTsrubIAAM5Vh.jpg?name=orig)

---

**14/14**

Following Gulwani, comp. biologists who use coding agents to solve novel problems (Mars rover) could distill their analyses into tools (the Tesla) comprising LLM calls where flexibility is still required and classical symbolic code for speed & determinism.
