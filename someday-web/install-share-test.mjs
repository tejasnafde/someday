import { chromium, request as createRequest } from "playwright";
import { mkdirSync, readFileSync } from "node:fs";

const BASE = process.env.UI_BASE ?? "http://localhost:3001";
const env = Object.fromEntries(
  readFileSync(".env.local", "utf8")
    .split("\n")
    .filter((line) => line.includes("="))
    .map((line) => [line.slice(0, line.indexOf("=")), line.slice(line.indexOf("=") + 1)]),
);
const API = (env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const ref = new URL(env.NEXT_PUBLIC_SUPABASE_URL).hostname.split(".")[0];
const encode = (value) => Buffer.from(JSON.stringify(value)).toString("base64url");
const userId = "00000000-0000-0000-0000-000000000001";
const expiresAt = Math.floor(Date.now() / 1000) + 86400;
const token = `${encode({ alg: "HS256", typ: "JWT" })}.${encode({ sub: userId, exp: expiresAt, role: "authenticated" })}.x`;
const session = {
  access_token: token,
  refresh_token: "fake-refresh",
  expires_at: expiresAt,
  expires_in: 86400,
  token_type: "bearer",
  user: { id: userId, email: "test@example.com", aud: "authenticated" },
};
const user = { id: userId, email: "test@example.com", display_name: "Tester", avatar_url: null };
const circle = {
  id: "circle-one",
  name: "Weekend plans",
  emoji: null,
  owner_id: userId,
  invite_token: "invite",
  member_count: 2,
  open_intent_count: 3,
  created_at: "2026-08-01T00:00:00Z",
};

const failures = [];
function check(name, condition) {
  console.log(`${condition ? "✓" : "✗"} ${name}`);
  if (!condition) failures.push(name);
}

function addSession(context) {
  return context.addInitScript(
    ([key, value]) => localStorage.setItem(key, value),
    [`sb-${ref}-auth-token`, JSON.stringify(session)],
  );
}

async function stubApi(context) {
  await context.route(`${API}/auth/me`, (route) => route.fulfill({ json: { user, circles: [circle] } }));
  await context.route(`${API}/unfurl`, (route) => route.fulfill({
    json: { title: "A reel worth saving", image: null, site: "Instagram" },
  }));
}

mkdirSync("screenshots", { recursive: true });
const api = await createRequest.newContext();
const receive = await api.post(`${BASE}/share/receive`, {
  multipart: {
    title: "Morning reel",
    text: "Watch this https://www.instagram.com/reel/ABC123/",
    url: "",
  },
  maxRedirects: 0,
});
check("share receiver responds with See Other", receive.status() === 303);
const location = receive.headers().location ?? "";
check("share receiver redirects to same-origin capture", location.startsWith(`${BASE}/share?`));
check("share receiver preserves the Instagram URL", location.includes(encodeURIComponent("https://www.instagram.com/reel/ABC123/")));
await api.dispose();

const browser = await chromium.launch();
const errors = [];

const android = await browser.newContext({
  viewport: { width: 390, height: 844 },
  userAgent: "Mozilla/5.0 (Linux; Android 16; CPH2747) AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36",
});
await addSession(android);
await stubApi(android);
const androidPage = await android.newPage();
androidPage.on("pageerror", (error) => errors.push(error.message));
await androidPage.goto(`${BASE}/settings`, { waitUntil: "networkidle" });
check("Android Settings recommends the APK", await androidPage.getByText("Save reels and links straight from Android's share sheet.").isVisible());
const apkLink = androidPage.getByRole("link", { name: "Download latest Android APK" });
check("Android Settings uses the permanent latest-release URL", await apkLink.getAttribute("href") === "https://github.com/tejasnafde/someday/releases/latest/download/someday.apk");
await androidPage.screenshot({ path: "screenshots/install-android.png", fullPage: true });
await android.close();

const ios = await browser.newContext({
  viewport: { width: 390, height: 844 },
  userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 Version/19.0 Mobile/15E148 Safari/604.1",
});
await addSession(ios);
await stubApi(ios);
const iosPage = await ios.newPage();
iosPage.on("pageerror", (error) => errors.push(error.message));
await iosPage.goto(`${BASE}/settings`, { waitUntil: "networkidle" });
check("iOS Settings shows Safari Home Screen instructions", await iosPage.getByText("Choose Add to Home Screen, then tap Add.").isVisible());
await iosPage.screenshot({ path: "screenshots/install-ios.png", fullPage: true });
await ios.close();

const share = await browser.newContext({ viewport: { width: 390, height: 844 } });
await addSession(share);
await stubApi(share);
const sharePage = await share.newPage();
sharePage.on("pageerror", (error) => errors.push(error.message));
await sharePage.goto(`${BASE}/share?title=Morning%20reel&url=https%3A%2F%2Fwww.instagram.com%2Freel%2FABC123%2F`, { waitUntil: "networkidle" });
check("shared title is editable", await sharePage.getByPlaceholder("What’s the plan?").inputValue() === "Morning reel");
check("shared URL is editable", await sharePage.getByPlaceholder("Paste the shared link").inputValue() === "https://www.instagram.com/reel/ABC123/");
check("circle picker loads the user's circles", await sharePage.getByRole("button", { name: /Weekend plans/ }).isVisible());
await sharePage.getByRole("button", { name: /Weekend plans/ }).click();
await sharePage.getByRole("button", { name: "Continue" }).click();
await sharePage.waitForURL(/\/circles\/circle-one\/add\?/);
check("capture continues into the existing add flow", sharePage.url().includes("title=Morning+reel") && sharePage.url().includes("url=https"));
await sharePage.screenshot({ path: "screenshots/shared-add-flow.png", fullPage: true });
await share.close();

await browser.close();
check("browser run has no page errors", errors.length === 0);
if (errors.length) errors.forEach((error) => console.error(`  ${error}`));

if (failures.length) {
  console.error(`\n${failures.length} checks failed`);
  process.exit(1);
}
console.log("\nall install and share browser checks passed");
