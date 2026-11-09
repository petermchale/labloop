"""Ingest explicit scientist feedback; agent assessments are not ground truth."""
from .knowledge import Vault
from .file_provenance import RunArtifacts


def record_feedback(root, vault_dir, report):
    vault_path = (root / vault_dir).resolve()
    if not vault_path.is_relative_to(root.resolve()):
        raise ValueError("Vault must be inside the workspace")
    vault = Vault(vault_path)
    target = report["target"]
    if target not in vault.records:
        raise ValueError("Feedback target is not a known record ID")
    if report["status"] not in ("supported", "contradicted", "uncertain", "context"):
        raise ValueError("Unknown feedback status")
    if not report["text"].strip():
        raise ValueError("Feedback must explain the outcome or domain knowledge")
    artifacts = RunArtifacts(root, root / "runs" / "feedback", vault)
    experiment = vault.records[target].get("experiment", target)
    files = [artifacts.file_record(p, experiment) for p in report.get("evidence", [])]
    ident = vault.put("Feedback", report["text"], target=target, because=[target],
                      status=report["status"], files=files, experiment=experiment)
    if report["status"] == "contradicted" and vault.can_retract(target):
        vault.reject(target, [ident])
    return ident
