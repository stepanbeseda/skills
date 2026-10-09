#!/usr/bin/env bash
# Publish changes in the shared skills repository: rebuild the subagent adapters, secret scan,
# version bump, validation, commit and push. Never forces anything.
# Usage: publish.sh <skills-repo-path> ["change description"]
set -euo pipefail

repo="${1:?missing path to the skills repository}"
message="${2:-Update skills}"

cd "$repo"
for f in .claude-plugin/marketplace.json .claude-plugin/plugin.json plugin.json scripts/validate.py scripts/build-adapters.py; do
  [ -f "$f" ] || { echo "ERROR: $repo is not the skills repository (missing $f)."; exit 1; }
done

branch="$(git rev-parse --abbrev-ref HEAD)"
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  if ! git pull --rebase --autostash -q; then
    echo "ERROR: could not rebase onto the remote. Resolve it by hand (git status); nothing was pushed."
    exit 1
  fi
fi

# Subagent adapters are generated from skills/<skill>/roles/*.md; bring them in sync first.
python3 scripts/build-adapters.py

git add -A
changed="$(git diff --cached --name-only)"
if [ -z "$changed" ]; then
  echo "Nothing to publish."
  exit 0
fi

# The repository is public: stop on anything that looks like a secret or private contact data.
leaks="$(git diff --cached -U0 | grep -E '^\+' | grep -v '^+++' | grep -nE \
  -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' \
  -e '(ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}' \
  -e 'sk-(ant-)?[A-Za-z0-9_-]{20,}' \
  -e 'xox[abpr]-[A-Za-z0-9-]{10,}' \
  -e 'AKIA[0-9A-Z]{16}' \
  -e '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' \
  -e '/home/[a-z_][a-z0-9_-]*/|/Users/[A-Za-z0-9_-]+/' \
  | grep -vE '@example\.(com|org|net|invalid)|noreply@' || true)"
if [ -n "$leaks" ]; then
  echo "ERROR: the change contains something that must not be public (secret, e-mail or personal path):"
  printf '%s\n' "$leaks" | cut -c1-160
  echo "Remove it and run again. Nothing was committed."
  git reset -q
  exit 1
fi

# Installed copies update only when the version changes: when skills or adapters changed, bump
# the patch version in both manifests (Claude Code and Agent Plugins) to the same value, unless
# this change already sets a version.
if printf '%s\n' "$changed" | grep -qE '^(skills|adapters)/'; then
  if git diff --cached -- plugin.json .claude-plugin/plugin.json | grep -q '^+.*"version"'; then
    echo "  version set in this change, kept"
  else
    python3 - plugin.json .claude-plugin/plugin.json <<'PY'
import json, re, sys
paths = sys.argv[1:]
old = json.load(open(paths[1]))["version"]
if not re.fullmatch(r"\d+\.\d+\.\d+", old):
    sys.exit(f"ERROR: {paths[1]} has no MAJOR.MINOR.PATCH version")
major, minor, patch = map(int, old.split("."))
new = f"{major}.{minor}.{patch + 1}"
for path in paths:
    text = open(path).read()
    text, n = re.subn(r'("version"\s*:\s*")[^"]*"', r'\g<1>' + new + '"', text, count=1)
    if n != 1:
        sys.exit(f"ERROR: no version field in {path}")
    open(path, "w").write(text)
print(f"  sbskills: {old} -> {new}")
PY
  fi
fi

fail() { printf '%s\n' "$1"; echo "ERROR: $2; nothing was committed."; git reset -q; exit 1; }
out="$(python3 scripts/validate.py 2>&1)" || fail "$out" "the repository did not validate"
if command -v claude >/dev/null 2>&1; then
  out="$(claude plugin validate . 2>&1)" || fail "$out" "the Claude Code marketplace did not validate"
fi

git add -A
git commit -qm "$message"
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  git push -q
else
  git push -q -u origin "$branch"
fi
version="$(python3 -c 'import json; print(json.load(open("plugin.json"))["version"])')"
echo "Published: $(git log -1 --format='%h %s') (sbskills $version)"
