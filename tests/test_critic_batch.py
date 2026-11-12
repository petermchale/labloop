import json

from labloop.agents import DemoAgent
from labloop.loop import run_loop


def test_batch_groups_followups_and_repairs_evidence(tmp_path, monkeypatch):
    render_sizes = []

    def render(artifacts, launcher, requests):
        render_sizes.append(len(requests))
        return [{"image": "snapshot.png"} for _ in requests]

    monkeypatch.setattr("labloop.loop.render_views", render)
    monkeypatch.setattr("labloop.critic_batch.render_views", render)
    view = {"start": 10, "end": 20, "display": "squish", "sort": "POSITION",
            "group": "NONE", "color": "NONE", "track_indices": None}

    class Agent(DemoAgent):
        def ask(self, role, instruction, context, schema, artifacts, trace):
            if role == "actor":
                evidence = f"{context['output']}/evidence.tsv"
                artifacts.path(evidence).write_text("test")
                return schema.model_validate({
                    "summary": "test", "needs_input": None,
                    "products": [
                        {"key": key, "type_name": "Candidate", "description": key,
                         "evidence": [evidence],
                         "igv_snapshot": {"reference": "ref.fa", "tracks": ["trio.bam"],
                                          "chromosome": "chr22", "view": view}}
                        for key in ("a", "b", "c")
                    ],
                })
            if role != "critic":
                return super().ask(role, instruction, context, schema, artifacts, trace)
            schema_json = schema.model_json_schema()
            verdict = next(iter(schema_json["$defs"].values()))
            assert verdict["properties"]["key"]["enum"] == [
                entry["product"]["key"] for entry in context["batch"]
            ]
            reviews = []
            for entry in context["batch"]:
                product = entry["product"]
                path = product["evidence"][0]
                review = {"key": product["key"], "verdict": "supported",
                          "diagnosis": "test verdict", "evidence": [path], "needs_input": None}
                if entry["igv"]["remaining_requests"]:
                    review["igv_views"] = [view] if product["key"] in ("a", "b") else None
                    if "correction" not in context and product["key"] == "c":
                        review["evidence"] = [path + " — inspected"]
                else:
                    assert entry["igv"]["previous_review"]["key"] == product["key"]
                reviews.append(review)
            self.calls.append((trace.stem, [r["key"] for r in reviews]))
            return schema.model_validate({"reviews": reviews})

    agent = Agent()
    agent.calls = []
    config = {"goal": "test", "criteria": "test", "distill": "test",
              "critic_batch_size": 10, "igv_snapshots": True}
    path = run_loop(config, tmp_path, agent, cycles=1, tools={"igv": {"argv": ["igv"]}})
    manifest = json.loads(path.read_text())
    assert manifest["state"] == "budget_exhausted"
    assert render_sizes == [3, 2]
    assert agent.calls == [
        ("1-critic-batch-0", ["a", "b", "c"]),
        ("1-critic-batch-0-repair", ["a", "b", "c"]),
        ("1-critic-batch-0-view-1", ["a", "b"]),
    ]
    assert [o["item"] for o in manifest["cycles"][0]["observations"]] == ["a", "b", "c"]
