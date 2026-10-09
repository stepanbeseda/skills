# skills

Public, general-purpose [Agent Skills](https://agentskills.io/specification) by Stepan Beseda.
Every skill is a plain folder with a `SKILL.md` in the vendor-neutral Agent Skills format, so
the same files work in Claude Code, OpenAI Codex, OpenCode, Gemini CLI, Cursor, GitHub Copilot
and other tools that read the format. The repository is also a plugin marketplace
(`stepanbeseda-skills`) with one plugin, `sbskills`, for Claude Code and Codex.

## Skills

| Skill | What it does |
|---|---|
| [`new-skill`](skills/new-skill/SKILL.md) | Creates or updates a skill and saves it in the right place — this project only (`.agents/skills`), or shared here |
| [`publish-skills`](skills/publish-skills/SKILL.md) | Publishes changes in this repository: adapters, secret scan, version bump, validation, commit and push |
| [`check-skills`](skills/check-skills/SKILL.md) | Shows which skills each tool sees and where they come from, finds duplicates, checks the setup |
| [`mao`](skills/mao/SKILL.md) | Multi-agent orchestration: plan → spec → implement → independent review → merge, for one PR or a batch; explicit only, `/mao` |

## Install

### Claude Code

```text
/plugin marketplace add stepanbeseda/skills
/plugin install sbskills@stepanbeseda-skills
```

Skills are available as `/sbskills:<skill>`; the `mao` subagents (`sbskills:mao-designer`, …)
are installed with the plugin. Updates: `/plugin marketplace update stepanbeseda-skills`,
then `/reload-plugins`.

### OpenAI Codex

```bash
codex plugin marketplace add stepanbeseda/skills
```

Then install the `sbskills` plugin from that marketplace (skills are discovered from
`skills/`) and call a skill with `$<skill>`. Subagents are copied by hand:

```bash
git clone https://github.com/stepanbeseda/skills && cd skills
mkdir -p ~/.codex/agents && cp adapters/codex/agents/*.toml ~/.codex/agents/
```

### OpenCode, Gemini CLI, Cursor, GitHub Copilot and others

```bash
npx skills add stepanbeseda/skills
```

The [`skills`](https://github.com/vercel-labs/skills) installer copies or links the skill
folders into each tool's skills directory (`-a <agent>` picks the tool, `-g` installs for the
user instead of the project). Run it again to update. OpenCode subagents:

```bash
mkdir -p ~/.config/opencode/agents && cp adapters/opencode/agents/*.md ~/.config/opencode/agents/
```

Tools without subagents (Gemini CLI, Cursor, Copilot, …) run the `mao` roles inline: the
orchestrator reads `skills/mao/roles/<role>.md` and follows it itself.

### What is verified

- Verified: `claude plugin validate .`, and a Claude Code install from a local clone
  (marketplace add + plugin install; skills and agents show up), `scripts/validate.py`.
- Not verified on a real install: the Codex marketplace and plugin (format per the Codex
  docs), the `npx skills` installer and its flags, the OpenCode and Codex subagent copies,
  and Gemini CLI / Cursor / Copilot discovery. Reports welcome.

## Layout

```text
skills/<name>/
├── SKILL.md                 the skill (front matter: Agent Skills spec fields only)
├── scripts/ references/     optional helpers, referenced with relative paths
├── roles/<role>.md          optional subagent roles (name, description, tier: strong|fast)
└── agents/openai.yaml       optional Codex settings, e.g. explicit-only invocation
adapters/{claude,codex,opencode}/agents/   generated subagent files — do not edit
.claude-plugin/plugin.json   Claude Code plugin manifest (sbskills)
.claude-plugin/marketplace.json            Claude Code marketplace (stepanbeseda-skills)
plugin.json                  Agent Plugins 1.0 manifest (Codex, Copilot), same version
.agents/plugins/marketplace.json           Codex marketplace (stepanbeseda-skills)
scripts/build-adapters.py    generates adapters/ from skills/*/roles/*.md
scripts/validate.py          spec, manifests, adapters and secret checks
```

## Adding a skill

1. Create `skills/<name>/SKILL.md` (or ask an agent: "save this as a skill" with `new-skill`).
   `name` equals the folder name; front matter uses only the spec fields `name`,
   `description`, `license`, `compatibility`, `metadata`, `allowed-tools`. Keep `SKILL.md`
   under 500 lines.
2. Explicit-only skill: say so in the description and add `agents/openai.yaml` with
   `policy: { allow_implicit_invocation: false }` for Codex.
3. Subagent roles: add `roles/<role>.md` and run `python3 scripts/build-adapters.py`.
4. Run `python3 scripts/validate.py`, then publish with `publish-skills`
   (`bash skills/publish-skills/scripts/publish.sh . "<message>"`).

## Rules

- This repository is public: no secrets, tokens, e-mail addresses, personal paths, host
  names, client names or private data in skills, scripts or examples. `validate.py` and
  `publish-skills` scan for them and stop.
- One skill lives in exactly one place: a project's `.agents/skills/` (Claude Code reads it
  through the symlink `.claude/skills -> ../.agents/skills`) or this repository. Do not keep
  hand-made copies of shared skills in user folders.
- Content is English. Versions follow `MAJOR.MINOR.PATCH`; `publish-skills` bumps the patch
  version in both plugin manifests on every change to `skills/` or `adapters/`.

## License

[MIT](LICENSE)
