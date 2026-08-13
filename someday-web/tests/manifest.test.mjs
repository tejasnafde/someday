import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("web app registers a POST share target for title, text, and URL", async () => {
  const manifest = JSON.parse(
    await readFile(new URL("../public/manifest.json", import.meta.url), "utf8"),
  );

  assert.deepEqual(manifest.share_target, {
    action: "/share/receive",
    method: "POST",
    enctype: "multipart/form-data",
    params: { title: "title", text: "text", url: "url" },
  });
});
