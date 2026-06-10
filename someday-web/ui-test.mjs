// UI smoke test: screenshots every screen in light+dark, fails on console errors.
// Usage: node ui-test.mjs [--auth <supabase-session-json>] [--routes /login,/]
import { chromium } from "playwright";
import { mkdirSync } from "fs";

const args = process.argv.slice(2);
const authIdx = args.indexOf("--auth");
const sessionJson = authIdx >= 0 ? args[authIdx + 1] : null;
const routesIdx = args.indexOf("--routes");
const routes = routesIdx >= 0 ? args[routesIdx + 1].split(",") : ["/login"];

const BASE = "http://localhost:3000";
mkdirSync("screenshots", { recursive: true });

const browser = await chromium.launch();
const errors = [];
let shot = 0;

for (const theme of ["light", "dark"]) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });

  if (sessionJson) {
    const session = JSON.parse(sessionJson);
    const key = `sb-${new URL(process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321").hostname.split(".")[0]}-auth-token`;
    await ctx.addInitScript(
      ([k, v]) => localStorage.setItem(k, v),
      [key, JSON.stringify(session)],
    );
  }
  await ctx.addInitScript((t) => localStorage.setItem("theme", t), theme);

  const page = await ctx.newPage();
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(`[${theme}] ${page.url()}: ${msg.text()}`);
  });
  page.on("pageerror", (err) => errors.push(`[${theme}] ${page.url()}: ${err.message}`));

  for (const route of routes) {
    await page.goto(`${BASE}${route}`, { waitUntil: "networkidle" });
    const name = route === "/" ? "home" : route.replaceAll("/", "_").replace(/^_/, "");
    await page.screenshot({ path: `screenshots/${name}-${theme}.png` });
    shot++;
    console.log(`✓ ${route} [${theme}]`);
  }
  await ctx.close();
}

await browser.close();

if (errors.length) {
  console.error(`\n${errors.length} console errors:`);
  errors.forEach((e) => console.error(`  ✗ ${e}`));
  process.exit(1);
}
console.log(`\n${shot} screenshots, 0 console errors`);
