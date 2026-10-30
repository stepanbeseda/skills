# Batch — several plan chapters as a merge train

`/mao PR-06 PR-09 PR-11 … [profile] [--merge]`. Every PR runs the normal
per-PR procedure of `SKILL.md` (steps 1–7) in its own worktree; this file
adds what is shared: preflight for the whole batch (B0–B1), scheduling (B2),
the merge train (B3), and the close (B4–B5). You remain the only
orchestrator; agents of different PRs never talk to each other — cross-PR
information goes through the batch file.

## B0. Batch preflight (you, before any agent)

1. `git fetch`; read the plan table and every chapter's "Depends on"; drop
   duplicates; a PR whose dependency is neither done nor in the batch is an
   error — ask.
2. **Merge order.** Dependencies first; then the order the plan suggests;
   then the PR with the fewest shared files first. Write it down.
3. **Batch questions** (one round of questions, before agents start):
   - merge each PR when green + approved, in the merge order? (default yes
     when `--merge` was given; without `--merge` a batch only opens PRs,
     and later PRs will conflict — say so);
   - every step a chapter needs that is stop-and-ask (a spike against a real
     account, a secret, a deploy): allow / offline only / drop the PR;
   - deploys: one deploy bundle at the end (default) or stop after each
     merge.
4. **Worktrees.** One per PR from `origin/<base>`, branch per `project.md`,
   journal `<PR>.md` each. Never build or edit in a checkout that runs a
   live service.
5. **Batch file** `<ROOT>/.mao/log/BATCH-<date>.md` (`<ROOT>` = the
   main checkout's log dir, so every worktree's agents find it):
   - table PR → worktree → branch;
   - merge order;
   - **pre-assigned schema/migration numbers in merge order** for PRs that
     will add one (the designer confirms in its inventory whether its PR
     needs one; the number on the branch is the next after `<base>`, and
     each later PR renumbers on rebase — keep the migration a self-contained
     block so that is mechanical);
   - resource rules copied from `project.md` "Parallel runs" with the
     PR-specific values (image tags, e2e project names);
   - owner decisions from step 3;
   - a "Cross-PR notes" list you append to as designs come in (e.g. "PR 13 adds `matching.suggest()`; PR 09 feeds its data into it
     after its rebase").
   Every agent prompt in the batch includes the batch file path.

## B1. Dependent PRs: the after-rebase addendum

When PR B merges after PR A and must build on code A introduces (A's spec is
the contract, its code does not exist on B's branch yet), B's designer
writes a clearly separated spec section **"After the rebase onto PR A"**.
The implementer leaves it out of round 1 and applies it when B is rebased
onto a base that contains A; that change then gets a delta review (6b). The
reviewer of round 1 is told the section is deliberately not implemented.

## B2. Scheduling

- Start designers in parallel for the PRs that build only on merged work;
  a PR that builds on another PR of the batch is designed when that PR is
  approved ("Context budget" in SKILL.md: design one PR ahead).
- **Cap** concurrent implementers / heavy checks at the "Parallel runs"
  limit in `project.md` (default 2), and all heavy agents together at three
  (SKILL.md, "Context budget"). When a slot frees up, start the next
  PR **in merge order** — the PR that merges first must never wait for a
  build lock behind one that merges last.
- PR bodies and other light work are not capped beyond the machine lock.
- Every agent follows the machine lock and PR-private names from
  `project.md`; the check script (when the project has one) applies them.

## B3. Merge train

Repeat for the next PR in merge order, once it is APPROVED:

1. `git fetch`. Rebase onto `origin/<base>`:
   - base unchanged since the branch was cut → nothing to do;
   - an earlier PR of the batch was squash-merged and this branch was
     stacked on its tip → `git rebase --onto origin/<base> <that-tip>`;
   - otherwise `git rebase origin/<base>`.
   Conflicts → this PR's implementer as an assigned task (resumed while its
   context is small, otherwise a new one with the conflict list): resolve
   keeping all sides, renumber its migration to the pre-assigned number,
   apply the after-rebase addendum if any, run the full check. Then a delta
   review (6b). The implementer may run `git rebase --continue/--skip` in
   its worktree only for this assigned task; it never pushes.
2. Clean rebase → compare trees: `git diff <checked-commit> HEAD` empty →
   the check holds; otherwise the full check runs on the final tree.
3. PR body (worker, after the final review), push, `gh pr create`, CI,
   merge, delete the remote branch, remove the worktree and local branch,
   journal line with the merge sha.
4. **Rebase early:** right after each merge, rebase every remaining
   APPROVED or in-review branch mechanically (no check yet) to surface
   conflicts now rather than when its turn comes. Hand non-trivial
   conflicts to that PR's implementer while the train continues.
5. Optional stacking: when the next PR is blocked only by the current one's
   review, you may rebase it onto the current PR's tip and let it run its
   rebase round in parallel; after the merge use `--onto` as in 1.

## B4. Docs PR

After the last merge: one worktree from `origin/<base>`, a worker writes
the "Delivered" blocks (merge sha, final test counts, schema numbers after
renumbering, criteria that still need the test host), the table statuses,
section-5 open items for the follow-ups, and the batch's lessons into
`lessons.md` / `checklist.md`. You commit, open the PR; merge it with the
same rule as the batch (`--merge` → merge).

## B5. Deploy bundle and close

When any PR of the batch needs a deploy, the worker writes
`<ROOT>/.mao/log/DEPLOY-<date>.md` from the PR bodies and specs:

1. backup of every volume a migration or secret change touches, in the
   **old** way (new backup commands exist only in the new images);
2. `git pull` in the live checkout; secrets to create before any `up`, and
   what must not run between pull and deploy;
3. `.env` additions (names only, no values);
4. compare running image IDs with the tags (no surprise rebuilds);
5. the deploy command with every service that must restart together;
6. schema versions before → after, and the downgrade path;
7. per PR, the test-host criteria and the exact command or observation
   that verifies each.

You show the bundle to the user (deploys are stop-and-ask) and offer to run
the verification part after they deploy. Then the close: no agent, loop,
container, image tag or worktree of the batch left behind; one final report
to the user with a table PR → URL → merge sha → review rounds → note, the
open items, and the deploy bundle path.
