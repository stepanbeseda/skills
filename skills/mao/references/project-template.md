# MAO — project configuration <name>

Project layer of the `/mao` skill (`<SKILL>`). Whatever stands here
takes precedence over the skill's general procedure. Do not copy the repo's
own rules (`AGENTS.md`, `CLAUDE.md`, `README.md`) here — only link to them.

## Files

- Checklist: `.mao/checklist.md`
- Lessons: `.mao/lessons.md`
- Host gate: `.mao/host-gate.md` | none

## Plan

- File: `docs/plan.md`
- Decisions and boundaries: `## 1.`
- Common PR conditions: `## 2.`
- PR table: `## 3.`; row `| NN | <name> | <depends on> | <status> |`,
  read the number with the regex `^\| (\d{2}) \|`
- Chapters: `### PR NN — <name>`; a new one goes after the last `### PR`
  and before `## 5.`
- Open items: `## 5.`

## Commands

- Check (must be green before the PR): `<command>` | none yet — the first
  PR introduces it. Prefer one script (e.g. `scripts/check.sh --tag <id>`)
  that runs every step, forces tests to really run (no cached test stage
  without a count), uses the names in "Parallel runs", and ends with one
  machine-readable line, e.g. `CHECK OK tree=<hash> <suite>=<passed> …`.
- Targeted tests: `<command>` (with a PR-private tag / name)
- Forbidden: <e.g. `npm install` without a lockfile — with the reason>

## Git

- Base branch: `main`; remote: `origin` | none (local)
- Run branch: `mao/pr<NN>-<slug>`
- Commits: <style, language — default English Conventional Commits>;
  trailers your session or project requires (e.g. a `Co-Authored-By` line), or none
- PR title: `PR NN — <name from the table>` | <e.g. Conventional Commit
  title with suffix `(PR NN)` when squash merge uses the PR title>
- Merge: `gh pr merge --squash --delete-branch`
- CI checks: <names> | none

## Test host

None. | Profile = <what>; the worker verifies: <steps>. Details in
`host-gate.md`.

## Preview

None. | Webapp profile: dev server `<command>` on port `<port>` (from
`<config file>`), production preview `<command>`; main flow to walk:
<steps>. See `<SKILL>/references/profiles/webapp-preview.md`.

## Parallel runs

None (one run at a time). | What several MAO runs or a batch share on this
machine, and the rules:
- Limit: <n> concurrent implementers / heavy checks (CPU, RAM).
- Lock: <e.g. every `docker build` and e2e run under `flock /tmp/<x>.lock`>.
- Private names: <image tags `<x>-<purpose>-pr<NN>`, compose project /
  database / port per PR>; shared default names belong to nobody — use them
  only inside your own locked run.
- Schema migrations: the next number after `<base>`; renumber on rebase.
- Rebase after the base branch was squash-merged:
  `git rebase --onto origin/<base> <old-base-tip>`; a tree-identical rebase
  (`git diff <checked> HEAD` empty) keeps the check valid.

## Stop-and-ask

<Commands and operations for which the orchestrator always asks the user.>

## Role rules

### Designer (in addition to the skill's spec)
### Worker (additional spec checks)
### Implementer
### Reviewer (repo rules)
