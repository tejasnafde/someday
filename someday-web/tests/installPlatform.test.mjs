import assert from "node:assert/strict";
import test from "node:test";
import { detectInstallPlatform } from "../lib/installPlatform.cjs";

test("standalone mode wins over device detection", () => {
  assert.equal(
    detectInstallPlatform({ userAgent: "Mozilla/5.0 (Linux; Android 16)", platform: "Linux", maxTouchPoints: 5, standalone: true }),
    "installed",
  );
});

test("native Someday WebView is already installed", () => {
  assert.equal(
    detectInstallPlatform({ userAgent: "Mozilla/5.0 SomedayNative/1.14.0", platform: "Linux", maxTouchPoints: 5, standalone: false }),
    "installed",
  );
});

test("detects Android", () => {
  assert.equal(
    detectInstallPlatform({ userAgent: "Mozilla/5.0 (Linux; Android 16)", platform: "Linux", maxTouchPoints: 5, standalone: false }),
    "android",
  );
});

test("detects iPhone and modern iPad desktop user agents", () => {
  assert.equal(
    detectInstallPlatform({ userAgent: "Mozilla/5.0 (iPhone)", platform: "iPhone", maxTouchPoints: 5, standalone: false }),
    "ios",
  );
  assert.equal(
    detectInstallPlatform({ userAgent: "Mozilla/5.0 (Macintosh)", platform: "MacIntel", maxTouchPoints: 5, standalone: false }),
    "ios",
  );
});

test("falls back to desktop", () => {
  assert.equal(
    detectInstallPlatform({ userAgent: "Mozilla/5.0 (X11; Linux x86_64)", platform: "Linux", maxTouchPoints: 0, standalone: false }),
    "desktop",
  );
});
