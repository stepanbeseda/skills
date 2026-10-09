# Checklist

The implementer goes through it in self-review, the reviewer in round 1;
each item gets `ok` / `finding` / `n/a` — an empty line is a blocking
finding. Delete items that do not apply to the project; add items from
repeated findings. For a webapp, append the applicable sections of
`<SKILL>/references/profiles/webapp-checklist.md`.

## Acceptance criteria and tests

- [ ] Every acceptance criterion verifiable offline has a test that
  **fails** when the feature is disabled (mutation: comment out a line, the
  test must go red).
- [ ] The test measures behaviour or parsed structure, not file text —
  `"x" in source` is satisfied by a comment too.
- [ ] Tests do not depend on the environment (global git config, HOME,
  time zone, file order, network).
- [ ] An extended closed enumeration (`assert ids == {…}`, list of routes,
  table of states) is updated in the diff.
- [ ] Nothing was silently weakened: a deleted test has a "new home" line in
  the spec/PR.
- [ ] Time: fixed dates and relative dates in one test file are a calendar
  bomb — freeze the whole file or compute everything from `now`.

## Failure

- [ ] An error ends with a non-zero exit code or an exception (or a visible
  error state in a UI), not a silent no-op.
- [ ] Zero, an empty string and a missing config value are validated at
  start-up, not deep inside a handler.
- [ ] Input of unbounded size is not read into memory whole.
- [ ] Clean-up is in `finally` / a cleanup hook, not on a single failure
  branch.

## Configuration and secrets

- [ ] A new config value has its default in one place and is documented
  (`.env.example` or equivalent, README).
- [ ] No secrets, personal paths (`/Users/<name>/…`) or deployment identity
  in versioned code or in any commit (`git log -p`).
- [ ] Dependencies without known critical vulnerabilities (`npm audit` or
  equivalent; reporting one as non-blocking with a reason is allowed).

## Data

- [ ] Irreversible operations (deleting records or data) have a
  confirmation or a visible warning, and the README describes the way back.
- [ ] Stored data has a schema version; older data is migrated and an
  invalid record is dropped with a warning instead of crashing.

## Documentation

- [ ] Docs and docstrings describe the new behaviour; grep for the old
  wording is empty.
- [ ] Links in docs lead to existing files.
