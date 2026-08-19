import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const source = (path) => readFile(new URL(path, root), "utf8");

test("Someday publishes canonical social metadata", async () => {
  const layout = await source("app/layout.tsx");
  assert.match(layout, /alternates:\s*\{\s*canonical:\s*["']\/["']/s);
  assert.match(layout, /url:\s*["']\/["']/);
  assert.match(layout, /twitter:/);
});

test("Someday publishes crawler, sitemap, and agent discovery files", async () => {
  const [robots, llms, sitemap] = await Promise.all([
    source("public/robots.txt"),
    source("public/llms.txt"),
    source("app/sitemap.ts"),
  ]);
  assert.match(robots, /User-agent: GPTBot\nDisallow: \//);
  assert.match(robots, /User-agent: Claude-User\nAllow: \//);
  assert.match(robots, /Sitemap: https:\/\/someday\.tn07\.dev\/sitemap\.xml/);
  assert.match(llms, /^# Someday$/m);
  assert.match(sitemap, /https:\/\/someday\.tn07\.dev/);
});
