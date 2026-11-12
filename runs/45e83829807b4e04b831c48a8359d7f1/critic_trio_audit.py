"""Recompute the trio ledgers, verify them, and tabulate spanning-read linkage.

Run as python critic_trio_audit.py INPUT_DIR RUN_DIR, using the same inputs
as trio_baseline.py. The JSON report is written to stdout.
"""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path

import trio_baseline as baseline
import pysam


def spanning_counts(rows, positions):
    counts = Counter()
    for row in rows:
        bases = row["bases"]
        if all(pos in bases for pos in positions):
            pattern = "/".join(bases[pos] for pos in positions)
            counts[f'{row["ps"]}:{row["hp"]} {row["strand"]} {pattern}'] += 1
    return dict(sorted(counts.items()))


def marker_summary(markers, child, target, positions):
    return {
        pos: {
            "alleles": marker["alleles"],
            "transmitted_target_hp": marker["transmitted_target_hp"],
            "child_ps": marker["calls"][child]["ps"],
            "target_ps": marker["calls"][target]["ps"],
            "gq": {sample: call["gq"] for sample, call in marker["calls"].items()},
            "filter": marker["filter"],
            "calls": marker["calls"],
            "read_bases_by_ps_hp": marker["read_bases_by_ps_hp"],
        }
        for pos, marker in markers.items()
        if pos in positions or marker["transmitted_target_hp"] is not None
    }


def audit(source, output):
    pedigree = baseline.read_pedigree(source / "trio.ped")
    report = {}
    with (
        pysam.VariantFile(source / "trio.vcf.gz") as vcf,
        pysam.FastaFile(source / "chr22.fa") as reference,
        (source / "candidates.tsv").open() as candidates,
    ):
        for row in csv.DictReader(candidates, delimiter="\t"):
            key = row["key"]
            child, target = row["child"], row["parent"]
            left, right = int(row["left_1based"]), int(row["right_1based"])
            baseline.FLANK = 5000
            standard = baseline.evaluate(row, pedigree, source, vcf, reference)
            saved = json.loads((output / f"{key}.json").read_text())
            if json.loads(json.dumps(standard)) != saved:
                raise ValueError(f"Recomputed ledger differs from saved ledger for {key}")

            baseline.FLANK = 15000
            wide = baseline.evaluate(row, pedigree, source, vcf, reference)
            markers = wide["snvs"]
            resolved = [p for p, m in markers.items() if m["transmitted_target_hp"]]
            nearest = sorted(resolved, key=lambda p: min(abs(p - left), abs(p - right)))[:8]
            panels = {
                "endpoints": [left, right],
                "nearby_markers": sorted({left, right, *nearest}),
            }
            flanks = {
                20959352: [20955483],
                21165471: [21165364, 21166076],
                21291740: [21290886, 21292406],
            }
            panels["linked_flanks"] = sorted({left, right, *flanks[left]})
            if left == 20959352:
                panels["downstream_confirmation"] = [left, right, 20968297, 20968600]
            report[key] = {
                "ledger_reproduced": True,
                "child_ps_orientation_anchors": wide["child_ps_orientation_anchors"],
                "markers": marker_summary(markers, child, target, {left, right, *flanks[left]}),
                "linkage": {
                    name: {
                        "positions": positions,
                        "counts": {
                            sample: spanning_counts(reads, positions)
                            for sample, reads in wide["reads"].items()
                        },
                    }
                    for name, positions in panels.items()
                },
            }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.source, args.run), indent=2))
