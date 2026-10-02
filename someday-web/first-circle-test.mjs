// First-circle onboarding test: stubs the someday-api at the network layer and
// walks a zero-circle sign-in through create -> invite, then the skip path.
// Usage: UI_BASE=http://localhost:3001 node first-circle-test.mjs
import { chromium } from "playwright";
import { readFileSync } from "fs";

const BASE = process.env.UI_BASE ?? "http://localhost:3001";

const env = Object.fromEntries(
  readFileSync(".env.local", "utf8")
    .split("\n")
    .filter((l) => l.includes("="))
    .map((l) => [l.slice(0, l.indexOf("=")), l.slice(l.indexOf("=") + 1)]),
);
const ref = new URL(env.NEXT_PUBLIC_SUPABASE_URL).hostname.split(".")[0];
const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
const USER_ID = "00000000-0000-0000-0000-000000000001";
const exp = Math.floor(Date.now() / 1000) + 60 * 60 * 24;
const jwt = `${b64({ alg: "HS256", typ: "JWT" })}.${b64({ sub: USER_ID, email: "t@t.io", exp, aud: "authenticated", role: "authenticated" })}.x`;
const session = {
  access_token: jwt, refresh_token: "fake-refresh", expires_at: exp, expires_in: 86400,
  token_type: "bearer", user: { id: USER_ID, email: "t@t.io", aud: "authenticated" },
};
const user = { id: USER_ID, email: "t@t.io", display_name: "tester", avatar_url: null, tour_state: { seen: [] } };
const created = {
  id: "c1", name: "Sunday people", emoji: null, owner_id: USER_ID, invite_token: "tok123",
  member_count: 1, open_intent_count: 0, created_at: "2026-06-01T00:00:00Z",
};

const failures = [];
function check(name, cond) {
  console.log(`${cond ? "PASS" : "FAIL"} ${name}`);
  if (!cond) failures.push(name);
}

const browser = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const API = (env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function newPage() {
  const ctx = await browser.newContext({ viewport: { width: 375, height: 812 } });
  await ctx.addInitScript(([k, v]) => localStorage.setItem(k, v), [`sb-${ref}-auth-token`, JSON.stringify(session)]);
  let circles = [];
  await ctx.route(`${API}/auth/me`, (r) => r.fulfill({ json: { user, circles } }));
  await ctx.route(`${API}/circles`, (r) => {
    circles = [created];
    return r.fulfill({ json: created });
  });
  await ctx.route(`${API}/notifications`, (r) => r.fulfill({ json: { items: [], unseen: 0 } }));
  await ctx.route(`${API}/tour/seen`, (r) => r.fulfill({ json: { tour_state: { seen: [] } } }));
  const page = await ctx.newPage();
  page.on("pageerror", (e) => failures.push(`page error: ${e.message}`));
  return page;
}

// 1. Zero circles -> the step, then create -> invite stays up after reload of me()
let page = await newPage();
await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
check("zero circles shows the first-circle step", await page.getByText("Who do you make plans with?").isVisible());
await page.getByLabel("Circle name").fill("Sunday people");
await page.getByRole("button", { name: "Create circle" }).click();
await page.getByText("Invite them to Sunday people").waitFor({ timeout: 5000 });
const wa = page.getByRole("link", { name: "Share on WhatsApp" });
const href = (await wa.getAttribute("href")) ?? "";
check("WhatsApp link targets wa.me with the invite URL", href.startsWith("https://wa.me/?text=") && decodeURIComponent(href).includes("/join/tok123"));
check("invite link is shown", await page.getByText(`${BASE}/join/tok123`).isVisible());
check("copy button is shown", await page.getByRole("button", { name: "Copy link" }).isVisible());
check("onboarding tour step appears", await page.getByText("Send it where you already talk").isVisible());
await page.context().close();

// 2. Skip -> dashboard, and the step does not come back on reload
page = await newPage();
await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Skip for now" }).click();
check("skip shows the dashboard", await page.getByText("New Circle").isVisible());
await page.reload({ waitUntil: "networkidle" });
check("skip persists across reloads", !(await page.getByText("Who do you make plans with?").isVisible()));
await page.context().close();

await browser.close();
if (failures.length) {
  console.log(`\n${failures.length} failure(s):\n- ${failures.join("\n- ")}`);
  process.exit(1);
}
