"""Render structured locus requests in the controller's desktop session."""
import os
import re
import signal
import subprocess
from collections import defaultdict
from pathlib import Path
from tempfile import mkdtemp


def _local_file(artifacts, value):
    path = artifacts.path(value)
    if not path.is_file():
        raise ValueError(f"IGV input does not exist: {value}")
    return path


def _render_inputs(artifacts, request, view):
    reference = _local_file(artifacts, request.reference)
    if reference.suffix.lower() not in {".fa", ".fasta", ".fna"}:
        raise ValueError("IGV reference must be a local indexed FASTA")
    fai = _local_file(artifacts, f"{reference}.fai")
    with fai.open() as index:
        for line in index:
            fields = line.split("\t")
            if fields[0] == request.chromosome:
                chromosome_length = int(fields[1]) if len(fields) >= 5 else 0
                break
        else:
            raise ValueError(f"Chromosome {request.chromosome} is absent from the FASTA index")
    if not view.start <= view.end <= chromosome_length:
        raise ValueError(f"IGV interval is outside {request.chromosome}:1-{chromosome_length}")

    indices = view.track_indices if view.track_indices is not None else range(len(request.tracks))
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("Select one or more distinct IGV track indices")
    tracks = []
    for index in indices:
        if not 0 <= index < len(request.tracks):
            raise ValueError(f"IGV track index is out of range: {index}")
        track = _local_file(artifacts, request.tracks[index])
        if track.suffix.lower() == ".bam":
            candidates = [Path(f"{track}.bai"), track.with_suffix(".bai"), Path(f"{track}.csi")]
        elif track.name.lower().endswith(".vcf.gz"):
            candidates = [Path(f"{track}.tbi"), Path(f"{track}.csi")]
        else:
            raise ValueError(f"IGV track must be a local indexed BAM or VCF.gz: {track.name}")
        sidecar = next((path for path in candidates if path.is_file()), None)
        if sidecar is None:
            raise ValueError(f"Missing IGV track index: {track.name}")
        tracks.append((track, _local_file(artifacts, sidecar)))
    return (reference, fai), tuple(tracks)


def _link_input(directory, inputs, source, index, suffix):
    key = (source, index)
    if key not in inputs:
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", source.name)
        alias = f"input-{len(inputs) + 1}-{name}"
        (directory / alias).symlink_to(source)
        (directory / (alias + suffix)).symlink_to(index)
        # IGV's FASTA loader requires the path to have a parent component.
        inputs[key] = (f"./{alias}", f"./{alias}{suffix}")
    return inputs[key]


def _run_batch(launcher, batch, log, timeout):
    with log.open("w") as handle:
        with subprocess.Popen([*launcher, "-b", str(batch)], cwd=batch.parent,
                              stdout=handle, stderr=subprocess.STDOUT,
                              start_new_session=True) as process:
            try:
                code = process.wait(timeout=timeout)
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                raise
    if code:
        return (f"IGV exited with code {code}. Launch LabLoop from a graphical desktop "
                "session with permission to start IGV.")
    if re.search(r"\[BatchRunner\].* => |\[IGV\] Error loading track",
                 log.read_text(errors="replace")):
        return "IGV reported a failed batch command"
    return None


def _is_png(path):
    if not path.is_file() or path.stat().st_size < 45:
        return False
    with path.open("rb") as image:
        header = image.read(16)
        image.seek(-12, os.SEEK_END)
        return (header == b"\x89PNG\r\n\x1a\n\0\0\0\rIHDR"
                and image.read(12) == b"\0\0\0\0IEND\xaeB\x60\x82")


def render_views(artifacts, launcher, requests):
    """Return a result for every (snapshot spec, view) pair, in request order."""
    results = []
    groups = defaultdict(list)
    for request, view in requests:
        result = {"chromosome": request.chromosome, "view": view.model_dump()}
        results.append(result)
        try:
            reference, tracks = _render_inputs(artifacts, request, view)
        except (OSError, ValueError) as exc:
            result["error"] = str(exc)
            continue
        groups[reference, tracks].append((request.chromosome, view, result))
    if not groups:
        return results

    # Create files after the agent returns, in a fresh controller-owned directory.
    if artifacts.output.resolve() != artifacts.output:
        raise ValueError("IGV output directory was redirected")
    directory = Path(mkdtemp(prefix="igv-", dir=artifacts.output))
    batch = directory / "batch.txt"
    log = directory / "igv.log"
    commands = []
    snapshots = []
    inputs = {}
    for ((reference, fai), tracks), views in groups.items():
        if commands:
            commands.append("new")
        genome, _ = _link_input(directory, inputs, reference, fai, ".fai")
        commands.append(f"genome {genome}")
        if not snapshots:
            commands.extend(["snapshotDirectory $SCRIPT_DIR", "setSleepInterval 250"])
        for track, index in tracks:
            data, sidecar = _link_input(directory, inputs, track, index, index.suffix)
            commands.append(f"load {data} index={sidecar}")
        for chromosome, view, result in views:
            name = f"view-{len(snapshots) + 1}.png"
            snapshots.append((directory / name, result))
            commands.extend([
                f"goto {chromosome}:{view.start}-{view.end}",
                view.display,
                f"group {view.group}",
                f"sort {view.sort}",
                f"colorBy {view.color}",
                f"snapshot {name}",
            ])
    batch.write_text("\n".join([*commands, "exit", ""]), encoding="utf-8")
    timeout = 60 + 5 * len(snapshots)
    try:
        error = _run_batch(launcher, batch, log, timeout)
    except subprocess.TimeoutExpired:
        error = f"IGV batch exceeded {timeout}s"
    except OSError as exc:
        error = f"Could not run IGV: {exc}"
    for path, result in snapshots:
        result["batch"] = str(batch.relative_to(artifacts.root))
        result["log"] = str(log.relative_to(artifacts.root))
        if error:
            result["error"] = error
        elif _is_png(path):
            result["snapshot"] = str(path.relative_to(artifacts.root))
        else:
            result["error"] = "IGV did not produce a complete PNG"
    return results
