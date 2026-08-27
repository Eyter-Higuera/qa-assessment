#!/usr/bin/env python3
"""Build testing_manual_report.pdf from the manual in README.md.

The manual is not duplicated here. It is read from README.md between the
`testing-manual` markers, so the PDF cannot drift from the document people
actually read in the repository. What this script adds is the part a static
document cannot have: the three suites are executed and their real output,
durations and exit codes are appended.

    python scripts/build_testing_report.py            # run the suites, then render
    python scripts/build_testing_report.py --no-run   # render from the manual alone

Rendering prefers WeasyPrint and falls back to the Chromium that Playwright
already installs, because WeasyPrint needs GTK natively and cannot be installed
on a stock Windows machine without an elevated system install.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PDF = ROOT / "testing_manual_report.pdf"
MARKER = re.compile(
    r"<!--\s*testing-manual:start\s*-->(.*?)<!--\s*testing-manual:end\s*-->",
    re.S,
)

# Each suite as it is actually documented, so the report proves the commands work.
SUITES = [
    ("Unit (Vitest)", ROOT / "playwright",
     ["npm", "run", "test:unit", "--", "--coverage"]),
    ("API (Karate)", ROOT / "karate",
     ["mvn", "-B", "test", "-Dtest=SmokeTest", "-Dkarate.env=dev"]),
    ("UI (Playwright)", ROOT / "playwright",
     ["npx", "playwright", "test", "--project=chromium", "--grep", "@smoke"]),
]

CSS = """
@page { size: A4; }
:root { --ink:#111827; --muted:#6b7280; --rule:#e5e7eb; --accent:#1f4e79;
        --ok:#047857; --bad:#b91c1c; --code-bg:#f6f8fa; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       color: var(--ink); font-size: 10.5pt; line-height: 1.55; margin: 0; }
h1,h2,h3,h4 { color: var(--accent); line-height:1.25; margin: 1.4em 0 .5em; }
h1 { font-size: 22pt; margin-top: 0; }
h2 { font-size: 15pt; border-bottom: 2px solid var(--rule); padding-bottom: .25em;
     page-break-before: always; }
h2:first-of-type { page-break-before: avoid; }
h3 { font-size: 12.5pt; }
h4 { font-size: 11pt; color: var(--ink); }
p, li { orphans: 2; widows: 2; }
code { font-family: "Cascadia Mono", Consolas, "SF Mono", monospace;
       font-size: 9pt; background: var(--code-bg); padding: .1em .3em;
       border-radius: 3px; }
pre { background: var(--code-bg); border: 1px solid var(--rule); border-left: 3px solid var(--accent);
      border-radius: 4px; padding: .7em .9em; overflow-wrap: anywhere;
      white-space: pre-wrap; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.6pt; }
table { border-collapse: collapse; width: 100%; margin: .8em 0; font-size: 9.5pt;
        page-break-inside: avoid; }
th, td { border: 1px solid var(--rule); padding: .38em .55em; text-align: left; vertical-align: top; }
th { background: #eef3f8; font-weight: 600; }
tr:nth-child(even) td { background: #fbfcfd; }
blockquote { margin: .9em 0; padding: .55em .9em; border-left: 3px solid #f59e0b;
             background: #fffbeb; color: #92400e; page-break-inside: avoid; }
blockquote p { margin: .25em 0; }
.cover { text-align: center; padding-top: 26vh; page-break-after: always; }
.cover h1 { font-size: 30pt; border: 0; }
.cover .sub { color: var(--muted); font-size: 12pt; margin-top: .3em; }
.cover .meta { margin-top: 3em; font-size: 9.5pt; color: var(--muted); }
.shot { border: 1.5px dashed #b6c2d2; border-radius: 6px; background: #f8fafc;
        color: var(--muted); text-align: center; padding: 1.6em .8em; margin: .8em 0;
        font-size: 9pt; page-break-inside: avoid; }
.shot .label { font-weight: 600; color: #475569; display: block; margin-bottom: .2em; }
.shot .path { font-family: Consolas, monospace; font-size: 8pt; }
img { max-width: 100%; border: 1px solid var(--rule); border-radius: 4px; }
.run { border: 1px solid var(--rule); border-radius: 6px; margin: 1em 0;
       page-break-inside: avoid; }
.run .hd { padding: .5em .8em; font-weight: 600; border-bottom: 1px solid var(--rule);
           display: flex; justify-content: space-between; }
.run.pass .hd { background: #ecfdf5; color: var(--ok); }
.run.fail .hd { background: #fef2f2; color: var(--bad); }
.run pre { margin: 0; border: 0; border-radius: 0; border-left: 0; max-height: none; }
"""


def read_manual() -> str:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    found = MARKER.search(readme)
    if not found:
        sys.exit("README.md has no <!-- testing-manual:start --> ... :end --> block")
    return found.group(1).strip()


def run_suite(name: str, cwd: Path, cmd: list[str]) -> dict:
    """Execute a suite and capture what it actually printed."""
    exe = shutil.which(cmd[0]) or shutil.which(cmd[0] + ".cmd")
    if exe is None:
        return {"name": name, "cmd": " ".join(cmd), "skipped": True,
                "output": f"{cmd[0]} is not on PATH on this machine.",
                "code": None, "seconds": 0.0}
    print(f"  running {name} ...", flush=True)
    started = time.time()
    proc = subprocess.run([exe, *cmd[1:]], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return {
        "name": name,
        "cmd": " ".join(cmd),
        "skipped": False,
        "output": ((proc.stdout or "") + (proc.stderr or "")).strip(),
        "code": proc.returncode,
        "seconds": time.time() - started,
    }


def tail(text: str, lines: int = 28) -> str:
    kept = [ln for ln in text.splitlines() if ln.strip()]
    clipped = kept[-lines:]
    prefix = "" if len(kept) <= lines else f"... {len(kept) - lines} earlier lines omitted ...\n"
    return prefix + "\n".join(clipped)


def coverage_table() -> str:
    path = ROOT / "playwright" / "coverage" / "coverage-summary.json"
    try:
        total = json.loads(path.read_text(encoding="utf-8"))["total"]
    except Exception:
        return ""
    rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{:.1f}%</td></tr>".format(
            m.capitalize(), total[m]["covered"], total[m]["total"], total[m]["pct"])
        for m in ("statements", "branches", "functions", "lines") if m in total
    )
    return ("<h3>Measured coverage</h3>"
            "<table><tr><th>Metric</th><th>Covered</th><th>Total</th><th>%</th></tr>"
            f"{rows}</table>")


def results_html(results: list[dict]) -> str:
    if not results:
        return ""
    out = ["<h2>Live results</h2>",
           "<p>Captured by running each suite on the machine that built this "
           "report, so the commands above are shown working rather than "
           "asserted to work.</p>"]
    out.append("<table><tr><th>Suite</th><th>Command</th><th>Result</th>"
               "<th>Duration</th></tr>")
    for r in results:
        if r["skipped"]:
            verdict = "not run"
        else:
            verdict = "passed" if r["code"] == 0 else f"FAILED (exit {r['code']})"
        out.append("<tr><td>{}</td><td><code>{}</code></td><td>{}</td>"
                   "<td>{:.1f}s</td></tr>".format(
                       html.escape(r["name"]), html.escape(r["cmd"]),
                       verdict, r["seconds"]))
    out.append("</table>")
    out.append(coverage_table())
    for r in results:
        state = "pass" if r.get("code") == 0 else "fail"
        out.append(
            '<div class="run {}"><div class="hd"><span>{}</span><span>{}</span></div>'
            "<pre><code>{}</code></pre></div>".format(
                state, html.escape(r["name"]),
                "not run" if r["skipped"] else f"exit {r['code']} · {r['seconds']:.1f}s",
                html.escape(tail(r["output"]))))
    return "\n".join(out)


IMG_TAG = re.compile(r"<img[^>]*>", re.I)
ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def placeholder_images(body: str) -> str:
    """Swap missing screenshots for a labelled box instead of a broken image.

    Attribute order is not assumed: the manual writes these as hand-rolled HTML
    (src first, for the centred full-width form GitHub renders), while a plain
    Markdown image would arrive alt-first.
    """
    def swap(match):
        attrs = dict(ATTR.findall(match.group(0)))
        src = attrs.get("src", "")
        if not src or (ROOT / src).exists():
            return match.group(0)
        return ('<div class="shot"><span class="label">{}</span>'
                '<span class="path">{}</span></div>').format(
                    html.escape(attrs.get("alt", "screenshot")), html.escape(src))
    return IMG_TAG.sub(swap, body)


def build_html(manual_md: str, results: list[dict]) -> str:
    import markdown
    body = markdown.markdown(manual_md, extensions=["tables", "fenced_code"])
    body = placeholder_images(body)
    stamp = dt.datetime.now().strftime("%d %B %Y, %H:%M")
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = ""
    cover = f"""
    <div class="cover">
      <h1>Book Store QA</h1>
      <div class="sub">Testing manual &mdash; unit, API and UI</div>
      <div class="meta">
        Generated {stamp}{' &middot; commit ' + sha if sha else ''}<br>
        Vitest &middot; Karate &middot; Playwright &middot; GitHub Actions
      </div>
    </div>"""
    return (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>Book Store QA — testing manual</title><style>{CSS}</style>"
            f"</head><body>{cover}{body}{results_html(results)}</body></html>")


def render(html_text: str, keep: bool = False) -> None:
    tmp = ROOT / ".testing-report.html"
    tmp.write_text(html_text, encoding="utf-8")
    try:
        try:
            from weasyprint import HTML  # noqa: PLC0415
            HTML(string=html_text, base_url=str(ROOT)).write_pdf(OUT_PDF)
            print(f"rendered with WeasyPrint -> {OUT_PDF.name}")
            return
        except Exception as exc:
            print(f"  WeasyPrint unavailable ({type(exc).__name__}); "
                  "falling back to Playwright's Chromium")
        node = shutil.which("node")
        if node is None:
            sys.exit("neither WeasyPrint nor node is available to render the PDF")
        proc = subprocess.run(
            [node, "scripts/html-to-pdf.mjs", str(tmp), str(OUT_PDF)],
            cwd=ROOT / "playwright", capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit((proc.stderr or proc.stdout).strip() or "PDF rendering failed")
        print(f"rendered with Chromium -> {OUT_PDF.name}")
    finally:
        if keep:
            print(f"kept {tmp.name}")
        else:
            tmp.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-run", action="store_true",
                    help="skip executing the suites and render the manual alone")
    ap.add_argument("--keep-html", action="store_true",
                    help="leave the intermediate HTML on disk for inspection")
    args = ap.parse_args()

    results = []
    if not args.no_run:
        print("Executing the suites to capture real output:")
        for name, cwd, cmd in SUITES:
            results.append(run_suite(name, cwd, cmd))

    render(build_html(read_manual(), results), keep=args.keep_html)
    size = OUT_PDF.stat().st_size / 1024
    print(f"{OUT_PDF.name}: {size:.0f} KB")
    failed = [r for r in results if not r["skipped"] and r["code"] != 0]
    if failed:
        # Report, do not fail: a suite failing is content for the report, not a
        # reason to withhold it.
        print("note: %d suite(s) failed - their output is in the report"
              % len(failed))


if __name__ == "__main__":
    main()
