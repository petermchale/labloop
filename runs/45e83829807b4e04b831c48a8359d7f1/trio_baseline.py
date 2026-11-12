"""Evaluate listed trio intervals with Mendelian SNVs and read-level linkage.

Run from the project root with the focused input and run output directories
as positional arguments. Requires pysam. Positions in the JSON are 1-based.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path

import pysam


FLANK = 5000
MIN_MAPQ = 30
MIN_BASEQ = 20
PRIMARY_FLAGS_EXCLUDED = 0xF04


def read_pedigree(path):
    pedigree = {}
    for line in path.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            _, child, father, mother, *_ = line.split()
            pedigree[child] = (father, mother)
    return pedigree


def sample_call(sample):
    return {
        "gt": sample.get("GT"),
        "phased": sample.phased,
        "ps": sample.get("PS"),
        "gq": sample.get("GQ"),
        "dp": sample.get("DP"),
        "ad": sample.get("AD"),
    }


def mendelian_options(calls, child, target, other):
    """Return compatible (target GT index, child GT index), both 1-based."""
    trio = [calls[name]["gt"] for name in (child, target, other)]
    if any(gt is None or len(gt) != 2 or not set(gt) <= {0, 1} for gt in trio):
        return None
    child_gt, target_gt, other_gt = trio
    return [
        (j + 1, i + 1)
        for i, inherited in enumerate(child_gt)
        for j, allele in enumerate(target_gt)
        if inherited == allele and child_gt[1 - i] in other_gt
    ]


def collect_markers(vcf, reference, chrom, start, end, child, target, other):
    markers = {}
    exclusions = Counter()
    orientation = defaultdict(lambda: defaultdict(list))
    for record in vcf.fetch(chrom, start - 1, end):
        alleles = record.alleles
        if len(alleles) != 2 or any(base not in ("A", "C", "G", "T") for base in alleles):
            exclusions["non_biallelic_snv"] += 1
            continue
        pos = record.pos
        if reference.fetch(chrom, pos - 1, pos).upper() != alleles[0]:
            raise ValueError(f"Reference mismatch at {chrom}:{pos}")
        if pos in markers:
            raise ValueError(f"Multiple biallelic SNV records at {chrom}:{pos}")
        calls = {name: sample_call(record.samples[name]) for name in (child, target, other)}
        options = mendelian_options(calls, child, target, other)
        markers[pos] = {
            "alleles": alleles,
            "filter": list(record.filter),
            "calls": calls,
            "mendelian_options": options,
        }
        call = calls[child]
        child_indices = {i for _, i in options or []}
        if call["phased"] and call["ps"] is not None and len(child_indices) == 1:
            orientation[call["ps"]][next(iter(child_indices))].append(pos)

    for marker in markers.values():
        calls = marker["calls"]
        options = marker["mendelian_options"] or []
        child_call = calls[child]
        anchors = orientation.get(child_call["ps"], {})
        if len(anchors) == 1 and child_call["phased"]:
            inherited_index = next(iter(anchors))
            options = [(j, i) for j, i in options if i == inherited_index]
        target_call = calls[target]
        indices = {j for j, _ in options}
        marker["transmitted_target_hp"] = None
        if (len(indices) == 1 and target_call["phased"] and
                target_call["ps"] is not None and len(set(target_call["gt"])) == 2):
            marker["transmitted_target_hp"] = next(iter(indices))
    return markers, orientation, exclusions


def read_observations(bam, chrom, start, end, positions):
    rows = []
    exclusions = Counter()
    names = set()
    for read in bam.fetch(chrom, start - 1, end):
        if read.flag & PRIMARY_FLAGS_EXCLUDED or not MIN_MAPQ <= read.mapping_quality < 255:
            exclusions["flags_or_mapq"] += 1
            continue
        if read.query_qualities is None or read.query_sequence is None:
            exclusions["missing_sequence_or_base_quality"] += 1
            continue
        if read.query_name in names:
            raise ValueError(f"Repeated eligible alignment for {read.query_name}")
        names.add(read.query_name)
        bases = {
            ref + 1: read.query_sequence[query]
            for query, ref in read.get_aligned_pairs(matches_only=True)
            if ref + 1 in positions and read.query_qualities[query] >= MIN_BASEQ
        }
        rows.append({
            "read": read.query_name,
            "hp": read.get_tag("HP") if read.has_tag("HP") else None,
            "ps": read.get_tag("PS") if read.has_tag("PS") else None,
            "mapq": read.mapping_quality,
            "strand": "-" if read.is_reverse else "+",
            "bases": bases,
        })
    return rows, exclusions


def counts_by_tag(reads, positions):
    counts = defaultdict(Counter)
    for read in reads:
        pattern = "/".join(read["bases"].get(pos, ".") for pos in positions)
        if set(pattern) <= {".", "/"}:
            continue
        counts[f'{read["ps"]}:{read["hp"]}'][pattern] += 1
    return counts


def evaluate(row, pedigree, source, vcf, reference):
    child, target, chrom = row["child"], row["parent"], row["chromosome"]
    other, = [name for name in pedigree[child] if name != target]
    left, right = int(row["left_1based"]), int(row["right_1based"])
    length = reference.get_reference_length(chrom)
    start, end = max(1, left - FLANK), min(length, right + FLANK)
    markers, orientation, exclusions = collect_markers(
        vcf, reference, chrom, start, end, child, target, other
    )
    if not {left, right} <= markers.keys():
        raise ValueError(f"Missing endpoint SNVs for {row['key']}")
    evidence = {
        "candidate": row,
        "other_parent": other,
        "window_1based_inclusive": [start, end],
        "filters": {
            "flank_bp": FLANK,
            "minimum_mapq": MIN_MAPQ,
            "minimum_baseq": MIN_BASEQ,
            "excluded_flags_hex": hex(PRIMARY_FLAGS_EXCLUDED),
            "mapq_255_excluded": True,
            "vcf_filter_and_gq_retained_as_annotations": True,
        },
        "child_ps_orientation_anchors": orientation,
        "excluded_vcf_records": exclusions,
        "snvs": markers,
        "endpoint_read_patterns_by_ps_hp": {},
        "read_filter_counts": {},
        "reads": {},
    }
    for name in (child, target, other):
        with pysam.AlignmentFile(source / f"{name}.GRCh38.haplotagged.bam") as bam:
            if {group.get("SM") for group in bam.header.to_dict()["RG"]} != {name}:
                raise ValueError(f"Unexpected read group sample for {name}")
            if not bam.check_index() or bam.get_reference_length(chrom) != length:
                raise ValueError(f"Index or reference check failed for {name}")
            reads, dropped = read_observations(bam, chrom, start, end, markers.keys())
        evidence["reads"][name] = reads
        evidence["read_filter_counts"][name] = dropped
        evidence["endpoint_read_patterns_by_ps_hp"][name] = counts_by_tag(reads, (left, right))
        for pos, marker in markers.items():
            marker.setdefault("read_bases_by_ps_hp", {})[name] = counts_by_tag(reads, (pos,))
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = args.source
    pedigree = read_pedigree(source / "trio.ped")
    with (
        pysam.VariantFile(source / "trio.vcf.gz") as vcf,
        pysam.FastaFile(source / "chr22.fa") as reference,
        (source / "candidates.tsv").open() as candidates,
    ):
        for row in csv.DictReader(candidates, delimiter="\t"):
            result = evaluate(row, pedigree, source, vcf, reference)
            path = args.output / f"{row['key']}.json"
            path.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
