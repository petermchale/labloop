import json
from urllib.parse import urlencode

from labloop.evidence_view import cited_file, evidence_page
from labloop.knowledge import Vault


def test_first_cycle_and_cited_file_links(tmp_path):
    vault = Vault(tmp_path / "vault")
    first = vault.put("Experiment", "First cycle")
    second = vault.put("Experiment", "Second cycle")
    path = "audit #1.json"
    file = tmp_path / path
    file.write_text("{}")
    uncited = tmp_path / "unrelated.txt"
    uncited.touch()
    outside = tmp_path.parent / "outside.txt"
    outside.touch()
    (tmp_path / "outside-link.txt").symlink_to(outside)
    file_record = vault.put("FilePath", path, path=path, experiment=first)
    product = vault.put("WorkProduct", "Actor report", experiment=first, files=[file_record])
    obs = vault.put("Observation", "Audited", experiment=first, because=[product])

    runs = tmp_path / "runs"
    run = runs / "test-run"
    run.mkdir(parents=True)
    (run / "run.json").write_text(json.dumps({
        "session": run.name,
        "cycles": [
            {"cycle": 2, "experiment": second},
            {"cycle": 1, "experiment": first, "observations": [
                {"id": obs, "item": "Report", "verdict": "supported",
                 "evidence": ["outside-link.txt", "missing.txt"]},
            ]},
        ],
    }))

    page = evidence_page(vault.records, runs, root=tmp_path)
    query = urlencode({"run": run.name, "cycle": 1, "path": path}).replace("&", "&amp;")
    assert 'aria-current="page">Cycle 1' in page
    assert "<summary>How to read this tree</summary>" in page
    assert "<summary>Critic evidence files (2)</summary>" in page
    assert ('<summary>Actor work product reviewed</summary><div class="branch">'
            '<p>Actor report</p><details><summary>Actor evidence files (1)</summary>') in page
    assert f'href="/evidence/file?{query}"' in page
    assert "audit%20%231.json" in page
    assert page.count("File unavailable") == 2
    assert cited_file(vault.records, runs, tmp_path, run.name, "1", path) == file.resolve()
    assert cited_file(vault.records, runs, tmp_path, run.name, "2", path) is None
    assert cited_file(vault.records, runs, tmp_path, run.name, "1", uncited.name) is None
    assert cited_file(vault.records, runs, tmp_path, run.name, "1", "outside-link.txt") is None
