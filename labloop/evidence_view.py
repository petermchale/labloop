"""Render a run's evidence from its manifest and the current vault."""
import json
from html import escape
from pathlib import Path
from textwrap import shorten
from urllib.parse import quote, urlencode

from .file_provenance import _evidence_file
from .knowledge import heuristic_id


def _available_runs(records, runs_path, run=None):
    runs = {}
    manifests = []
    for path in runs_path.glob("*/run.json"):
        if run is not None and path.parent.name != run:
            continue
        try:
            manifests.append((path.stat().st_mtime, path))
        except FileNotFoundError:
            continue
    for _, path in sorted(manifests, reverse=True):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(manifest, dict) or manifest.get("session") != path.parent.name:
            continue
        cycles = {
            str(cycle["cycle"]): cycle
            for cycle in manifest.get("cycles", [])
            if records.get(cycle["experiment"], {}).get("type") == "ll:Experiment"
        }
        if cycles:
            runs[manifest["session"]] = dict(sorted(cycles.items(), key=lambda entry: int(entry[0])))
    return runs


def _details(label, body, *, badge=""):
    return (
        f'<details><summary>{escape(label)}{badge}</summary>'
        f'<div class="branch">{body}</div></details>'
    )


def _resolve_file(root, path):
    if Path(path).is_absolute():
        return None
    try:
        return _evidence_file(root, path)
    except (OSError, ValueError, RuntimeError):
        return None


def _product_evidence(records, cycle, observation):
    record = records.get(observation["id"], {})
    for ref in record.get("because", []):
        product = records.get(ref, {})
        if product.get("experiment") == cycle["experiment"]:
            paths = [
                records[file_id]["path"]
                for file_id in product.get("files", [])
                if "path" in records.get(file_id, {})
            ]
            yield product, paths


def cited_file(records, runs_path, root, run, cycle, path):
    selected = _available_runs(records, runs_path, run).get(run, {}).get(cycle)
    if selected is None:
        return None
    for obs in selected.get("observations", []):
        if path in obs.get("evidence", []) or any(
            path in paths for _, paths in _product_evidence(records, selected, obs)
        ):
            return _resolve_file(root, path)
    return None


def _evidence_files(paths, root, run, cycle, label):
    if not paths:
        return _details(f"{label} (0)", '<p class="muted">No files cited.</p>')
    unique_paths = dict.fromkeys(paths)
    items = []
    for path in unique_paths:
        file = _resolve_file(root, path)
        title = f"<code>{escape(path)}</code>"
        if file is None:
            items.append(f'<li>{title} <span class="muted">File unavailable</span></li>')
            continue
        query = escape(urlencode({"run": run, "cycle": cycle, "path": path}))
        editor_url = "vscode://file/" + quote(file.as_posix().lstrip("/"), safe="/:")
        items.append(
            f'<li><a href="/evidence/file?{query}" target="_blank" rel="noopener">{title}</a>'
            f' <a class="editor-link" href="{escape(editor_url)}">Open in VS Code</a></li>'
        )
    return _details(f"{label} ({len(unique_paths)})", f"<ul>{''.join(items)}</ul>")


def _observation(records, cycle, observation, root, run):
    ident = observation["id"]
    record = records.get(ident, {})
    verdict = observation["verdict"]
    diagnosis = records.get(observation.get("diagnosis"), {})
    text = diagnosis.get("text") or record.get("text") or "Observation text unavailable."
    body = f"<p>{escape(text)}</p>"
    body += _evidence_files(observation.get("evidence", []), root, run, cycle["cycle"], "Critic evidence files")
    for product, paths in _product_evidence(records, cycle, observation):
        files = _evidence_files(paths, root, run, cycle["cycle"], "Actor evidence files")
        body += _details("Actor work product reviewed", f'<p>{escape(product["text"])}</p>' + files)
    body += f'<p class="muted">Vault observation <code>{escape(ident)}</code></p>'
    tone = {"supported": "positive", "contradicted": "negative"}.get(verdict, "neutral")
    badge = f' <span class="badge {tone}">{escape(verdict)}</span>'
    return _details("Critic observation · " + observation["item"], body, badge=badge)


def _cycle_tree(records, cycle, root, run):
    observations = {
        obs["id"]: _observation(records, cycle, obs, root, run) for obs in cycle.get("observations", [])
    }
    # The manifest preserves each cycle's citations even when the vault merges repeated lessons.
    distillation = cycle.get("distillation") or {}
    lessons = distillation.get("lessons", [])
    retractions = distillation.get("retract", [])
    branches = []
    cited = set()
    for lesson in lessons:
        claim = lesson["claim"]
        refs = lesson.get("because", [])
        cited.update(refs)
        body = f'<p>{escape(claim)}</p><p><strong>Proposed test</strong> {escape(lesson["test"])}</p>'
        current = records.get(heuristic_id(claim), {})
        if current.get("status"):
            body += f'<p class="muted">Current vault status · {escape(current["status"])}</p>'
        body += '<p class="edge-label">Cites observations</p>'
        body += "".join(observations.get(ref, f'<p>Observation unavailable: <code>{escape(ref)}</code></p>')
                        for ref in refs)
        branches.append(_details("Distilled lesson · " + shorten(claim, width=108, placeholder="…"), body))
    for retraction in retractions:
        target = retraction["target"]
        refs = retraction.get("because", [])
        cited.update(refs)
        body = f'<p>Target <code>{escape(target)}</code></p>'
        body += "".join(observations.get(ref, f'<p>Observation unavailable: <code>{escape(ref)}</code></p>')
                        for ref in refs)
        branches.append(_details("Proposed retraction", body))
    uncited = "".join(branch for ident, branch in observations.items() if ident not in cited)
    if branches:
        heading = "Distilled lessons" if lessons else "Retractions"
        if lessons and retractions:
            heading += " and retractions"
        tree = f"<h3>{heading}</h3>" + "".join(branches)
        if uncited:
            tree += (
                '<h3>Other critic observations</h3>'
                '<p class="muted">These observations are uncited by the distiller in this cycle.</p>'
                + uncited
            )
        return tree
    if uncited:
        return "<h3>Critic observations</h3>" + uncited
    return '<p class="muted">This cycle has no recorded observations or lessons yet.</p>'


def evidence_page(records, runs_path, run=None, cycle=None, *, root=None):
    root = Path.cwd() if root is None else root
    runs = _available_runs(records, runs_path)
    if not runs and run is None and cycle is None:
        return _PAGE.format(content='<p class="muted">No run cycles match this vault. '
                            'Check the <code>--vault</code> and <code>--runs</code> directories.</p>')
    run = next(iter(runs), None) if run is None else run
    if run not in runs:
        return None
    cycles = runs[run]
    cycle = next(iter(cycles)) if cycle is None else cycle
    if cycle not in cycles:
        return None
    options = "".join(
        f'<option{" selected" if item == run else ""}>{escape(item)}</option>' for item in runs
    )
    links = []
    for item in cycles:
        query = escape(urlencode({"run": run, "cycle": item}))
        current = ' aria-current="page"' if item == cycle else ""
        links.append(f'<a href="/evidence?{query}"{current}>Cycle {escape(item)}</a>')
    selected = cycles[cycle]
    experiment = records[selected["experiment"]]
    content = (
        '<form action="/evidence"><label for="run">Run</label>'
        f'<select id="run" name="run">{options}</select><button>View run</button></form>'
        f'{_TREE_GUIDE}'
        f'<nav aria-label="Run cycles">{"".join(links)}</nav>'
        f'<p class="muted">Experiment <code>{escape(experiment["id"])}</code>'
        f' · {escape(experiment.get("status", "unknown"))}</p>'
        f'<section class="cycle-tree" aria-label="Cycle {escape(cycle)} evidence">'
        + _cycle_tree(records, selected, root, run) + '</section>'
    )
    return _PAGE.format(content=content)


_TREE_GUIDE = """
<details class="tree-guide" open>
  <summary>How to read this tree</summary>
  <div class="branch">
    <p>Start at a lesson and expand each branch to follow its citations. Indentation shows which
    record each branch belongs to. A critic observation records a verdict on an actor work
    product and branches to the critic’s evidence and the work product it reviewed.</p>
    <ul class="tree-key">
      <li><strong>Distilled lesson</strong>
        <ul>
          <li><strong>Critic observation</strong> cited by the lesson
            <ul>
              <li><strong>Critic evidence files</strong> cited by the critic to support the verdict</li>
              <li><strong>Actor work product reviewed</strong>
                <ul>
                  <li><strong>Actor evidence files</strong> cited by the actor to support the work product</li>
                </ul>
              </li>
            </ul>
          </li>
        </ul>
      </li>
    </ul>
    <p>A shared observation or file can appear on more than one branch.
    Select a filename to open it in a new tab,
    or choose <strong>Open in VS Code</strong>.</p>
  </div>
</details>
"""


_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LabLoop evidence tree</title>
<style>
  :root {{
    color-scheme: light dark;
    --page: light-dark(#f5f7f7, #121719);
    --surface: light-dark(#fff, #1b2225);
    --ink: light-dark(#172527, #e9f1f0);
    --muted: light-dark(#4f6266, #aabdc0);
    --line: light-dark(#cbd7d8, #435357);
    --accent: light-dark(#00655e, #8ddbd0);
    --accent-ink: light-dark(#fff, #123330);
    --positive: light-dark(#145338, #a1e4bc);
    --negative: light-dark(#9b3434, #fcb1ad);
  }}
  * {{ box-sizing: border-box; }}
  body {{ background: var(--page); color: var(--ink); font: 1rem/1.55 "Inter", system-ui, sans-serif; margin: 0; }}
  main {{ max-width: 58rem; margin: auto; padding: clamp(1rem, 4vw, 3rem); overflow-wrap: anywhere; }}
  h1, h2, h3 {{ line-height: 1.2; }}
  h1 {{ font-size: clamp(1.75rem, 4vw, 2.5rem); margin: 0 0 1.25rem; letter-spacing: -.035em; }}
  h2 {{ font-size: 1.125rem; margin-top: 1.5rem; }}
  h3 {{ font-size: 1rem; }}
  form, nav {{ display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; margin-bottom: 1rem; }}
  select, button, nav a {{ font: inherit; border: 1px solid var(--line); border-radius: .4rem; padding: .4rem .65rem; }}
  select, button {{ color: var(--ink); background: var(--surface); max-width: 100%; }}
  button, summary {{ cursor: pointer; }}
  nav a {{ color: var(--accent); text-decoration: none; }}
  nav a[aria-current] {{ background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }}
  details {{ background: var(--surface); border: 1px solid var(--line); border-radius: .5rem; margin: .5rem 0; }}
  .branch details {{ position: relative; border: 0; border-top: 1px solid var(--line); border-radius: 0; }}
  .branch details::before {{
    content: ""; position: absolute; top: 1.3rem; left: -.8rem;
    width: .8rem; border-top: 1px solid var(--line);
  }}
  summary {{ padding: .6rem .8rem; font-weight: 600; }}
  summary::marker {{ color: var(--accent); }}
  .branch {{ margin: 0 .8rem .8rem; padding-left: .8rem; border-left: 2px solid var(--line); }}
  .branch p {{ margin: .5rem 0; white-space: pre-wrap; }}
  .edge-label {{ color: var(--muted); font-size: .875rem; font-weight: 600; }}
  .tree-guide {{ margin-bottom: 1.25rem; }}
  .tree-guide p {{ white-space: normal; }}
  .tree-key, .tree-key ul {{ list-style: none; margin: .25rem 0; padding: 0; }}
  .tree-key ul {{ margin-left: .3rem; }}
  .tree-key ul > li {{ position: relative; padding-left: .85rem; border-left: 1px solid var(--line); }}
  .tree-key ul > li::before {{
    content: ""; position: absolute; left: 0; top: .75em; width: .6rem;
    border-top: 1px solid var(--line);
  }}
  .tree-key ul > li:last-child {{ border-color: transparent; }}
  .tree-key ul > li:last-child::before {{ height: .75em; top: 0; border-top: 0;
    border-left: 1px solid var(--line); border-bottom: 1px solid var(--line); }}
  .cycle-tree {{ border-top: 1px solid var(--line); margin-top: 1rem; }}
  .cycle-tree a {{ color: var(--accent); }}
  .editor-link {{ display: inline-block; margin-left: .5rem; font-size: .875rem; }}
  .muted {{ color: var(--muted); font-size: .875rem; }}
  .badge {{ font-size: .8rem; color: var(--muted); margin-left: .35rem; }}
  .positive {{ color: var(--positive); }}
  .negative {{ color: var(--negative); }}
  ul {{ padding-left: 1.25rem; }}
</style>
</head>
<body><main>
<h1>LabLoop evidence tree</h1>
{content}
</main>
<script>
  const guide = document.querySelector(".tree-guide");
  if (guide) {{
    const key = "labloop:evidence-guide-open";
    try {{
      guide.open = sessionStorage.getItem(key) !== "false";
      guide.addEventListener("toggle", () => {{
        sessionStorage.setItem(key, String(guide.open));
      }});
    }} catch {{
      // The native disclosure still works when browser storage is disabled.
    }}
  }}
</script>
</body>
</html>
"""
