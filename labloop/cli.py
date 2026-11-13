import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from shutil import copyfileobj
from urllib.parse import parse_qs, quote, urlparse

from .evidence_view import cited_file, evidence_page
from .knowledge import Vault


_IMAGE_PREVIEWS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                   ".gif": "image/gif", ".webp": "image/webp"}
_TEXT_PREVIEWS = {".txt", ".md", ".log", ".py", ".r", ".sh", ".json", ".jsonl",
                  ".csv", ".tsv", ".vcf", ".bed", ".ped", ".sam", ".ttl",
                  ".html", ".svg", ".xml", ".yaml", ".yml"}


def serve(vault_path, port, runs_path=Path("runs"), *, root=None):
    root = Path.cwd() if root is None else root.resolve()

    class Handler(BaseHTTPRequestHandler):
        def send_evidence_file(self, path):
            if path is None:
                self.send_error(404, "Cited file unavailable")
                return
            try:
                file = path.open("rb")
            except OSError:
                self.send_error(404, "Cited file unavailable")
                return
            with file:
                suffix = path.suffix.lower()
                content_type = _IMAGE_PREVIEWS.get(suffix)
                if suffix in _TEXT_PREVIEWS:
                    content_type = "text/plain; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", content_type or "application/octet-stream")
                self.send_header("Content-Length", str(os.fstat(file.fileno()).st_size))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                if content_type is None:
                    self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(path.name)}")
                self.end_headers()
                copyfileobj(file, self.wfile)

        def do_GET(self):
            parsed = urlparse(self.path)
            vault = Vault(vault_path)
            query = parse_qs(parsed.query)
            if parsed.path == "/evidence/file":
                run, cycle, path = (query.get(key, [""])[0] for key in ("run", "cycle", "path"))
                self.send_evidence_file(cited_file(vault.records, runs_path, root, run, cycle, path))
                return
            if parsed.path in ("/", "/evidence"):
                page = evidence_page(vault.records, runs_path, query.get("run", [None])[0],
                                     query.get("cycle", [None])[0], root=root)
                if page is None:
                    self.send_error(404, "Run or cycle not found in this vault")
                    return
                body, content_type = page.encode("utf-8"), "text/html; charset=utf-8"
            elif parsed.path == "/recall":
                body = json.dumps(vault.recall(query.get("q", [""])[0])).encode()
                content_type = "application/json"
            elif parsed.path == "/graph.ttl":
                body, content_type = vault.export().encode(), "text/turtle"
            elif parsed.path == "/graph.jsonld":
                body, content_type = vault.export("json-ld").encode(), "application/ld+json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if content_type.startswith("text/html"):
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
    print(f"Knowledge server: http://127.0.0.1:{port}", flush=True)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main():
    parser = argparse.ArgumentParser(description="LabLoop: actor → critic → distiller")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("config", type=Path)
    run.add_argument("--root", type=Path, default=Path.cwd())
    run.add_argument("--demo", action="store_true", help="Scripted fixture; no Codex invocations")
    run.add_argument("--cycles", type=int, default=2)
    run.add_argument("--model", help="Override Codex's configured model")
    run.add_argument("--critic-model")
    run.add_argument("--distiller-model")
    run.add_argument("--codex", default="codex", help="Codex CLI executable")
    run.add_argument("--igv", help="IGV CLI launcher path (otherwise auto-discovered when required)")
    run.add_argument("--timeout", type=float, default=900, help="Seconds allowed per role invocation")
    run.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"], default="medium")
    run.add_argument("--vault", default="vault")
    run.add_argument("--runs", default="runs")
    recall = sub.add_parser("recall")
    recall.add_argument("query", nargs="?", default="")
    recall.add_argument("--vault", type=Path, default=Path("vault"))
    recall.add_argument("--research-only", action="store_true",
                        help="Exclude archived goals, criteria, and distill instructions from research evidence")
    export = sub.add_parser("export")
    export.add_argument("--vault", type=Path, default=Path("vault"))
    export.add_argument("--format", choices=["turtle", "json-ld"], default="turtle")
    server = sub.add_parser("serve")
    server.add_argument("--root", type=Path, default=Path.cwd(), help="Project root for vault, runs, and evidence paths")
    server.add_argument("--vault", type=Path, default=Path("vault"))
    server.add_argument("--runs", type=Path, default=Path("runs"), help="Run manifest directory for the evidence view")
    server.add_argument("--port", type=int, default=8765)
    feedback = sub.add_parser("feedback", help="Record scientist outcome feedback or domain context")
    feedback.add_argument("report", type=Path)
    feedback.add_argument("--root", type=Path, default=Path.cwd())
    feedback.add_argument("--vault", default="vault")
    evidence = sub.add_parser("register-evidence", help="Register evidence files for an active run")
    evidence.add_argument("--registry", type=Path, required=True)
    evidence.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.command == "run":
        from .agents import DemoAgent, CodexAgent
        from .loop import run_loop
        from .tool_setup import prepare_tools
        config = json.loads(args.config.read_text())
        try:
            tools = {} if args.demo else prepare_tools(config, igv=args.igv)
        except ValueError as exc:
            parser.error(str(exc))
        for name, tool in tools.items():
            import shlex
            print(f"{name} ready: {shlex.join(tool['argv'])}", flush=True)
        models = {"actor": args.model, "critic": args.critic_model or args.model,
                  "distiller": args.distiller_model or args.model}
        agent = DemoAgent() if args.demo else CodexAgent(models, executable=args.codex,
                                                       timeout=args.timeout, effort=args.effort)
        path = run_loop(config, args.root, agent, cycles=args.cycles,
                        vault_dir=args.vault, run_dir=args.runs, tools=tools)
        print(path)
        manifest = json.loads(path.read_text())
        print(manifest["state"])
        if "question" in manifest:
            print(manifest["question"])
    elif args.command == "recall":
        print(json.dumps(Vault(args.vault).recall(args.query, research_only=args.research_only), indent=2))
    elif args.command == "feedback":
        from .scientist_feedback import record_feedback
        print(record_feedback(args.root.resolve(), args.vault, json.loads(args.report.read_text())))
    elif args.command == "register-evidence":
        from .file_provenance import EvidenceRegistry
        try:
            registry = EvidenceRegistry(Path.cwd(), args.registry)
            citations = {path: registry.register(path) for path in args.paths}
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(json.dumps(citations))
    elif args.command == "export":
        print(Vault(args.vault).export(args.format))
    else:
        root = args.root.resolve()
        serve(root / args.vault, args.port, root / args.runs, root=root)


if __name__ == "__main__":
    main()
