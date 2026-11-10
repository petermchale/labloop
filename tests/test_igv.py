import json
import sys

from labloop.agents import DemoAgent
from labloop.loop import run_loop


def test_controller_renders_initial_and_critic_requested_views(tmp_path):
    root = tmp_path / "project with spaces"
    root.mkdir()
    (root / "reference with spaces.fa").touch()
    (root / "reference with spaces.fa.fai").write_text("chrTest\t1000\t9\t80\t81\n")
    (root / "reads.bam").touch()
    (root / "reads.bam.bai").touch()
    renderer = root / "fake_igv.py"
    renderer.write_text(
        "import base64, pathlib, sys\n"
        "batch = pathlib.Path(sys.argv[2])\n"
        "for line in batch.read_text().splitlines():\n"
        "    command, *args = line.split()\n"
        "    if command == 'genome':\n"
        "        assert args[0].startswith('./') and pathlib.Path(args[0]).is_file()\n"
        "    if command == 'snapshot':\n"
        "        (batch.parent / args[0]).write_bytes(base64.b64decode(\n"
        "            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j9/8AAAAASUVORK5CYII='))\n"
    )
    initial = dict(start=100, end=500, display="squish", sort="POSITION", group="NONE",
                   color="NONE", track_indices=None)
    zoom = {**initial, "start": 240, "end": 300, "group": "STRAND", "track_indices": [0]}
    invalid = {**zoom, "end": 1001}

    class ReviewingAgent(DemoAgent):
        def ask(self, role, instruction, context, schema, artifacts, trace):
            if role == "actor":
                return schema.model_validate({
                    "summary": "Synthetic candidate", "needs_input": None,
                    "products": [{
                        "key": "candidate", "type_name": "CrossoverCandidate",
                        "description": "Synthetic", "evidence": ["reads.bam"],
                        "igv_snapshot": {
                            "reference": "reference with spaces.fa", "tracks": ["reads.bam"],
                            "chromosome": "chrTest", "view": initial,
                        },
                    }],
                })
            if role != "critic":
                return super().ask(role, instruction, context, schema, artifacts, trace)
            assert "igv" not in context["tools"]
            views = context["igv"]["views"]
            assert artifacts.path(views[0]["snapshot"]).is_file()
            report = dict(verdict="uncertain", diagnosis="Synthetic review", needs_input=None,
                          evidence=[views[0]["snapshot"]], igv_views=[invalid, zoom])
            if len(views) > 1:
                assert "outside" in views[1]["error"]
                assert artifacts.path(views[2]["snapshot"]).is_file()
                assert "goto chrTest:240-300" in artifacts.path(views[2]["batch"]).read_text()
                assert context["igv"]["previous_review"]["igv_views"] == [invalid, zoom]
                report.update(igv_views=None, evidence=[views[2]["snapshot"]])
            return schema.model_validate(report)

    config = dict(goal="Synthetic", criteria="Review", distill="Summarize", igv_snapshots=True)
    tools = {"igv": {"argv": [sys.executable, str(renderer)]}}
    manifest = json.loads(run_loop(config, root, ReviewingAgent(), cycles=1, tools=tools).read_text())
    cycle = manifest["cycles"][0]
    assert len(cycle["observations"]) == 1
    assert cycle["observations"][0]["evidence"] == [cycle["igv_views"]["candidate"][2]["snapshot"]]
