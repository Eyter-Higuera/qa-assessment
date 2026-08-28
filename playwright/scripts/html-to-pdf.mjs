/**
 * Render a local HTML file to PDF using the Chromium this project already
 * installs for Playwright.
 *
 * WeasyPrint is the usual choice for this and is what the report script reaches
 * for first, but it needs GTK/Pango/Cairo natively and cannot be installed on a
 * stock Windows machine without an elevated system install. Chromium is already
 * here, prints CSS faithfully, and needs nothing new.
 *
 *   node scripts/html-to-pdf.mjs <input.html> <output.pdf>
 *
 * Must run with this directory as cwd so `playwright` resolves from
 * playwright/node_modules.
 */
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const [input, output, footerLabel] = process.argv.slice(2);
if (!input || !output) {
  console.error('usage: node scripts/html-to-pdf.mjs <input.html> <output.pdf> [footer]');
  process.exit(2);
}

const browser = await chromium.launch();
try {
  // Light scheme explicitly: a document with a prefers-color-scheme block would
  // otherwise render dark if the machine is set that way, and a dark PDF is
  // never what anyone wanted from a print.
  const page = await browser.newPage({ colorScheme: 'light' });
  // networkidle so late-loading images and webfonts are in place before printing.
  await page.goto(pathToFileURL(resolve(input)).href, { waitUntil: 'networkidle' });
  // Falls back to the document's own <title> so each document footers itself.
  const label = footerLabel ?? (await page.title()) ?? '';
  await page.pdf({
    path: resolve(output),
    format: 'A4',
    // Without this every background colour renders white and the styling is lost.
    printBackground: true,
    margin: { top: '16mm', bottom: '18mm', left: '14mm', right: '14mm' },
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: `
      <div style="width:100%;font-size:8pt;color:#6b7280;padding:0 14mm;
                  font-family:-apple-system,Segoe UI,sans-serif;
                  display:flex;justify-content:space-between;">
        <span>${label.replace(/[<>&]/g, '')}</span>
        <span class="pageNumber"></span>/<span class="totalPages"></span>
      </div>`,
  });
  console.log(`wrote ${output}`);
} finally {
  await browser.close();
}
