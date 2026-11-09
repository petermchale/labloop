"""Controller-side evidence validation and provenance; not agent-facing tools."""
import hashlib


class RunArtifacts:
    def __init__(self, root, output, vault):
        self.root = root.resolve()
        self.output = output.resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.vault = vault

    def path(self, value):
        path = (self.root / value).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Evidence path escapes project root")
        return path

    def file_record(self, path, experiment):
        resolved = self.path(path)
        if not resolved.is_file():
            raise ValueError(f"Evidence file does not exist: {path}")
        digest = hashlib.sha256()
        with resolved.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return self.vault.put("FilePath", str(resolved.relative_to(self.root)),
                              path=str(resolved.relative_to(self.root)), sha256=digest.hexdigest(),
                              experiment=experiment)
