# Multi-target Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `./install.sh --target codex,copilot` installs the kit's agents, command-skills, rules and instructions for OpenAI Codex CLI and GitHub Copilot (CLI + VS Code), user-level, by copying ready-made per-target files.

**Architecture:** The repo gains three hand-maintained trees that mirror their install homes: `codex/` → `~/.codex`, `copilot/` → `~/.copilot`, `dotagents/` → `~/.agents`. Their initial content is generated once by a throwaway script (not committed). `install.sh` gets a `--target` flag; the Claude path is unchanged and stays the default.

**Tech Stack:** bash, Python 3.11+ stdlib (`tomllib` in tests only), `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-30-multi-target-install-design.md`

## Global Constraints

- `./install.sh` with no `--target` behaves exactly as today; every existing test in `tests/` stays green.
- No converter in the repo, no new dependency. The bootstrap script lives in the session scratchpad and is never committed.
- User-level only. Homes: `CODEX_HOME` (default `~/.codex`), `COPILOT_HOME` (default `~/.copilot`), `AGENTS_HOME` (default `~/.agents`).
- Never delete files the kit does not own: agents, instructions and skills are installed per item, never by replacing the parent directory.
- `codex/AGENTS.md` ≤ 32768 bytes.
- Out of scope, excluded from `dotagents/skills` and from `AGENTS_HOME`: commands `instinct-status instinct-export instinct-import evolve promote projects prune save-session resume-session`, and the skill `continuous-learning-v2` (its scripts hard-code `~/.claude`; comes back with hooks in phase 2).
- Tests: `python3 -m unittest discover -s tests`.

## Review Focus

- Existing `~/.agents/skills/<own-skill>` or `~/.copilot/agents/<own>.agent.md` of the user → must survive install (test in Task 3).
- `--target` typo (`--target codx`) → exit 2 and nothing written in any home (test in Task 3).
- Re-running install over a previous install → overwritten items land in `<home>/.backup/my-claude-kit-<ts>/` (test in Task 3).
- Agent/command description containing `:` or quotes → generated frontmatter must still parse (Task 2 writes values with `json.dumps`; Task 1 test parses every file).
- A new agent added to `agents/` later without its codex/copilot twin → Task 1 test fails naming it.

---

### Task 1: Parity and format tests for the target trees

**Files:**
- Create: `tests/test_targets.py`

**Interfaces:**
- Produces: the contract Task 2's generated content must satisfy.

- [ ] **Step 1: Write the test**

```python
"""Tests for the hand-maintained codex/, copilot/ and dotagents/ trees."""
import re
import tomllib
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
OUT_OF_SCOPE = {"instinct-status", "instinct-export", "instinct-import", "evolve",
                "promote", "projects", "prune", "save-session", "resume-session"}
WRITE_TOOLS = {"Write", "Edit"}


def frontmatter(path: Path) -> dict:
    m = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    assert m, f"{path}: no frontmatter"
    out = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and not line.startswith(" "):
            out[k.strip()] = v.strip()
    return out


def claude_tools(path: Path) -> set[str]:
    return set(re.findall(r"[A-Za-z]+", frontmatter(path).get("tools", "")))


AGENTS = sorted(p.stem for p in (KIT / "agents").glob("*.md"))
COMMANDS = sorted(p.stem for p in (KIT / "commands").glob("*.md") if p.stem not in OUT_OF_SCOPE)


class TargetParityTest(unittest.TestCase):
    def test_every_agent_has_codex_and_copilot_twin(self):
        for name in AGENTS:
            self.assertTrue((KIT / "codex/agents" / f"{name}.toml").is_file(), f"codex missing {name}")
            self.assertTrue((KIT / "copilot/agents" / f"{name}.agent.md").is_file(), f"copilot missing {name}")

    def test_every_in_scope_command_has_a_skill(self):
        for name in COMMANDS:
            self.assertTrue((KIT / "dotagents/skills" / name / "SKILL.md").is_file(), f"skill missing {name}")

    def test_out_of_scope_commands_are_not_shipped(self):
        for name in OUT_OF_SCOPE:
            self.assertFalse((KIT / "dotagents/skills" / name).exists(), name)

    def test_command_skills_do_not_collide_with_shared_skills(self):
        shared = {p.name for p in (KIT / "skills").iterdir() if p.is_dir()}
        own = {p.name for p in (KIT / "dotagents/skills").iterdir() if p.is_dir()}
        self.assertEqual(shared & own, set())


class TargetFormatTest(unittest.TestCase):
    def test_codex_agents_parse_and_have_required_keys(self):
        for path in (KIT / "codex/agents").glob("*.toml"):
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            for key in ("name", "description", "developer_instructions"):
                self.assertTrue(data.get(key), f"{path.name}: missing {key}")
            self.assertEqual(data["name"], path.stem)

    def test_read_only_agents_stay_read_only(self):
        for name in AGENTS:
            if claude_tools(KIT / "agents" / f"{name}.md") & WRITE_TOOLS:
                continue
            codex = tomllib.loads((KIT / "codex/agents" / f"{name}.toml").read_text(encoding="utf-8"))
            self.assertEqual(codex.get("sandbox_mode"), "read-only", name)
            copilot = frontmatter(KIT / "copilot/agents" / f"{name}.agent.md")
            self.assertNotIn("edit", copilot.get("tools", ""), name)

    def test_markdown_targets_have_name_and_description(self):
        files = list((KIT / "copilot/agents").glob("*.agent.md")) + list((KIT / "dotagents/skills").glob("*/SKILL.md"))
        self.assertTrue(files)
        for path in files:
            fm = frontmatter(path)
            self.assertTrue(fm.get("name"), f"{path}: name")
            self.assertTrue(fm.get("description"), f"{path}: description")

    def test_skill_name_matches_its_directory(self):
        for path in (KIT / "dotagents/skills").glob("*/SKILL.md"):
            self.assertEqual(frontmatter(path)["name"].strip('"'), path.parent.name)

    def test_copilot_instructions_have_apply_to(self):
        files = list((KIT / "copilot/instructions").glob("*.instructions.md"))
        self.assertTrue(files)
        for path in files:
            self.assertTrue(frontmatter(path).get("applyTo"), path.name)

    def test_codex_agents_md_fits_the_32k_limit(self):
        self.assertLessEqual((KIT / "codex/AGENTS.md").stat().st_size, 32768)

    def test_codex_rules_mirror_kit_rules(self):
        kit = sorted(p.relative_to(KIT / "rules") for p in (KIT / "rules").rglob("*.md"))
        codex_root = KIT / "codex/my-claude-kit/rules"
        codex = sorted(p.relative_to(codex_root) for p in codex_root.rglob("*.md"))
        self.assertEqual(kit, codex)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it, expect failures**

Run: `python3 -m unittest tests.test_targets -v`
Expected: FAIL/ERROR on every test (`codex/`, `copilot/`, `dotagents/` do not exist yet).

- [ ] **Step 3: Commit the red test together with Task 2** (no separate commit; the test is meaningless without content).

---

### Task 2: Generate the initial target trees (one-time bootstrap)

**Files:**
- Create (scratchpad, NOT committed): `<scratchpad>/bootstrap_targets.py`
- Create (committed, generated): `codex/AGENTS.md`, `codex/agents/*.toml`, `codex/my-claude-kit/rules/**`, `copilot/copilot-instructions.md`, `copilot/agents/*.agent.md`, `copilot/instructions/*.instructions.md`, `dotagents/skills/<command>/SKILL.md`

**Interfaces:**
- Consumes: Task 1 tests as acceptance.
- Produces: the three trees that Task 3's installer copies.

- [ ] **Step 1: Write the bootstrap script** into the session scratchpad (`$SCRATCH` below is that path):

```python
#!/usr/bin/env python3
"""One-time: generate codex/, copilot/, dotagents/ from the Claude sources. Not committed."""
import json
import re
import shutil
import sys
from pathlib import Path

KIT = Path(sys.argv[1]).resolve()
OUT_OF_SCOPE = {"instinct-status", "instinct-export", "instinct-import", "evolve",
                "promote", "projects", "prune", "save-session", "resume-session"}
COPILOT_TOOL = {"Read": "read", "Grep": "search", "Glob": "search", "Write": "edit",
                "Edit": "edit", "Bash": "execute", "WebFetch": "web"}


def split(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text
    fm, key = {}, None
    for line in m.group(1).splitlines():
        if line.startswith("  - ") and key:
            fm.setdefault(key, []).append(line[4:].strip().strip('"'))
        elif ":" in line and not line.startswith(" "):
            key, _, v = line.partition(":")
            key, v = key.strip(), v.strip()
            fm[key] = v if v else []
    return fm, m.group(2).lstrip("\n")


def tool_list(raw):
    return re.findall(r"[A-Za-z]+", raw or "")


def q(s):
    return json.dumps(s, ensure_ascii=False)  # valid YAML/TOML basic string


def body_with_skills(fm, body):
    skills = fm.get("skills")
    return f"Load these skills first: {skills}\n\n{body}" if skills else body


def toml_multiline(s):
    if "'''" not in s:
        return "'''\n" + s + "'''"
    return q(s)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


for d in ("codex", "copilot", "dotagents"):
    shutil.rmtree(KIT / d, ignore_errors=True)

# Agents
for src in sorted((KIT / "agents").glob("*.md")):
    fm, body = split(src)
    name, desc = src.stem, fm["description"]
    tools = tool_list(fm.get("tools"))
    body = body_with_skills(fm, body)
    lines = [f"name = {q(name)}", f"description = {q(desc)}"]
    if not {"Write", "Edit"} & set(tools):
        lines.append('sandbox_mode = "read-only"')
    lines.append(f"developer_instructions = {toml_multiline(body)}")
    write(KIT / "codex/agents" / f"{name}.toml", "\n".join(lines) + "\n")
    ctools = list(dict.fromkeys(COPILOT_TOOL[t] for t in tools if t in COPILOT_TOOL))
    write(KIT / "copilot/agents" / f"{name}.agent.md",
          f"---\nname: {q(name)}\ndescription: {q(desc)}\ntools: {json.dumps(ctools)}\n---\n\n{body}")

# Commands -> shared skills
for src in sorted((KIT / "commands").glob("*.md")):
    if src.stem in OUT_OF_SCOPE:
        continue
    fm, body = split(src)
    body = body.replace("$ARGUMENTS", "the user's request")
    hint = fm.get("argument-hint")
    if hint:
        body = f"Input: {hint}\n\n{body}"
    write(KIT / "dotagents/skills" / src.stem / "SKILL.md",
          f"---\nname: {q(src.stem)}\ndescription: {q(fm['description'])}\n---\n\n{body}")

# Rules
claude_md = (KIT / "claude/CLAUDE.md").read_text(encoding="utf-8")
index = ["", "## Rules", "",
         "Before editing a file, read every rule file of the matching group under `~/.codex/my-claude-kit/rules/`.", ""]
for ns_dir in sorted(p for p in (KIT / "rules").iterdir() if p.is_dir()):
    globs = []
    for rule in sorted(ns_dir.glob("*.md")):
        fm, body = split(rule)
        paths = fm.get("paths") or []
        globs += [g for g in paths if g not in globs]
        write(KIT / "codex/my-claude-kit/rules" / ns_dir.name / rule.name, rule.read_text(encoding="utf-8"))
        apply_to = ",".join(paths) if paths else "**"
        write(KIT / "copilot/instructions" / f"{ns_dir.name}-{rule.stem}.instructions.md",
              f"---\napplyTo: {q(apply_to)}\n---\n\n{body}")
    scope = ", ".join(f"`{g}`" for g in globs) if globs else "every file"
    index.append(f"- `{ns_dir.name}/`: {scope}")
write(KIT / "codex/AGENTS.md", claude_md.rstrip("\n") + "\n" + "\n".join(index) + "\n")
write(KIT / "copilot/copilot-instructions.md", claude_md)
print("done")
```

- [ ] **Step 2: Run it**

Run: `python3 "$SCRATCH/bootstrap_targets.py" /Users/mac/code/github.com/my-claude-kit`
Expected: `done`; `ls codex copilot dotagents/skills | head` shows files; `ls dotagents/skills | wc -l` = 19.

- [ ] **Step 3: Run the Task 1 tests**

Run: `python3 -m unittest tests.test_targets -v`
Expected: all PASS. If a TOML fails to parse, open the file named in the failure and fix the bootstrap, then rerun Step 2.

- [ ] **Step 4: Spot-check by eye** `codex/agents/planner.toml`, `copilot/agents/code-reviewer.agent.md`, `dotagents/skills/quick/SKILL.md`, `copilot/instructions/php-coding-style.instructions.md`, `codex/AGENTS.md` (tail shows the rules index).

- [ ] **Step 5: Run the full suite** (lint test must not choke on new dirs)

Run: `python3 -m unittest discover -s tests`
Expected: all PASS.

- [ ] **Step 6: Commit** (bootstrap script stays in the scratchpad)

```bash
git add tests/test_targets.py codex copilot dotagents
git commit -m "feat: add Codex and Copilot target trees

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `install.sh --target`

**Files:**
- Modify: `install.sh` (option parsing lines 19-29; `install_item` lines 37-49; wrap Claude section lines 58-102)
- Test: `tests/test_install.py` (new class at end)

**Interfaces:**
- Consumes: `codex/`, `copilot/`, `dotagents/skills/`, `skills/` from Task 2.
- Produces: CLI `./install.sh [--target claude,codex,copilot | --target=...] [--dry-run] [--no-hooks] [--no-claude-md]`; env `CODEX_HOME`, `COPILOT_HOME`, `AGENTS_HOME`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_install.py`, before the `if __name__` block if any)

```python
class MultiTargetInstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.claude, self.codex = root / ".claude", root / ".codex"
        self.copilot, self.agents = root / ".copilot", root / ".agents"
        own_skill = self.agents / "skills" / "my-own-skill"
        own_skill.mkdir(parents=True)
        (own_skill / "SKILL.md").write_text("mine", encoding="utf-8")
        (self.copilot / "agents").mkdir(parents=True)
        (self.copilot / "agents" / "mine.agent.md").write_text("mine", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def install(self, *args):
        env = {**os.environ, "CLAUDE_DIR": str(self.claude), "CODEX_HOME": str(self.codex),
               "COPILOT_HOME": str(self.copilot), "AGENTS_HOME": str(self.agents)}
        return subprocess.run(["bash", str(KIT_ROOT / "install.sh"), *args],
                              env=env, capture_output=True, text=True, timeout=120)

    def test_installs_codex_and_copilot(self):
        r = self.install("--target", "codex,copilot")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.codex / "AGENTS.md").is_file())
        self.assertTrue((self.codex / "agents" / "planner.toml").is_file())
        self.assertTrue((self.codex / "my-claude-kit" / "rules" / "php" / "coding-style.md").is_file())
        self.assertTrue((self.copilot / "copilot-instructions.md").is_file())
        self.assertTrue((self.copilot / "agents" / "planner.agent.md").is_file())
        self.assertTrue((self.copilot / "instructions" / "php-coding-style.instructions.md").is_file())
        self.assertTrue((self.agents / "skills" / "debugging" / "SKILL.md").is_file())
        self.assertTrue((self.agents / "skills" / "quick" / "SKILL.md").is_file())
        self.assertFalse((self.agents / "skills" / "continuous-learning-v2").exists())
        self.assertFalse(self.claude.exists(), "claude target must not run")

    def test_equals_form_works(self):
        r = self.install("--target=codex")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.codex / "agents" / "planner.toml").is_file())
        self.assertFalse((self.copilot / "copilot-instructions.md").exists())

    def test_keeps_items_the_kit_does_not_own(self):
        self.install("--target", "codex,copilot")
        self.assertEqual((self.agents / "skills" / "my-own-skill" / "SKILL.md").read_text(), "mine")
        self.assertEqual((self.copilot / "agents" / "mine.agent.md").read_text(), "mine")

    def test_reinstall_backs_up_overwritten_items(self):
        self.install("--target", "codex")
        (self.codex / "AGENTS.md").write_text("edited", encoding="utf-8")
        r = self.install("--target", "codex")
        self.assertEqual(r.returncode, 0, r.stderr)
        backups = list((self.codex / ".backup").glob("my-claude-kit-*/AGENTS.md"))
        self.assertEqual([b.read_text() for b in backups], ["edited"])

    def test_no_claude_md_skips_instruction_files(self):
        r = self.install("--target", "codex,copilot", "--no-claude-md")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.codex / "AGENTS.md").exists())
        self.assertFalse((self.copilot / "copilot-instructions.md").exists())
        self.assertTrue((self.codex / "agents" / "planner.toml").is_file())

    def test_unknown_target_writes_nothing(self):
        r = self.install("--target", "codex,codx")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.codex.exists())
        self.assertFalse(self.claude.exists())

    def test_empty_target_is_rejected(self):
        self.assertEqual(self.install("--target=").returncode, 2)

    def test_dry_run_writes_nothing(self):
        r = self.install("--target", "codex,copilot", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.codex.exists())
        self.assertFalse((self.copilot / "copilot-instructions.md").exists())
```

- [ ] **Step 2: Run, expect failure**

Run: `python3 -m unittest tests.test_install.MultiTargetInstallTest -v`
Expected: FAIL — `unknown option: --target` (exit 2) in most tests.

- [ ] **Step 3: Implement.** Edit `install.sh`:

(a) Header usage comment — replace the `# Usage:` line with:
```bash
# Usage: ./install.sh [--target claude,codex,copilot] [--dry-run] [--no-hooks] [--no-claude-md]
#   --target        comma list of AI tools to install for (default: claude)
```
and add to the `# Env:` block:
```bash
#        CODEX_HOME (default ~/.codex), COPILOT_HOME (default ~/.copilot), AGENTS_HOME (default ~/.agents)
```

(b) Replace the option loop (current `for arg in "$@"; do ... done`) with:
```bash
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
COPILOT_HOME="${COPILOT_HOME:-$HOME/.copilot}"
AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"
TARGETS="claude"
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --no-hooks) REGISTER_HOOKS=0 ;;
    --no-claude-md) INSTALL_CLAUDE_MD=0 ;;
    --target=*) TARGETS="${1#--target=}" ;;
    --target) shift; TARGETS="${1:-}" ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done
TARGETS=" ${TARGETS//,/ } "
[ -n "${TARGETS// /}" ] || { echo "--target needs a value (claude, codex, copilot)" >&2; exit 2; }
for t in $TARGETS; do
  case "$t" in claude|codex|copilot) ;; *) echo "unknown target: $t (use claude, codex, copilot)" >&2; exit 2 ;; esac
done
has_target() { case "$TARGETS" in *" $1 "*) return 0 ;; *) return 1 ;; esac; }
```

(c) Make backups per home. Replace `BACKUP_DIR=...` and `install_item` with:
```bash
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_DIR/.backup/my-claude-kit-$STAMP"

# install_item <src> <dest> [home]: back up dest if it exists, then copy src over it.
# home (default CLAUDE_DIR) decides where the backup goes.
install_item() {
  local src="$1" dest="$2" home="${3:-$CLAUDE_DIR}"
  local rel="${dest#"$home"/}"
  if [ -e "$dest" ]; then
    local backup="$home/.backup/my-claude-kit-$STAMP"
    run mkdir -p "$backup/$(dirname "$rel")"
    run cp -R "$dest" "$backup/$rel"
    run rm -rf "$dest"
  fi
  run mkdir -p "$(dirname "$dest")"
  run cp -R "$src" "$dest"
  echo "installed $rel"
}
```

(d) Wrap everything from the first `for f in "$KIT_DIR"/agents/*.md` through the end of the `if [ "$REGISTER_HOOKS" -eq 1 ]; then ... fi` block in:
```bash
if has_target claude; then
  # ...existing Claude install, unchanged...
fi
```

(e) After that block, before the final `backup:` echo, add:
```bash
# Codex and Copilot share ~/.agents/skills. continuous-learning-v2 hard-codes ~/.claude paths.
if has_target codex || has_target copilot; then
  for d in "$KIT_DIR"/skills/*/ "$KIT_DIR"/dotagents/skills/*/; do
    d="${d%/}"; name="$(basename "$d")"
    [ "$name" = "continuous-learning-v2" ] && continue
    install_item "$d" "$AGENTS_HOME/skills/$name" "$AGENTS_HOME"
  done
fi
if has_target codex; then
  for f in "$KIT_DIR"/codex/agents/*.toml; do install_item "$f" "$CODEX_HOME/agents/$(basename "$f")" "$CODEX_HOME"; done
  install_item "$KIT_DIR/codex/my-claude-kit" "$CODEX_HOME/my-claude-kit" "$CODEX_HOME"
  if [ "$INSTALL_CLAUDE_MD" -eq 1 ]; then install_item "$KIT_DIR/codex/AGENTS.md" "$CODEX_HOME/AGENTS.md" "$CODEX_HOME"; fi
fi
if has_target copilot; then
  for f in "$KIT_DIR"/copilot/agents/*.agent.md; do install_item "$f" "$COPILOT_HOME/agents/$(basename "$f")" "$COPILOT_HOME"; done
  for f in "$KIT_DIR"/copilot/instructions/*.instructions.md; do install_item "$f" "$COPILOT_HOME/instructions/$(basename "$f")" "$COPILOT_HOME"; done
  if [ "$INSTALL_CLAUDE_MD" -eq 1 ]; then install_item "$KIT_DIR/copilot/copilot-instructions.md" "$COPILOT_HOME/copilot-instructions.md" "$COPILOT_HOME"; fi
fi
```

(f) Replace the final backup echo with one that reports every home:
```bash
if [ "$DRY_RUN" -eq 0 ]; then
  for h in "$CLAUDE_DIR" "$CODEX_HOME" "$COPILOT_HOME" "$AGENTS_HOME"; do
    if [ -d "$h/.backup/my-claude-kit-$STAMP" ]; then echo "backup: $h/.backup/my-claude-kit-$STAMP"; fi
  done
fi
exit 0
```

- [ ] **Step 4: Run the new tests**

Run: `python3 -m unittest tests.test_install -v`
Expected: all PASS, old `InstallTest` cases included (proves default target unchanged).

- [ ] **Step 5: Full suite + dry run by eye**

Run: `python3 -m unittest discover -s tests && CODEX_HOME=$(mktemp -d) COPILOT_HOME=$(mktemp -d) AGENTS_HOME=$(mktemp -d) ./install.sh --target codex,copilot --dry-run | tail -5`
Expected: tests PASS; dry-run prints `[dry-run] cp -R ...` lines and no errors.

- [ ] **Step 6: Commit**

```bash
git add install.sh tests/test_install.py
git commit -m "feat(install): --target flag for Codex and Copilot

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: README

**Files:**
- Modify: `README.md` section `## 1. Cài đặt` (add rows to the command table around line 61-66, and a short subsection before `### Gỡ bỏ`)

- [ ] **Step 1: Add to the install command table**

```markdown
| `./install.sh --target codex`           | Cài cho OpenAI Codex CLI (`~/.codex`, skills vào `~/.agents/skills`)         |
| `./install.sh --target copilot`         | Cài cho GitHub Copilot CLI và VS Code (`~/.copilot`, skills vào `~/.agents/skills`) |
| `./install.sh --target claude,codex`    | Cài nhiều target một lần                                                     |
```

- [ ] **Step 2: Add subsection before `### Gỡ bỏ`**

```markdown
### Codex và Copilot

File cho từng AI nằm sẵn trong repo, installer chỉ copy:

| Thư mục repo  | Cài vào                 | Nội dung                                                     |
| ------------- | ----------------------- | ------------------------------------------------------------ |
| `skills/`     | `~/.agents/skills/`     | Skill dùng chung, cả Codex và Copilot đều đọc                 |
| `dotagents/`  | `~/.agents/`            | Command của kit ở dạng skill (`quick`, `feature`, `debug`…)  |
| `codex/`      | `~/.codex/`             | `AGENTS.md`, agent dạng TOML, rules                          |
| `copilot/`    | `~/.copilot/`           | `copilot-instructions.md`, `*.agent.md`, `*.instructions.md` |

- **Sửa agent hay command thì sửa ở cả 3 nơi** (`agents/`, `codex/agents/`, `copilot/agents/`). `tests/test_targets.py` báo lỗi nếu thiếu file ở target nào.
- Chưa có cho Codex/Copilot: hooks (`guard.sh`, continuous learning) và các command instinct/session.
- Đổi thư mục cài bằng `CODEX_HOME`, `COPILOT_HOME`, `AGENTS_HOME`.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document Codex and Copilot install targets

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>"
```
