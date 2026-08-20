import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("native API requests identify the installed app version", async () => {
  const [api, home, appConfigSource] = await Promise.all([
    readFile(new URL("../lib/api.ts", import.meta.url), "utf8"),
    readFile(new URL("../screens/Home.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app.json", import.meta.url), "utf8"),
  ]);

  assert.match(api, /X-Someday-Client/);
  assert.match(api, /native\/\$\{Constants\.expoConfig\?\.version/);
  assert.match(home, /X-Someday-Client/);
  assert.equal(
    JSON.parse(appConfigSource).expo.version,
    "1.16.0",
    "native client identification requires a publishable release version",
  );
});
