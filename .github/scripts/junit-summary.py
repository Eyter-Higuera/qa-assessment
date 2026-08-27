#!/usr/bin/env python3
"""Render JUnit XML as a GitHub run-summary section.

Both suites emit JUnit XML - Playwright through its `junit` reporter, Karate
through outputJunitXml(true) - so one reader serves both and the two stages read
alike on the summary page.

Writes GitHub-flavoured markdown to stdout; the caller appends it to
$GITHUB_STEP_SUMMARY. Nothing here fails a build: a summary that blew up while
reporting a failure would hide the thing worth seeing, so parse errors are
reported as text and the exit code stays 0.

    junit-summary.py "Karate - dev - smoke" 'karate/target/karate-reports/*.xml'
"""
import glob
import sys
import xml.etree.ElementTree as ET

MAX_FAILURES = 20


def suites(paths):
    """Yield every <testsuite>, whether or not a <testsuites> wraps it."""
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            print("> Could not read `%s`: %s\n" % (path, exc))
            continue
        if root.tag == "testsuite":
            yield root
        else:
            for suite in root.iter("testsuite"):
                yield suite


def classify(case):
    """JUnit encodes outcome as the presence of a child element, not a status."""
    if case.find("failure") is not None:
        return "failed", case.find("failure")
    if case.find("error") is not None:
        return "failed", case.find("error")
    if case.find("skipped") is not None:
        return "skipped", None
    return "passed", None


def detail(node):
    """First meaningful line of a failure, short enough for a table cell."""
    text = (node.get("message") or node.text or "").strip()
    for line in text.splitlines():
        line = line.strip()
        if line:
            return (line[:157] + "...") if len(line) > 160 else line
    return "no message"


def main():
    title = sys.argv[1]
    paths = sorted({p for pattern in sys.argv[2:] for p in glob.glob(pattern)})

    print("## %s\n" % title)
    if not paths:
        print("> No JUnit XML was produced, so there is nothing to report here.")
        print("> The suite may have failed before it could run a single test.\n")
        return

    rows, failures = [], []
    totals = {"passed": 0, "failed": 0, "skipped": 0}
    grand_time = 0.0

    for suite in suites(paths):
        counts = {"passed": 0, "failed": 0, "skipped": 0}
        for case in suite.iter("testcase"):
            outcome, node = classify(case)
            counts[outcome] += 1
            totals[outcome] += 1
            if node is not None:
                failures.append((case.get("classname") or suite.get("name") or "",
                                 case.get("name") or "", detail(node)))
        try:
            seconds = float(suite.get("time") or 0)
        except ValueError:
            seconds = 0.0
        grand_time += seconds
        if sum(counts.values()):
            rows.append((suite.get("name") or "(unnamed)", counts, seconds))

    total = sum(totals.values())
    if not total:
        # Files existed but held no test cases - a truncated or unreadable
        # report. Saying "passed" here would be exactly the false green this
        # summary exists to prevent.
        print("> The report held no test cases. Treat this as a reporting")
        print("> failure, not as a pass - check the step log above.\n")
        return
    verdict = "**FAILED**" if totals["failed"] else "passed"
    print("%s - %d test%s in %.1fs: %d passed, %d failed, %d skipped\n"
          % (verdict, total, "" if total == 1 else "s", grand_time,
             totals["passed"], totals["failed"], totals["skipped"]))

    print("| Suite | Passed | Failed | Skipped | Duration |")
    print("|---|--:|--:|--:|--:|")
    for name, counts, seconds in rows:
        mark = " :x:" if counts["failed"] else ""
        print("| %s%s | %d | %d | %d | %.1fs |"
              % (name, mark, counts["passed"], counts["failed"],
                 counts["skipped"], seconds))
    print()

    if failures:
        print("### Failures\n")
        print("| Suite | Test | Detail |")
        print("|---|---|---|")
        for classname, name, why in failures[:MAX_FAILURES]:
            # Escape pipes so a failure message cannot break the table apart.
            cells = [c.replace("|", "\\|") for c in (classname, name, why)]
            print("| %s | %s | %s |" % tuple(cells))
        if len(failures) > MAX_FAILURES:
            print("\n_%d further failures omitted; the uploaded report has them all._"
                  % (len(failures) - MAX_FAILURES))
        print()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never fail a build over its own summary
        print("> The run summary could not be rendered: %s\n" % exc)
