# Gates — who runs the check, and when a result carries over

A **gate** is a run that must be green before a PR merges: the project's
full check, every CI job, and any extra gate `project.md` lists (a deploy
check, a cluster smoke, a run that only one host can do). This file says
who runs each gate, on which tree, and when an earlier result still holds.
`SKILL.md` step 5–7 and `batch.md` B3 point here.

## 1. Gate runner: a small agent waits, not the implementer

A full check took 19–52 minutes in measured runs. An implementer that
waits for it keeps a 150–250k context idle; after five minutes its cache
expires and the next step writes the whole context again. In one measured
run these rewrites cost 8.7 % of all tokens, three quarters of it in
implementers. So the implementer hands the full check to a gate runner.

**Implementer.** Finishes the code, the targeted tests of the changed
areas, the mutant list and the self-review. Commits everything
(`git status --porcelain` empty), records `git rev-parse HEAD^{tree}`,
writes its report with `Check: pending tree=<hash>` and reports
`Verdict: GATE`. When the full check is short (under about five minutes,
or `project.md` says so) or the project has no single check, the
implementer runs it itself in the foreground as before and reports `DONE`.

**Orchestrator.** On `GATE`, starts a worker (fast tier, medium effort;
in Claude Code `sonnet`) with the gate-run prompt below. It is a new, small
agent: a wait in it is cheap.

**Gate run (worker).**

1. `git -C <worktree> status --porcelain` is empty and
   `git -C <worktree> rev-parse HEAD^{tree}` equals the tree from the
   prompt. Otherwise report `Verdict: GATE MISMATCH` and run nothing.
2. Do what "Agent environment" in `project.md` says before a check (for
   example remove build outputs a build cache could restore stale).
3. Run **exactly** the command from the prompt (the check from
   `project.md` with the PR's tag) with output to
   `<ROOT>/.mao/log/<PR>-check-<n>.log`. Never wrap it in `timeout`. Wait
   in the foreground with the tool's longest wait, or in the background for
   the notification.
4. Green: the summary line must name the same tree. Append to the
   implementer's report:
   ```
   ## Gate
   Command: <exact command>   Exit: 0   Log: <path>
   <the summary line verbatim, e.g. CHECK OK tree=<hash> unit=… e2e=…>
   ```
5. Red: when every failing test is on the project's known-flake list
   (`project.md`), run the same command once more into
   `<PR>-check-<n>b.log` and record both runs. Otherwise, or when the
   rerun is red too, append `## Gate` with `CHECK FAILED`, the exit code,
   the failing step and tests, at most 40 lines from the log, and the log
   paths. Fix nothing, diagnose nothing, change no file.
6. Final message: `Verdict: CHECK OK | CHECK FAILED | GATE MISMATCH`, the
   summary line, the log path.

**After the gate.** `CHECK OK` → the attempt is done; go on to the preview
and the review. `CHECK FAILED` → a new implementer part of the same attempt
(not a new attempt) gets the report and the log path; it fixes, commits and
reports `GATE` again. A failure that looks environmental (a runner, a
cluster, the disk) is still `CHECK FAILED`; you decide whether to rerun it
or open a chore. Do not diagnose infrastructure inside a PR's fix round:
in a measured run one such fix round took five hours for a flake that was
not the PR's.

The evidence is the same as before: the same command, the same tree, the
same summary line. The reviewer still compares `tree=` with
`HEAD^{tree}` of the commit it reviews.

## 2. CI is the independent run

When the project's CI runs the same check on the PR (`project.md`, "CI
checks"):

- the round-1 reviewer does **not** run the full check. It verifies that
  the report's `tree=` equals `HEAD^{tree}`, runs the tests of the changed
  areas and its own mutants. CI on a clean runner is the independent run,
  and it catches environment drift that a second local run cannot;
- the merge gate is green CI on the PR head.

When the project has no CI, or CI does not run the check (billing, an
outage, a job that is off), the round-1 reviewer runs the full check
itself as the independent run, and the final tree gets a local gate run.

## 3. The final tree

Before merge, the final tree has:

1. **one fresh run of the full check** on exactly that tree: CI's run when
   CI runs the check, otherwise a gate run (or a recorded tree-identical
   comparison, below);
2. **every CI job green**;
3. **every extra gate** from `project.md`: a fresh run, or a carried-over
   result (below).

**Carry-over.** A gate result from an earlier commit holds for the final
tree when

- the rebase was conflict-free (no delta review needed for it), and
- `git diff <checked-commit> HEAD -- <the gate's input paths>` is empty
  (the input paths stand next to each gate in `project.md`; without a list
  the whole tree is the input).

A tree-identical rebase (`git diff <checked-commit> HEAD` empty) carries
over every gate. A gate that only one machine or host can run (a hardware
smoke, a local cluster on another OS) is the usual case: it carries over
whenever its inputs are unchanged, while the full check and CI run fresh.
Record each carry-over in the journal: gate, checked commit, final commit,
the empty diff.

## 4. Rebases in a train

- **No gate after an intermediate rebase.** "Rebase early" (`batch.md` B3)
  surfaces conflicts; it does not need a check. Only the rebase right
  before the merge gets the gates of §3.
- **Stalled branches leave the train.** A PR whose fix round takes longer
  than one gate cycle leaves the merge order and is not rebased again until
  its fix is approved. In a measured run one PR in a long fix round was
  rebased four times and left nine check logs.
- A conflict resolution is a change after approval: delta review (6b),
  then the gates of §3.
