# Webapp profile — preview gate

Some acceptance criteria cannot be verified by build and tests alone: the
main flow in the browser, responsiveness, empty states, behaviour after
saving and reading data back, and network errors. **Where** they are
verified is decided in preflight and in the spec, not during review.
Applies only when `project.md` has a "Preview" section.

## Verification levels

1. **Offline (check + tests).** The check from `project.md`. Always
   mandatory; the result goes into the PR body.
2. **Browser preview.** The worker starts the dev/preview server (port from
   the config), the orchestrator opens the browser, walks the main flow of
   the brief and takes a screenshot. Findings go to the implementer
   (`<PR>-preview-N.md`); it is repeated after the last review fix
   (regressions). Default level for every app with a UI — without it the
   app is only "built", not "done". No browser tool in the session → the
   flow is marked "requires manual preview" with exact steps for the user.
3. **Production / demo deployment.** Only when the user explicitly named it
   (hosting, VPS, static host). Without it, deployment criteria are marked
   "requires production" and the report to the user lists the steps
   (`npm run build && npm run preview` / deploy recipe → expected results).

## Without production

The run continues; criteria that depend on production are marked
"requires production" in the spec and the implementer writes an exact
manual step for each one (command, expected result). The PR is opened as
**partially verified** and the report to the user says what remains for
after deployment.

## Main flow checked in the browser

- Loading the app → welcome/empty state (no hidden crashes in the console).
- The first action of the brief (add a record) → it is saved → it is shown.
- Reading back / repeating (edit, a second record) — data really persists
  (reload the page).
- Network error / empty data → the UI shows a state, not silence.
- Mobile width (if the brief asks for it), no horizontal scrolling.

Stop-and-ask rules (deleting data, `--force`, overwriting a store) still
apply — whoever needs one stops and asks the user.
