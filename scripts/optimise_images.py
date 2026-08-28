#!/usr/bin/env python3
"""Shrink the documentation screenshots without touching their resolution.

The terminal captures are 2400px wide but contain only a couple of thousand
distinct colours, so a 256-colour palette is visually lossless on them and
roughly halves the file. That matters because the images are most of
testing_manual_report.pdf, and a large PDF is what GitHub's in-browser viewer
declines to render.

Downscaling was tried first and made things WORSE - resampling a screenshot of
flat-coloured text invents thousands of intermediate colours, and the same image
at 1800px came out at 1103 KB against 446 KB at 2400px. Resolution is not the
problem; colour depth is.

    python scripts/optimise_images.py            # optimise, in place
    python scripts/optimise_images.py --check    # report only, change nothing

Only the generated `local-*.png` captures are touched. The hand-taken ci-*.png
screenshots are left alone on principle. An image is rewritten only when
quantising actually makes it smaller and it has few enough colours for the
palette to be faithful, so gradient-heavy images are skipped too.
"""
from __future__ import annotations

import argparse
import io
import os
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "docs" / "images"

# Above this many distinct colours a 256-entry palette starts to show banding,
# so the image is left as it is rather than quietly degraded.
MAX_COLOURS = 12_000
PALETTE = 256


def distinct_colours(im: Image.Image) -> int:
    colours = im.convert("RGB").getcolors(maxcolors=1 << 24)
    return len(colours) if colours else 1 << 24


def quantised_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.convert("RGB").quantize(colors=PALETTE, method=Image.MEDIANCUT).save(
        buf, format="PNG", optimize=True)
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report what would change without writing anything")
    args = ap.parse_args()

    before = after = 0
    changed = skipped = 0
    # Only the captures this repository generates. The ci-*.png files are
    # screenshots someone took by hand; re-encoding another person's image
    # without being asked is not this script's business, and they are small.
    for path in sorted(IMAGES.glob("local-*.png")):
        original = path.stat().st_size
        before += original
        with Image.open(path) as im:
            colours = distinct_colours(im)
            if colours > MAX_COLOURS:
                after += original
                skipped += 1
                print("  %-40s %5d KB  left alone (%d colours)"
                      % (path.name, original // 1024, colours))
                continue
            data = quantised_bytes(im)

        if len(data) >= original:
            after += original
            skipped += 1
            print("  %-40s %5d KB  left alone (already smaller)"
                  % (path.name, original // 1024))
            continue

        after += len(data)
        changed += 1
        saved = 100 * (original - len(data)) / original
        print("  %-40s %5d KB -> %5d KB  (-%.0f%%)"
              % (path.name, original // 1024, len(data) // 1024, saved))
        if not args.check:
            path.write_bytes(data)

    print()
    print("  %d optimised, %d left alone" % (changed, skipped))
    print("  total %d KB -> %d KB (-%.0f%%)%s"
          % (before // 1024, after // 1024,
             100 * (before - after) / before if before else 0,
             "   [--check: nothing written]" if args.check else ""))


if __name__ == "__main__":
    main()
