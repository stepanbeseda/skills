# Context budget

Nearly all of a run's tokens are context that agents re-read at every step:
in measured runs 96–97 % of the tokens were cache reads, and the quarter of
agents with more than 150 steps used more than half of everything. Every
line an agent reads stays in its context until it ends. These rules keep
that down. `SKILL.md` lists them in short; this file has the detail.

## Output and reading

- **Long output goes to a file.** Every agent sends the check, test suites,
  mutation runs, builds and cluster or browser logs to a log file and reads
  only the summary line and the failures (`… > <log> 2>&1; tail -n 40
  <log>`).
- **Every run file starts with the PR id**: `<PR>-check-2.log`,
  `<PR>-mutants-1.log`, `<PR>-proto/`, `<PR>-impl-1-progress.md`. Parallel
  PRs never share a file name; a bare `check.log` or `progress.md` gets
  overwritten by the next PR.
- **Read by range.** Agents find code with `grep -n` and read it with
  `sed -n a,bp` (or a ranged read), not whole files, and do not read a file
  twice in one context. Reviewers read the diff file by file, starting
  from `git diff --stat`. Whole files were the largest single item in
  measured implementer contexts (29–41 % of what roles carried).
- **The role file is already loaded.** With an installed role agent type
  (`mao-<role>`), the role file is the agent's system prompt. Do not tell
  it to read `roles/<role>.md` again: in one measured run every prompt did,
  and each agent carried the role text twice. A generic subagent, or a
  tool without subagents, still reads the role file first.

## Parts and hard stops

- **Implementers work in parts.** After about 70 tool calls, at the next
  step of the spec's order of work with green tests, the implementer writes
  `<PR>-impl-N-progress.md` and reports `Verdict: CONTINUE`. A new
  implementer continues the same attempt with that file and the spec
  sections (or spec files) its next steps name. A part is not an attempt.
  A continuation reads no lessons and no checklist; the last part reads
  the checklist for its self-review.
- **About 90 tool calls is the hard stop**, even in the middle of a step:
  commit the work as `wip:` and say in the progress file what is red.
  Every tool call counts, a wait and a re-read too.
- **Designers split at the inventory.** The first designer call writes
  `<PR>-inventory.md` early (by about call 50, before prototype runs) with
  line-ranged excerpts of the code it will design against and the
  decisions so far, then returns `QUESTIONS` or `INVENTORY`. A **new**
  designer writes the spec from the inventory (and the answers). Its hard
  stop is also about 90 calls: `<PR>-design-progress.md` and
  `Verdict: CONTINUE`. In a measured run 10 of 11 designers ran 92–170
  calls and wrote the inventory only at call 80–110, at 235–285k context;
  the spec was then written in the largest context of the PR.
- **Enforcing the stops.** Agents overran the soft limits when the limit
  was only in the role file. So:
  - the prompt's first line states the budget (`Budget: ~70 calls, hard
    stop 90`);
  - the agent keeps its progress file current after every finished step,
    so a stop at any point loses at most one step;
  - long waits are not the implementer's: the full check goes to a gate
    runner (`references/gates.md`), which took 20–50 minutes and dozens of
    calls out of measured parts;
  - you note each agent's tool-call count (Claude Code reports it when the
    agent finishes) in the journal. A part above about 100 calls is an
    overrun: say so in the next prompt of that role. A hard backstop in the
    agent definition (`maxTurns`) is an opt-in experiment
    (`references/experiments.md`).

## Specs

- **Sectioned spec.** The spec body stays in `<PR>-spec.md`; appendices
  (exact texts, long test tables, SQL, the mutant list) go into their own
  files `<PR>-spec-<letter>-<name>.md`. Each step of the order of work
  names the sections and files it needs; a continuation part reads only
  those. In a measured run implementer parts re-read the whole 580–860-line
  spec 29 times. The part that does the self-review still reads §1 in full.
- **Spec checks have a budget** of about 60 tool calls, spent in this
  order: repo facts by `grep`/`ls` (paths, identifiers, import and
  architecture rules, migration numbers, ports, env variables), then
  executable claims without a recorded run, guards and acceptance
  criteria first. Claims left when the budget runs out are listed as
  "Not checked" for the implementer and the reviewer.
- **Mutants run from one script.** The implementer writes each mutant as
  a small patch (or `sed` line) and runs the list with one loop script
  that applies a mutant, runs its killing test, records red/green to one
  log and restores the file. One tool call per mutant was a whole
  implementer part in measured runs.

## Scheduling

- **Resume only small agents.** A resumed agent keeps its whole context.
  Resume only while it is about 150k tokens or less, or when the next round
  really needs what it learned; otherwise start a new agent of the same
  role with file paths. A one-line fix in an agent that carries 400k tokens
  costs more than a fresh agent that reads 40k.
- **Design one PR ahead.** Start a designer when the PR's dependencies are
  merged or approved, not earlier. A spec written two or three merges ahead
  gets rewritten and re-checked when those merges land.
- **At most three heavy agents at once** (implementers, reviewers and spec
  checks that run tests, designers that run prototypes, gate runs), unless
  "Parallel runs" in `project.md` sets another number. More only wait for
  the machine lock and make timing-sensitive tests flaky.
- **Short prompts.** One prompt template for every agent
  (`references/prompt-template.md`); run-wide rules live in the batch file
  and `project.md`, not in each prompt.
