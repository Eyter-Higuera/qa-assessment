#!/usr/bin/env python3
"""Render Vitest's coverage JSON as a GitHub run-summary section.

Reads coverage/coverage-summary.json - the json-summary reporter - rather than
parsing lcov, because the percentages are already computed there and a summary
that has to derive them is a summary that can disagree with the gate.

Writes GitHub-flavoured markdown to stdout; the caller appends it to
$GITHUB_STEP_SUMMARY. Exit code is always 0: the threshold is enforced by Vitest
itself, and a reporting script that can fail a build would be a second, quieter
gate nobody asked for.

    coverage-summary.py playwright/coverage/coverage-summary.json 80
"""
import json
import os
import sys

METRICS = ("statements", "branches", "functions", "lines")


def pct(entry, metric):
    """A metric with nothing in it is reported by v8 as 100%, which flatters."""
    data = entry.get(metric) or {}
    total = data.get("total", 0)
    return (data.get("pct", 0.0), data.get("covered", 0), total)


def bar(value, threshold):
    return ":white_check_mark:" if value >= threshold else ":x:"


def main():
    path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 80.0

    print("### Unit test coverage\n")
    try:
        with open(path, encoding="utf-8") as fh:
            report = json.load(fh)
    except (OSError, ValueError) as exc:
        print("> No coverage report could be read from `%s`: %s\n" % (path, exc))
        print("> The unit suite may have failed before coverage was written.\n")
        return

    total = report.get("total")
    if not total:
        print("> The coverage report had no totals in it.\n")
        return

    print("| Metric | Covered | Total | %% | Threshold %.0f%% |" % threshold)
    print("|---|--:|--:|--:|:--:|")
    worst = 100.0
    for metric in METRICS:
        value, covered, count = pct(total, metric)
        worst = min(worst, value)
        print("| %s | %d | %d | %.1f%% | %s |"
              % (metric.capitalize(), covered, count, value, bar(value, threshold)))
    print()

    files = [(k, v) for k, v in report.items() if k != "total"]
    if files:
        root = os.getcwd()
        print("<details><summary>Per file (%d)</summary>\n" % len(files))
        print("| File | Statements | Branches | Functions | Lines |")
        print("|---|--:|--:|--:|--:|")
        for name, entry in sorted(files):
            try:
                shown = os.path.relpath(name, root).replace(os.sep, "/")
            except ValueError:      # different drive on Windows
                shown = name.replace(os.sep, "/")
            print("| %s | %.1f%% | %.1f%% | %.1f%% | %.1f%% |"
                  % ((shown,) + tuple(pct(entry, m)[0] for m in METRICS)))
        print("\n</details>\n")

    if worst < threshold:
        print("> Below the %.0f%% floor - Vitest fails the job on this, so the "
              "step above has already gone red.\n" % threshold)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never fail a build over its own summary
        print("> The coverage summary could not be rendered: %s\n" % exc)
