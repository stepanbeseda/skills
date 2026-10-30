# mao — multi-agent orchestration of pull requests

`mao` delivers one pull request, or a batch of plan chapters as a merge
train, through role agents in any git repository. The orchestrator reads
reports and decides; the roles do the work:

| Role | Tier | Does |
|---|---|---|
| designer | strong | inventory, clarifying questions, plan chapter, spec (backed by runs) |
| implementer | fast | code, tests, docs, self-review, green check; works in parts |
| reviewer | strong | independent review before the PR, delta review after any later change |
| worker | fast / light | spec check, commands, PR body, docs, plan edits, deploy bundle |

Pipeline per PR: questions → spec → spec check → implementation →
review (→ fixes → review) → PR → green check and CI → merge → docs.

The procedure is in [SKILL.md](SKILL.md), the roles in [roles/](roles/),
templates in [references/](references/), and the history in
[CHANGELOG.md](CHANGELOG.md).

## Use

```
/mao                          set up the project layer (.mao/) and stop
/mao PR-07 [--merge]          one plan chapter
/mao PR-06 PR-09 --merge      a batch as a merge train
/mao "connect X to Y"         a new request: questions, plan chapter, then the PR
```

It runs only when invoked explicitly. Stop-and-ask rules in the project's
`.mao/project.md` (deploys, accounts, secrets, data deletion) always hold.

## Versions

| Version | Date | Theme |
|---|---|---|
| 0.2.6 | 2026-10-30 | light track, `Risk: high` → strong implementer, designer parts, spec-check budget, mutants from one script, plan edits straight to base |
| 0.2.5 | 2026-10-30 | README with benchmarks, CHANGELOG (docs only) |
| 0.2.4 | 2026-10-30 | read by range, diff-first review, shorter implementer parts, short hand-backs |
| 0.2.3 | 2026-10-30 | context budget: logs to files, implementer parts, fresh agents, slim spec check |
| 0.2.2 | 2026-10-29 | model and effort per task, light tier, delta review reuses the check |
| 0.2.1 | 2026-10-11 | disproved spec claims are blocking |
| 0.2.0 | 2026-10-09 | first marketplace version |

## Benchmarks

Measured on one long run: a private TypeScript monorepo (pnpm, PostgreSQL
with RLS, Vitest, Playwright, Helm/k3d) with a 44-PR plan, orchestrated
with `--merge` from 2026-10-22. Orchestrator on the strong model (Opus),
roles per the model table of each version.

### Method

- Source: the Claude Code transcripts of the orchestrator and of every
  subagent. Per assistant message (deduplicated by message id) the usage
  fields input, cache write, cache read and output.
- **Raw** = the sum of the four fields, in millions of tokens (M).
  **Input-equivalent** = input + 1.25 × cache write + 0.1 × cache read +
  5 × output, a rough price weight within one model.
- **Context per step** = input + cache write + cache read of one assistant
  message, averaged over the agent's steps.
- An agent counts for the version it was started under. Agents still
  running when the numbers were taken are left out of the per-task
  averages.
- Caveats: one project; the PRs of each period differ in size; 0.2.3 has
  few samples per task. Treat single-sample rows as indications.

### Totals per version

| | 0.2.1 | 0.2.2 | 0.2.3 | 0.2.4–0.2.5 |
|---|---|---|---|---|
| Period | 10-22 → 10-29 | 10-29 → 10-30 | 10-30 (first hours) | 10-30 (9 hours) |
| Subagents | 87 | 23 | 20 | 48 |
| PRs merged in the period | 12 + docs | 4 + docs | 1 + docs | 3, four more in flight |
| Subagent tokens, raw | 2 034 M | 607 M | 177 M | 404 M |
| Subagent tokens, input-equivalent | 335 M | 100 M | 29 M | 72 M |
| Average context per step (all agents) | 255k | 294k | 164k | **141k** |
| Agents with more than 150 steps | 17 | 8 | 0 | 0 |
| Orchestrator: average context per step | 180k | 212k | 204k | 219k |

Cache reads were 97 % of all tokens in 0.2.1/0.2.2: the cost is the
context an agent carries, re-read at every step.

### Per task (average per finished agent)

| Task | 0.2.1 | 0.2.2 | 0.2.3 | 0.2.4 |
|---|---|---|---|---|
| Designer: spec (strong) | 31.5 M, 144 steps, ctx 215k | 29.3 M, 144 steps, ctx 204k | — | 22.6 M, 116 steps, ctx 188k (n=3; max 150 steps, ctx 359k) |
| Designer: spec fix | resumed designer (one case: 47.9 M, ctx 197k) | resumed designer | **2.9 M**, new agent, ctx 78k (n=2) | 1.8 M, new agent (n=5) |
| Worker: spec check (fast) | 20.2 M, ctx 183k | 27.9 M, ctx 187k | **12.6 M**, ctx 177k (n=1) | 15.1 M, 90 steps, ctx 154k (n=3; max 116 steps) |
| Implementer: attempt or part (fast) | 49.9 M per attempt, ctx 296k | 87.3 M per attempt, ctx 398k | **23.8 M per part**, ctx 221k (n=4) | **11.1 M per part**, ctx **135k** (n=11; one part ran 131 calls, 25 M) |
| Implementer: round after `CHANGES` | resumed implementer | resumed implementer | **2.6 M**, new agent (n=2) | 9.5 M (n=4; real blockers, one in two parts) |
| Implementer: rebase / conflict task | — | 2.2 M | 2.0 M (n=3) | 2.0 M (n=4) |
| Reviewer: round 1 (strong) | 16.0 M, ctx 196k | 15.4 M, ctx 179k | 15.5 M, ctx 188k (n=2) | 13.8 M, ctx 172k (n=4) |
| Reviewer: round 2+ / delta | 0.8 M | 0.85 M | 0.7 M (fast, new agent) | 4.1 M (n=4, strong) |
| Worker: PR body | 0.6 M (fast) | 0.8 M (light) | 0.4 M (light) | 0.6 M (light, n=4) |
| Worker: docs PR | 1.7 M (fast) | 2.2 M (light) | — | — |

Reading the table:

- **0.2.3 halved the context** an agent carries per step. The implementer
  is still the largest item, but one attempt of the largest PR so far
  (offline client core, seven steps including e2e in two browsers) ran as
  four parts at ctx 177–245k each, instead of one agent growing to 600k.
- **Spec checks** got cheaper once they stopped running mutants and suites
  and read the designer's recorded runs.
- **Follow-ups in new agents** (spec fixes, rounds after `CHANGES`, small
  reviews) cost 0.4–5 M, where a resumed agent re-read ~200k per step.
- **Round-1 reviews did not change** in 0.2.3; 0.2.4 targets them (diff
  first, spec sections only).
- The orchestrator's share grew to about 9 % as the roles got cheaper;
  0.2.4's ten-line hand-backs target it.

### What 0.2.4 showed (what 0.2.6 changes)

- Implementer parts dropped to 135k average context and 11 M per part
  (from 221k and 24 M): read-by-range and ~70-call parts work. One part
  ignored the soft limit (131 calls, 25 M) → 0.2.6 adds a hard stop at
  about 90.
- Designers are now the largest single agents (spec phase up to 150
  calls, 31 M, 360k context) and design is 29 % of subagent cost →
  designer parts, and the spec phase reuses the inventory.
- Spec checks grew back to 15 M (up to 116 calls); the findings that
  mattered were repo facts (an architecture import rule, a generated file
  that depended on the working directory) → a 60-call budget, repo facts
  first.
- Running the mutant list one tool call per mutant filled a whole
  implementer part → one loop script.
- Plan splits committed on feature branches made `docs/plan.md` conflict
  on every rebase (one PR rebased four times) → plan edits go to the base
  branch at once.
- Cost by role in the period: implementer 43 %, designer 29 %, reviewer
  21 %, worker 8 %; orchestrator 8 % on top. Cache reads were 96 % of all
  tokens and cost the same on the strong and the fast tier, so the strong
  tier for the implementer raises its cost by about 40 %, not 2× →
  `Risk: high` PRs get a strong implementer.

### Where the tokens went in 0.2.3 (what 0.2.4 changes)

Breakdown of tool traffic in seven 0.2.3 agents (characters of tool input
and output that stayed in context):

| Source | Implementer parts | Round-1 reviews |
|---|---|---|
| Reading files whole (`cat`, `sed`, Read) | 731k chars in 125 calls (+ Read) | 388k chars |
| Writing code (heredoc / Write input) | 738k chars, mostly new files | — |
| `git diff` / `git show` | 14k | 126k |
| Test, build and lint output | 112k | 77k |
| Bootstrap re-reads per part (lessons, checklist, project, spec) | the spec read 11× in one attempt (184k chars) | — |

Context grew from 30k at the first step to 83–140k within ten steps, and to
245k by step 60. The first agent started with the 0.2.4 reading rules in
its prompt (a continuation part) stayed at an average of 99k after 57
steps, against 177–245k for earlier parts; one sample, still running.
