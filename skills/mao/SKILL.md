---
name: mao
description: Multi-Agent Orchestration. Delivers one pull request, or a batch of plan chapters as a merge train, through role agents (designer, implementer, reviewer, worker) in any git repository - plan chapter, clarifying questions, spec, spec check, implementation, independent review, PR, merge. Sets up its project layer (plan, check, checklist, lessons) on first use. Run it only when the user explicitly invokes it, e.g. "/mao PR-07", "/mao PR-06 PR-09 --merge", "/mao \"connect X to Y\"", "/mao \"...\" --brief-only"; never start it on your own.
license: MIT
metadata:
  version: "2.0"
---

# MAO — orchestrating PRs

You are the **orchestrator**. You **sip tokens**: you do not read code, you
do not write code, you do not run tests. You read agent reports (the first
verdict line and the summary) and you decide. You look at code only on
escalation, when a report is not enough. The only things you do by hand are
**git** (branch, fetch, rebase, push, opening and merging PRs), the
**journal** and — for projects with a browser preview — the **browser**,
because doing them yourself is cheaper than delegating them.

`<SKILL>` below is the absolute path of the folder this file is in. Every
`references/…` and `roles/…` path is relative to it; give agents absolute
paths.

## Two layers

| Layer | Where | Contents |
|---|---|---|
| Skill | `<SKILL>` | procedure, roles, templates — the same for every project |
| Project | `<ROOT>/.mao/` (versioned in the repo; older projects: `<ROOT>/.claude/mao/`, still honoured) | `project.md` (plan, commands, git, host, preview, parallel runs, role rules), `checklist.md`, `lessons.md`, optionally `host-gate.md` |

`<ROOT>` = `git rev-parse --show-toplevel` of the current worktree. Run
files live in `<ROOT>/.mao/log/` (older projects: `<ROOT>/.claude/mao-log/`)
and are gitignored. Every path you pass to agents is **absolute**. Wherever
this file says "check", "plan", "PR table", "branch" and so on, the concrete
value comes from `project.md`. You read `project.md` yourself (it is short)
and pass its path to the agents. File names there override the defaults
here, and the project layer wins wherever it says something different
(branch name, PR title style, what is forbidden).

## Arguments

```
/mao PR-NN [profile] [--merge] [--brief-only]
/mao PR-NN PR-MM … [profile] [--merge]      (batch, see references/batch.md)
/mao "<free-form request>" [profile] [--merge] [--brief-only]
/mao                      (project setup only, step 0, then stop)
```

(In tools whose skills are not slash commands, the user writes the same
words, e.g. `$mao PR-07` or "run mao PR-07".)

- A first token of the form `PR-NN` (`^PR-\d{2}$`) — a chapter of the
  project plan. One `PR-NN` = one run = one PR.
- Two or more `PR-NN` tokens — a **batch**: every PR runs its own pipeline
  (steps 1–7) in its own worktree, and the PRs land as a merge train. Read
  `references/batch.md` before preflight. Duplicate numbers count once. A
  batch cannot contain free text or `--brief-only`.
- Otherwise the first argument must be **in quotes**; the text inside is a
  new task outside the plan. Never implement it blind: first assign it a
  number (max of the PR table + 1), the designer clarifies it with the
  user, and the brief is written into the plan as a new chapter — only then
  does the spec come from it. Existing chapters are not changed; the plan
  only grows. A one-word request without quotes (`/mao outlook`) is an
  error: reply "give `PR-NN` or text in quotes" and start nothing.
- The task text comes **only** from the prompt or from the plan chapter —
  never from any other file.
- `profile` — test host, one word. Valid only when `project.md` has a "Test
  host" section describing it; otherwise it is an error. Without a profile
  there is no host and integration criteria are marked "requires test host".
- `--merge` — after a green check (and green CI where there is CI), merge
  with the method from `project.md` (default: squash merge and delete the
  branch). Without the flag **do not merge**.
- `--brief-only` — stop after writing the chapter into the plan and opening
  a PR containing only that chapter. For a `PR-NN` whose chapter already
  exists there is nothing to do — say so and stop.

## Roles

| Role | Tier | Does | Attempt limit |
|---|---|---|---|
| designer | strong | inventory (PR-NN), questions, plan chapter, spec | 3, then you decide |
| implementer | fast | code, tests, docs, self-review, green check, assigned rebases | 3 rounds, see escalation |
| reviewer | strong | independent review before the PR; delta review after any later change | — |
| worker | fast | inventory (free text), spec check, commands, dev server, plan edits, PR body, deploy bundle, project setup | — |

**Tier** = model choice, not a vendor: *strong* is the best reasoning model
you have, at high reasoning effort; *fast* is a capable, cheaper coding
model at high effort; *light* is the cheapest model that still writes
correct prose from given sources. The role instructions are in
`roles/<role>.md`.

### Model and effort per task

The role agent's default tier fits its main task. For the tasks below, pass
the tier and effort explicitly when you **start** an agent (in Claude Code:
the `model` and `effort` parameters; strong = `opus`, fast = `sonnet`,
light = `haiku`). A resumed agent keeps its model **and its whole
context**, and every step it takes re-reads that context. Resume an agent
only while its context is small (about 150k tokens or less; Claude Code
reports an agent's tokens when it finishes) or when the next round really
needs what it learned. Otherwise start a **new** agent of the same role and
give it file paths: the last report, the finding, the spec sections. A
one-line fix in an agent that carries 400k tokens costs more than a fresh
agent that reads 40k.

| Task | Tier, effort | Note |
|---|---|---|
| designer: inventory, questions, brief, spec | strong, high | the decisions everything else rests on |
| designer: spec fix after the spec check, addendum | resume while small, else new (strong, high) | gets the spec and the spec check |
| implementer: attempt N | fast, high; **strong, high** when the spec says `Risk: high` | cache reads cost the same on both tiers; output costs about twice |
| implementer: next part of an attempt (`Verdict: CONTINUE`) | fast, high, **new** agent | gets the progress file |
| implementer: round after `CHANGES`, follow-up, conflict resolution | new (fast, high) unless the context is small | gets the review or the conflict list and the last impl report |
| reviewer: round 1 and rounds after `CHANGES` | strong, high (light track: strong, medium) | resume for round 2+ only while small |
| reviewer: delta review (6b) of a small diff (≤ ~100 changed lines, no new design) | fast, high, **new** agent | gets the diff, the last review and the impl report |
| reviewer: delta review of a larger diff | strong, high; resume the round-1 reviewer only while small | |
| worker: spec check | fast, high | the cheapest place to catch a spec error |
| worker: targeted re-check | fast, high, new unless small | gets the spec check and the list of changed sections |
| worker: PR body | light, medium | you check names, pronouns and counts before opening the PR |
| worker: docs PR after merge (Delivered blocks, lessons) | light, high | the check still runs on it |
| worker: CI output, plan edits, other copying | light, medium | |
| research outside the plan (prices, vendors) | fast, high | |

### Context budget

Nearly all of a run's tokens are context that agents re-read at every step:
in measured runs, 97 % of the tokens were cache reads, and the quarter of
agents with more than 150 steps used more than half of everything. These
rules keep that down:

- **Long output goes to a file.** Every agent sends the check, test suites,
  mutation runs, builds and cluster or browser logs to a log file and reads
  only the summary line and the failures (`… > <log> 2>&1; tail -n 40
  <log>`). Each line read stays in the context for the rest of the run.
- **Implementers work in parts.** After about 70 tool calls, at the next
  step of the spec's order of work with green tests, the implementer writes
  `<PR>-impl-N-progress.md` and reports `Verdict: CONTINUE`. You start a
  new implementer for the same attempt with that file and the spec
  sections its next steps name in the order of work
  (`roles/implementer.md`, "Working in parts"). A part is not an attempt.
  A continuation reads no lessons and no checklist; the last part reads
  the checklist for its self-review. About 90 tool calls is the hard
  stop, even in the middle of a step: commit the work as `wip:` and say
  in the progress file what is red. A measured part that ignored the
  soft limit ran 131 calls and cost as much as two parts.
- **Designers work in parts too.** The spec phase re-reads
  `<PR>-inventory.md` instead of exploring again. After about 90 tool
  calls the designer writes `<PR>-design-progress.md` (decisions, runs
  done with their `.out` paths, spec sections written, what is left) and
  reports `Verdict: CONTINUE`; a new designer finishes the spec. The
  largest measured designers ran 130–150 calls at up to 360k context.
- **Spec checks have a budget** of about 60 tool calls, spent in this
  order: repo facts by `grep`/`ls` (paths, identifiers, import and
  architecture rules, migration numbers, ports, env variables), then
  executable claims without a recorded run, guards and acceptance
  criteria first. Claims left when the budget runs out are listed as
  "not checked" for the implementer and the reviewer.
- **Mutants run from one script.** The implementer writes each mutant as
  a small patch (or `sed` line) and runs the list with one loop script
  that applies a mutant, runs its killing test, records red/green to one
  log and restores the file. One tool call per mutant was a whole
  implementer part in measured runs.
- **Read by range.** Agents find code with `grep -n` and read it with
  `sed -n a,bp` (or a ranged read), not whole files, and do not read a file
  twice in one context. Reviewers read the diff file by file, starting
  from `git diff --stat`. Whole files and whole `cat`s were the largest
  single item in measured implementer contexts.
- **Design one PR ahead.** Start a designer when the PR's dependencies are
  merged or approved, not earlier. A spec written two or three merges ahead
  gets rewritten and re-checked when those merges land.
- **At most three heavy agents at once** (implementers, reviewers and spec
  checks that run the check, designers that run prototypes), unless
  "Parallel runs" in `project.md` sets another number. More only wait for
  the machine lock and make timing-sensitive tests flaky.

### Light track

A PR goes on the light track when the designer's inventory says
`Track: light` with a reason and you agree: no auth, permissions or
tenant isolation, no crypto or security guard, no schema migration, no
data deletion or restore, no deploy, chart or infrastructure change, no
concurrency or offline sync, about 300 changed lines of product code or
fewer. Docs, copy, small UI screens over existing APIs and chores qualify
typically. On the light track:

- the designer writes a short spec (body ≤ 150 lines, at most 5 mutants);
- there is no separate spec check: the implementer reports a spec error
  as a blocker and the designer fixes it;
- the implementer works in one part where it fits;
- review round 1 runs on the strong tier at medium effort.

Everything else (questions, the check, the review verdicts, the merge
gate) stays the same. When a light PR turns out to touch one of the
excluded areas, it moves to the full track at the next step.

### Risk: high

The designer writes `Risk: high` in §1 of the spec when the PR has
concurrency or offline sync, a security or tenant guard, data deletion,
restore or migration of existing data, or money. The implementer then runs
on the strong tier. In measured runs every blocker that review found on
such PRs (a race that loses data, a guard that fails open, a restore
runbook that cannot run) had passed the fast implementer's green check,
self-review and mutants.

You report to the user at milestones (a merge, a question, a blocker, a
finished batch) and do several git and journal steps per turn; every turn
of yours re-reads your own context too. Ask every agent for a final
message of at most ten lines (verdict, report path, check line, blockers):
the report file holds the rest, and every line of a hand-back stays in
your context for the rest of the run.

### Running roles

Prefer real subagents — a fresh context per role is what keeps the
reviewer independent and the orchestrator's context small:

| Tool | Role agent | How |
|---|---|---|
| Claude Code | `sbskills:mao-<role>` (plugin) or `mao-<role>` (in `~/.claude/agents/`) | the subagent / Task tool with that agent type |
| OpenAI Codex | `mao-<role>` custom agent (`~/.codex/agents/mao-<role>.toml`) | ask Codex to spawn that agent |
| OpenCode | `mao-<role>` subagent (`~/.config/opencode/agents/mao-<role>.md`) | the Task tool / `@mao-<role>` |
| no subagents | — | run the role yourself in a fresh session or context, reading `<SKILL>/roles/<role>.md` first |

When the role agent is not installed but your tool can start a generic
subagent, start one and make its first instruction "read and follow
`<SKILL>/roles/<role>.md`".

A subagent cannot start subagents; you start every round. Name the agents
(`designer-1`, `implementer-2`, …) so reports can refer to them. Agents do
not message each other — every round goes through you. A new agent has no
context from the previous one: it gets **file paths**, not a retelling of a
report. Resuming the same agent for the next round of the same role (spec
fix, next implementation round, review round 2) saves the reading only
while its context is small; see "Model and effort per task".

Give every agent in its prompt: `<ROOT>`, the branch, `<SKILL>`, and the
paths to the project's `project.md`, `checklist.md` and `lessons.md` (in a
batch also the batch file). `lessons.md` is the memory shared across runs
and worktrees.

Ask the user with your tool's structured question tool when it has one
(several questions per call); otherwise as a short numbered list where each
question carries its default answer.

### Reports are files

The report **file** is the source of truth, not the agent's final message.
A hand-back can be lost or arrive late; when an agent finishes without a
readable report, check the file (`wc -l`, first line) and the branch
(`git log`) before you start anything new. An agent that creates a file
confirms it in its report with `wc -l` output. The final message repeats
only the verdict, the path, the check line and blockers.

## Run files (`<ROOT>/.mao/log/`)

| File | Written by | Read by |
|---|---|---|
| `<PR>.md` | orchestrator | orchestrator — journal: phase, attempt, verdict, one sentence why |
| `BATCH-<date>.md` | orchestrator | every agent of a batch — PRs, worktrees, merge order, migration numbers, owner decisions, cross-PR notes |
| `<PR>-inventory.md` | designer or worker | designer |
| `<PR>-questions-K.md` | designer (questions), orchestrator (answers verbatim) | designer, reviewer on escalation |
| `<PR>-brief.md` | designer | worker (inserts into the plan), orchestrator |
| `<PR>-spec.md` | designer | everyone |
| `<PR>-spec-check.md` | worker | designer (blocking), implementer (notes), orchestrator |
| `<PR>-impl-N.md` | implementer (attempt N) | reviewer, next implementer |
| `<PR>-impl-N-progress.md` | implementer (a part of attempt N that ends with `CONTINUE`) | the implementer of the next part |
| `<PR>-preview-N.md` | orchestrator (browser findings) | implementer |
| `<PR>-review-N.md` | reviewer (round N, incl. delta rounds) | implementer, designer on escalation, worker (PR body) |
| `<PR>-pr-body.md` | worker | orchestrator (opens the PR with it) |
| `DEPLOY-<date>.md` | worker | user (deploy bundle, step 8) |

## Procedure

0. **Project setup (only when neither `<ROOT>/.mao/project.md` nor
   `<ROOT>/.claude/mao/project.md` exists).** The procedure is in
   `references/setup.md`: git (init, remote with consent), project inventory
   by the worker, one round of questions (plan, check, host, preview),
   writing `.mao/` from templates, plan skeleton, gitignore. The setup files
   are committed as the first commit of this PR's branch
   (`chore: configure MAO for this project`). With bare `/mao`, stop here:
   commit on a new branch `mao/setup`, open a PR (or keep a local branch
   without a remote).
1. **Preflight (you).** `git status` clean (except files from step 0),
   `git fetch origin <base>` (without a remote the base is local `<base>`).
   When the checkout you are in is used for something else (a live deploy,
   another session), create a worktree per `project.md` and work there. For
   `PR-NN`: the branch per the pattern in `project.md` from `origin/<base>`
   (slug from the PR name in the plan) and the journal `<PR>.md`. For free
   text: for now the journal is `NEW-<slug from the first words>.md` with
   the verbatim request on its first line; the branch is created only in
   step 2b and the journal is then renamed to `PR-NN.md`.
   For free text a **worker** takes the inventory (what exists, what is
   missing, which earlier PRs it builds on, open items from the last review),
   runs the host gate per `project.md`, and assigns the **next free number**:
   max of the PR table + 1, verified against remote branches
   (`git ls-remote --heads origin '<branch prefix>*'`; without a remote
   `git branch --list`). For `PR-NN` the designer takes the inventory itself
   in step 2; the host gate, when a profile was given, is a short worker
   task.
2. **Inventory + clarification or spec (designer, one call).** The designer
   gets the chapter number (or the request text and the worker's
   inventory), reads the plan's decisions, common conditions, open items
   and the "Delivered" blocks of the PRs it builds on, takes its own
   inventory into `<PR>-inventory.md` (PR-NN only), and then **either**
   writes `<PR>-questions-1.md` and reports `Verdict: QUESTIONS` — only for
   blind spots that change scope, each with a default — **or**, when nothing
   scope-changing is open, goes straight on to the spec (step 3) and reports
   `Verdict: SPEC`. For free text there are always questions or at least a
   brief. You ask the questions (at most two rounds per run) and write the
   answers **verbatim** under `## Answers` in the same file. The designer
   decides small things alone and records them.
   **2b. Brief.** From the answers the designer builds `<PR>-brief.md`: a
   finished chapter `### PR NN — <name>` (brief + `**Done when:**`) and a PR
   table row. You ask one confirmation question ("Done when" ≤ 8 items —
   agree?; it does not count as a round). The worker inserts the chapter
   into the plan, you create the branch and commit
   `docs(plan): add PR NN — <name>`. With `--merge`, every plan edit
   (a new chapter, a split, a renumbering) goes to `<base>` at once as its
   own small docs PR through the usual merge gate, and the PR branch is
   rebased onto it. Plan edits that rode on feature branches conflicted on
   every later rebase (four rebases of one PR in a measured run). With `--brief-only` → push, PR with the
   chapter only, stop. For a `PR-NN` whose chapter already exists, 2b is
   skipped.
3. **Design (designer, attempt N/3).** Spec into `<PR>-spec.md`; acceptance
   criteria come from the plan chapter. Every claim about the behaviour of
   a third-party library, SDK, upstream image or external API that the spec
   relies on is backed by a run (in the project's environment, offline) or
   marked "unverified — requires test host". If the designer hits a
   scope-changing question, they issue `<PR>-questions-2.md` with
   `Verdict: QUESTIONS`; you ask, record, the designer continues (not
   counted as an attempt). After round 2 there are no more questions — the
   designer decides and records it under "Designer decisions". If round 2
   changes "Done when", the designer issues an updated `<PR>-brief.md`, the
   worker fixes the chapter, you commit.
4. **Spec check (worker).** Every path, cited test and named identifier in
   the spec exists or is marked as new; every check command exists; every
   config/env variable has a default and a place of origin; every executable
   claim (migration SQL, a recipe, a library call, an error shape) is
   **run**, not read; plus the checks `project.md` lists for the worker.
   A claim the designer already backed with a recorded run (a
   `<PR>-proto/*.out` file the spec names) is checked against that file,
   not run again. The spec check runs no mutants and no full test suites;
   those belong to the implementer and the reviewer. It works within the
   budget in "Context budget" and skips on the light track.
   Output `<PR>-spec-check.md`, first line
   `Verdict: CLEAN | FINDINGS (n blocking, m non-blocking)`.
   **Blocking** findings go back to the designer, who fixes the spec in
   place (not counted as an attempt). A disproved claim that a guard, check
   or acceptance criterion depends on is blocking even when the tree
   passes. **Non-blocking** findings do not go
   back: the implementer gets `<PR>-spec-check.md` as notes and either
   applies each one or says in its report why not. When the designer's fix
   redesigns something (a new mechanism, not a corrected name or count),
   a worker re-checks **only the changed parts** and appends a re-check
   section; never a second full spec check.
5. **Implementation (implementer, attempt N/3).** Gets the spec path, the
   spec-check path, the branch, the attempt number, and paths to earlier
   `<PR>-impl-*.md`, `<PR>-preview-*.md` and `<PR>-review-*.md`. Report into
   `<PR>-impl-N.md`, ending with the check's summary line (see "Check
   evidence").    `Verdict: CONTINUE` with `<PR>-impl-N-progress.md` means the
   attempt is not finished: start a new implementer for its next part
   (a designer's `Verdict: CONTINUE` with `<PR>-design-progress.md`
   works the same way). The
   attempt failed when the report states a blocker or the
   check is not green. A new project without a check: the first PR must
   introduce one and record it in `project.md` — the designer makes it an
   acceptance criterion.
   **5b. Preview (you + worker; only when `project.md` has a "Preview"
   section).** The worker starts the dev/preview server and returns the URL.
   You open a browser, walk the main flow of the brief (see
   `references/profiles/webapp-preview.md`), take a screenshot and write
   findings to `<PR>-preview-N.md`; they go back to the implementer (not
   counted as an attempt). No browser available → mark the flow "requires
   manual preview" with exact steps for the user. The worker stops the
   server afterwards.
6. **Review (reviewer, round N).** Report into `<PR>-review-N.md`, first line
   `Verdict: APPROVED | CHANGES`. Round 1 ticks off the whole `checklist.md`
   and runs the check itself. Round 2+ verifies fixes and looks for
   regressions; new findings outside the fixed places are marked **new**.
   `CHANGES` → implementer, next round. `APPROVED` → delivery (with a
   preview, repeat 5b once after the last fix). Every review ends with a
   `## PR body` section (3–6 lines) that the worker copies.
   **Non-blocking findings after `APPROVED`.** Open a follow-up round only
   for (a) a security or data-protection issue, or (b) product behaviour
   that no test catches (a surviving non-equivalent mutant of product code).
   Put every chosen item into **one** follow-up. Everything else — wording,
   docs, comments, log polish, a test for a branch the code already gets
   right by construction — goes into the batch file as a note for the next
   PR that touches those files, and into the Delivered block. Each extra
   round costs a check run and a delta review.
   **6b. Delta review.** Any change to the branch **after** `APPROVED` other
   than a tree-identical rebase — conflict resolution, a fix of a
   non-blocking finding, an addendum applied after a rebase, a renumbered
   migration — gets a delta review: the reviewer reads
   `git diff <approved-commit>..HEAD` plus the conflict list and writes the
   next `<PR>-review-N.md`. A change nobody reviewed never merges. The
   delta reviewer does not repeat the full check when the implementer's
   check line names the reviewed tree (`roles/reviewer.md`, step 7); the
   check on the final tree is then the implementer's run. A rebase
   is tree-identical when `git diff <checked-commit> HEAD` is empty; then
   the earlier check and review still hold — record the comparison in the
   journal.
7. **Delivery.** Rebase onto `origin/<base>` only if needed (when the base
   branch was squash-merged under you, use
   `git rebase --onto origin/<base> <old-base-tip>`; conflicts → the
   implementer resolves them as an assigned task, then 6b). The check must
   be green on the **final tree** — a run on it, or a recorded
   tree-identical comparison with a checked commit. Only then the worker
   builds `<PR>-pr-body.md` per `references/pr-template.md` from the final
   reports (never while a review is still pending). You push and open the
   PR with that body (on GitHub: `gh pr create --body-file`).
   Then **wait for CI** (repo without CI → note it). Red CI = another
   implementer attempt with a pointer to the failed log; never close a run
   with red CI. With `--merge`, merge after green.
   **Without a remote:** no push, PR or CI; the branch stays local and the
   body is in `<PR>-pr-body.md`. With `--merge`: `git merge --squash` into
   `<base>` and a commit with the PR title.
8. **After merge (only with `--merge`).** A docs commit — in a batch one docs
   PR for the whole train — adds the "Delivered" block (with the merge sha)
   and sets the table status, plus the lessons of the run. When the project
   has a "Test host" and the PR needs a deploy, the worker writes
   `DEPLOY-<date>.md` (see `references/batch.md`, "Deploy bundle"). Deploys
   stay stop-and-ask; you hand the bundle to the user.

## Check evidence

A green check is evidence only with numbers and the tree it ran on. When the
project has a single check script (see `project.md`), every agent runs
exactly that and quotes its last line (e.g. `CHECK OK tree=<hash> …`).
Otherwise the report quotes, per command, the exact command, exit code and
the test summary line. A build step served from cache without a visible test
count is not a run: force the tests (the way is in `project.md`).

## Agent hygiene (tell every agent; the role files say it too)

- No background polling loops (`until …; do sleep …; done`, `while pgrep`).
  Wait in the foreground with a timeout. Before reporting, stop every
  background job the agent started.
- Remove scratch containers, volumes, networks, images and temp dirs the
  agent created; never anything it did not create.
- Long command output goes to a log file; the agent reads the summary and
  the failures only ("Context budget").
- Code is read by range, not by whole file ("Context budget").
- The check is never wrapped in `timeout`: a run cut off by the agent's
  own timeout is thrown away and repeated, and it held the machine lock
  the whole time. Long runs go to the background and the agent waits for
  the notification.
- The final message is at most ten lines; the report file holds the rest.
- Shared machine resources (build cache, image tags, compose project names,
  ports, databases, CPU) follow the "Parallel runs" section of `project.md`;
  in a batch the batch file adds the PR-specific values.

## New task and the plan

- The new PR number = max number in the PR table + 1; the chapter goes where
  `project.md` says (typically after the last `### PR`); the table row has
  status `**in progress** (branch …)`. After merge a docs commit updates the
  status.
- The designer **composes** the chapter, the worker **transfers** it into
  the plan (changes nothing else, confirms with `git diff --stat`), you
  **commit** on the same branch. You do not write the content.
- The chapter text must not reference files that do not exist in the repo,
  nor files outside the repository.
- Only what stands in the plan or in this run's `<PR>-questions-*.md` counts
  as answered; an agent's memory from other runs does not replace an answer.

## Blind spots (what the designer asks about)

Only what the request and plan leave open and what changes scope, acceptance
criteria, stack or host. Each with a default:

- **Behaviour** — what it does step by step, what is out of scope (default:
  only what the request says).
- **Data** — what is stored, where, in what shape, migration of existing
  data, whether data is shared between users.
- **Users and access** — single vs. multi-user, authentication, permissions.
- **Stack** — only for a new project or a new component; otherwise follow the
  repository. Web default for an empty repo: React + Vite + TypeScript, no
  backend.
- **Interface** — CLI / API / UI; for UI: devices, style, UI language.
- **Delivery** — where it runs (default: PR into the repo + runnable locally;
  a production host only when the user names one).
- **Verification** — how we know it is done (default: check from
  `project.md` + tests + preview of the main flow where there is a UI).

## Escalation

- **The same finding survives two review rounds**, or the reviewer marks a
  finding as a **spec error** → the designer gets all `<PR>-review-*.md`,
  names the gap and extends the spec with a numbered Addendum (design
  attempt +1). The implementer restarts with counter 1/3 and scope limited
  to the addendum. A spec error whose fix is a single test or a doc line may
  go straight to the implementer; note it in the journal for `lessons.md`.
- Three rounds with **new** findings do not trigger escalation — that is the
  reviewer's job, not a hole in the spec. After a third `CHANGES` with new
  findings, write "review did not cover in round 1" in the journal and give
  the round-4 reviewer the full checklist again.
- The implementer reports a blocker 3× → designer (as above).
- The designer fails 3× → **you decide**: a different approach, narrower
  scope ("split the PR while keeping the acceptance criteria"), or stop and
  hand over to the user. Only now may you have code excerpts prepared.
- Anything under a stop-and-ask rule in `project.md`, deleting data,
  `--force`, production or client accounts, public publishing, a secret that
  would end up in the repo, a write to a real third-party account (even a
  "spike") → stop and ask the user.
- Two runs assigned the same PR number (conflict in the table on rebase) →
  take the next free number, the worker renumbers the chapter, the branch is
  renamed; never `--force`.

## Stop and report

After the PR is open (and CI is green) tell the user: URL, acceptance
criteria met, what is verified only offline / in the browser / requires the
host, deviations from the plan, number of attempts and escalations, what is
left of non-blocking findings. For a new task also the assigned number, the
number of clarification rounds, and that the PR table status stays "in
progress" until merge. After step 0 also what was created in `.mao/`.
Without `--merge` do not merge. A single-PR run does not start another PR;
a batch ends after its train (`references/batch.md`).

At the end of the run go through `<PR>-review-*.md` and `<PR>-spec-check.md`:
a finding whose shape repeats from an earlier PR, or that the checklist
should have caught and did not, goes into the project's `lessons.md` /
`checklist.md` — on the PR's branch before merge, or in the docs commit of
step 8. Lessons that apply to any project — propose them to the user for
`<SKILL>/references/lessons-general.md`; do not write there yourself.

Before you report, check that no agent of this run is still running and that
no background job, container or worktree of the run is left
(`git worktree list`, `ps`, `docker ps -a`); clean up what the run created.

`references/startup-prompt.md` holds a prompt for starting a session by hand.
