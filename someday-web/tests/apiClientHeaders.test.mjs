import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("web API requests identify the browser client", async () => {
  const api = await readFile(new URL("../lib/api.ts", import.meta.url), "utf8");

  assert.match(api, /X-Someday-Client/);
  assert.match(api, /["']web["']/);
});
