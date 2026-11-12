"""Controller-side evidence validation and provenance; not agent-facing tools."""
import hashlib
import re
from pathlib import Path
from tempfile import NamedTemporaryFile


EVIDENCE_ID_PATTERN = r"^evidence_[0-9a-f]{32}$"


def _workspace_path(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Evidence path escapes project root")
    return path


def _evidence_file(root, value):
    resolved = _workspace_path(root, value)
    if not resolved.is_file():
        raise ValueError(f"Evidence file does not exist: {value}")
    return resolved


class EvidenceRegistry:
    def __init__(self, root, directory):
        self.root = root.resolve()
        self.directory = _workspace_path(self.root, directory)

    def register(self, path):
        if not path or Path(path).is_absolute():
            raise ValueError("Evidence must be a project-relative file path")
        resolved = _evidence_file(self.root, path)
        relative = resolved.relative_to(self.root).as_posix()
        evidence_id = self._id(relative)
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.directory,
                                delete=False) as entry:
            entry.write(relative)
        temporary = Path(entry.name)
        try:
            temporary.replace(self.directory / evidence_id)
        finally:
            temporary.unlink(missing_ok=True)
        return evidence_id

    def resolve(self, evidence_id):
        if not re.fullmatch(EVIDENCE_ID_PATTERN, evidence_id):
            raise ValueError(f"Expected an evidence ID from register-evidence: {evidence_id!r}")
        entry = self.directory / evidence_id
        if entry.is_symlink() or not entry.is_file():
            raise ValueError(f"Unregistered evidence ID: {evidence_id}")
        path = entry.read_text(encoding="utf-8")
        resolved = _evidence_file(self.root, path)
        relative = resolved.relative_to(self.root).as_posix()
        if self._id(relative) != evidence_id:
            raise ValueError(f"Evidence registration does not match its ID: {evidence_id}")
        return relative

    @staticmethod
    def _id(path):
        return "evidence_" + hashlib.sha256(path.encode("utf-8")).hexdigest()[:32]


class RunArtifacts:
    def __init__(self, root, output, vault):
        self.root = root.resolve()
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.vault = vault

    def path(self, value):
        return _workspace_path(self.root, value)

    def evidence_file(self, path):
        return _evidence_file(self.root, path)

    def file_record(self, path, experiment):
        resolved = self.evidence_file(path)
        digest = hashlib.sha256()
        with resolved.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return self.vault.put("FilePath", str(resolved.relative_to(self.root)),
                              path=str(resolved.relative_to(self.root)), sha256=digest.hexdigest(),
                              experiment=experiment)
