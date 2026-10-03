#!/usr/bin/env python3
"""Lint a Claude Code config dir against AGENT_STANDARD.md. Usage: python3 lint.py [~/.claude]"""
from __future__ import annotations
import glob, json, os, re, sys
try:
    import yaml
except ImportError:
    yaml = None

ROOT = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/.claude")
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SECTIONS = ["Role", "Inputs", "Process", "Output", "Never"]
RO_ROLE = re.compile(r"review|analyzer|audit|sanitizer|verifier|hunter|explorer")
problems: list[tuple[str, str, str]] = []

def add(level: str, where: str, msg: str) -> None:
    problems.append((level, where, msg))

def parse(path: str) -> tuple[dict | None, str]:
    text = open(path, errors="ignore").read()
    m = re.match(r"---\s*\n(.*?)\n---\s*\n?(.*)", text, re.S)
    if not m:
        add("ERROR", path, "missing frontmatter"); return None, text
    raw, body = m.group(1), m.group(2)
    if yaml:
        try:
            return (yaml.safe_load(raw) or {}), body
        except Exception as e:
            add("ERROR", path, f"invalid YAML: {str(e).splitlines()[0]}"); return None, body
    fm = {}
    for line in raw.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1); fm[k.strip()] = v.strip().strip('"')
    return fm, body

def as_list(v) -> list[str]:
    if v is None: return []
    if isinstance(v, list): return [str(x).strip() for x in v]
    return [x.strip() for x in str(v).strip("[]").replace('"', "").split(",") if x.strip()]

agents = {os.path.basename(p)[:-3] for p in glob.glob(f"{ROOT}/agents/*.md")}
skills = {os.path.basename(os.path.dirname(p)) for p in glob.glob(f"{ROOT}/skills/**/SKILL.md", recursive=True)}
desc_total = 0

for p in sorted(glob.glob(f"{ROOT}/agents/*.md")):
    n = os.path.basename(p)[:-3]; where = f"agents/{n}"
    fm, body = parse(p)
    if fm is None: continue
    d = str(fm.get("description", "")); desc_total += len(d)
    if fm.get("name") != n: add("ERROR", where, f"name '{fm.get('name')}' != file name")
    if not fm.get("model"): add("WARN", where, "no model")
    if "tools" not in fm: add("ERROR", where, "no tools → inherits ALL tools incl. MCP")
    tools = set(as_list(fm.get("tools")))
    if RO_ROLE.search(n) and tools & WRITE_TOOLS: add("ERROR", where, f"read-only role has {sorted(tools & WRITE_TOOLS)}")
    if len(d) > 600 or "<example>" in d: add("WARN", where, f"description bloat ({len(d)} chars)")
    if not re.search(r"use (when|this|for|proactively|after|at|to)|must be used", d, re.I): add("WARN", where, "description lacks 'Use when'")
    if not re.search(r"do not use|not for|don't use", d, re.I): add("WARN", where, "description lacks negative scope")
    found = re.findall(r"^## (Role|Inputs|Process|Output|Never)\b", body, re.M)
    if found != SECTIONS: add("ERROR", where, f"sections {' → '.join(found) or 'none'}, need {' → '.join(SECTIONS)}")
    if len(body.splitlines()) > 250: add("WARN", where, f"body {len(body.splitlines())} lines > 250")
    for s in as_list(fm.get("skills")) + re.findall(r"skills?:\s*`([a-z0-9-]+)`", body):
        if s not in skills: add("ERROR", where, f"missing skill '{s}'")

for p in sorted(glob.glob(f"{ROOT}/skills/**/SKILL.md", recursive=True)):
    n = os.path.basename(os.path.dirname(p)); where = f"skills/{n}"
    fm, body = parse(p)
    if fm is None: continue
    d = str(fm.get("description", "")).strip(); desc_total += len(d)
    if fm.get("name") != n: add("ERROR", where, f"name '{fm.get('name')}' != folder")
    if len(d) > 1024: add("ERROR", where, f"description {len(d)} > 1024")
    if len(body.splitlines()) > 500: add("ERROR", where, f"SKILL.md {len(body.splitlines())} lines > 500 — split into references/")
    for a in re.findall(r"`([a-z0-9-]+)` agent", body):
        if a not in agents: add("WARN", where, f"mentions missing agent '{a}'")

for p in sorted(glob.glob(f"{ROOT}/commands/*.md")):
    n = os.path.basename(p)[:-3]; where = f"commands/{n}"
    fm, body = parse(p)
    if fm is None: continue
    desc_total += len(str(fm.get("description", "")))
    if not fm.get("description"): add("WARN", where, "no description")
    refs = set(re.findall(r"`([a-z0-9-]+)` agent|([a-z0-9-]+(?:-reviewer|-resolver|-analyst|-planner)) agent|subagent_type[:=]\s*\"?([a-z0-9-]+)|use `([a-z0-9-]+)` agent type", body))
    for tup in refs:
        a = next(x for x in tup if x)
        if a not in agents: add("ERROR", where, f"missing agent '{a}'")
    for tup in set(re.findall(r"skills?:?\s*`([a-z0-9-]+)`|`([a-z0-9-]+)` skill", body)):
        s = next(x for x in tup if x)
        if s not in skills: add("ERROR", where, f"missing skill '{s}'")
    for m in sorted(set(re.findall(r"(gitnexus_\w+|mcp__ace-tool__\w+)", body))):
        add("ERROR", where, f"needs unavailable MCP tool {m}")

for sf in ("settings.json",):
    p = f"{ROOT}/{sf}"
    if not os.path.exists(p): continue
    s = json.load(open(p))
    if not s.get("hooks"): add("ERROR", sf, "no hooks registered (files in hooks/ do nothing)")
    if not s.get("permissions", {}).get("deny"): add("ERROR", sf, "permissions.deny is empty")
lp = f"{ROOT}/settings.local.json"
if os.path.exists(lp) and json.load(open(lp)).get("enableAllProjectMcpServers"):
    add("WARN", "settings.local.json", "enableAllProjectMcpServers=true auto-trusts every repo's MCP servers")

order = {"ERROR": 0, "WARN": 1}
for lvl, where, msg in sorted(problems, key=lambda x: (order[x[0]], x[1])):
    print(f"{lvl:5} {where:40} {msg}")
e = sum(1 for x in problems if x[0] == "ERROR"); w = len(problems) - e
print(f"\n{len(agents)} agents · {len(skills)} skills · {len(glob.glob(f'{ROOT}/commands/*.md'))} commands · always-loaded descriptions ≈ {desc_total} chars (~{desc_total // 4} tokens)")
print(f"ERROR {e} · WARN {w}")
sys.exit(1 if e else 0)
