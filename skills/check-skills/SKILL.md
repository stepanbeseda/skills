---
name: check-skills
description: Shows which skills each agent tool (Claude Code, Codex, OpenCode, Gemini CLI, Cursor, GitHub Copilot) can see in a project and where every skill comes from (project folders, user folders, installed plugins), finds duplicates and skills in the wrong place, checks the .claude/skills symlink and whether the shared skills marketplace is installed. Use when the user does not know where a skill comes from, sees a skill twice, a skill behaves unexpectedly, or asks whether the skills setup is correct.
license: MIT
---

# Check skills

## Steps

1. Run the script next to this file with the current project root:

   ```bash
   bash "<this skill's folder>/scripts/check.sh" "<project root>"
   ```

   It only reads; it changes and deletes nothing.

2. Summarise the result for the user briefly:
   - what is fine;
   - what should be fixed and why;
   - for duplicates: which copy is the right one (a project skill in
     `.agents/skills`, or the shared one from the skills repository —
     the `sbskills` plugin or a `npx skills add` copy) and which copies are
     extra.
3. Delete nothing on your own. Propose concrete steps per skill and carry
   them out only after the user agrees:
   - a skill in the wrong place that exists nowhere else → propose to
     **move** it (into the project's `.agents/skills`, or into the shared
     repository with `new-skill`), not to delete it;
   - propose deleting a copy only after you have verified that the same
     skill exists in its right place;
   - never propose deleting a whole skills folder at once.

## Reading the output

| Location | Read by | Expected? |
|---|---|---|
| project `.agents/skills` | Codex, OpenCode, Gemini CLI, Cursor, Copilot | yes — the project skills |
| project `.claude/skills` | Claude Code, OpenCode, Cursor, Copilot | yes, as a symlink to `../.agents/skills` |
| project `.opencode/`, `.gemini/`, `.cursor/`, `.github/skills` | one tool each | better moved to `.agents/skills` |
| `claude plugin sbskills` | Claude Code | yes — the shared skills |
| user folders (`~/.agents/skills`, `~/.claude/skills`, …) | per tool | only for shared skills installed with `npx skills add`, or private helpers never shared; a copy of a plugin skill is a duplicate |

The tool-to-folder mapping follows each tool's documentation; a tool may
read more places than listed. Skills uploaded in account settings (for
example claude.ai → Settings → Skills) are not on disk; remind the user to
review those by hand.
