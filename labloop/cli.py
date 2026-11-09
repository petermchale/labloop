import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .knowledge import Vault


def serve(vault_path, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            vault = Vault(vault_path)
            if parsed.path == "/recall":
                body = json.dumps(vault.recall(parse_qs(parsed.query).get("q", [""])[0])).encode()
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
    server.add_argument("--vault", type=Path, default=Path("vault"))
    server.add_argument("--port", type=int, default=8765)
    feedback = sub.add_parser("feedback", help="Record scientist outcome feedback or domain context")
    feedback.add_argument("report", type=Path)
    feedback.add_argument("--root", type=Path, default=Path.cwd())
    feedback.add_argument("--vault", default="vault")
    args = parser.parse_args()
    if args.command == "run":
        from .agents import DemoAgent, CodexAgent
        from .loop import run_loop
        models = {"actor": args.model, "critic": args.critic_model or args.model,
                  "distiller": args.distiller_model or args.model}
        agent = DemoAgent() if args.demo else CodexAgent(models, executable=args.codex,
                                                       timeout=args.timeout, effort=args.effort)
        path = run_loop(json.loads(args.config.read_text()), args.root, agent,
                        cycles=args.cycles, vault_dir=args.vault, run_dir=args.runs)
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
    elif args.command == "export":
        print(Vault(args.vault).export(args.format))
    else:
        serve(args.vault, args.port)


if __name__ == "__main__":
    main()
