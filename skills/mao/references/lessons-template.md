# Lessons from MAO runs

Memory shared across PRs and worktrees of this project. Agent `memory:` is
stored per worktree, which is why this is a file in the repo. The
orchestrator adds findings whose shape repeats at the end of a run. All
agents read it before working; general lessons are in
`<SKILL>/references/lessons-general.md`.

## Error shapes that repeated

## Spec error shapes (designer)

## Operational lessons

A missed repo-wide pin goes into the pins script (`project.md`, "Pins"),
not here: a list in prose did not stop the next PR from missing it.
