#!/usr/bin/env node
// Interactive front end for install.sh: ask targets and stack groups, then run it.
// With any CLI arguments it skips the menu and passes them straight to install.sh.
import { spawnSync } from "node:child_process";
import { readFileSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const KIT_DIR = join(dirname(fileURLToPath(import.meta.url)), "..");
const NEEDS_FRONTEND = ["react", "vue"];

export function parseGroups(text) {
  return text.split("\n")
    .filter((line) => line.trim() && !line.startsWith("#"))
    .map((line) => line.split(":")[0].trim());
}

export function buildArgs({ targets, groups, dryRun }) {
  const only = [...groups];
  if (only.some((g) => NEEDS_FRONTEND.includes(g)) && !only.includes("frontend")) only.push("frontend");
  const args = ["--target", targets.join(",")];
  if (only.length) args.push("--only", only.join(","));
  if (dryRun) args.push("--dry-run");
  return args;
}

function runInstall(args) {
  const r = spawnSync("bash", [join(KIT_DIR, "install.sh"), ...args], { stdio: "inherit" });
  return r.status ?? 1;
}

async function ask() {
  const p = await import("@clack/prompts");
  const bail = (v) => {
    if (p.isCancel(v)) { p.cancel("Đã huỷ."); process.exit(1); }
    return v;
  };
  p.intro("My Claude Kit");
  const targets = bail(await p.multiselect({
    message: "Cài cho AI nào?",
    options: [
      { value: "claude", label: "Claude Code", hint: "~/.claude" },
      { value: "codex", label: "Codex CLI", hint: "~/.codex + ~/.agents/skills" },
      { value: "copilot", label: "GitHub Copilot", hint: "~/.copilot + ~/.agents/skills" },
    ],
    initialValues: ["claude"],
    required: true,
  }));
  const names = parseGroups(readFileSync(join(KIT_DIR, "groups.txt"), "utf8"));
  const groups = bail(await p.multiselect({
    message: "Nhóm stack? (core luôn được cài; bỏ trống = cài tất cả)",
    options: names.map((n) => ({ value: n, label: n })),
    required: false,
  }));
  const dryRun = bail(await p.select({
    message: "Chạy thế nào?",
    options: [
      { value: true, label: "Xem trước (dry-run)" },
      { value: false, label: "Cài luôn" },
    ],
  }));
  const args = buildArgs({ targets, groups, dryRun });
  p.outro(`install.sh ${args.join(" ")}`);
  return args;
}

const isMain = process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const cliArgs = process.argv.slice(2);
  const args = cliArgs.length || !process.stdin.isTTY ? cliArgs : await ask();
  process.exit(runInstall(args));
}
