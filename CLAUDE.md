# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Overview

This is a **multi-harness skills repository** for the Automatis team. Author Agent Skills once and distribute them through native plugins for Codex, Claude Code, and Grok, and a Gemini CLI extension. Product-repository vendoring remains an optional snapshot workflow.

Install `automatis@automatis-tools` once through each host's native manager and enable automatic updates as described in README.md. Adding the marketplace alone does not install the plugin. Claude native skills are named `/automatis:automatis-<name>`; Codex uses `$automatis-<name>`, while Grok and the generated Gemini aliases use `/automatis-<name>`. A skill remains available for implicit agent selection from its description.

The marketplace schema supports multiple plugins, but this one deliberately ships only `automatis` so team members get every command from a single source package.

## Structure

```
.claude-plugin/marketplace.json    # Claude/Grok catalog (one entry: automatis)
.agents/plugins/marketplace.json  # Codex catalog (same plugin source)
gemini-extension.json             # Gemini manifest; skills/ is generated in release assets

automatis/
├── .claude-plugin/plugin.json
├── .codex-plugin/plugin.json
└── skills/
    ├── automatis-create-github-issues/SKILL.md
    ├── automatis-fix-pr/SKILL.md          # → /automatis-fix-pr
    ├── automatis-ports-release/SKILL.md   # → /automatis-ports-release
    ├── automatis-git-cleanup/SKILL.md
    └── automatis-ste100/SKILL.md

scripts/
├── build-automatis-release       # validate versions and build Gemini release archive
├── migrate-automatis-install     # archive manifest-owned legacy copies
└── vendor-automatis-commands     # optional product snapshots; --check validates skills
```

There is no `automatis/commands/`. Gemini command aliases are generated inside the release archive from canonical skills, never authored as a second source tree.

## Naming Convention

- **Plugin**: always `automatis`. New commands go inside this plugin as skills — do not create sibling plugin directories unless there's a strong reason.
- **Skills**: folder and frontmatter `name:` are `automatis-<action>` (kebab-case after the prefix): `automatis-fix-pr`, `automatis-ports-release`, `automatis-git-cleanup`.
- **Usage**: use the host's registered name from README.md. Skill examples use canonical `/automatis-<name>` names; Claude's native plugin adds `/automatis:` before that name.

## Adding a Command (common case)

1. Create `automatis/skills/automatis-<name>/SKILL.md` with `name: automatis-<name>` following the house style in [Skill File Structure](#skill-file-structure) below.
2. Run `./scripts/vendor-automatis-commands --check`, `./scripts/build-automatis-release --check`, and the unit tests.
3. Commit in this repo and release through the native packaging workflow below. Installed plugins receive new skills through their host's update mechanism.
4. Only for deliberately pinned product snapshots, vendor and commit the generated files in those repos.

Deleting a skill: remove its folder and publish a new version. Product snapshots require a vendor run with `--prune` to remove deleted names.

## Native Packaging and Releases

- Keep canonical content under `automatis/skills/`; preserve complete directories so relative resources remain available.
- Codex uses `automatis/.codex-plugin/plugin.json` with `skills: "./skills/"`. Its catalog uses a structured local source pointing at `./automatis`, relative to the repository root.
- Claude and Grok share `.claude-plugin/marketplace.json` and the existing plugin manifest.
- Gemini's release archive contains root `gemini-extension.json`, generated `skills/`, and `commands/*.toml`. Install from the unpinned GitHub repository with `--auto-update`. Do not use a local directory install for production auto-updates.
- Before releasing, bump all three package manifests to the same stable semantic version and update Claude marketplace metadata. Merge the reviewed release commit into `main`, then push a tag equal to the version (for example `1.1.0`). `.github/workflows/release.yml` validates and publishes the archive. Tags do not start with `v`.
- Claude plugin cache updates depend on its version changing. Codex/Grok/Claude refresh the Git marketplace; Gemini checks GitHub releases. A release does not instantly replace skills already loaded into a running session.
- Before retiring old installations, install and verify the native plugins. Then use `scripts/migrate-automatis-install` to archive only manifest-owned legacy paths. Do not remove skills by glob; preserve unrelated and untracked local files.

## Adding a Plugin (rare)

Only needed if a new tool genuinely belongs in its own namespace (distinct audience, separate install lifecycle, licensing boundary, etc.). Otherwise use "Adding a Command" above.

1. Create directory at repo root (**not** under `plugins/` — that path was removed in commit `24e6c10` to work around plugin discovery):
   ```
   <plugin-name>/
   ├── .claude-plugin/plugin.json
   └── skills/automatis-<action>/SKILL.md
   ```

2. Plugin manifest (`.claude-plugin/plugin.json`):
   ```json
   {
     "name": "<plugin-name>",
     "version": "1.0.0",
     "description": "What it does",
     "author": { "name": "Automatis Tools" },
     "keywords": ["relevant", "tags"]
   }
   ```

3. Register in `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "<plugin-name>",
     "source": "./<plugin-name>",
     "description": "What it does",
     "category": "category",
     "tags": ["tags"]
   }
   ```
   Source paths are relative to the repo root and must use the `./<dir>` form — other formats have broken plugin discovery before (commits `978043a`, `9dd783e`, `7adaae1`, `ae84edf`, `24e6c10`).

## Plugin Capabilities

Each plugin can include:
- `skills/` - Agent skills with `SKILL.md` (this plugin ships these)
- `agents/` - Custom subagents (markdown)
- `hooks/` - Event hooks in `hooks.json`
- `.mcp.json` - MCP server configs
- `.lsp.json` - LSP server configs

Do not add `automatis/commands/`. Claude plugin skills are colon-namespaced (`/automatis:automatis-<name>`); optional product snapshots get `/automatis-<name>` from vendored `.claude/commands/`.

### Skill File Structure

Every `automatis/skills/automatis-<action>/SKILL.md` in this repo follows the same shape — keep new skills consistent so they read as one family:

- **YAML frontmatter** (between `---` fences) with `name` (must equal the folder name, `automatis-<action>`), `description` (one-line blurb for the `/` menu), `argument-hint` (arg shape shown after the command name in autocomplete), `allowed-tools` (comma-separated whitelist — tighter is safer, e.g. `Bash` alone for commands that never edit files). Then a `# Title` line.
- `## When to Use` — 2–4 bullets describing trigger scenarios.
- `## Arguments` — every accepted input form shown as a concrete example line (`/automatis-<cmd> <positional>`, `/automatis-<cmd>` for interactive mode). Include one Codex `$automatis-<cmd>` line. Document optional `--flag=value` here.
- `## Procedure` — numbered steps (`### Step 1: …`), each containing the exact bash block Claude should run. Mark irreversible steps with `**CRITICAL**` so Claude treats them as blocking.
- `## Safety Rules` — numbered list of guardrails (what to refuse, what to confirm with the user).
- `## Example Session` (optional) — fenced block showing a real interaction.

Reference implementation: `automatis/skills/automatis-fix-pr/SKILL.md`.

## Shell Safety

Plugin command files generate bash snippets that Claude executes. A few traps have bitten this repo before (see commits `bdad29e`, `aa4e7be`); codify them here so new plugins don't repeat them.

- **`!` in jq inside double-quoted bash breaks.** Bash history expansion corrupts `!` even inside `"..."`. Never write `jq '... != null ...'` in a bash block — use Python (`python3 -c`) for any filter that needs `!=`.
- **Don't chain `--argjson` with shell variables.** If the variable is empty or not valid JSON, `gh`/`jq` fail silently and the pipeline "succeeds" with wrong data. Prefer Python when you need to pass structured data.
- **Use Python for multi-step JSON filtering.** Single-field extraction with `--jq '.user.login'` is safe. Anything involving sets, joins, or author comparisons: switch to `python3 -c`.
- **Command files are executed as written.** Copy exact code blocks; do not let Claude "rewrite jq from memory" — that's how the above bugs entered.

These rules live here (not inside individual command files) because any new plugin calling `gh`, `jq`, or `curl | jq` will hit the same traps.

## Manual Verification

To verify a change:

1. Validate skills and manifests:
   ```bash
   ./scripts/vendor-automatis-commands --check
   ```
   `--check` parses `marketplace.json` and `automatis/.claude-plugin/plugin.json`, verifies `./automatis`, and rejects a leftover `automatis/commands/` directory.

2. Run unit tests:
   ```bash
   python3 -m unittest discover -s tests -v
   ```

3. Validate native package versions and build the Gemini archive:
   ```bash
   ./scripts/build-automatis-release --check
   ./scripts/build-automatis-release --output dist
   ```

CI (`.github/workflows/lint.yml`) runs the tests, vendor validation, and release builder.

## Git hooks

Point this worktree at the tracked hooks so pre-push runs `--check`:

```bash
git config core.hooksPath .githooks
```

`.githooks/pre-push` runs the unit tests and both validation commands. Never `--no-verify`.
