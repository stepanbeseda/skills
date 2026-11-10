# Agent prompt template

Every agent prompt has the same shape. Rules that hold for the whole run
(the machine lock, private names, the flake list, part limits) live in
`project.md` and the batch file, which the agent reads; the prompt names
paths and the task. Aim for about 1 000 characters plus the "Agent
environment" block. In a measured run prompts were 1.5–3.6k characters each
and made up a quarter of what the orchestrator's context grew by.

## Template

```
<role> for <PR> — <the task in one line>. Budget: ~<soft> calls, hard stop <hard>.
ROOT=<absolute worktree>  branch=<branch>  base=<base sha>
SKILL=<absolute skill folder>
Project: <ROOT>/.mao/project.md, checklist.md, lessons.md   Batch: <absolute batch file | none>
Read: <absolute paths, each with the sections to read: spec §1 §4, spec-B-mutants, spec check, impl-1, review-1, progress file, log>
Write: <absolute report path>. Final message ≤ 10 lines: verdict, path, check line, blockers.
Task:
- <only what is specific to this agent: mode, attempt or part, rulings, what to skip>
Agent environment (from project.md, verbatim):
<the block>
```

## Rules

- **Description.** Name the agent `PR-NN <phase>[ part K]` with a phase from
  this list: `inventory`, `design`, `spec`, `spec check`, `re-check`,
  `spec fix`, `impl part K`, `gate`, `fix round N`, `rebase`, `review r1`,
  `delta review`, `preview`, `PR body`, `docs`, `chore`. The cost helper
  (`scripts/agent-cost.py --by pr,phase`) groups by these words.
- **Role file.** With an installed role agent type (`mao-<role>`) do not
  tell the agent to read `roles/<role>.md`; it is already its system prompt.
  With a generic subagent, or in a tool without subagents, the first line
  is `Read and follow <SKILL>/roles/<role>.md first.`
- **Tier and effort** are spawn parameters (`model`, `effort` in Claude
  Code), chosen from the model table in `SKILL.md`; they are not prompt
  text.
- **Budget.** Implementer part: `~70 calls, hard stop 90`. Designer:
  `inventory by ~50, hard stop 90`. Spec check: `~60`. Gate run, PR body,
  delta review: no budget line.
- **Paths, not retellings.** Name the report and the finding by path and
  id (`review-1 B1`), not by restating it. A ruling of yours goes into the
  file the agent reads (the spec check, the review, the batch file) and the
  prompt names where.
- **Agent environment** is copied verbatim from `project.md` into every
  prompt that runs a command, so a new agent does not rediscover the PATH
  or a stale build output.

## Examples

```
implementer for PR-31 — attempt 1, part 2 of the spec's order of work. Budget: ~70 calls, hard stop 90.
ROOT=/abs/wt/pr31  branch=mao/pr31-planner-ui  base=4e1c0a2
SKILL=/abs/skills/mao
Project: /abs/wt/pr31/.mao/project.md, checklist.md, lessons.md   Batch: /abs/repo/.mao/log/BATCH-<date>.md
Read: PR-31-impl-1-progress.md first; spec §5 and PR-31-spec-B-mutants.md (steps 4–6 name them).
Write: /abs/repo/.mao/log/PR-31-impl-1.md (append part 2). Final message ≤ 10 lines.
Task:
- Steps 4–6. Commit, then report GATE with the tree (references/gates.md); do not run the full check.
Agent environment (from project.md, verbatim):
- prepend <tool dir> to PATH before the package manager
- remove <app>/dist before the check (a cache hit can restore a stale one)
```

```
worker for PR-31 — gate run.
ROOT=/abs/wt/pr31  branch=mao/pr31-planner-ui  tree=9f3c…  (must equal HEAD^{tree})
SKILL=/abs/skills/mao   Project: /abs/wt/pr31/.mao/project.md
Write: append "## Gate" to /abs/repo/.mao/log/PR-31-impl-1.md; log /abs/repo/.mao/log/PR-31-check-1.log
Task:
- Pins first: scripts/pins.sh. Then run exactly: scripts/check.sh --tag pr31, the cluster smoke step first (it has not passed on this kind of change yet).
- Follow references/gates.md §1 (one rerun only for a flake, §6; resume with --from <step>).
Agent environment (from project.md, verbatim):
<the block>
```
