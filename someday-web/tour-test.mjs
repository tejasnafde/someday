// Tour behavior test: stubs the someday-api at the network layer and walks the
// first-login tour, skip persistence, circle mini-tour, and replay flow.
// Usage: UI_BASE=http://localhost:3001 node tour-test.mjs
import { chromium } from "playwright";
import { mkdirSync, readFileSync } from "fs";

const BASE = process.env.UI_BASE ?? "http://localhost:3001";
mkdirSync("screenshots", { recursive: true });

// --- fake supabase session (client never verifies the signature) ---
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
  access_token: jwt,
  refresh_token: "fake-refresh",
  expires_at: exp,
  expires_in: 86400,
  token_type: "bearer",
  user: { id: USER_ID, email: "t@t.io", aud: "authenticated" },
};

// --- mutable fake backend state ---
let seen = [];
const seenPosts = [];
const user = () => ({
  id: USER_ID,
  email: "t@t.io",
  display_name: "tester",
  avatar_url: null,
  tour_state: { seen: [...seen] },
});
const circle = {
  id: "c1",
  name: "Movie nights",
  emoji: null,
  owner_id: USER_ID,
  invite_token: "tok",
  member_count: 2,
  open_intent_count: 1,
  created_at: "2026-06-01T00:00:00Z",
};
const intent = {
  id: "i1",
  circle_id: "c1",
  created_by: USER_ID,
  title: "Watch Spirited Away",
  url: null,
  note: null,
  category: "watch",
  tags: [],
  task_status: "saved",
  link_meta: null,
  planned_for: null,
  reaction_count: 1,
  boosted_by_me: false,
  reacted_by_me: false,
  created_at: "2026-06-02T00:00:00Z",
  updated_at: "2026-06-02T00:00:00Z",
};

const failures = [];
function check(name, cond) {
  console.log(`${cond ? "✓" : "✗"} ${name}`);
  if (!cond) failures.push(name);
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
await ctx.addInitScript(
  ([k, v]) => localStorage.setItem(k, v),
  [`sb-${ref}-auth-token`, JSON.stringify(session)],
);

// Scope stubs to the API origin so app page routes (/circles/c1) aren't intercepted.
const API = (env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
await ctx.route(`${API}/auth/me`, (r) =>
  r.fulfill({ json: { user: user(), circles: [circle] } }),
);
await ctx.route(`${API}/circles/c1`, (r) =>
  r.fulfill({ json: { ...circle, members: [{ user_id: USER_ID, display_name: "tester", avatar_url: null, role: "owner", joined_at: "2026-06-01T00:00:00Z" }] } }),
);
await ctx.route(`${API}/circles/c1/intents*`, (r) => r.fulfill({ json: [intent] }));
await ctx.route(`${API}/tour/seen`, async (r) => {
  const body = r.request().postDataJSON();
  seenPosts.push(body.step_ids);
  seen = [...new Set([...seen, ...body.step_ids])];
  await r.fulfill({ json: { tour_state: { seen: [...seen] } } });
});
await ctx.route(`${API}/tour/reset`, async (r) => {
  seen = [];
  await r.fulfill({ json: { tour_state: { seen: [] } } });
});

const page = await ctx.newPage();
const pageErrors = [];
page.on("pageerror", (e) => pageErrors.push(e.message));

// 1. First login → dashboard tour runs
await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await page.waitForTimeout(400);
check("dashboard tour appears on first login", await page.getByText("Welcome to Someday").isVisible());
await page.screenshot({ path: "screenshots/tour-1-welcome.png" });

await page.getByRole("button", { name: "Next", exact: true }).click();
await page.waitForTimeout(350);
check("step 2 anchors to create-circle", await page.getByText("Start a circle").isVisible());
await page.screenshot({ path: "screenshots/tour-2-create.png" });

await page.getByRole("button", { name: "Next", exact: true }).click();
await page.waitForTimeout(350);
check("step 3 anchors to settings", await page.getByText("Make it yours").isVisible());

await page.getByRole("button", { name: "Done" }).click();
await page.waitForTimeout(600);
check("overlay closes after Done", !(await page.getByText("Make it yours").isVisible()));
check(
  "dash steps flushed to /tour/seen",
  JSON.stringify(seenPosts[0]?.toSorted()) === JSON.stringify(["dash.create", "dash.settings", "dash.welcome"]),
);

// 2. Reload → no tour (server remembers)
await page.evaluate(() => localStorage.removeItem("someday:cache")); // drop SWR cache if keyed differently this is harmless
await page.reload({ waitUntil: "networkidle" });
await page.waitForTimeout(600);
check("no tour on reload once seen", !(await page.getByText("Welcome to Someday").isVisible()));
await page.screenshot({ path: "screenshots/tour-3-no-replay.png" });

// 3. First circle visit → circle mini-tour, then Skip marks the rest
await page.goto(`${BASE}/circles/c1`, { waitUntil: "networkidle" });
await page.waitForTimeout(600);
check("circle tour auto-starts on first circle visit", await page.getByText("Save an idea").isVisible());
await page.screenshot({ path: "screenshots/tour-4-circle.png" });
await page.getByRole("button", { name: "Skip tour" }).click();
await page.waitForTimeout(600);
const allCircle = ["circle.add", "circle.status", "circle.reactions", "circle.payoff", "circle.invite"];
check("skip flushes all circle steps", allCircle.every((id) => seen.includes(id)));
check("no circle tour after skip", !(await page.getByText("Save an idea").isVisible()));

// 4. Replay from settings
await page.goto(`${BASE}/settings`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Replay tour" }).click();
await page.waitForURL(`${BASE}/`);
await page.waitForTimeout(800);
check("replay resets and restarts tour", await page.getByText("Welcome to Someday").isVisible());

// 5. Dark mode render
const dark = await ctx.newPage();
await dark.addInitScript(() => localStorage.setItem("theme", "dark"));
await dark.goto(`${BASE}/`, { waitUntil: "networkidle" });
await dark.waitForTimeout(600);
await dark.screenshot({ path: "screenshots/tour-5-dark.png" });
check("tour renders in dark mode", await dark.getByText("Welcome to Someday").isVisible());

check("no page errors", pageErrors.length === 0);
if (pageErrors.length) pageErrors.forEach((e) => console.error(`  pageerror: ${e}`));

await browser.close();
if (failures.length) {
  console.error(`\n${failures.length} FAILED`);
  process.exit(1);
}
console.log("\nall tour checks passed");
