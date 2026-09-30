import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { buildArgs, parseGroups } from "../bin/cli.js";

test("parseGroups reads group names from groups.txt, skipping comments", () => {
  const names = parseGroups("# c\nlaravel: skills/a\n\ngo: skills/b rules/golang\n");
  assert.deepEqual(names, ["laravel", "go"]);
});

test("parseGroups matches the real groups.txt", () => {
  const names = parseGroups(readFileSync(new URL("../groups.txt", import.meta.url), "utf8"));
  assert.ok(names.includes("laravel") && names.includes("go"));
});

test("buildArgs joins targets and groups", () => {
  assert.deepEqual(buildArgs({ targets: ["claude", "codex"], groups: ["go"], dryRun: false }),
    ["--target", "claude,codex", "--only", "go"]);
});

test("buildArgs with no groups installs everything", () => {
  assert.deepEqual(buildArgs({ targets: ["copilot"], groups: [], dryRun: true }),
    ["--target", "copilot", "--dry-run"]);
});

test("react or vue pull in frontend once", () => {
  assert.deepEqual(buildArgs({ targets: ["claude"], groups: ["react", "vue"], dryRun: false }),
    ["--target", "claude", "--only", "react,vue,frontend"]);
  assert.deepEqual(buildArgs({ targets: ["claude"], groups: ["frontend", "vue"], dryRun: false }),
    ["--target", "claude", "--only", "frontend,vue"]);
});
