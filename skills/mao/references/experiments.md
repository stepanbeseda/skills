# Opt-in experiments

Changes that measured runs suggest but have not proven. None of them is on
by default. Switch one on for a few named PRs, measure, and keep or drop
it. Write the switch into the batch file (`Experiments: E1 on PR 54, 50, …`)
so every agent prompt of those PRs can say so, and keep a results table in
the run log.

## Measuring

`<SKILL>/scripts/agent-cost.py` reads the Claude Code transcripts of the
session and its subagents and prints tokens, estimated cost, tool calls,
context, wall and idle time per group:

```
python3 <SKILL>/scripts/agent-cost.py ~/.claude/projects/<project-slug>/<session-id>.jsonl --by pr,phase --match '^PR-07 '
python3 <SKILL>/scripts/agent-cost.py <session>.jsonl --by phase --since <ISO time the experiment started>
```

It groups by the agent description, so name agents `PR-NN <phase>`
(`references/prompt-template.md`). Edit the price table at the top of the
script (or pass `--prices`) before you quote dollars; shares and ratios do
not depend on the price level. Per PR, record: cost per phase, tool calls
per agent, round-1 blocking findings, review rounds, and wall clock from
the first agent to the merge. Compare with the same numbers of earlier PRs
of similar size and risk, not with the run average.

## E1. Guard mutants by design

- **Change.** The designer's mutant list gets one mutant per operand of
  each guard condition (each side of an `&&` / `||`, each bound of a
  comparison) and, for every loop over protected items, a "process only
  the first item" mutant. The cap of ~12 stays; rank guard mutants first.
  The implementer may not declare a spec mutant equivalent: it lists it
  under "Decisions outside the spec" with the test that would tell the two
  apart, and you rule (accept, or the test is written) before the review.
- **Switch.** One line in the designer's and the implementer's prompt:
  `Experiment E1: guard mutants per operand; no equivalent mutant without a ruling.`
- **Why.** In a measured run 7 of 7 round-1 `CHANGES` verdicts had the same
  blocking finding: a guard or branch that no test pinned (a reviewer
  mutant survived). Rework was 7 % of the run's cost and each round took
  45–90 minutes of wall clock.
- **Metric.** Share of round-1 `CHANGES`, reviewer mutants that survive,
  implementer parts per PR, design cost.
- **Keep** when round-1 `CHANGES` drop clearly over about six PRs.
  **Stop** when implementer parts grow by more than one per PR.

## E2. Lean agent definitions (Claude Code)

- **Change.** Role front matter may carry Claude-only fields that
  `scripts/build-adapters.py` copies into the generated agent:
  `claude-tools` → `tools` (allow-list), `claude-disallowed-tools` →
  `disallowedTools`, `claude-max-turns` → `maxTurns`. No role sets them;
  the shipped agents keep every tool.
- **Why.** A subagent in a measured run started with about 31k tokens of
  fixed context (tool schemas, including tools a role never uses, and the
  listing of every installed skill), re-read at every step: 13 % of
  subagent cost.
- **Switch.** Copy a generated agent (e.g. `mao-worker.md` of the installed
  plugin) to `~/.claude/agents/mao-worker-lean.md`, rename it
  (`name: mao-worker-lean`) and add one line: either
  `disallowedTools: Agent, Skill` plus the MCP servers no role needs, or an
  allow-list such as
  `tools: Bash, Read, Write, Edit, Grep, Glob, ToolSearch, Monitor, TaskStop`
  plus the tool your version uses for the final hand-back and, for a
  designer, `WebFetch, WebSearch`. A new agent file may show up only in a
  new session. Spawn one PR-body or gate-run worker with the lean type first.
- **Metric.** Context of the agent's first call (the helper's per-agent
  JSON, `--json`), cost per step, any "tool not available" error or a lost
  hand-back.
- **Keep** when the first-call context drops and nothing a role needs is
  missing; then try the other roles one at a time. **Stop** at the first
  missing tool or lost hand-back.
- **Backstop.** `maxTurns` (e.g. 120 for implementer and designer parts)
  ends an agent that ignores its hard stop. Use it only with progress
  files kept current after every step; an agent cut off by it writes no
  report.

## E3. Fast tier for mechanical parts of `Risk: high` PRs

- **Change.** The designer marks each step of the order of work
  `tier: strong | fast`. Guard, concurrency, migration, crypto and money
  code is `strong`; UI over existing APIs, fixtures, docs, e2e scripts and
  the mutant script are `fast`. Parts are separate agents already; you
  pick the tier per part.
- **Switch.** Designer prompt: `Experiment E3: mark each order-of-work step tier: strong | fast.`
  Then spawn each part with the tier of its steps.
- **Why.** When nearly every PR of a plan is `Risk: high`, every
  implementer runs on the strong tier; the strong tier costs more for every
  token class (about 1.7× at the list prices of the measured run).
- **Metric.** Round-1 blocking findings per PR. In the measured run they
  were about 1.0 per PR with strong implementers and 2.4 with fast ones
  (small samples). Implementer cost per PR.
- **Stop** when round-1 blocking findings exceed 1.5 per PR over four PRs.

## E4. Earlier orchestrator compaction

- **Change.** The orchestrator compacts at about 200k tokens of context
  instead of near the window limit. In Claude Code: the `autoCompactWindow`
  setting (or `/autocompact`), or `/compact` by hand after each merge. The
  journal and the batch file hold the state.
- **Why.** In a measured run the orchestrator carried about 200k per step
  on average, compacted at about 365k, and was 8–10 % of the run's cost.
- **Metric.** Orchestrator cost per merged PR, average context per step,
  rulings repeated or lost after a compaction, re-reads of the batch file.
- **Stop** at the first ruling or open item lost after a compaction.

## E5. Fast-tier inventory

- **Change.** With the designer split at the inventory, a fast-tier
  designer writes `<PR>-inventory.md` (files with line ranges, quoted
  interfaces, Delivered blocks, migration numbers, shared files) and the
  strong designer writes the spec from it.
- **Metric.** Spec-check blocking findings and reviewer `[spec error]`
  findings against earlier PRs; design cost.
- **Stop** when a missed constraint reaches the review.
