"""Compare endpoint novelty with automatically selected read-linked flanks.

Run with python -B trio_flank_linkage.py INPUT_DIR RUN_DIR.
Positions are 1-based. The saved baseline and audit ledgers remain unchanged.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

import pysam

import trio_baseline as baseline
from critic_trio_audit import spanning_counts


FLANK = 15000  # Same search radius as the previous critic audit.
MIN_GQ = 20
MIN_PARENT_READS_PER_HP = 2
MIN_PARENT_CONCORDANCE = 0.8
MIN_CHILD_READS_PER_SIDE = 2
LESSON = "heuristic_8d6779429db1e79ea69cd632"


def high_quality(marker):
    # The focused VCF also uses "." (an empty filter list).
    return marker["filter"] in ([], ["PASS"]) and all(
        call["gq"] is not None and call["gq"] >= MIN_GQ
        for call in marker["calls"].values()
    )


def child_origins(markers, child):
    anchors = defaultdict(lambda: defaultdict(dict))
    for pos, marker in markers.items():
        call = marker["calls"][child]
        options = marker["mendelian_options"] or []
        indices = {index for _, index in options}
        if high_quality(marker) and call["phased"] and call["ps"] is not None and len(indices) == 1:
            index = indices.pop()
            allele = marker["alleles"][call["gt"][index - 1]]
            anchors[call["ps"]][index][pos] = allele
    return anchors


def transmission(marker, child, target, origins):
    call = marker["calls"][target]
    if not call["phased"] or call["ps"] is None or len(set(call["gt"] or ())) != 2:
        return None
    options = marker["mendelian_options"] or []
    child_call = marker["calls"][child]
    anchors = origins.get(child_call["ps"], {})
    if child_call["phased"] and len(anchors) == 1:
        index = next(iter(anchors))
        options = [(hp, i) for hp, i in options if i == index]
    hps = {hp for hp, _ in options}
    return next(iter(hps)) if len(hps) == 1 else None


def phase_support(marker, pos, sample, reads):
    call = marker["calls"][sample]
    if not call["phased"] or call["ps"] is None or set(call["gt"] or ()) != {0, 1}:
        return {}
    counts = {hp: Counter() for hp in (1, 2)}
    for read in reads:
        if read["ps"] == call["ps"] and read["hp"] in counts and pos in read["bases"]:
            counts[read["hp"]][read["bases"][pos]] += 1
    return {
        hp: {"expected": marker["alleles"][allele], "counts": counts[hp]}
        for hp, allele in enumerate(call["gt"], 1)
    }


def phase_supported(support):
    return bool(support) and all(
        (total := sum(entry["counts"].values())) >= MIN_PARENT_READS_PER_HP
        and entry["counts"][entry["expected"]] / total >= MIN_PARENT_CONCORDANCE
        for entry in support.values()
    )


def spanning(reads, positions):
    return [read for read in reads if all(pos in read["bases"] for pos in positions)]


def pattern(read, positions):
    return "/".join(read["bases"][pos] for pos in positions)


def endpoint_comparison(saved, child, target, other, endpoints):
    reads = {name: spanning(rows, endpoints) for name, rows in saved["reads"].items()}
    parent_patterns = {
        name: Counter(pattern(read, endpoints) for read in reads[name])
        for name in (target, other)
    }
    origins = saved["child_ps_orientation_anchors"]
    assigned = [
        read for read in reads[child]
        if set(origins.get(str(read["ps"]), {})) == {str(read["hp"])}
    ]
    novel = [
        read for read in assigned
        if all(counts and pattern(read, endpoints) not in counts for counts in parent_patterns.values())
    ]
    return {
        "saved_baseline_window": saved["window_1based_inclusive"],
        "counts": {name: spanning_counts(rows, endpoints) for name, rows in reads.items()},
        "assigned_child_counts": spanning_counts(assigned, endpoints),
        "novel_assigned_child_counts": spanning_counts(novel, endpoints),
        "novel_assigned_child_read_count": len(novel),
        "endpoints": {pos: saved["snvs"][str(pos)] for pos in endpoints},
    }


def evaluate(row, source, run, pedigree, vcf, reference):
    child, target, chrom = row["child"], row["parent"], row["chromosome"]
    other, = (name for name in pedigree[child] if name != target)
    left, right = int(row["left_1based"]), int(row["right_1based"])
    endpoints = (left, right)
    start = max(1, left - FLANK)
    end = min(reference.get_reference_length(chrom), right + FLANK)
    markers, _, excluded_markers = baseline.collect_markers(
        vcf, reference, chrom, start, end, child, target, other
    )
    reads = {}
    excluded_reads = {}
    for name in (child, target, other):
        with pysam.AlignmentFile(source / f"{name}.GRCh38.haplotagged.bam") as bam:
            if {group.get("SM") for group in bam.header.to_dict()["RG"]} != {name}:
                raise ValueError(f"Unexpected sample in {name} BAM")
            if not bam.check_index() or bam.get_reference_length(chrom) != reference.get_reference_length(chrom):
                raise ValueError(f"Index or reference check failed for {name}")
            reads[name], excluded_reads[name] = baseline.read_observations(
                bam, chrom, start, end, markers
            )
    saved = json.loads((run / f"{row['key']}.json").read_text())
    if saved["candidate"] != row:
        raise ValueError(f"Saved candidate differs from input for {row['key']}")
    for rows in saved["reads"].values():
        for read in rows:
            read["bases"] = {int(pos): base for pos, base in read["bases"].items()}
    comparison = endpoint_comparison(saved, child, target, other, endpoints)
    origins = child_origins(markers, child)
    candidate_phase_sets = {
        ps for pos in endpoints if (ps := markers[pos]["calls"][target]["ps"]) is not None
    }
    candidate_ps = next(iter(candidate_phase_sets)) if len(candidate_phase_sets) == 1 else None
    endpoint_hps = [transmission(markers[pos], child, target, origins) for pos in endpoints]
    endpoint_support = {
        pos: phase_support(markers[pos], pos, target, reads[target]) for pos in endpoints
    }
    eligible_endpoints = (
        candidate_ps is not None and set(endpoint_hps) == {1, 2}
        and all(high_quality(markers[pos]) and phase_supported(endpoint_support[pos]) for pos in endpoints)
    )

    endpoint_reads = {name: spanning(rows, endpoints) for name, rows in reads.items()}
    if comparison["counts"] != {name: spanning_counts(rows, endpoints) for name, rows in endpoint_reads.items()}:
        raise ValueError(f"Wide-window endpoint counts differ from saved baseline for {row['key']}")
    assigned = [
        read for read in endpoint_reads[child]
        if set(origins.get(read["ps"], {})) == {read["hp"]}
    ]
    direct_anchors = {
        read["read"]: [
            pos for pos, allele in origins[read["ps"]][read["hp"]].items()
            if read["bases"].get(pos) == allele
        ]
        for read in assigned
    }
    expected = None
    switch_reads = []
    if eligible_endpoints:
        expected = "/".join(
            endpoint_support[pos][hp]["expected"] for pos, hp in zip(endpoints, endpoint_hps)
        )
        switch_reads = [read for read in assigned if pattern(read, endpoints) == expected]
    parent_matches = {
        name: sum(pattern(read, endpoints) == expected for read in endpoint_reads[name])
        for name in (target, other)
    }

    markers_by_side = {"left": {}, "right": {}}
    selection_counts = {"left": Counter(), "right": Counter()}
    linked = {"left": set(), "right": set()}
    corroborating_positions = {"left": [], "right": []}
    for pos, marker in markers.items():
        if left <= pos <= right:
            continue
        side = "left" if pos < left else "right"
        counts = selection_counts[side]
        counts["biallelic_snvs"] += 1
        if candidate_ps is None or marker["calls"][target]["ps"] != candidate_ps:
            counts["outside_target_phase_set"] += 1
            continue
        if not high_quality(marker):
            counts["low_or_missing_gq_or_filtered"] += 1
            continue
        hp = transmission(marker, child, target, origins)
        if hp is None:
            counts["unresolved_transmission"] += 1
            continue
        support = phase_support(marker, pos, target, reads[target])
        if not phase_supported(support):
            counts["insufficient_parent_phase_support"] += 1
            continue
        counts["eligible"] += 1
        positions = sorted((*endpoints, pos))
        covered = spanning(assigned, positions)
        matching = [
            read for read in spanning(switch_reads, positions)
            if read["bases"][pos] == support[hp]["expected"]
        ]
        names = {read["read"] for read in matching}
        corroborates = eligible_endpoints and hp == endpoint_hps[side == "right"]
        if corroborates and names:
            linked[side].update(names)
            corroborating_positions[side].append(pos)
        markers_by_side[side][pos] = {
            "marker": marker,
            "transmitted_target_hp": hp,
            "parent_phase_support": support,
            "positions": positions,
            "trio_spanning_counts": {
                name: spanning_counts(rows, positions) for name, rows in endpoint_reads.items()
            },
            "assigned_child_counts": spanning_counts(covered, positions),
            "switch_pattern_reads_matching_marker": sorted(names),
            "corroborates_endpoint_direction": corroborates,
        }

    up_rank = (
        eligible_endpoints and all(len(linked[side]) >= MIN_CHILD_READS_PER_SIDE for side in linked)
        and all(endpoint_reads[name] for name in (target, other))
        and not any(parent_matches.values())
        and any(direct_anchors[read["read"]] for read in switch_reads)
    )
    return {
        "candidate": row,
        "motivating_lesson": LESSON,
        "window_1based_inclusive": [start, end],
        "rules": {
            "flank_bp": FLANK,
            "minimum_trio_gq": MIN_GQ,
            "accepted_vcf_filter": [".", "PASS"],
            "minimum_mapq": baseline.MIN_MAPQ,
            "minimum_baseq": baseline.MIN_BASEQ,
            "excluded_flags_hex": hex(baseline.PRIMARY_FLAGS_EXCLUDED),
            "minimum_parent_reads_per_hp": MIN_PARENT_READS_PER_HP,
            "minimum_parent_concordance_per_hp": MIN_PARENT_CONCORDANCE,
            "minimum_distinct_child_reads_per_side": MIN_CHILD_READS_PER_SIDE,
        },
        "excluded_vcf_records": excluded_markers,
        "excluded_reads": excluded_reads,
        "endpoint_only": comparison,
        "target_phase_set": candidate_ps,
        "transmitted_target_hp_at_endpoints": endpoint_hps,
        "endpoint_parent_phase_support": endpoint_support,
        "eligible_endpoints_for_switch": eligible_endpoints,
        "child_origin_anchors_by_ps_hp": origins,
        "direct_origin_anchors_observed_by_assigned_child_read": direct_anchors,
        "assigned_child_endpoint_reads": assigned,
        "expected_switch_endpoint_pattern": expected,
        "switch_endpoint_read_names": [read["read"] for read in switch_reads],
        "parent_endpoint_pattern_matches": parent_matches if expected else None,
        "flank_selection_counts": selection_counts,
        "eligible_flanks": markers_by_side,
        "corroborating_flank_positions": corroborating_positions,
        "corroborating_child_read_names_by_side": {side: sorted(names) for side, names in linked.items()},
        "child_read_names_corroborating_both_sides": sorted(linked["left"] & linked["right"]),
        "augmented_up_rank": up_rank,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    pedigree = baseline.read_pedigree(args.source / "trio.ped")
    comparison = {}
    with (
        pysam.VariantFile(args.source / "trio.vcf.gz") as vcf,
        pysam.FastaFile(args.source / "chr22.fa") as reference,
        (args.source / "candidates.tsv").open() as candidates,
    ):
        for row in csv.DictReader(candidates, delimiter="\t"):
            result = evaluate(row, args.source, args.run, pedigree, vcf, reference)
            key = row["key"]
            (args.run / f"flank-{key}.json").write_text(json.dumps(result, indent=2) + "\n")
            comparison[key] = {
                "endpoint_novel_assigned_child_reads": result["endpoint_only"]["novel_assigned_child_read_count"],
                "augmented_up_rank": result["augmented_up_rank"],
                "retained_for_review": True,
                "corroborating_flank_positions": result["corroborating_flank_positions"],
                "corroborating_child_reads_by_side": {
                    side: len(names) for side, names in result["corroborating_child_read_names_by_side"].items()
                },
                "corroborating_child_reads_on_both_sides": len(result["child_read_names_corroborating_both_sides"]),
                "eligible_flanks": {
                    side: len(flanks) for side, flanks in result["eligible_flanks"].items()
                },
            }
    report = {
        "motivating_lesson": LESSON,
        "candidate_comparison": comparison,
        "endpoint_only_review_tiers": review_tiers(comparison, lambda c: c["endpoint_novel_assigned_child_reads"]),
        "augmented_review_tiers": review_tiers(
            comparison, lambda c: (c["augmented_up_rank"], c["endpoint_novel_assigned_child_reads"])
        ),
        "lost_candidates": [],
        "scope": "Three previously audited intervals. No independent test set or detection accuracy estimate.",
    }
    (args.run / "trio_flank_comparison.json").write_text(json.dumps(report, indent=2) + "\n")


def review_tiers(comparison, score):
    tiers = defaultdict(list)
    for key, candidate in comparison.items():
        tiers[score(candidate)].append(key)
    return [tiers[score_value] for score_value in sorted(tiers, reverse=True)]


if __name__ == "__main__":
    main()
