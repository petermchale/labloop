# Vault excerpts

These records are from run `45e83829807b4e04b831c48a8359d7f1`. The excerpts
retain the original record text, IDs, and statuses. Headings and links identify
the records and the evidence included in this walkthrough.

## Cycle 1 critic observations

### Paternal candidate at 20,959,352–20,961,970

Record `324f470874c44773af835ea84c8a74a7` · `supported`

> The trio reads support a paternal HP1-to-HP2 switch in NA12879 within NA12877
> phase set 19256651. Eight eligible child reads carry G/G across the
> endpoints, four on each strand. Six also carry the paternal G allele at the
> upstream Mendelian anchor at 20,955,483. The father has 17 G/A reads on HP1
> and 17 A/G reads on HP2, and neither parent has an eligible G/G spanning
> read. Two child reads link the G/G endpoint pair to paternal HP2 alleles at
> both 20,968,297 and 20,968,600. The phase-grouped IGV view shows child HP1
> alignments extending across the candidate interval into the downstream marker
> region. The audited linkage supports a crossover within the interval at
> marker resolution.

### Maternal candidate at 21,165,471–21,165,499

Record `07e889d3f722427c81c21fe482365c69` · `uncertain`

> The VCF suggests maternal HP1-to-HP2 across the endpoints. The right endpoint
> has maternal GQ 3, and the marker at 21,166,076 implies HP1 again. All 26
> eligible child reads and all 68 eligible paternal reads spanning both
> endpoints carry C/A, as do 11 maternal reads across both HP tags. Including
> the upstream maternal-origin anchor and downstream marker still leaves the
> same four-site pattern in eight maternal-origin child reads, five maternal
> reads across both HP tags, and 20 paternal reads. The zoomed, phase-grouped
> IGV view shows mismatches and alignment gaps in the local maternal pileup.
> The read patterns leave the switch unresolved. Confidently phased maternal
> markers linked on child reads on both sides would help distinguish a switch.

[Phase-grouped IGV snapshot](maternal-candidate-igv.png)

### Maternal candidate at 21,291,740–21,291,798

Record `887624952fa64d96b69887c4319e2c00` · `uncertain`

> The maternal left endpoint is unphased at GQ 9, and the VCF implies maternal
> HP2 at both flanking markers. The three eligible maternal-origin child reads
> spanning both endpoints and both flanks carry C/C/A/A, a pattern also present
> in four maternal HP1-tagged reads and one paternal read. Three other maternal
> HP1-tagged reads carry T at the left endpoint, so that tag contains both C
> and T there. The phase-grouped IGV view shows alignments spanning the flanks
> in the child and both parents. The audited bases leave the maternal switch
> unresolved. Resolving the maternal phase at the left endpoint and linking it
> to additional informative markers on child reads would help.

## Distilled lesson

Record `heuristic_8d6779429db1e79ea69cd632` · `proposed`

The lesson's `because` field references all three [cycle 1 observations](#cycle-1-critic-observations).

> Test whether ranking crossover candidates by read-linked support from
> additional informative markers improves on ranking by endpoint evidence
> alone. For each candidate, look on both sides for confidently phased markers
> in the same phase set of the transmitting parent. Up-rank a switch when child
> reads assigned to that parent link the candidate to markers that corroborate
> the inferred haplotype on each side and the parental reads support the marker
> phase. In the supported paternal case, child reads linked the endpoint
> pattern to an upstream paternal-origin anchor, and two child reads linked
> that same endpoint pattern to two downstream HP2 markers beyond the original
> window. In both unresolved maternal cases, the longer child patterns also
> occurred in parental reads, and a low-quality or unphased endpoint weakened
> the haplotype assignment. Sparse coverage or a lack of informative markers
> can leave a genuine switch unresolved, so retain such candidates for review.
> These three reviews motivate the hypothesis but do not establish a gain in
> detection accuracy.

**Proposed test**

> Reuse collect_markers and read_observations from trio_baseline.py and
> spanning_counts from critic_trio_audit.py. Replace the audit's hand-selected
> marker panels with an automatic search using a prespecified window and
> marker-quality criteria. Compare endpoint-only and augmented rankings on
> held-out trio candidates with independently adjudicated switches and
> artifacts. At a fixed review budget, test whether the augmented ranking
> recovers more confirmed switches, and report how often insufficient
> informative read coverage leaves candidates unresolved. Use the three
> reviewed loci as regression cases and keep the two maternal cases labeled
> unresolved.

## Cycle 2 critic observation

### Paternal candidate after the automated marker search

Record `81659e3fa5f34c719e2e5984382fb6a6` · `supported`

> The trio reads support a paternal HP1-to-HP2 switch in NA12879 within NA12877
> phase set 19256651. Eight child reads assigned to paternal origin carry G/G
> across the endpoints, four on each strand. Six directly carry the paternal
> allele at the Mendelian anchor at 20,955,483. The father has 17 HP1 G/A reads
> and 17 HP2 A/G reads spanning the endpoints, and neither parent has an
> eligible G/G spanning read. All eight G/G child reads link to upstream HP1
> markers, three also link to downstream HP2 markers, and two cover both
> 20,968,297 and 20,968,600. The IGV overview shows child alignments extending
> from the interval into the downstream marker region. The reproduced BAM and
> VCF audit supports the switch at marker resolution.

[Actor's comparison output](trio-flank-comparison.json)
