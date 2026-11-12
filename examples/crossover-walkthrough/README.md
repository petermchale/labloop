# Reassessing three meiotic crossover candidates with read-linked flanking markers

LabLoop used the [focused configuration](../crossover-focused.json) to review
three candidate crossovers on chromosome 22 over two cycles. The source links
below require the local `runs/` and `vault/` directories, which Git ignores.
[Run manifest](../../runs/45e83829807b4e04b831c48a8359d7f1/run.json)

## Cycle 1 · Audit the candidates

The critic found read evidence for one paternal switch and left two maternal
candidates unresolved. At one maternal interval, an endpoint genotype had low
confidence, and both parents' reads carried the child's four-marker pattern.
The critic requested a zoomed IGV view to inspect local alignment gaps and mismatches.
[Critic observation](../../vault/Records/07e889d3f722427c81c21fe482365c69.md) ·
[IGV snapshot](../../runs/45e83829807b4e04b831c48a8359d7f1/igv-p90h8th3/view-2.png)

## Between cycles · Store a testable lesson

The distiller proposed ranking candidates using child reads that link the
endpoints to confidently phased markers on both sides. The vault record links
the proposal to the three audits and describes a test on independent candidates.
[Distilled lesson](../../vault/Records/heuristic_8d6779429db1e79ea69cd632.md)

## Cycle 2 · Apply the lesson and audit again

The next actor searched within 15 kb of each interval and checked marker phase
against parental reads. Three child reads linked the paternal candidate to
corroborating markers on both sides. Both maternal calls remained uncertain,
and the review order stayed the same. The follow-up reused the original three
cases. Measuring detection accuracy requires independently adjudicated cases.
[Second-cycle critic observation](../../vault/Records/81659e3fa5f34c719e2e5984382fb6a6.md) ·
[Actor's comparison output](../../runs/45e83829807b4e04b831c48a8359d7f1/trio_flank_comparison.json)
