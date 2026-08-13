import assert from "node:assert/strict";
import test from "node:test";
import { normalizeSharePayload } from "../lib/sharePayload.cjs";

test("extracts an Instagram URL from shared text", () => {
  assert.deepEqual(
    normalizeSharePayload({
      text: "Watch this reel https://www.instagram.com/reel/ABC123/?igsh=sample",
      webUrl: null,
      files: [],
    }),
    {
      url: "https://www.instagram.com/reel/ABC123/?igsh=sample",
      text: "Watch this reel https://www.instagram.com/reel/ABC123/?igsh=sample",
      hasMedia: false,
      needsLink: false,
    },
  );
});

test("prefers the structured web URL", () => {
  assert.equal(
    normalizeSharePayload({
      text: "A reel",
      webUrl: "https://instagram.com/reel/structured",
      files: [],
    }).url,
    "https://instagram.com/reel/structured",
  );
});

test("keeps useful text when a media share has no URL", () => {
  assert.deepEqual(
    normalizeSharePayload({
      text: "Plan this hike",
      webUrl: null,
      files: [{ mimeType: "image/jpeg" }],
    }),
    {
      url: null,
      text: "Plan this hike",
      hasMedia: true,
      needsLink: false,
    },
  );
});

test("requests a link when a media-only share has no useful text", () => {
  assert.deepEqual(
    normalizeSharePayload({
      text: "  ",
      webUrl: null,
      files: [{ mimeType: "video/mp4" }],
    }),
    {
      url: null,
      text: "",
      hasMedia: true,
      needsLink: true,
    },
  );
});
