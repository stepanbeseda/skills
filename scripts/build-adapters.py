#!/usr/bin/env python3
"""Generate per-tool subagent files from the vendor-neutral role files.

Every skills/<skill>/roles/<role>.md (front matter: name, description, tier: strong|fast;
body: the role's system prompt) becomes three adapters named <skill>-<role>:

  adapters/claude/agents/<skill>-<role>.md      Claude Code subagent (shipped with the plugin)
  adapters/codex/agents/<skill>-<role>.toml     OpenAI Codex custom agent
  adapters/opencode/agents/<skill>-<role>.md    OpenCode subagent

It also writes the list of Claude agent files into .claude-plugin/plugin.json ("agents").

Usage: python3 scripts/build-adapters.py [--check]
  --check  change nothing; exit 1 if an adapter is missing, outdated or orphaned.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
CLAUDE_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
TARGETS = {
    "claude": (ROOT / "adapters" / "claude" / "agents", ".md"),
    "codex": (ROOT / "adapters" / "codex" / "agents", ".toml"),
    "opencode": (ROOT / "adapters" / "opencode" / "agents", ".md"),
}
CLAUDE_MODEL = {"strong": "opus", "fast": "sonnet"}
TIERS = set(CLAUDE_MODEL)
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class RoleError(Exception):
    pass


def split_front_matter(text, path):
    """Return (front matter dict, body). Supports the simple YAML used in role files."""
    if not text.startswith("---\n"):
        raise RoleError(f"{path}: no front matter (must start with '---')")
    end = text.find("\n---\n", 3)
    if end == -1:
        if text.endswith("\n---"):
            end = len(text) - 4
        else:
            raise RoleError(f"{path}: front matter is not closed with '---'")
    head = text[4:end]
    body = text[end + 5:]
    return parse_simple_yaml(head, path), body


def parse_simple_yaml(head, path):
    data = {}
    lines = head.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$", line)
        if not m:
            raise RoleError(f"{path}: cannot parse front matter line: {line!r}")
        key, value = m.group(1), (m.group(2) or "").strip()
        if value in (">", "|", ">-", "|-", ">+", "|+"):
            block = []
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                block.append(lines[i].strip())
                i += 1
            joiner = " " if value.startswith(">") else "\n"
            value = joiner.join(b for b in block if b) if joiner == " " else "\n".join(block).strip("\n")
        elif value.startswith('"') and value.endswith('"') and len(value) >= 2:
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise RoleError(f"{path}: cannot parse the quoted value of '{key}'") from None
        elif value.startswith("'") and value.endswith("'") and len(value) >= 2:
            value = value[1:-1].replace("''", "'")
        else:
            # plain scalar, possibly continued on indented lines
            while i < len(lines) and lines[i].startswith((" ", "\t")) and lines[i].strip():
                value += " " + lines[i].strip()
                i += 1
        data[key] = value
    return data


def load_roles():
    roles = []
    errors = []
    invalid = set()
    for path in sorted(SKILLS.glob("*/roles/*.md")):
        skill = path.parent.parent.name
        role = path.stem
        rel = path.relative_to(ROOT).as_posix()
        try:
            meta, body = split_front_matter(path.read_text(encoding="utf-8"), rel)
            name = meta.get("name", "")
            if name not in (role, f"{skill}-{role}"):
                raise RoleError(f"{rel}: name '{name}' must be the role id '{role}' (the file name)")
            if not NAME_RE.match(role):
                raise RoleError(f"{rel}: role id '{role}' must be lowercase letters, digits and single hyphens")
            description = meta.get("description", "").strip()
            if not description:
                raise RoleError(f"{rel}: missing description")
            tier = meta.get("tier", "")
            if tier not in TIERS:
                raise RoleError(f"{rel}: tier must be one of {sorted(TIERS)}, got '{tier}'")
        except RoleError as exc:
            errors.append(str(exc))
            invalid.add(f"{skill}-{role}")
            continue
        marker = f"Started only by the /{skill} orchestrator."
        if marker not in description:
            description = description.rstrip() + " " + marker
        roles.append({
            "skill": skill, "role": role, "id": f"{skill}-{role}", "source": rel,
            "description": description, "tier": tier, "body": body,
        })
    return roles, errors, invalid


def yaml_str(value):
    # A JSON string is a valid YAML double-quoted scalar.
    return json.dumps(value, ensure_ascii=False)


def toml_basic(value):
    out = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    return '"' + "".join(out) + '"'


def toml_multiline(value):
    if not value.endswith("\n"):
        value += "\n"
    literal_ok = "'''" not in value and not any(
        (ord(c) < 0x20 and c not in "\n\t") or ord(c) == 0x7F for c in value)
    if literal_ok:
        # The newline right after the opening delimiter is trimmed by TOML.
        return "'''\n" + value + "'''"
    out = []
    for ch in value:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch in "\n\t":
            out.append(ch)
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    return '"""\n' + "".join(out) + '"""'


def render(role):
    note = f"Generated from {role['source']} by scripts/build-adapters.py. Do not edit; edit the role file."
    claude = (
        "---\n"
        f"# {note}\n"
        f"name: {role['id']}\n"
        f"description: {yaml_str(role['description'])}\n"
        f"model: {CLAUDE_MODEL[role['tier']]}\n"
        "effort: high\n"
        "---\n"
        f"{role['body']}"
    )
    codex = (
        f"# {note}\n"
        f"name = {toml_basic(role['id'])}\n"
        f"description = {toml_basic(role['description'])}\n"
        'model_reasoning_effort = "high"\n'
        f"developer_instructions = {toml_multiline(role['body'])}\n"
    )
    opencode = (
        "---\n"
        f"# {note}\n"
        f"description: {yaml_str(role['description'])}\n"
        "mode: subagent\n"
        "---\n"
        f"{role['body']}"
    )
    return {"claude": claude, "codex": codex, "opencode": opencode}


def manifest_text(claude_files):
    data = json.loads(CLAUDE_MANIFEST.read_text(encoding="utf-8"))
    if claude_files:
        data["agents"] = claude_files
    else:
        data.pop("agents", None)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv):
    check = "--check" in argv
    roles, errors, invalid = load_roles()
    expected = {}
    for role in roles:
        for tool, text in render(role).items():
            directory, ext = TARGETS[tool]
            expected[directory / f"{role['id']}{ext}"] = text
    claude_dir = TARGETS["claude"][0]
    claude_files = sorted(
        "./" + p.relative_to(ROOT).as_posix() for p in expected if p.parent == claude_dir)

    problems = list(errors)
    changed = []
    for path, text in sorted(expected.items()):
        rel = path.relative_to(ROOT).as_posix()
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        if check:
            problems.append(f"{rel}: {'missing' if current is None else 'outdated'}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            changed.append(f"wrote {rel}")
    for directory, ext in TARGETS.values():
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix == ext and path not in expected:
                rel = path.relative_to(ROOT).as_posix()
                if path.stem in invalid:
                    continue  # the role file exists but is invalid; that error is reported
                if check:
                    problems.append(f"{rel}: orphaned (no role file)")
                else:
                    path.unlink()
                    changed.append(f"removed {rel}")
    if CLAUDE_MANIFEST.exists() and not errors:
        text = manifest_text(claude_files)
        if CLAUDE_MANIFEST.read_text(encoding="utf-8") != text:
            if check:
                problems.append(".claude-plugin/plugin.json: \"agents\" list is outdated")
            else:
                CLAUDE_MANIFEST.write_text(text, encoding="utf-8")
                changed.append("updated .claude-plugin/plugin.json agents")

    for line in changed:
        print(line)
    if problems:
        for line in problems:
            print(f"ERROR: {line}", file=sys.stderr)
        if check:
            print("Run: python3 scripts/build-adapters.py", file=sys.stderr)
        return 1
    if check:
        print(f"adapters up to date ({len(roles)} roles)")
    elif not changed:
        print(f"adapters already up to date ({len(roles)} roles)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
