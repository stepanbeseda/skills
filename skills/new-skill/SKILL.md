---
name: new-skill
description: Creates a new skill or updates an existing one and saves it in the right place — either only for the current project, or shared across all projects and agent tools through the public skills repository. Use when the user says "save this as a skill", "make a skill out of this", "new skill", "update the skill", "I want this in every project", or wants to reuse a skill from another project.
license: MIT
---

# New or updated skill

The user only has to say "save this as a skill". You decide where it
belongs, write it in the vendor-neutral Agent Skills format, and — for a
shared skill — publish it.

## 1. Project skill or shared skill?

Decide in this order:

1. **The user said it** ("only here", "for all projects", "shared") → do
   that without asking.
2. **The skill is clearly tied to this project** — it names this project's
   clients, people, folders, templates, data or tone → save it as a project
   skill and say in one sentence why. Merely working inside a project folder
   is not enough; invoices, e-mails or meetings exist in other projects too.
3. **Otherwise ask one short question with a recommendation**, for example
   "This is a general helper — I'd make it shared so every project gets it.
   Or only here?" Save nothing until the user answers.

**Never save a shared skill without the user's explicit consent** — the
skills repository is public and the skill becomes visible to anyone.

| Rather a project skill | Rather a shared skill |
|---|---|
| uses this project's files, folders, templates or data | needs nothing from a specific project |
| about one company, client, team, or their style | a personal helper that should work the same everywhere |
| would be done differently in another project | would look identical in any project |

When in doubt, recommend a project skill: promoting it to shared later is
easy, splitting a shared skill into per-project exceptions is not.

**Where it goes**

- **Project skill:** `<project root>/.agents/skills/<name>/SKILL.md`. Codex,
  OpenCode, Gemini CLI, Cursor and GitHub Copilot read `.agents/skills`.
  Claude Code does not, so the project also gets one symlink (create it
  once if it is missing, and commit it):

  ```bash
  mkdir -p .claude && ln -s ../.agents/skills .claude/skills
  ```

  If `.claude/skills` already exists as a real folder, move its skills into
  `.agents/skills` first, then replace the folder with the symlink.
- **Shared skill:** in the skills repository
  (`https://github.com/stepanbeseda/skills`; local clone path from the
  project's `AGENTS.md` / `CLAUDE.md`; if it is not recorded, ask) at
  `skills/<name>/SKILL.md`.

Do not copy shared skills into user-level folders (`~/.claude/skills`,
`~/.agents/skills`, `~/.codex/…`) or account settings by hand: they would
shadow or duplicate the installed copy. Installation is described in the
repository README.

## 2. Check that it does not exist already

Look in the project's `.agents/skills/` (and `.claude/skills/` if it is not
yet a symlink) and in `skills/` of the skills repository for a skill with the
same or a similar purpose. If there is one, update it instead of adding a
second.

- **Taking over a skill from another project:** copy it here and adapt it.
  Do not reference the other project's folder; projects stay independent.
- **Promoting a project skill to shared:** move it (do not copy) into the
  skills repository, so no second copy is left in the project.

## 3. Write `SKILL.md`

- **Folder name and `name`:** lowercase letters, digits and single hyphens,
  at most 64 characters, equal to the folder name (e.g. `weekly-report`).
- **Front matter:** only fields of the Agent Skills specification —
  `name`, `description`, optionally `license`, `compatibility`, `metadata`
  (string map) and `allowed-tools`. No tool-specific fields; other tools
  reject or ignore them.
- **`description`** (max 1024 characters): what the skill does and when to
  use it, including the phrases a user would typically say. This is how the
  agent decides to run it — be concrete.
- **Explicit-only skills** (should run only when the user names it): say so
  in the description ("Run it only when the user explicitly invokes it …;
  never start it on your own"), and for Codex add `agents/openai.yaml` in the
  skill folder:

  ```yaml
  policy:
    allow_implicit_invocation: false
  ```
- **Body:** steps, inputs, what the output looks like, and a short example
  if it helps. Plain, short sentences; keep `SKILL.md` under 500 lines and
  move long detail to `references/`.
- **Supporting files** go into `scripts/`, `references/` or `assets/` next
  to `SKILL.md` and are referenced with relative paths.
- **Subagent roles** (shared skills only): one file per role in
  `roles/<role>.md` with front matter `name` (the role id = file name),
  `description` and `tier: strong|fast`; the body is the role's system
  prompt. Then run `python3 scripts/build-adapters.py` in the skills
  repository; it generates the Claude Code, Codex and OpenCode subagent
  files under `adapters/`. Tools without subagents run the role inline.
- **Public content:** a shared skill is published. No secrets, tokens,
  personal paths, host names, client names, e-mail addresses or private
  data — not in the text, not in the scripts, not in examples.

Template:

```markdown
---
name: skill-name
description: What the skill does. Use when the user ...
---

# Skill name

## Steps
1. ...

## Output
...
```

## 4. Finish

- **Project skill:** available in a new session in this project.
- **Shared skill:** run `python3 scripts/validate.py` in the skills
  repository, then publish right away with the `publish-skills` skill; that
  is part of saving it, the user does not have to ask again. The same applies
  after editing a shared skill.

Tell the user where the skill was saved (project or shared, and why) and how
to call it:

- Claude Code: `/sbskills:<name>` for a shared skill from the plugin,
  `/<name>` for a project skill;
- Codex: `$<name>`;
- other tools: by name as their docs describe, or simply by asking.

Agents also run a skill on their own when a request matches its description,
unless it is explicit-only.
