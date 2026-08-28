#!/usr/bin/env python3
"""Build testing_report.pdf from the manual in README.md.

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
OUT_PDF = ROOT / "testing_report.pdf"
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
/* An image is never printed wider than the page, and never wider than the width
   the manual asked for. The two portrait CI captures are only 345px and 569px
   across; stretching those to the full 180mm text column is what made them
   blurry, because there are no more pixels to show. The terminal captures are
   2400px wide and downscale, so they stay at 100%. */
img { max-width: 100%; height: auto; border: 1px solid var(--rule);
      border-radius: 4px; page-break-inside: avoid; }
p[align="center"] { text-align: center; margin: .9em 0; }
p[align="center"] img { display: inline-block; }
.run { border: 1px solid var(--rule); border-radius: 6px; margin: 1em 0;
       page-break-inside: avoid; }
.run .hd { padding: .5em .8em; font-weight: 600; border-bottom: 1px solid var(--rule);
           display: flex; justify-content: space-between; }
.run.pass .hd { background: #ecfdf5; color: var(--ok); }
.run.fail .hd { background: #fef2f2; color: var(--bad); }
.run pre { margin: 0; border: 0; border-radius: 0; border-left: 0; max-height: none; }
.cards { display: flex; gap: 10px; margin: 1em 0; page-break-inside: avoid; }
.card { flex: 1; border: 1px solid var(--rule); border-radius: 7px; padding: .75em .5em;
        text-align: center; background: #fbfcfd; }
.card .n { font-size: 21pt; font-weight: 700; color: var(--accent); line-height: 1.1; }
.card .l { font-size: 8pt; color: var(--muted); text-transform: uppercase;
           letter-spacing: .04em; margin-top: .25em; }
.card.good .n { color: var(--ok); }
.card.bad .n { color: var(--bad); }
.badge { display: inline-block; padding: .12em .5em; border-radius: 10px;
         font-size: 8.5pt; font-weight: 600; }
.badge.ok { background: #ecfdf5; color: var(--ok); border: 1px solid #a7f3d0; }
.badge.no { background: #fef2f2; color: var(--bad); border: 1px solid #fecaca; }
.chartwrap { display: flex; align-items: center; gap: 20px; margin: 1em 0;
             page-break-inside: avoid; }
.chartwrap svg { flex: 0 0 auto; }
.legend { font-size: 9.5pt; }
.legend div { margin: .3em 0; }
.legend .sw { display: inline-block; width: 11px; height: 11px; border-radius: 2px;
              margin-right: 7px; vertical-align: -1px; }
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


SLICE_COLOURS = ("#1f4e79", "#2e8b95", "#7aa6c2")


def donut_svg(slices: list[tuple[str, int, str]], size: int = 190) -> str:
    """Inline SVG donut. Vector, so it stays sharp at any print resolution -
    which a rasterised chart pasted in at 96dpi would not."""
    import math
    total = sum(n for _, n, _ in slices) or 1
    cx = cy = size / 2
    r_out, r_in = size / 2 - 4, size / 2 - 34
    parts, angle = [], -math.pi / 2      # start at twelve o'clock
    for label, value, colour in slices:
        if not value:
            continue
        sweep = 2 * math.pi * value / total
        end = angle + sweep
        large = 1 if sweep > math.pi else 0
        x1, y1 = cx + r_out * math.cos(angle), cy + r_out * math.sin(angle)
        x2, y2 = cx + r_out * math.cos(end), cy + r_out * math.sin(end)
        x3, y3 = cx + r_in * math.cos(end), cy + r_in * math.sin(end)
        x4, y4 = cx + r_in * math.cos(angle), cy + r_in * math.sin(angle)
        parts.append(
            '<path d="M{:.2f} {:.2f} A{:.2f} {:.2f} 0 {} 1 {:.2f} {:.2f} '
            'L{:.2f} {:.2f} A{:.2f} {:.2f} 0 {} 0 {:.2f} {:.2f} Z" fill="{}"/>'
            .format(x1, y1, r_out, r_out, large, x2, y2, x3, y3,
                    r_in, r_in, large, x4, y4, colour))
        angle = end
    return ('<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}" '
            'xmlns="http://www.w3.org/2000/svg">{p}'
            '<text x="{c}" y="{c}" text-anchor="middle" dy="-2" '
            'font-family="Segoe UI,sans-serif" font-size="26" font-weight="700" '
            'fill="#1f4e79">{t}</text>'
            '<text x="{c}" y="{c}" text-anchor="middle" dy="16" '
            'font-family="Segoe UI,sans-serif" font-size="9" fill="#6b7280">'
            'CASES</text></svg>').format(s=size, p="".join(parts), c=cx, t=total)


def metrics_html() -> str:
    """Executive dashboard, generated from the recorded run - never hand-typed."""
    path = ROOT / "docs" / "test-metrics.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    head, suites = data["headline"], data["suites"]
    cov = data.get("coverage") or {}

    cards = [
        ("", head["total"], "test cases"),
        ("good" if not head["failed"] else "", "%.0f%%" % head["pass_rate"], "pass rate"),
        ("bad" if head["failed"] else "good", head["failed"], "failed"),
    ]
    if cov:
        cards.append(("good" if min(cov.values()) >= 80 else "bad",
                      "%.0f%%" % cov.get("lines", 0), "line coverage"))
    cards_html = "".join(
        '<div class="card {}"><div class="n">{}</div><div class="l">{}</div></div>'
        .format(cls, val, lab) for cls, val, lab in cards)

    slices, legend = [], []
    for i, key in enumerate(data["headline_scope"]):
        s, colour = suites[key], SLICE_COLOURS[i % len(SLICE_COLOURS)]
        slices.append((s["label"], s["total"], colour))
        legend.append('<div><span class="sw" style="background:{}"></span>'
                      '<strong>{}</strong> — {} case{} ({})</div>'
                      .format(colour, html.escape(s["label"]), s["total"],
                              "" if s["total"] == 1 else "s", html.escape(s["tool"])))

    rows = []
    order = list(data["headline_scope"]) + ["api-regression", "ui-regression"]
    for key in order:
        s = suites[key]
        badge = ('<span class="badge ok">100%</span>' if s["total"] and not s["failed"]
                 else '<span class="badge no">%d failed</span>' % s["failed"])
        rows.append("<tr><td>{}</td><td>{}</td><td align=\"right\">{}</td>"
                    "<td align=\"right\">{}</td><td align=\"right\">{}</td>"
                    "<td>{}</td><td>{}</td></tr>".format(
                        html.escape(s["label"]), html.escape(s["tool"]), s["total"],
                        s["passed"], s["failed"], badge, html.escape(s["scope"])))

    return """<h2>Executive test metrics</h2>
<p>Every figure below was produced by executing the suites at commit
<code>{sha}</code>, not by counting source. Regenerate with
<code>python scripts/collect_test_metrics.py</code>.</p>
<div class="cards">{cards}</div>
<h3>Smoke gate by layer</h3>
<div class="chartwrap">{donut}<div class="legend">{legend}</div></div>
<table><tr><th>Test suite / layer</th><th>Tool</th><th>Total</th><th>Passed</th>
<th>Failed</th><th>Result</th><th>Coverage / scope</th></tr>{rows}</table>
<p>The smoke gate is the first three rows: what a pull request runs and what
verifies a production deployment. The regression rows are shown apart from it
deliberately &mdash; quoting the API layer as {api} cases without saying
<em>smoke</em> would misrepresent a suite that has {apireg}.</p>""".format(
        sha=html.escape(data.get("commit", "")), cards=cards_html,
        donut=donut_svg(slices), legend="".join(legend), rows="".join(rows),
        api=suites["api-smoke"]["total"], apireg=suites["api-regression"]["total"])


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
            f"</head><body>{cover}{metrics_html()}{body}{results_html(results)}</body></html>")


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
            [node, "scripts/html-to-pdf.mjs", str(tmp), str(OUT_PDF),
             "Book Store QA — testing manual"],
            cwd=ROOT / "playwright", capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            if "EBUSY" in detail or "EPERM" in detail:
                # Windows locks an open PDF, and the raw node error buries why.
                sys.exit(f"{OUT_PDF.name} is open in another program - close the "
                         "PDF viewer and run this again.")
            sys.exit(detail or "PDF rendering failed")
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
