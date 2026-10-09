# Notes for agents working in this repository

This is a public, cross-vendor Agent Skills repository. It is also a plugin marketplace
(`stepanbeseda-skills`) with one plugin, `sbskills`, for Claude Code and Codex.

- Skills live only in `skills/<name>/SKILL.md` (+ `scripts/`, `references/`, `assets/`,
  `roles/`, `agents/openai.yaml`). Follow the `new-skill` skill. Front matter: only the Agent
  Skills spec fields (`name` = folder name, `description`, optional `license`,
  `compatibility`, `metadata`, `allowed-tools`). No tool-specific fields.
- Subagent roles are `skills/<skill>/roles/<role>.md` (front matter `name`, `description`,
  `tier: strong|fast`). Never edit `adapters/` by hand; run `python3 scripts/build-adapters.py`.
  It also updates the `agents` list in `.claude-plugin/plugin.json`.
- `plugin.json` and `.claude-plugin/plugin.json` always carry the same version.
- Before a commit run `python3 scripts/validate.py` and, if the `claude` CLI exists,
  `claude plugin validate .`.
- Publish with `bash skills/publish-skills/scripts/publish.sh <repo> "<message>"`: it rebuilds
  adapters, scans for secrets, bumps the version, validates and pushes. Never force-push.
- Everything here is public: no secrets, tokens, e-mail addresses, personal paths, host
  names, client or project names, and no private data in examples.
- Content is English.
