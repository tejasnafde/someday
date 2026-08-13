import assert from "node:assert/strict";
import test from "node:test";
import { normalizeWebShare } from "../lib/webShare.cjs";

test("normalizes a structured shared URL and title", () => {
  assert.deepEqual(
    normalizeWebShare({
      title: "A reel",
      text: "Sent from Instagram",
      url: "https://www.instagram.com/reel/ABC123/",
    }),
    {
      title: "A reel",
      text: "Sent from Instagram",
      url: "https://www.instagram.com/reel/ABC123/",
    },
  );
});

test("extracts a URL embedded in shared text", () => {
  assert.equal(
    normalizeWebShare({
      title: "",
      text: "Watch https://example.com/reel/one now",
      url: "",
    }).url,
    "https://example.com/reel/one",
  );
});

test("rejects non-http URLs", () => {
  assert.equal(
    normalizeWebShare({ title: "", text: "", url: "javascript:alert(1)" }).url,
    "",
  );
});

test("uses useful shared text as the fallback title", () => {
  assert.equal(
    normalizeWebShare({ title: "", text: "Plan this hike", url: "" }).title,
    "Plan this hike",
  );
});

test("bounds untrusted share fields before putting them in a redirect URL", () => {
  const shared = normalizeWebShare({ title: "", text: "a".repeat(5000), url: "" });
  assert.equal(shared.title.length, 120);
  assert.equal(shared.text.length, 2000);
});
