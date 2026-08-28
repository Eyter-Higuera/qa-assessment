#!/usr/bin/env python3
"""Run the suites and record exactly how many tests each one has.

The executive metrics in README.md and testing_manual_report.pdf are generated
from docs/test-metrics.json, which this writes. Nothing about the counts is
typed by hand: each suite is executed and its JUnit XML counted, so the table
cannot quietly drift away from the suites it describes.

    python scripts/collect_test_metrics.py             # run and record
    python scripts/collect_test_metrics.py --no-run    # re-render from the last run

Scope matters and is recorded with the numbers. The headline is the SMOKE gate -
what a pull request runs and what verifies a production deployment. The wider
regression counts are collected too, because a table that reports 2 API tests
without saying "smoke" is misleading about a suite that has far more.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from glob import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PW = ROOT / "playwright"
KARATE = ROOT / "karate"
OUT = ROOT / "docs" / "test-metrics.json"

# key -> (label, tool, cwd, argv, xml glob, scope description)
SUITES = {
    "unit": ("Unit", "Vitest", PW,
             ["npm", "run", "test:unit", "--", "--coverage"],
             "playwright/test-results/unit-junit.xml",
             "Pure logic in src/ - 100% of the covered surface"),
    "api-smoke": ("API (smoke)", "Karate", KARATE,
                  ["mvn", "-B", "test", "-Dtest=SmokeTest", "-Dkarate.env=dev"],
                  "karate/target/karate-reports/*.xml",
                  "@smoke scenarios - the deployment gate"),
    "ui-smoke": ("UI (smoke)", "Playwright", PW,
                 ["npx", "playwright", "test", "--project=chromium", "--grep", "@smoke"],
                 "playwright/test-results/junit.xml",
                 "@smoke journeys on chromium"),
    "api-regression": ("API (regression)", "Karate", KARATE,
                       ["mvn", "-B", "test", "-Dtest=BookStoreApiTest",
                        "-Dkarate.env=dev"],
                       "karate/target/karate-reports/*.xml",
                       "Every scenario, all tags"),
    "ui-regression": ("UI (regression)", "Playwright", PW,
                      ["npx", "playwright", "test", "--project=chromium"],
                      "playwright/test-results/junit.xml",
                      "Every spec on chromium"),
}

# The headline figure: what a pull request runs and what verifies production.
HEADLINE = ("unit", "api-smoke", "ui-smoke")


def count(pattern: str) -> dict:
    passed = failed = skipped = 0
    seconds = 0.0
    for path in glob(str(ROOT / pattern)):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            continue
        suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
        for suite in suites:
            try:
                seconds += float(suite.get("time") or 0)
            except ValueError:
                pass
            for case in suite.iter("testcase"):
                if case.find("failure") is not None or case.find("error") is not None:
                    failed += 1
                elif case.find("skipped") is not None:
                    skipped += 1
                else:
                    passed += 1
    return {"passed": passed, "failed": failed, "skipped": skipped,
            "total": passed + failed + skipped, "seconds": round(seconds, 1)}


def clean(pattern: str) -> None:
    """Old XML would be counted alongside new; remove it before a run."""
    for path in glob(str(ROOT / pattern)):
        Path(path).unlink(missing_ok=True)


def run(key: str) -> dict:
    label, tool, cwd, argv, pattern, scope = SUITES[key]
    exe = shutil.which(argv[0]) or shutil.which(argv[0] + ".cmd")
    if exe is None:
        sys.exit(f"{argv[0]} is not on PATH")
    clean(pattern)
    print(f"  {key}: running …", flush=True)
    started = time.time()
    proc = subprocess.run([exe, *argv[1:]], cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    wall = time.time() - started
    result = count(pattern)
    result.update(label=label, tool=tool, scope=scope, exit_code=proc.returncode,
                  command=" ".join(argv), wall_seconds=round(wall, 1))
    print("  {}: {} of {} passed in {:.1f}s".format(
        key, result["passed"], result["total"], wall))
    return result


MARK_START, MARK_END = "<!-- metrics:start -->", "<!-- metrics:end -->"


def readme_section(data: dict) -> str:
    """The executive block, generated so it cannot drift from the suites."""
    suites, head = data["suites"], data["headline"]

    slices = "\n".join(
        '    "%s (%s)" : %d' % (suites[k]["label"].split(" (")[0], suites[k]["tool"],
                                suites[k]["total"])
        for k in data["headline_scope"])

    rows = []
    for key in data["headline_scope"]:
        s = suites[key]
        rows.append("| **%s** | %s | %d | %d | %d | %s |"
                    % (s["label"], s["tool"], s["total"], s["passed"],
                       s["failed"], s["scope"]))
    rows.append("| **Smoke gate total** | — | **%d** | **%d** | **%d** | "
                "Runs on every pull request and verifies every production deploy |"
                % (head["total"], head["passed"], head["failed"]))
    for key in ("api-regression", "ui-regression"):
        s = suites[key]
        rows.append("| %s | %s | %d | %d | %d | %s |"
                    % (s["label"], s["tool"], s["total"], s["passed"],
                       s["failed"], s["scope"]))

    cov = data.get("coverage") or {}
    cov_line = ""
    if cov:
        cov_line = ("\nUnit coverage on the surface unit tests own: "
                    + ", ".join("%s %.0f%%" % (m.capitalize(), v)
                                for m, v in cov.items())
                    + " — floor 80%.\n")

    return (
        "**{total} test cases, {passed} passed, {failed} failed — a {rate:.0f}% pass "
        "rate** on the smoke gate, measured at commit `{sha}` by executing every "
        "suite rather than by counting source.\n\n"
        "```mermaid\n"
        "pie showData title Smoke gate test cases by layer ({total} total)\n"
        "{slices}\n"
        "```\n\n"
        "| Test suite / layer | Tool | Total cases | Passed | Failed | Coverage / scope |\n"
        "|---|---|--:|--:|--:|---|\n"
        "{rows}\n"
        "{cov}\n"
        "The regression rows are listed apart from the gate on purpose: reporting "
        "\"2 API cases\" without saying *smoke* would misrepresent a suite that has "
        "{reg}. Regenerate every figure here with "
        "`python scripts/collect_test_metrics.py`."
    ).format(total=head["total"], passed=head["passed"], failed=head["failed"],
             rate=head["pass_rate"], sha=data["commit"], slices=slices,
             rows="\n".join(rows), cov=cov_line,
             reg=suites["api-regression"]["total"])


def update_readme(data: dict) -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    if MARK_START not in text or MARK_END not in text:
        print("  README has no metrics markers — skipped")
        return
    head, rest = text.split(MARK_START, 1)
    _, tail = rest.split(MARK_END, 1)
    path.write_text(head + MARK_START + "\n" + readme_section(data) + "\n"
                    + MARK_END + tail, encoding="utf-8")
    print("  README metrics section updated")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-run", action="store_true",
                    help="count the XML already on disk instead of re-running")
    args = ap.parse_args()

    print("Collecting test metrics:")
    if args.no_run:
        # Deliberately re-reads the recorded JSON rather than recounting the XML
        # on disk. Smoke and regression write to the same report paths, so a
        # recount cannot tell them apart - it would read whichever ran last and
        # silently report the regression totals as the smoke gate.
        if not OUT.exists():
            sys.exit(f"{OUT.relative_to(ROOT)} does not exist yet - run without "
                     "--no-run once to record the numbers.")
        recorded = json.loads(OUT.read_text(encoding="utf-8"))
        update_readme(recorded)
        print("  re-rendered from %s (no suites run)" % OUT.relative_to(ROOT))
        return
    suites = {k: run(k) for k in SUITES}

    headline = {
        "total": sum(suites[k]["total"] for k in HEADLINE),
        "passed": sum(suites[k]["passed"] for k in HEADLINE),
        "failed": sum(suites[k]["failed"] for k in HEADLINE),
    }
    headline["pass_rate"] = round(
        100.0 * headline["passed"] / headline["total"], 1) if headline["total"] else 0.0

    coverage = None
    try:
        total = json.loads((PW / "coverage" / "coverage-summary.json")
                           .read_text(encoding="utf-8"))["total"]
        coverage = {m: total[m]["pct"] for m in
                    ("statements", "branches", "functions", "lines") if m in total}
    except Exception:
        pass

    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"headline_scope": list(HEADLINE), "headline": headline,
         "coverage": coverage, "commit": sha, "suites": suites},
        indent=2) + "\n", encoding="utf-8")

    print()
    print(f"headline (smoke gate): {headline['passed']}/{headline['total']} passed"
          f" - {headline['pass_rate']}% pass rate")
    for k in SUITES:
        s = suites[k]
        print("  %-18s %-11s %2d total  %2d passed  %2d failed"
              % (s["label"], s["tool"], s["total"], s["passed"], s["failed"]))
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    update_readme(json.loads(OUT.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
