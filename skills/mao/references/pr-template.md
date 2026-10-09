# PR body template

Title per `project.md` (default `PR NN — <name from the plan table>`).
The worker builds the body into `<ROOT>/.mao/log/<PR>-pr-body.md`
**after the final review verdict** (never with "pending" placeholders), from
the spec, the last impl report and the `## PR body` sections of the review
reports; the orchestrator passes it via `gh pr create --body-file`. The
footer lines come from the session's attribution instructions.

```
<One sentence: what the PR delivers; link to the plan chapter.>

Changes:
- <for a new task first: docs — new chapter PR NN in the plan (brief, Done when, table row)>
- <for the first run in a project: chore — MAO configuration in .mao/>
- <area — what>

Acceptance criteria:
- [x] <criterion> — <verified by: test / command / browser preview>
- [ ] <criterion> — requires test host: <manual step>

Validation:
- Check (`<command from project.md>`): <green, numbers per suite, tree hash
  or "tree identical to <checked commit>">
- CI: <green, link to run | repo has no CI>
- Browser preview: <main flow → ok, screenshot | n/a>

Deviations from the plan and spec:
- <or "none"; for each, who accepted it (reviewer round N)>

Open non-blocking findings:
- <from the last review; or "none">

Rollback:
- <how to revert; what must not be damaged (e.g. user data)>

Review:
- <round N: verdict + 1–2 lines, from the review's `## PR body` section;
  delta reviews after a rebase included>

Deploy (only when the PR needs one):
- <order, secrets, migrations, which criteria to verify after it; in a
  batch a pointer to the deploy bundle>

Orchestration: design <n> attempts, implementation <n> rounds, review <n>
rounds (<findings per round in one sentence>), escalations <n>.

<footer lines required by the session or project, if any>
```
