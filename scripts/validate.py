#!/usr/bin/env python3
"""Validate the repository before a commit or publish.

Checks:
  - every skills/*/SKILL.md follows the Agent Skills specification (agentskills.io):
    allowed front matter fields, name = folder name, name/description/compatibility limits;
    warns when SKILL.md is longer than 500 lines;
  - the JSON manifests parse and agree on the plugin name, marketplace name and version;
  - the generated subagent adapters are up to date (scripts/build-adapters.py --check);
  - no file in the repository contains a secret, an e-mail address or a personal home path.

Usage: python3 scripts/validate.py      (exit 1 on any error)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "sbskills"
MARKETPLACE_NAME = "stepanbeseda-skills"
ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
MAX_LINES = 500

LEAK_PATTERNS = [
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("a GitHub token", re.compile(r"\b(ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}")),
    ("an API key", re.compile(r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}")),
    ("a Slack token", re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}")),
    ("an AWS key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("an e-mail address", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("a personal path", re.compile(r"/home/[a-z_][a-z0-9_-]*/|/Users/[A-Za-z0-9_-]+/")),
]
# Documentation domains and no-reply addresses (e.g. a Co-authored-by trailer) are not personal.
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net", "example.invalid")
# Files that define the leak patterns themselves: their pattern lines are not leaks.
PATTERN_FILES = {"scripts/validate.py", "skills/publish-skills/scripts/publish.sh"}
PATTERN_LINE = re.compile(r"""-e '|re\.compile\(|r["']""")

errors = []
warnings = []


def error(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def parse_front_matter(text, rel):
    """Parse the YAML subset used in SKILL.md front matter: scalars and one-level maps."""
    if not text.startswith("---\n"):
        error(f"{rel}: must start with a '---' front matter block")
        return None
    end = text.find("\n---", 3)
    if end == -1:
        error(f"{rel}: front matter is not closed with '---'")
        return None
    lines = text[4:end].split("\n")
    data = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$", line)
        if not m:
            error(f"{rel}: cannot parse front matter line: {line!r}")
            continue
        key, value = m.group(1), (m.group(2) or "").strip()
        if key in data:
            error(f"{rel}: field '{key}' appears twice")
        if value == "":
            mapping = {}
            while i < len(lines) and lines[i].startswith((" ", "\t")):
                sub = lines[i].strip()
                i += 1
                if not sub or sub.startswith("#"):
                    continue
                sm = re.match(r"^([^:]+):\s*(.*)$", sub)
                if not sm:
                    error(f"{rel}: cannot parse '{key}' entry: {sub!r}")
                    continue
                mapping[unquote(sm.group(1).strip())] = unquote(sm.group(2).strip())
            data[key] = mapping
        elif value in (">", "|", ">-", "|-", ">+", "|+"):
            block = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            data[key] = (" " if value.startswith(">") else "\n").join(b for b in block if b)
        else:
            while i < len(lines) and lines[i].startswith((" ", "\t")) and lines[i].strip():
                value += " " + lines[i].strip()
                i += 1
            data[key] = unquote(value)
    return data


def unquote(value):
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def check_skills():
    skill_dirs = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    if not skill_dirs:
        error("skills/: no skills found")
    for folder in skill_dirs:
        skill_md = folder / "SKILL.md"
        rel = skill_md.relative_to(ROOT).as_posix()
        if not skill_md.is_file():
            error(f"{folder.relative_to(ROOT).as_posix()}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        meta = parse_front_matter(text, rel)
        if meta is None:
            continue
        for key in meta:
            if key not in ALLOWED_FIELDS:
                error(f"{rel}: field '{key}' is not in the Agent Skills spec "
                      f"(allowed: {', '.join(sorted(ALLOWED_FIELDS))})")
        name = meta.get("name")
        if not isinstance(name, str) or not name:
            error(f"{rel}: missing 'name'")
        else:
            if len(name) > 64 or not NAME_RE.match(name):
                error(f"{rel}: name '{name}' must be 1-64 characters of a-z, 0-9 and single "
                      "hyphens, not starting or ending with a hyphen")
            if name != folder.name:
                error(f"{rel}: name '{name}' must equal the folder name '{folder.name}'")
        desc = meta.get("description")
        if not isinstance(desc, str) or not desc.strip():
            error(f"{rel}: missing 'description'")
        elif len(desc) > 1024:
            error(f"{rel}: description is {len(desc)} characters (max 1024)")
        comp = meta.get("compatibility")
        if comp is not None and (not isinstance(comp, str) or not 1 <= len(comp) <= 500):
            error(f"{rel}: compatibility must be a string of 1-500 characters")
        if "metadata" in meta and not isinstance(meta["metadata"], dict):
            error(f"{rel}: metadata must be a map of string keys to string values")
        for key in ("license", "allowed-tools"):
            if key in meta and not isinstance(meta[key], str):
                error(f"{rel}: {key} must be a string")
        lines = text.count("\n") + 1
        if lines > MAX_LINES:
            warn(f"{rel}: {lines} lines (spec recommends under {MAX_LINES}; move detail to references/)")


def load_json(rel):
    path = ROOT / rel
    if not path.is_file():
        error(f"{rel}: missing")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        error(f"{rel}: invalid JSON ({exc})")
        return None


def check_manifests():
    claude_plugin = load_json(".claude-plugin/plugin.json")
    claude_market = load_json(".claude-plugin/marketplace.json")
    plugin = load_json("plugin.json")
    codex_market = load_json(".agents/plugins/marketplace.json")
    versions = {}
    for rel, data in ((".claude-plugin/plugin.json", claude_plugin), ("plugin.json", plugin)):
        if data is None:
            continue
        if data.get("name") != PLUGIN_NAME:
            error(f"{rel}: name must be '{PLUGIN_NAME}', got '{data.get('name')}'")
        version = data.get("version", "")
        if not VERSION_RE.match(str(version)):
            error(f"{rel}: version '{version}' is not MAJOR.MINOR.PATCH")
        versions[rel] = version
    if len(set(versions.values())) > 1:
        error("plugin versions differ: " + ", ".join(f"{k}={v}" for k, v in versions.items()))
    for rel, data in ((".claude-plugin/marketplace.json", claude_market),
                      (".agents/plugins/marketplace.json", codex_market)):
        if data is None:
            continue
        if data.get("name") != MARKETPLACE_NAME:
            error(f"{rel}: name must be '{MARKETPLACE_NAME}', got '{data.get('name')}'")
        entries = [p for p in data.get("plugins", []) if isinstance(p, dict)]
        names = [p.get("name") for p in entries]
        if names != [PLUGIN_NAME]:
            error(f"{rel}: must list exactly the plugin '{PLUGIN_NAME}', got {names}")
            continue
        source = entries[0].get("source")
        path = source.get("path") if isinstance(source, dict) else source
        if path not in ("./", "."):
            error(f"{rel}: plugin source must point to the repository root './', got {source!r}")


def check_adapters():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build-adapters.py"), "--check"],
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        for line in (result.stderr or result.stdout).strip().splitlines():
            if line.startswith("Run:"):
                continue
            error(f"adapters: {line.removeprefix('ERROR: ')} (run: python3 scripts/build-adapters.py)")


def repo_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=ROOT, capture_output=True, check=True).stdout
        return sorted({p for p in out.decode().split("\0") if p})
    except (OSError, subprocess.CalledProcessError):
        return sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                      if p.is_file() and ".git" not in p.parts)


def check_leaks():
    for rel in repo_files():
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if rel in PATTERN_FILES and PATTERN_LINE.search(line):
                continue
            for label, pattern in LEAK_PATTERNS:
                for match in pattern.finditer(line):
                    found = match.group(0)
                    if label == "an e-mail address" and (
                            found.lower().endswith(ALLOWED_EMAIL_DOMAINS)
                            or found.lower().startswith("noreply@")):
                        continue
                    error(f"{rel}:{number}: looks like {label}: {found[:60]}")


def main():
    check_skills()
    check_manifests()
    check_adapters()
    check_leaks()
    for msg in warnings:
        print(f"WARN   {msg}")
    for msg in errors:
        print(f"ERROR  {msg}")
    if errors:
        print(f"Validation failed: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"Validation passed ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
