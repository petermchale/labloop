"""A small Vault-LD-style server core; Markdown is authoritative, RDF is derived."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

NS = Namespace("https://labloop.local/id/")
TYPES = ("Goal", "Criteria", "DistillInstructions", "Experiment", "WorkProduct", "Hypothesis", "Observation", "Diagnosis",
         "Heuristic", "Claim", "FilePath", "GitCommit", "GitBranch", "Feedback")
CONTEXT = {
    "@base": str(NS), "ll": str(NS),
    "rdf": str(RDF), "rdfs": str(RDFS), "owl": str(OWL),
    "type": "@type", "id": "@id", "label": "rdfs:label",
    "status": "ll:status", "text": "ll:text", "created": "ll:created",
    "test": "ll:test", "path": "ll:path", "sha256": "ll:sha256",
    "rejectedBecause": {"@id": "ll:rejectedBecause", "@type": "@id"},
    "gitDirty": "ll:gitDirty", "subClassOf": {"@id": "rdfs:subClassOf", "@type": "@id"},
    **{k: {"@id": "ll:" + k, "@type": "@id"} for k in
       ("because", "experiment", "files", "commit", "branch", "target")},
}


class Vault:
    def __init__(self, root: Path):
        self.root = root
        if not root.exists():
            root.mkdir(parents=True)
        context = root / "context.jsonld"
        if not context.exists():
            self._write(context, json.dumps({"@context": CONTEXT}, indent=2))
        self.context = json.loads(context.read_text())["@context"]
        self.records = {}
        for path in root.rglob("*.md"):
            raw = path.read_text()
            if raw.startswith("---\n"):
                data = yaml.safe_load(raw.split("---", 2)[1])
                self.records[data["id"]] = data
        self.graph = Graph()
        for data in self.records.values():
            self._index(data)
        for name in TYPES:
            self.add_type(name)

    @staticmethod
    def _write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(text)
        temp.replace(path)

    def _index(self, data):
        self.graph.remove((NS[data["id"]], None, None))
        # Inline the shared context only in the derived JSON-LD projection.
        self.graph.parse(data=json.dumps({"@context": self.context, **data}), format="json-ld")

    def add_type(self, name):
        if not re.fullmatch(r"[A-Z][A-Za-z0-9]{0,63}", name):
            raise ValueError("Type names must be short PascalCase identifiers")
        if name not in self.records:
            self.put("owl:Class", name, id=name)

    def put(self, kind, text, *, id=None, **fields):
        ident = id or uuid4().hex
        if not re.fullmatch(r"[A-Za-z0-9_-]+", ident):
            raise ValueError("Invalid record ID")
        if not kind.startswith("owl:") and kind not in self.records:
            raise ValueError(f"Unknown ontology type: {kind}")
        data = {"id": ident, "type": kind if ":" in kind else "ll:" + kind,
                "text": text, "created": datetime.now(timezone.utc).isoformat(), **fields}
        if any(k not in self.context for k in data):
            raise ValueError("Add predicates to context.jsonld before using them")
        folder = "Ontologies/Classes" if kind == "owl:Class" else "Records"
        path = self.root / folder / f"{ident}.md"
        self._write(path, "---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n\n" + text + "\n")
        self.records[ident] = data
        self._index(data)
        return ident

    def recall(self, query="", *, experiment=None, limit=30, research_only=False):
        """Retrieve evidence; research mode excludes archived task instructions."""
        words = set(re.findall(r"\w+", query.lower()))
        candidates = [r for r in self.records.values()
                      if r["type"] != "owl:Class" and
                      (not research_only or r["type"] not in
                       ("ll:Goal", "ll:Criteria", "ll:DistillInstructions")) and
                      (experiment is None or r.get("experiment") == experiment)]
        def score(r):
            return len(words & set(re.findall(r"\w+", json.dumps(r).lower())))
        return sorted((r for r in candidates if not words or score(r)),
                      key=lambda r: (score(r), r["created"]), reverse=True)[:limit]

    def lessons(self):
        return [r for r in self.records.values() if r["type"] == "ll:Heuristic"
                and r.get("status") != "rejected"]

    def reject(self, ident, evidence):
        current = dict(self.records[ident])
        kind, text = current.pop("type").removeprefix("ll:"), current.pop("text")
        current.pop("created")
        current.update(status="rejected", rejectedBecause=evidence)
        self.put(kind, text, **current)

    def can_retract(self, ident):
        record = self.records.get(ident, {})
        return (record.get("status") in ("proposed", "supported", "uncertain", "contradicted")
                and record.get("type") not in ("ll:Experiment", "ll:Feedback"))

    def export(self, format="turtle"):
        return self.graph.serialize(format=format)
