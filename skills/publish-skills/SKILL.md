---
name: publish-skills
description: Publishes changes of shared skills to the public GitHub skills repository, so every machine, project and agent tool picks them up. Use when the user says "publish skills", "push the skills", "release the skill", or right after creating or editing a shared skill.
license: MIT
---

# Publish shared skills

Shared skills are installed from GitHub. Until a change is pushed, no other
session, machine or tool sees it.

## Steps

1. Find the local clone of the skills repository: the path recorded in the
   project's `AGENTS.md` / `CLAUDE.md`, otherwise ask the user. It is the
   folder that contains `skills/`, `plugin.json` and
   `.claude-plugin/marketplace.json`.
2. Run the script next to this file with the repository path and a short
   English description of the change:

   ```bash
   bash "<this skill's folder>/scripts/publish.sh" "<repo path>" "Add the weekly-report skill"
   ```

   The script:
   - refuses to run when the folder is not the skills repository or the
     remote history cannot be rebased cleanly;
   - regenerates the subagent adapters from `skills/*/roles/*.md`
     (`python3 scripts/build-adapters.py`);
   - scans the change for things that must not be public (private keys,
     tokens, e-mail addresses, personal home paths) and stops if it finds any;
   - when anything under `skills/` or `adapters/` changed, bumps the patch
     version in both `plugin.json` and `.claude-plugin/plugin.json` (they
     always stay equal; installed plugins update only when it changes);
   - runs `python3 scripts/validate.py` (Agent Skills spec, manifests,
     adapters, secret scan of the whole repository) and, when the `claude`
     CLI is available, `claude plugin validate .`;
   - commits and pushes.
3. If the script stops with an error, explain the message in plain words.
   Never force anything (`--force`, `--no-verify`); fix the cause and run it
   again.

## Tell the user afterwards

How each tool picks up the new version:

- **Claude Code:** with the next marketplace refresh; right away with
  `/plugin marketplace update stepanbeseda-skills`, then `/reload-plugins`.
- **OpenAI Codex:** refresh or upgrade the `stepanbeseda-skills`
  marketplace with the `codex plugin marketplace` commands (see
  `codex plugin marketplace --help`), then start a new session.
- **OpenCode, Gemini CLI, Cursor, GitHub Copilot and others** (installed with
  `npx skills add stepanbeseda/skills`): run the same command again to get
  the new copies.
- **Subagents copied by hand** (Codex, OpenCode): copy the changed files
  from `adapters/` again, as described in the repository README.
