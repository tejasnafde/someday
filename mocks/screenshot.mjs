// Run from someday-web/ (where playwright lives):
//   cd someday-web && node ../mocks/screenshot.mjs <html-file> [<html-file>...]
// Fails CI/process if any image fails to render or any console error fires.
import { chromium } from "playwright";
import { mkdirSync } from "fs";
import { resolve, basename, dirname } from "path";

const files = process.argv.slice(2);
if (!files.length) { console.error("usage: screenshot.mjs <file.html> ..."); process.exit(1); }

mkdirSync(resolve(dirname(files[0]), "screenshots"), { recursive: true });

const browser = await chromium.launch();
let bad = 0;
for (const f of files) {
  const url = "file://" + resolve(f);
  const ctx = await browser.newContext({ viewport: { width: 880, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForTimeout(400); // font swap settles
  const out = resolve(dirname(f), "screenshots", basename(f).replace(/\.html$/, "") + ".png");
  await page.screenshot({ path: out, fullPage: true });
  if (errors.length) { console.error(`✗ ${basename(f)}`); errors.forEach((e) => console.error("  ", e)); bad++; }
  else console.log(`✓ ${out}`);
  await ctx.close();
}
await browser.close();
process.exit(bad ? 1 : 0);
