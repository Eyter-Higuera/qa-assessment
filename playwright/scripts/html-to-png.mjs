/**
 * Screenshot a local HTML file with the Chromium Playwright already installs.
 *
 *   node scripts/html-to-png.mjs <input.html> <output.png> [widthPx]
 *
 * Used by scripts/capture_terminal_screenshots.py to turn captured terminal
 * output into the images the testing manual embeds. Must run with this
 * directory as cwd so `playwright` resolves from playwright/node_modules.
 */
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const [input, output, width = '1200'] = process.argv.slice(2);
if (!input || !output) {
  console.error('usage: node scripts/html-to-png.mjs <input.html> <output.png> [width]');
  process.exit(2);
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage({
    viewport: { width: Number(width), height: 800 },
    // Renders text at 2x so the image stays sharp when scaled to page width.
    deviceScaleFactor: 2,
  });
  await page.goto(pathToFileURL(resolve(input)).href, { waitUntil: 'networkidle' });
  // Prefer the card element: a fullPage shot pads out to the viewport height,
  // leaving dead space under short output. Falls back to fullPage so this stays
  // usable for any other page.
  const card = page.locator('.win');
  if (await card.count()) {
    await card.first().screenshot({ path: resolve(output) });
  } else {
    await page.screenshot({ path: resolve(output), fullPage: true });
  }
} finally {
  await browser.close();
}
