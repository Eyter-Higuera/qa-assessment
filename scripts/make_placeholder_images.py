#!/usr/bin/env python3
"""Generate placeholder PNGs for the screenshots the testing manual references.

The manual points at ten screenshots that have to be captured by hand. Until
they are, the references would render as broken images on GitHub and as gaps in
testing_report.pdf. This writes a labelled placeholder for each one
instead: same filename, same aspect, and the command to run written across it,
so the document is presentable and every slot says what belongs in it.

    python scripts/make_placeholder_images.py            # only what is missing
    python scripts/make_placeholder_images.py --force    # rewrite every one

Replacing a placeholder is just dropping the real capture over it - nothing
references these as placeholders, only by name.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"
SIZE = (1200, 640)

BG = (248, 250, 252)
BORDER = (182, 194, 210)
TITLE = (31, 78, 121)
BODY = (71, 85, 105)
FAINT = (148, 163, 184)

# filename -> (what the screenshot should show, the command that produces it)
SHOTS = {
    "local-unit-coverage.png": (
        "Unit test coverage in the terminal",
        "npm run test:unit -- --coverage"),
    "local-karate-dev.png": (
        "Karate smoke against dev",
        "mvn test -Dtest=SmokeTest -Dkarate.env=dev"),
    "local-karate-release.png": (
        "Karate regression against release",
        "mvn test -Dtest=BookStoreApiTest -Dkarate.env=release"),
    "local-karate-production.png": (
        "Karate smoke against production",
        "mvn test -Dtest=SmokeTest -Dkarate.env=production"),
    "local-playwright-dev.png": (
        "Playwright smoke against dev",
        "npx playwright test --project=chromium --grep @smoke"),
    "local-playwright-release.png": (
        "Playwright regression across browsers",
        "npx playwright test --project=chromium --project=firefox "
        "--project=webkit --project=msedge"),
    "local-playwright-production.png": (
        "Playwright smoke against production",
        "npx playwright test --project=msedge --grep @smoke"),
    "ci-scenario-a-eyter-dev.png": (
        "Scenario A - full chain from eyter_dev",
        "Actions > QA Automation > Run workflow, from eyter_dev, Promote ticked"),
    "ci-scenario-b-release-main.png": (
        "Scenario B - single stage from release or main",
        "Actions > QA Automation > Run workflow, from release or main"),
    "ci-job-summary.png": (
        "The GitHub job summary",
        "The Summary tab of any completed run"),
}


def font(size: int, bold: bool = False):
    for name in (("seguisb.ttf", "segoeuib.ttf") if bold else ("segoeui.ttf",)) + (
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def wrap(draw, text, fnt, max_width):
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_placeholder(path: Path, caption: str, command: str) -> None:
    img = Image.new("RGB", SIZE, BG)
    d = ImageDraw.Draw(img)

    # Dashed border, so it reads as a placeholder at a glance rather than as a
    # screenshot someone forgot to crop.
    w, h = SIZE
    for x in range(12, w - 12, 26):
        d.line([(x, 12), (min(x + 13, w - 12), 12)], fill=BORDER, width=3)
        d.line([(x, h - 12), (min(x + 13, w - 12), h - 12)], fill=BORDER, width=3)
    for y in range(12, h - 12, 26):
        d.line([(12, y), (12, min(y + 13, h - 12))], fill=BORDER, width=3)
        d.line([(w - 12, y), (w - 12, min(y + 13, h - 12))], fill=BORDER, width=3)

    f_small, f_title, f_cmd = font(22), font(38, bold=True), font(21)
    d.text((w / 2, 190), "SCREENSHOT PLACEHOLDER", font=f_small, fill=FAINT, anchor="mm")

    y = 252
    for line in wrap(d, caption, f_title, w - 200):
        d.text((w / 2, y), line, font=f_title, fill=TITLE, anchor="mm")
        y += 50

    y += 22
    d.text((w / 2, y), "Capture with:", font=f_small, fill=FAINT, anchor="mm")
    y += 38
    for line in wrap(d, command, f_cmd, w - 160):
        d.text((w / 2, y), line, font=f_cmd, fill=BODY, anchor="mm")
        y += 30

    d.text((w / 2, h - 46), f"docs/images/{path.name}", font=f_small, fill=FAINT, anchor="mm")
    img.save(path, "PNG", optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="overwrite placeholders that already exist")
    args = ap.parse_args()

    IMAGES.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    for name, (caption, command) in SHOTS.items():
        target = IMAGES / name
        if target.exists() and not args.force:
            # Never clobber a real capture someone has put here.
            skipped += 1
            continue
        draw_placeholder(target, caption, command)
        written += 1
    print(f"{written} written, {skipped} left alone (already present)")


if __name__ == "__main__":
    main()
