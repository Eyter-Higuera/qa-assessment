#!/usr/bin/env python3
"""Run each documented local command and screenshot what it actually printed.

The testing manual shows an image under every command. Those started life as
generated placeholders; this replaces them with the real thing - each command is
executed, its combined output captured, rendered as a terminal window and saved
over the placeholder under the same filename.

    python scripts/capture_terminal_screenshots.py              # all of them
    python scripts/capture_terminal_screenshots.py unit karate-dev

The commands here are copied from the manual deliberately. If one of them stops
working, this script produces a screenshot of it failing rather than a tidy
fiction, which is the point: the manual then shows the truth and someone fixes
the command.

Only the local captures are produced - the individual suites and the pipeline
runner. The three CI images (ci-scenario-*.png, ci-job-summary.png) are
screenshots of GitHub's own UI and have to be taken by hand from a signed-in
browser; drawing something that looked like them here would be a fabrication,
not a capture.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"
PW = ROOT / "playwright"
KARATE = ROOT / "karate"
DEMO = "https://demoqa.com"

# key -> (png name, working directory, argv, extra env)
CAPTURES: dict[str, tuple[str, Path, list[str], dict]] = {
    "unit": ("local-unit-coverage.png", PW,
             ["npm", "run", "test:unit", "--", "--coverage"], {}),
    "karate-dev": ("local-karate-dev.png", KARATE,
                   ["mvn", "test", "-Dtest=SmokeTest", "-Dkarate.env=dev"], {}),
    "karate-release": ("local-karate-release.png", KARATE,
                       ["mvn", "test", "-Dtest=BookStoreApiTest",
                        "-Dkarate.env=release", f"-DbaseUrl={DEMO}"], {}),
    "karate-production": ("local-karate-production.png", KARATE,
                          ["mvn", "test", "-Dtest=SmokeTest",
                           "-Dkarate.env=production", f"-DbaseUrl={DEMO}"], {}),
    "playwright-dev": ("local-playwright-dev.png", PW,
                       ["npx", "playwright", "test", "--project=chromium",
                        "--grep", "@smoke"], {"BASE_URL": DEMO}),
    "playwright-release": ("local-playwright-release.png", PW,
                           ["npx", "playwright", "test", "--project=chromium",
                            "--project=firefox", "--project=webkit",
                            "--project=msedge"], {"BASE_URL": DEMO}),
    "playwright-production": ("local-playwright-production.png", PW,
                              ["npx", "playwright", "test", "--project=msedge",
                               "--grep", "@smoke"], {"BASE_URL": DEMO}),

    # The local pipeline runner, exercising the matrix the way CI does.
    "pipeline-dry": ("local-pipeline-matrix.png", ROOT,
                     ["node", "scripts/pipeline.mjs", "--stage", "release",
                      "--suite", "regression", "--browser", "all", "--dry-run"], {}),
    "pipeline-dev-smoke": ("local-pipeline-dev-smoke.png", ROOT,
                           ["npm", "run", "dev:smoke"], {}),
    "pipeline-regression-firefox": ("local-pipeline-regression-firefox.png", ROOT,
                                    ["node", "scripts/pipeline.mjs", "--stage", "dev",
                                     "--suite", "regression", "--browser", "firefox"], {}),
    "pipeline-production-webkit": ("local-pipeline-production-webkit.png", ROOT,
                                   ["node", "scripts/pipeline.mjs", "--stage", "production",
                                    "--suite", "smoke", "--browser", "webkit"], {}),
}

MAX_LINES = 52          # keeps an image readable on an A4 page
ANSI = re.compile(r"\x1b\[([0-9;]*)m")
STRIP_OTHER = re.compile(r"\x1b\[[0-9;?]*[A-HJKSTfhlsu]|\x1b\][^\x07]*\x07|[\r\x08]")

# xterm defaults, tuned a little for contrast on the dark card.
COLOURS = {
    30: "#4b5563", 31: "#f87171", 32: "#4ade80", 33: "#fbbf24", 34: "#60a5fa",
    35: "#c084fc", 36: "#22d3ee", 37: "#e5e7eb",
    90: "#9ca3af", 91: "#fca5a5", 92: "#86efac", 93: "#fde047", 94: "#93c5fd",
    95: "#d8b4fe", 96: "#67e8f9", 97: "#f9fafb",
}


def ansi_to_html(text: str) -> str:
    """Convert SGR colour codes to spans; drop every other escape."""
    text = STRIP_OTHER.sub("", text)
    out, open_spans = [], 0
    pos = 0
    for m in ANSI.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        pos = m.end()
        codes = [int(c) for c in (m.group(1) or "0").split(";") if c.isdigit()] or [0]
        for code in codes:
            if code in (0, 39):
                out.append("</span>" * open_spans)
                open_spans = 0
            elif code == 1:
                out.append('<span style="font-weight:600">')
                open_spans += 1
            elif code in COLOURS:
                out.append(f'<span style="color:{COLOURS[code]}">')
                open_spans += 1
    out.append(html.escape(text[pos:]))
    out.append("</span>" * open_spans)
    return "".join(out)


def clip(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) <= MAX_LINES:
        return "\n".join(lines)
    head, tail = MAX_LINES // 3, MAX_LINES - MAX_LINES // 3 - 1
    omitted = len(lines) - head - tail
    return "\n".join(lines[:head] + [f"\x1b[90m… {omitted} lines omitted …\x1b[0m"]
                     + lines[-tail:])


def card_html(cwd: Path, argv: list[str], env: dict, body: str,
              code: int, seconds: float) -> str:
    prompt = "".join(f'<span style="color:#9ca3af">{k}={v} </span>'
                     for k, v in env.items())
    ok = code == 0
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  body {{ margin:0; background:#0d1117; font-family:"Cascadia Mono",Consolas,
         "SF Mono",Menlo,monospace; }}
  .win {{ background:#0d1117; }}
  .bar {{ background:#161b22; border-bottom:1px solid #30363d; padding:10px 16px;
         display:flex; align-items:center; gap:8px; }}
  .dot {{ width:12px; height:12px; border-radius:50%; display:inline-block; }}
  .t {{ color:#8b949e; font-size:13px; margin-left:10px; }}
  pre {{ margin:0; padding:16px 18px; color:#c9d1d9; font-size:13.5px;
        line-height:1.5; white-space:pre-wrap; word-break:break-word; }}
  .cmd {{ color:#58a6ff; }} .sig {{ color:#3fb950; }}
  .ft {{ border-top:1px solid #30363d; padding:9px 18px; font-size:13px;
        color:{"#3fb950" if ok else "#f85149"}; background:#161b22; }}
</style></head><body><div class="win">
  <div class="bar">
    <span class="dot" style="background:#ff5f56"></span>
    <span class="dot" style="background:#ffbd2e"></span>
    <span class="dot" style="background:#27c93f"></span>
    <span class="t">{html.escape(str(cwd.relative_to(ROOT)))} — {html.escape(argv[0])}</span>
  </div>
  <pre><span class="sig">$</span> {prompt}<span class="cmd">{html.escape(' '.join(argv))}</span>

{body}</pre>
  <div class="ft">{'exit 0 — passed' if ok else f'exit {code} — FAILED'} · {seconds:.1f}s</div>
</div></body></html>"""


def render(html_text: str, png: Path) -> None:
    tmp = PW / "_capture.html"
    tmp.write_text(html_text, encoding="utf-8")
    try:
        node = shutil.which("node")
        if node is None:
            sys.exit("node is required to render the screenshots")
        proc = subprocess.run([node, "scripts/html-to-png.mjs", str(tmp), str(png)],
                              cwd=PW, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit((proc.stderr or proc.stdout).strip() or "screenshot failed")
    finally:
        tmp.unlink(missing_ok=True)


def _quantise(png: Path) -> None:
    """A 256-colour palette is lossless on a terminal capture and halves it.
    Applied at capture time so the images never enter the repository large."""
    try:
        from PIL import Image
    except ImportError:
        return
    try:
        with Image.open(png) as im:
            data = im.convert("RGB").quantize(colors=256, method=Image.MEDIANCUT)
            buf = png.with_suffix(".tmp.png")
            data.save(buf, optimize=True)
        if buf.stat().st_size < png.stat().st_size:
            buf.replace(png)
        else:
            buf.unlink(missing_ok=True)
    except Exception:
        pass          # a bigger screenshot is not worth failing a capture over


def capture(key: str) -> tuple[str, int]:
    name, cwd, argv, extra = CAPTURES[key]
    exe = shutil.which(argv[0]) or shutil.which(argv[0] + ".cmd")
    if exe is None:
        print(f"  {key}: {argv[0]} is not on PATH — leaving the placeholder")
        return key, -1
    env = {**os.environ, **extra, "FORCE_COLOR": "1"}
    print(f"  {key}: running …", flush=True)
    started = time.time()
    proc = subprocess.run([exe, *argv[1:]], cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    seconds = time.time() - started
    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    render(card_html(cwd, argv, extra, ansi_to_html(clip(output)),
                     proc.returncode, seconds), IMAGES / name)
    _quantise(IMAGES / name)
    verdict = "passed" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
    print(f"  {key}: {verdict} in {seconds:.1f}s -> docs/images/{name}")
    return key, proc.returncode


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("only", nargs="*", choices=sorted(CAPTURES) or None,
                    help="capture only these (default: all)")
    args = ap.parse_args()
    keys = args.only or list(CAPTURES)

    IMAGES.mkdir(parents=True, exist_ok=True)
    print(f"Capturing {len(keys)} command(s):")
    results = [capture(k) for k in keys]

    failed = [k for k, code in results if code not in (0, -1)]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        # Not an error here: a failing command is captured honestly and the
        # image shows it. Surfacing the list is enough.
        print("captured as failing: " + ", ".join(failed))


if __name__ == "__main__":
    main()
