# Changelog — mao

Versions are the `sbskills` plugin versions that shipped a change to this
skill. Measured effects come from [README.md](README.md#benchmarks).

## 0.2.5 — 2026-10-30

- Documentation only: this changelog and a README with the benchmarks of
  0.2.1–0.2.3. No change to the procedure or the roles.

## 0.2.4 — 2026-10-30

Context budget, second pass. The 0.2.3 runs showed where the remaining
tokens went: implementers reading whole files with `cat` (the largest
single item in their contexts), every continuation part re-reading the
lessons, the checklist and the spec, contexts still reaching 320–360k at
the end of a 100-call part, reviewers reading whole files instead of the
diff, long agent hand-backs piling up in the orchestrator, and checks cut
off by an agent's own `timeout` and run again.

- Every role reads code by range (`grep -n`, then `sed -n a,bp` or a ranged
  read); a whole file only when it is short, and no file twice in one
  context.
- Reviewers start from `git diff --stat` and read the diff file by file;
  from the spec only §1, the decisions and the sections they judge. Round
  2+ and delta reviews do not re-read the lessons or the checklist.
- Implementer parts end after about 70 tool calls (was 100). The designer's
  order of work names the spec sections each step needs; the orchestrator
  passes them to each continuation part, which reads no lessons and no
  checklist. The part that finishes the attempt reads the checklist for
  the self-review.
- Agents end with a final message of at most ten lines; the report file
  holds the rest.
- The check is never wrapped in `timeout`; long runs go to the background
  and the agent waits for the notification.

Measured: not yet (no finished agent ran on 0.2.4 definitions).

## 0.2.3 — 2026-10-30

Context budget. In the 0.2.1/0.2.2 runs 97 % of all tokens were cache
reads, and the quarter of agents with more than 150 steps used more than
half of everything.

- New section "Context budget" in SKILL.md: long output goes to a log file
  and agents read only the summary and the failures; implementers work in
  parts (`Verdict: CONTINUE` with `<PR>-impl-N-progress.md`, a new agent
  continues); design at most one PR ahead of the merge front; at most three
  heavy agents at once.
- Resume an agent only while its context is small (about 150k); otherwise
  start a new agent of the same role with file paths. The model/effort
  table says which follow-ups (spec fix, round after `CHANGES`, conflict
  resolution, re-check) start a new agent.
- Slim spec check: claims backed by a designer run (`<PR>-proto/*.out`) are
  checked against the recorded output; no mutants, full suites or the whole
  check; slow environments only when no recorded run covers the claim.
- Designers save prototype output as `.out` files and list at most ~20
  mutations; reviewers run 3–5 mutants of their own choice.
- Batch scheduling follows the same rules (designers one PR ahead, heavy
  agents capped).

Measured against 0.2.2: average context per step 294k → 164k over all
agents; no agent above 150 steps (was 8 of 23); spec check −55 %;
implementer part context −44 %; spec fixes, rounds after `CHANGES` and
small reviews in new agents at 0.4–5 M tokens instead of resumed agents
carrying ~200k. Round-1 reviews unchanged.

## 0.2.2 — 2026-10-29

Model and effort per task.

- Per-task tier and effort table, with a light tier (`haiku`) for PR
  bodies, docs PRs, CI output and plan edits.
- A delta review reuses the implementer's check when the quoted tree hash
  equals `HEAD^{tree}`; small delta reviews (≤ ~100 lines, no new design)
  go to a fast, new agent.
- Follow-up rounds after approval only for security findings or untested
  product behaviour.
- Spec body capped at 600 lines (exact texts and tables go to appendices);
  a redesign after the spec check gets a targeted re-check of the changed
  parts, never a second full spec check.

Measured: per-task costs close to 0.2.1; PR bodies and docs moved to the
light tier. Implementer attempts grew (87 M vs 50 M tokens) because the PRs
of that period were larger and two attempts resumed after a usage-limit
cut-off with their whole context — the problem 0.2.3 addresses.

## 0.2.1 — 2026-10-11

- A run that disproves a spec claim a guard, check or acceptance criterion
  depends on is a blocking spec-check finding, even when the tree passes.

## 0.2.0 — 2026-10-09

- First version in the cross-vendor skills marketplace: orchestrator plus
  designer, implementer, reviewer and worker roles; project layer in
  `.mao/` (plan, check, checklist, lessons); batches as a merge train;
  adapters for Claude Code, Codex and OpenCode.
