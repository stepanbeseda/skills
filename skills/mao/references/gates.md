# Gates — who runs the check, and when a result carries over

A **gate** is a run that must be green before a PR merges: the project's
full check, every CI job, and any extra gate `project.md` lists (a deploy
check, a cluster smoke, a run that only one host can do). This file says
who runs each gate, on which tree, and when an earlier result still holds.
`SKILL.md` step 5–7 and `batch.md` B3 point here. Measured on a 0.2.7
trial of 14 PRs: a gate took about 85 minutes, a PR needed 3.3 gates on
average, and only 4 of 14 PRs were green at the first gate. The failures
were missed repo-wide pins (§5), flakes outside the diff (step 5 below) and
order dependences in new tests (`roles/implementer.md`, step 6).

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
3. Run the **pins script** from `project.md` first (§5; skip when "Pins"
   is none), into
   `<PR>-pins-<n>.log`. Red → `CHECK FAILED` at once, with the failing pins;
   do not start the full check.
4. Run **exactly** the command from the prompt (the check from
   `project.md` with the PR's tag) with output to
   `<ROOT>/.mao/log/<PR>-check-<n>.log`. When the prompt names a step to
   run first (a step that has never passed on this kind of change, e.g. a
   cluster smoke or a lockfile install), run that step first, then the
   rest (`project.md`, "Check resume" says how). Never wrap it
   in `timeout`. Wait in the foreground with the tool's longest wait, or in
   the background for the notification.
5. Green: the summary line must name the same tree. Append to the
   implementer's report:
   ```
   ## Gate
   Command: <exact command>   Exit: 0   Log: <path>
   <the summary line verbatim, e.g. CHECK OK tree=<hash> unit=… e2e=…>
   ```
6. Red: rerun **once** when every failure is a **flake** (§6): on the
   project's known-flake list, or a timeout, network or environment error
   in a test the diff does not touch. Rerun from the failed step on the same
   tree when the check can resume (`project.md`, "Check resume"), else the
   whole command, into `<PR>-check-<n>b.log`. Record both runs and the test
   ids under "Flaky" in the report. Otherwise, or when the rerun is red
   too, append `## Gate` with `CHECK FAILED`, the exit code, the failing
   step and tests (say when a test failed in both runs), at most 40 lines
   from the log, and the log paths. Fix nothing, diagnose nothing, change
   no file.
7. Final message: `Verdict: CHECK OK | CHECK FAILED | GATE MISMATCH`, the
   summary line, the log path.

**After the gate.** `CHECK OK` → the attempt is done; go on to the
preview, and to the review where it did not start beside the gate (§7). `CHECK FAILED` → a new implementer part of the same attempt
(not a new attempt) gets the report and the log path; it fixes, commits and
reports `GATE` again. A failure that looks environmental (a runner, a
cluster, the disk) is still `CHECK FAILED`; you decide whether to rerun it
or open a chore. Do not diagnose infrastructure inside a PR's fix round:
in a measured run one such fix round took five hours for a flake that was
not the PR's. A failure that repeats is not a flake (§6). A gate that
fails on a repo-wide pin the pins script does not run gets that pin added
to the script in the same fix (§5).

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
outage, a job that is off), the gate run is the independent run: a worker
that wrote none of the code runs exactly the project's check on the
reviewed tree. The reviewer does not repeat it; it runs no test while a
gate runs (§7). The final tree gets a local gate run. In the 0.2.7 trial
14 PRs merged this way with CI off, and no reviewer re-ran the check.

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
- **The final gate runs once, at the head of the train.** Rebase onto the
  *current* `origin/<base>` first; no other PR of the train merges while
  that gate runs. A PR built on an unmerged PR of the batch is rebuilt on
  the new base after that PR squash-merges (`git rebase --onto`, or a
  cherry-pick of its own commits), never by merging the base into it, and
  then gated once. Before that it gets no full gate: in the trial a PR
  implemented on top of the previous PR's branch was gated once, after the
  rebuild.
- **Stalled branches leave the train.** A PR whose fix round takes longer
  than one gate cycle leaves the merge order and is not rebased again until
  its fix is approved. In a measured run one PR in a long fix round was
  rebased four times and left nine check logs.
- A conflict resolution is a change after approval: delta review (6b),
  then the gates of §3.

## 5. The pins script

A **pin** is a test that fails when a repo-wide list or count changes: an
exports list, a migration count, a registry or palette size, the order of
blocks in a README that a test parses, a grants list, an alert rule count,
a schema snapshot. A PR that adds one item breaks a pin far from its
diff. In the trial about 8 of the failed gates were such pins; each cost a
fix part and a full gate (about 85 minutes) for a one-line change. A hint
list in prose did not help: implementers read it and still missed pins.

- The project keeps an executable **pins script** (e.g. `scripts/pins.sh`,
  `project.md` "Pins"), about five minutes at most. It runs every pin test
  of the repo, and lint and type check of the changed files (tests
  included). It needs no cluster and no browser.
- The implementer hands over only with it green (`roles/implementer.md`,
  step 6). The gate run starts with it (§1, step 3), so a missed pin costs
  five minutes, not a gate.
- When a gate still catches a pin the script does not run, the fix adds
  that test (or its file pattern) to the script in the same commit, and the
  journal says so. The script grows from what gates catch.
- A project without such tests leaves "Pins" as none.

## 6. Flakes

About 10 of the trial's failed gates came from flakes or races in code the
PR did not touch; each cost a full rerun of about 85 minutes, and two of
them were real bugs that a blind retry would have hidden.

- **Flake** = a failure in a test the diff does not touch
  (`git diff --name-only origin/<base>...HEAD` names neither the test nor a
  file it imports) whose error is a timeout, a network or download error,
  a socket reset or a lock wait, or a test on the known-flake list. An
  assertion failure on a value is not a flake.
- One rerun on the **same tree**, from the failed step when the check can
  resume (e.g. `check --from <step>`). Earlier steps' green results come
  from the first log; the summary line of the resumed run says
  `resumed-from=<step>` and names the same tree. Without resume, one full
  rerun.
- **A failure that repeats is a bug.** The same test failing in two runs,
  or the same spot failing again in a later gate, is diagnosed before any
  further gate: reproduce it N times on the branch and on `origin/<base>`.
  In the trial one "flake" that recurred was a client race from an earlier
  PR (4 of 20 runs on the base branch), and one perf assertion with less
  than 25 % headroom failed on every loaded run until its query was fixed.
- Every flake goes into the batch file's flake backlog (test id, error,
  how often), and becomes a chore when it recurs.

## 7. What may run beside a gate

- The next PR's design and implementation may run while a gate runs.
- **Static review beside the gate.** Round 1 starts when the implementer
  reports `GATE`. While the gate runs, the reviewer reads and reasons but
  runs no test; its own mutants run after the gate has ended, or go into
  the review as probes (patch and killing test) for the fix round or a
  worker to run (`roles/reviewer.md`).
- **Fix round in a second worktree.** On `CHANGES` while the gate runs,
  add a worktree at the reviewed commit on a new branch (e.g.
  `<branch>-fix`) and start the fix there; the gate keeps running for
  signal. When the fix is committed, stop the superseded gate (its green
  steps are signal, not evidence), fast-forward the PR branch to the fix
  (`git merge --ff-only <branch>-fix`), remove the second worktree and
  start the next gate and the delta review together. One tree per
  worktree: a fix in the gate's worktree would mix trees under a running
  check.
- **Not beside a perf step.** While a gate runs a step with timing or
  performance assertions (`project.md`, "Perf steps"), no other agent runs
  a test suite, a build or mutants on the same machine. In the trial an
  implementer's suite runs beside such a step turned a passing perf
  assertion red (974 ms against a 700 ms limit) and cost a gate.
- When several heavy jobs wait for the machine lock, the gate of the PR at
  the head of the merge train goes first (`batch.md` B2).
