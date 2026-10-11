# General lessons from MAO runs

Apply in every project. They come from real MAO runs (single PRs and a 7-PR
batch, backend services and web apps); project-specific lessons live in
`<ROOT>/.mao/lessons.md`. All agents read this file.

## Project setup (step 0)

- Find out which language commits are written in (repo rules, `git log`)
  and what squash merge uses as the commit title:
  `gh api repos/<o>/<r> --jq '.squash_merge_commit_title, .squash_merge_commit_message'`.

  The skill's defaults (PR title `PR NN — <name>`, English Conventional
  Commits for its fixed commits) can clash with the repo's convention. With
  `COMMIT_OR_PR_TITLE`, the PR title becomes the commit on `<base>` for PRs
  with more than one commit.

  `project.md` then sets the PR title (e.g. a Conventional Commit with the
  suffix `(PR NN)`) and the wording of the fixed commits.

## Worktree and git

- Never `git stash` (the stash stack is shared by all worktrees and
  sessions), never switch branches, never `--force`. Test-first
  verification = a WIP commit.
- All paths absolute inside the given `<ROOT>` — an agent once wrote a file
  into a different checkout. Confirm every created file with `wc -l`;
  without that it does not exist.
- Git (branch, commits outside implementation, push, PR) is done by the
  orchestrator.
- `/mao PR-NN` before the setup PR (step 0) is merged:
  - the branch is created from the setup PR's branch and the PR's base is
    `<base>`;
  - the scope for agents is `git diff <setup-commit>...HEAD`.

  After the setup PR is squash-merged, the PR reports an add/add conflict
  in `.mao/*`:
  1. Verify that `.mao/` on `<base>` is identical to the setup
     commit, i.e. `git diff <setup-commit> origin/<base> -- .mao` is
     empty.
  2. `git merge origin/<base>` and resolve the conflicts with the branch's
     versions.

  No rebase and no `--force`.
- The implementer may rewrite history only for their own commits that are
  neither on the remote nor in review. Example: gitleaks flags a sample in
  an earlier commit → `git reset --mixed` and commit again. Pushed or
  reviewed history is fixed only by a new commit; if the problem does not
  go away that way, it is a stop-and-ask.

## Parallel runs and batches

(from a batch of 7 PRs on a 2-CPU host)
- Shared Docker resources collide silently: a fixed test tag
  (`<svc>-test`) or a fixed e2e compose project lets one PR test another
  PR's image. Every run uses PR-private tags and project names; the shared
  default belongs to nobody. Serialize builds with one machine lock.
- Cap concurrent heavy checks and schedule by merge order — otherwise the
  PR that merges first waits behind the lock for the one that merges last.
- Migrations of parallel PRs all claim "next number": pre-assign numbers
  in merge order and keep each migration self-contained so the renumbering
  on rebase is mechanical.
- After the base branch was squash-merged, `git rebase origin/<base>`
  replays the base's own commits and conflicts with itself; use
  `git rebase --onto origin/<base> <old-base-tip>`.
- A rebase is tree-identical when `git diff <checked-commit> HEAD` is empty;
  then the earlier check holds. Any other change after approval (conflict
  resolution, a "small" fix, a removed guard) gets a delta review — one
  conflict resolution committed conflict markers that only a later commit
  removed.
- Cross-PR contracts (PR B uses code PR A adds) go into B's spec as a
  separate "after the rebase onto A" section, applied and delta-reviewed
  when B is rebased.

## Agent environment

- Variables agents need in commands (e.g. the path of a decryption key) belong
  in the shell's always-read file (for zsh `~/.zshenv`): it is read including the agents' non-interactive
  shells. An explicit key path in a command gets rejected by the permission
  classifier — do not work around it, ask the user.
- **A firewall that allows ssh from a single source IP only.** The
  machine's public IP can change in the middle of live steps (another
  network, VPN): ping goes through, port 22 does not, and the steps stall.
  Before live steps and after every wait for the user, check with a boolean
  that the current public IP is in the host's allowlist, and do not print
  the IP. ssh error output contains the host address.
- **Agents leave background loops.** `until …; do sleep 10; done` waiting
  for a file that never comes ran for 14 hours after the agents reported.
  No background polling; wait in the foreground with a timeout and stop
  your own jobs before reporting.

## Spec error shapes (designer)

- **A cited identifier does not exist.** The spec check greps every named
  function, method, fixture and constant, not just paths and files — and
  every check command (e.g. that `npm run …` really is in `package.json`).
- **An overlooked closed enumeration.** You add an element → grep the
  enumeration in tests; the spec names the test that must change. In a test
  parametrized with `for … in (…)` the new element is silently not measured
  — add it to every place the enumeration appears.
- **A pattern taken from the checklist without verifying its assumption.**
  For every adopted pattern, write under which assumption it holds and
  verify it on your case.
- **A state or proof described as an enumeration of outcomes instead of a
  rule over the cause.** Write from what the code actually sees ("set as
  soon as X is called"); an enumeration is only an illustration.
- **State based on what the run did, not on the state of the data.** A
  preview or a cancelled run must not overwrite the state of an operation in
  progress. Write the transition condition, not the result.
- **Missing terminal value "the evidence existed and stopped being valid"**
  for decisions that rest on external evidence.
  **Repeated with an action queue**. A pending move (across runs, after a transient
  error) re-verified only the configuration at execution time, not the
  target message. The user had deleted it in the meantime and the next run
  would have moved it out of the trash. A queued action re-verifies on
  execution **every** assumption it was created on, including the state of
  the target object (DB and a fresh query). The enumeration of `skipped`
  outcomes has the value "assumption no longer holds".
- **A literal expression instead of a rule.** For every field in the
  expression, look where it comes from and what it really contains.
- **"One transaction" across a DB and the file system** (or across UI and
  storage) does not exist; decide the order and what must succeed first.
- **A manual user step involving secrets, without a procedure.** When an
  acceptance criterion depends on a manual step (test host profile, keys,
  secrets), the spec contains the full procedure with commands:
  - where the keys live outside the repo;
  - how to encrypt the secret without a plaintext copy in the checkout;
  - a safety net in `.gitignore`.

  Otherwise review sends the PR back only after implementation.
- **A command block that cannot be pasted into a terminal verbatim.** zsh
  (the macOS default shell) has `interactivecomments` off. A `# comment`
  after a command, or a whole-line `#` in a ```sh block, is therefore passed
  to the command as arguments: `sops exec-env` then reports a misleading
  "missing file to decrypt" and `grep` searches for a file called `#`.
  Command blocks in docs and specs have no comments; the expected output
  goes into the text below the block. Placeholder text that looks like a
  value (`<now, e.g. 2026-…>`) fails the same way: the user copies it
  verbatim. An example in a block is a valid value; the explanation is in
  the text.
- The spec wants to edit a file that has a different purpose — first read
  what the file is for. In a non-empty repo, follow existing conventions
  instead of creating a parallel structure.
- **Literal text that contradicts a check in the same spec.** The spec
  prescribes a text and at the same time a negative grep, scan or linter the
  text cannot pass (the grep finds the prescribed sentence, the line is
  longer than the linter's limit). Before handing it over, run every check
  in the spec against the prescribed text.
  **Repeated**: a negative grep for
  `DELETE`/`send` found the SQL `DELETE` and an `AFTER DELETE` trigger that
  the spec itself prescribed. A negative grep targets the call shape
  (`.post(`, `request("DELETE"`), not the bare word.
- **A claim about data taken from a heuristic gauge.** A boolean from a list
  of known markers only measures known shapes; `false` does not mean "not
  there". Verify every claim about data content on the data itself
  (structure, counts); the gauge is only supporting evidence.
- **A queue of items without distinguishing transient and permanent
  errors.** A spec that, for per-item processing (bodies, attachments,
  sending), lets "any other error" propagate lets one permanently broken
  item block the whole queue on every later run. The spec defines, for an
  error of one item: transient → next run, permanent → mark the item and
  continue, or count attempts.
  **Repeated the other way round**: a
  service outage (timeout, 429, 5xx) burned an attempt for every item in the
  batch, so after three runs during an outage the whole queue would end up
  permanently `failed`. The distinction applies both ways. A permanent item
  error does not block the others. A transient service error ends the phase
  in this run and counts an attempt at most for the item that got it.
- **A secret or an environment mapping as a function argument.** pytest
  prints the arguments of every frame in a long traceback. A key passed as a
  parameter (`_client_for(key)`) or `environ=os.environ` thus ends up in the
  output the user copies into a report. The same happened to an identity
  (UPN) in a helper of a live test. A secret is read only inside the
  function that hands it to the SDK; arguments carry only the secret's name
  or a person's id. A leak test measures the real pytest output (pytester,
  subprocess), not `traceback.format_exception`, which does not print frame
  arguments.
- **A test scenario that cannot happen through the composed entry point.**
  The entry point runs steps in order (folders, phases) and an earlier step
  fails before the code reaches the tested place. Walk the scenario in the
  code's step order; call the tested place directly, and through the entry
  point only a scenario that really happens.
- **A pagination loop copied into code that deletes.** A non-destructive
  listing (backfill) treated an empty page as the end. Reconcile copied the
  loop and deleted, based on the "complete" listing, messages that were in
  the mailbox. Code that deletes based on completeness of a server listing
  has a table of server responses in the spec (empty page with a next link,
  repeated link, page cap, error in the middle). Every row ends either in a
  complete listing or in an error without writes.
- **A pattern for personal data derived from syntax, not from where it
  occurs.** The address pattern's boundaries came from the characters
  allowed in an address, so `forget` did not find the address in
  `?email=…`, `/unsub/…` or in apostrophes. The golden table has two halves:
  real contexts of occurrence (URL, query, quotes, encoding, `mailto:`) and
  non-matches of similar values (`dejan@` vs. `jan@`). The deletion test
  seeds all of them.
- **A data guarantee verified only on data written by the new code.** The
  claim "the address is not even in the bytes of the DB file" held only for
  a DB written with `secure_delete` already on. History from before the
  change left remnants. Test a guarantee about data state on the state after
  upgrade, i.e. on data written by the old code and old settings.
- **A live step waits for a state the deployment does not produce.** The
  spec expected an upgraded DB right after deploy, but the migration runs
  only on first open (the first timer tick). A live step that reads
  post-deploy state names the event that produces it (deploy, timer tick,
  manual command) and waits for it.
- **A promise of data migration in one big step** across UI and storage —
  no such single step exists; decide the order and what must succeed first.
- **Third-party behaviour written from memory is a spec error shape.** An
  SDK prefixing error texts, a library's pytest path, an upstream server's
  429 shape — each was assumed in a spec and disproved by running the image
  in the spec check. The designer runs it before writing it.
- **A disproved claim filed as a note.** The spec check ran a linter and
  showed that the spec's claim "a missing path always fails" was false
  under the chosen rule set, but filed it non-blocking because the tree
  passed. The implementer could not fix it without a design decision, the
  reviewer raised it as a spec error, and it cost a fix commit plus a delta
  review after approval. When a run disproves a claim that a guard, check
  or acceptance criterion depends on, the finding is blocking and goes back
  to the designer before implementation.

## Error shapes in code and docs

- **A variable read by the code, missing from the template.** The code reads
  `import.meta.env.NAME` / `process.env.NAME` and the default is missing from
  `.env.example` (and the README) — it silently works locally and fails on a
  clean checkout. Always declare it in `.env.example` and the README, and
  read it with a fallback.
- **The decision path does not use the same predicate as the delivery
  path.** Showing a button/action is driven by one shape of the data, the
  handler by another → the visible action does something other than it
  promises. One predicate called from every place; test through the real
  path, not through the predicate.
- **A comment or README describes a state the code does not produce.** After
  a behaviour change, grep for the old wording in README, docs and comments.
  This includes **enumerations** that drift from the code (list of routes,
  table of states): back every enumeration in text with a grep against the
  source.
- **A half-claim promising more than the code does.** "We never delete data
  any more" holds only while a backup / schema version exists — a half
  sentence with the condition is enough; a claim without it forces the next
  implementer to uphold an absolute guarantee nobody actually holds.
- **An irreversible operation without confirmation and without a way back.**
  Deleting data under `--force`, a one-step reset. Where it cannot be
  undone, there is either a confirmation or a visible boundary ("this will
  delete …"), and the README describes the way back.
- **A bug in a derived step, not in the main flow.** Build and lint green,
  but a route is missing from the menu because it is generated from an
  enumeration nobody updated. A review round must not end with "all green,
  done"; for a UI it walks the **main flow of the brief** in the browser.
- **Error handling hangs on a single failure path.** Clean-up/shutdown only
  on the "non-zero exit" branch is bypassed by an exception. Clean-up goes
  in `finally` / a cleanup hook, not on one branch.
- **Retention and clean-up must never touch what this run created.** A
  rotation that keeps "the newest N by name" deleted the archive it had
  just written whenever another file sorted later, and still reported
  success; a `find "$dir" -name '.tmp.*' -exec rm` without `-mindepth 1`
  could match `$dir` itself. Exclude the new item explicitly, check it
  still exists before reporting success, and plant a "future" file in the
  test.

## Tests

- An assertion `"<string>" in <file content>` measures a comment, not code.
  Measure parsed structure or runtime behaviour; a text assertion is only a
  supplement.
- Mutation self-review: disable the feature, the test must go red. A test
  that passes with the feature disabled is not a test.
- `assert X or True`, a fixture with a hash, a probe via `touch` under a
  different identity, a mock that always throws the targeted exception — do
  not test behaviour. For a security or boundary property, the input must
  come from the production path (render, fetch layer), not from an injected
  fixture.
- A test measures the function, not the delivery path (`main()`, CLI,
  handler) — the finding survives. Test through the real entry point.
- Tests skipped locally (`skipif` on a missing tool) but running in CI must
  be **run**, not just read — otherwise CI goes red after the PR is opened.
- `grep -c` counts lines, not occurrences: JSON or HTML on one line gives 1.
  Count occurrences with `grep -o … | wc -l`.
- **An invariant over a derived structure measures nothing.**
  `count(fts) = count(message)` on an external-content FTS5 table or a view
  reads the source table, so it always passes. Measure the storage of the
  structure itself (for FTS5 `<table>_docsize`) or a query that goes through
  the index.
- **A time bomb in tests over an age filter.** Retention and a "do not store
  older than 24 months" filter would have broken existing tests with fixed
  dates around 2028, because the CLIs used the wall clock. A PR that filters
  or deletes by age injects the clock into every entry point. Check with a
  grep for `datetime.now(` / `Date.now(` and fixed dates in tests.
- **A commit during a mutation batch.** A mutation (`if True: break`) ended
  up in a commit because the commit happened while the batch was changing
  the same file. Mutate only on a clean tree after a commit, revert the
  mutation before the next commit and grep the diff.

- **A default-valued argument hides a broken wiring.** The only HTTP test
  called the tool with the default lag and a range equal to the default,
  so dropping both arguments in the handler stayed green. A test of an
  optional argument uses a value different from the default, through the
  real entry point.
- **A cached test stage is not a run.** A build that prints the test layer
  from cache shows no count; after a rebase or for a reviewer's
  "independent" run, force the stage or run the tests explicitly, and
  quote counts plus the tree hash.
- **A negative grep must first find its positive.** A phrase that wraps
  over two lines makes "grep finds nothing" vacuous; show the hit on the
  old tree before trusting the empty result on the new one.

## Review

- Round 1 goes through the **whole** checklist. Findings that appear only in
  round 2 cost an extra implementation round — deployment-layer findings
  (env, gitignore, secrets) used to show up in round 2 every time.
- Some findings can only be found by running: the reviewer runs every new
  command / recipe. A green build is the start of a review, not its end.
