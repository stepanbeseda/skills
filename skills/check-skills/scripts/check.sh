#!/usr/bin/env bash
# List every skill the agent tools can see for a project (Claude Code, OpenAI Codex, OpenCode,
# Gemini CLI, Cursor, GitHub Copilot), where each comes from, duplicates by name, the
# .claude/skills symlink, and whether the shared skills marketplace/plugin is installed.
# Read-only: it never changes or deletes anything.
# Usage: check.sh [project-root]
set -uo pipefail

MARKETPLACE="stepanbeseda-skills"
PLUGIN="sbskills"
TOOLS="claude codex opencode gemini cursor copilot"

root="$(cd "${1:-$PWD}" 2>/dev/null && pwd -P)" || { echo "ERROR: folder '${1:-}' does not exist."; exit 1; }
issues=0
ok()   { printf '  ok     %s\n' "$1"; }
info() { printf '  info   %s\n' "$1"; }
warn() { printf '  WARN   %s\n' "$1"; issues=$((issues + 1)); }

inventory="$(mktemp)"
trap 'rm -f "$inventory"' EXIT
# inventory lines: <location>\t<tools reading it, comma separated>\t<call name>\t<bare name>\t<real path>
add_dir() {
  local location="$1" tools="$2" dir="$3" prefix="${4:-}" d name
  [ -d "$dir" ] || return 0
  for d in "$dir"/*/; do
    [ -f "$d/SKILL.md" ] || continue
    name="$(basename "$d")"
    printf '%s\t%s\t%s%s\t%s\t%s\n' "$location" "$tools" "$prefix" "$name" "$name" "$(cd "$d" && pwd -P)" >> "$inventory"
  done
}
short() { case "$1" in "$HOME"/*) printf '~%s' "${1#"$HOME"}" ;; *) printf '%s' "$1" ;; esac; }

echo "Project: $root"

# Skill folders and the tools that read them (from each tool's documentation).
# <location label>|<tools>|<path>
locations="project .agents/skills|codex,opencode,gemini,cursor,copilot|$root/.agents/skills
project .claude/skills|claude,opencode,cursor,copilot|$root/.claude/skills
project .opencode/skills|opencode|$root/.opencode/skills
project .gemini/skills|gemini|$root/.gemini/skills
project .cursor/skills|cursor|$root/.cursor/skills
project .github/skills|copilot|$root/.github/skills
user ~/.agents/skills|codex,opencode,gemini,copilot|$HOME/.agents/skills
user ~/.claude/skills|claude,opencode|$HOME/.claude/skills
user ~/.codex/skills|codex|$HOME/.codex/skills
user ~/.config/opencode/skills|opencode|$HOME/.config/opencode/skills
user ~/.gemini/skills|gemini|$HOME/.gemini/skills
user ~/.cursor/skills|cursor|$HOME/.cursor/skills
user ~/.copilot/skills|copilot|$HOME/.copilot/skills"

echo
echo "1) Shared skills ($PLUGIN from the $MARKETPLACE marketplace)"
plugins_json='[]'
if command -v claude >/dev/null 2>&1; then
  if claude plugin marketplace list --json 2>/dev/null | grep -q "\"$MARKETPLACE\""; then
    ok "Claude Code: marketplace '$MARKETPLACE' is added"
  else
    warn "Claude Code: marketplace '$MARKETPLACE' is not added: /plugin marketplace add stepanbeseda/skills"
  fi
  plugins_json="$(claude plugin list --json 2>/dev/null || echo '[]')"
  if printf '%s' "$plugins_json" | grep -q "\"$PLUGIN@$MARKETPLACE\""; then
    ok "Claude Code: plugin '$PLUGIN@$MARKETPLACE' is installed"
  else
    warn "Claude Code: plugin '$PLUGIN' is not installed: /plugin install $PLUGIN@$MARKETPLACE"
  fi
else
  info "Claude Code: the 'claude' CLI is not on PATH, plugins not checked"
fi
if command -v codex >/dev/null 2>&1; then
  if out="$(codex plugin marketplace list 2>/dev/null)"; then
    if printf '%s' "$out" | grep -q "$MARKETPLACE"; then
      ok "Codex: marketplace '$MARKETPLACE' is added"
    else
      warn "Codex: marketplace '$MARKETPLACE' is not added: codex plugin marketplace add stepanbeseda/skills"
    fi
  else
    info "Codex: could not list marketplaces with this codex version; check by hand"
  fi
else
  info "Codex: the 'codex' CLI is not on PATH, marketplace not checked"
fi
# Generated subagent adapters copied by hand (see the skills repository README).
for spec in "codex|$HOME/.codex/agents|toml" "opencode|$HOME/.config/opencode/agents|md"; do
  IFS='|' read -r tool dir ext <<< "$spec"
  [ -d "$dir" ] || continue
  n="$(grep -l 'Generated from skills/' "$dir"/*."$ext" 2>/dev/null | wc -l | tr -d ' ')"
  [ "$n" -gt 0 ] && info "$tool: $n subagent adapter(s) from the skills repository in $(short "$dir")"
done

echo
echo "2) Where skills come from"
while IFS='|' read -r label tools path; do
  add_dir "$label" "$tools" "$path"
done <<< "$locations"
plugin_dirs="$(printf '%s' "$plugins_json" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    data = []
for p in data if isinstance(data, list) else []:
    if p.get("enabled", True) and p.get("installPath"):
        print(p["id"].split("@")[0] + "\t" + p["installPath"])
' 2>/dev/null)"
while IFS=$'\t' read -r plugin path; do
  [ -n "$plugin" ] && add_dir "claude plugin $plugin" claude "$path/skills" "$plugin:"
done <<< "$plugin_dirs"

if [ ! -s "$inventory" ]; then
  info "no skills found in any known location"
else
  # Same real folder reached twice (e.g. through the .claude/skills symlink) is listed once per location.
  awk -F'\t' '{ c[$1]++; n[$1] = n[$1] " " $3; t[$1] = $2 } END { for (l in c) printf "  %-34s %3d  [%s]%s\n", l, c[l], t[l], n[l] }' "$inventory" | sort
fi

echo
echo "3) What each tool sees"
for tool in $TOOLS; do
  line="$(awk -F'\t' -v t="$tool" 'index("," $2 ",", "," t ",") { if (!seen[$5]++) { c++; src[$1]++ } } END { for (s in src) printf "%s%s=%d", (o++ ? ", " : ""), s, src[s]; printf "\t%d", c }' "$inventory")"
  count="${line##*$'\t'}"
  sources="${line%$'\t'*}"
  printf '  %-9s %3s  %s\n' "$tool" "${count:-0}" "${sources:-—}"
done

echo
echo "4) Duplicates (same skill name in two different folders seen by one tool)"
found=0
for tool in $TOOLS; do
  dupes="$(awk -F'\t' -v t="$tool" 'index("," $2 ",", "," t ",") && !seen[$5]++ { n[$4]++; w[$4] = w[$4] " " $1 } END { for (k in n) if (n[k] > 1) print k ":" w[k] }' "$inventory" | sort)"
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    warn "$tool: $d"
    found=1
  done <<< "$dupes"
done
[ "$found" -eq 0 ] && ok "no tool sees the same skill name twice"

echo
echo "5) Project skills folder for Claude Code"
agents_dir="$root/.agents/skills"
claude_dir="$root/.claude/skills"
if [ -L "$claude_dir" ]; then
  target="$(readlink "$claude_dir")"
  if [ "$(cd "$claude_dir" 2>/dev/null && pwd -P)" = "$(cd "$agents_dir" 2>/dev/null && pwd -P)" ]; then
    ok ".claude/skills -> $target (Claude Code sees the vendor-neutral project skills)"
  else
    warn ".claude/skills is a symlink to '$target', expected ../.agents/skills"
  fi
elif [ -d "$claude_dir" ]; then
  if [ -d "$agents_dir" ]; then
    warn ".claude/skills is a real folder next to .agents/skills: move its skills into .agents/skills, then replace it with a symlink to ../.agents/skills"
  else
    warn "project skills live only in .claude/skills (Claude Code-only): move them to .agents/skills and link .claude/skills -> ../.agents/skills"
  fi
elif [ -d "$agents_dir" ]; then
  warn ".agents/skills exists but Claude Code cannot see it: ln -s ../.agents/skills .claude/skills"
else
  ok "this project has no project skills"
fi

echo
echo "Skills uploaded in account settings (e.g. claude.ai → Settings → Skills) are not on disk; review them by hand."
echo
if [ "$issues" -eq 0 ]; then echo "Result: all good."; else echo "Result: $issues thing(s) to look at."; fi
