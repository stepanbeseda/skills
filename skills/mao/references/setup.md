# Step 0 — project setup

Runs when neither `<ROOT>/.mao/project.md` nor the older
`<ROOT>/.mao/project.md` exists. Goal: after one
round of questions, have a project layer that every later step runs from.
You (the orchestrator) write none of it — git yes, file contents are the
worker's job.

## 1. Git (orchestrator)

- The folder is not a git repo (`git rev-parse` fails): `git init -b main`.
  If the folder has files, the worker first lists what would go into the
  first commit and looks for secrets (`.env`, keys, tokens, `*.pem`, large
  binaries); a hit → `.gitignore`, not a commit. Then the first commit
  `chore: initial state`. Empty folder →
  `git commit --allow-empty -m "chore: init"`.
- A repo without commits: the same with an empty commit, so `<base>`
  exists.
- No `origin` remote: ask the user — "Create a GitHub repo?" with
  the options **private** (`gh repo create <folder name> --private --source .
  --push`), **public** (the same with `--public`), **stay local**. Never
  create a repo without an explicit choice. Local = no push, PR or CI (see
  SKILL.md step 7).
- Running in a worktree: nothing special; `<ROOT>` is the worktree root and
  `.mao/` is in git, so every worktree sees it after merge.

## 2. Inventory (worker)

The worker goes through the project and writes a draft
`<ROOT>/.mao/log/project-draft.md` by filling in
`project-template.md`:

- language, build tool, package manager; existing check commands
  (`just check`, `make check`, `npm test`, `pytest`, `cargo test`, …) and
  whether they pass on a clean tree (run them, exit code);
- CI (`.github/workflows/`) and the names of its checks;
- commit style from `git log -20` (language, Conventional Commits or not),
  default branch, merge method from history, and what squash merge uses as
  the commit title:
  `gh api repos/<o>/<r> --jq '.squash_merge_commit_title, .squash_merge_commit_message'`;
- an existing plan or roadmap (`docs/`, `PLAN*`, `ROADMAP*`, issues);
  `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md` — rules the agents must follow
  (link to them, do not copy them);
- a test host / environment, if the project has one (inventory, compose);
- whether the project has a UI served by a dev server (web frontend) — then
  propose the **webapp profile**: the dev/preview command and port for the
  "Preview" section;
- shared machine resources two runs at once would collide on (Docker image
  tags, compose project names, ports, databases, CPU count) — the draft of
  the "Parallel runs" section; when the check is several commands, propose
  one check script that runs them with private names and ends with a
  machine-readable summary line (the first PR may introduce it).

Empty project: check "none yet — the first PR introduces it", new plan.

## 3. Questions (orchestrator)

One round of at most four questions, only about what the inventory
did not settle. Typically: plan path (existing document / new
`docs/plan.md`), check command (proposed / other), test host (none /
description), webapp profile with browser preview (yes / no). Write the
answers verbatim into `project-draft.md`.

## 4. Writing (worker)

- `<ROOT>/.mao/project.md` from the draft and the answers.
- `<ROOT>/.mao/checklist.md` from `checklist-template.md`, narrowed
  to what makes sense in the project. With the webapp profile, append the
  sections of `profiles/webapp-checklist.md` that apply.
- `<ROOT>/.mao/lessons.md` from `lessons-template.md`.
- No plan → from `plan-template.md` at the path given in `project.md`.
- `.gitignore`: add `.mao/log/` (and your tool's agent-memory folder, e.g.
  `.claude/agent-memory/`) if
  missing.

Confirm every file with `wc -l`. The orchestrator commits them as the first
commit of the run's branch (`chore: configure MAO for this project`).
