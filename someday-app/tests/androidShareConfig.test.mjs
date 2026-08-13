import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("share intent plugin accepts text, image, and video without advertising every file", async () => {
  const appConfig = JSON.parse(
    await readFile(new URL("../app.json", import.meta.url), "utf8"),
  );
  const plugin = appConfig.expo.plugins.find(
    (entry) => Array.isArray(entry) && entry[0] === "expo-share-intent",
  );

  assert.ok(plugin, "expo-share-intent must use explicit configuration");
  assert.deepEqual(plugin[1].androidIntentFilters, ["text/*", "image/*", "video/*"]);
  assert.equal(plugin[1].androidIntentFilters.includes("*/*"), false);
  assert.equal(appConfig.expo.version, "1.15.0", "native share-filter changes require a new binary version");
});
