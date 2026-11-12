"""Build the three-candidate example from the full chr22 trio fixture."""

import csv
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pysam


CHROMOSOME = "chr22"
CHILD = "NA12879"
CANDIDATES = (
    ("NA12877", 20_959_352, 20_961_970),
    ("NA12878", 21_165_471, 21_165_499),
    ("NA12878", 21_291_740, 21_291_798),
)
# The prior read audit used phase anchors as far as 10,151 bases past a flank.
PADDING = 15_000
VARIANTS = "CEPH-1463.joint.GRCh38.deepvariant.glnexus.vcf.gz"


def build_fixture(source, destination):
    if destination.exists():
        raise FileExistsError(destination)
    with TemporaryDirectory(dir=destination.parent) as temporary:
        staging = Path(temporary) / "focused"
        staging.mkdir()
        for name in ("chr22.fa", "chr22.fa.fai", "chr22.fa.source.txt", "trio.ped"):
            shutil.copy2(source / name, staging / name)

        regions = [(left - 1 - PADDING, right + PADDING) for _, left, right in CANDIDATES]
        bed = staging / "regions.bed"
        with bed.open("w") as handle:
            for start, end in regions:
                handle.write(f"{CHROMOSOME}\t{start}\t{end}\n")
        with (staging / "candidates.tsv").open("w", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(("key", "child", "parent", "chromosome", "left_1based", "right_1based"))
            for parent, left, right in CANDIDATES:
                writer.writerow((f"{parent}-{CHROMOSOME}-{left}-{right}", CHILD,
                                 parent, CHROMOSOME, left, right))

        for sample in (CHILD, "NA12877", "NA12878"):
            name = f"{sample}.GRCh38.haplotagged.bam"
            target = str(staging / name)
            pysam.view("-b", "-M", "-L", str(bed), "-o", target,
                       str(source / name), catch_stdout=False)
            pysam.index(target)

        target_vcf = str(staging / "trio.vcf.gz")
        with pysam.VariantFile(str(source / VARIANTS)) as source_vcf:
            with pysam.VariantFile(target_vcf, "wz", header=source_vcf.header) as output_vcf:
                for start, end in regions:
                    for record in source_vcf.fetch(CHROMOSOME, start, end):
                        output_vcf.write(record)
        pysam.tabix_index(target_vcf, preset="vcf")
        staging.rename(destination)


if __name__ == "__main__":
    data = Path(__file__).resolve().parents[1] / "trio_dev_data"
    build_fixture(data / "input", data / "focused")
