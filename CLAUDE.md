# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Overview

This is a **multi-harness skills repository** for the Automatis team. Commands are authored once as Agent Skills and vendored into each product repo. In a product repo, invoke `/automatis-<name>` (Codex: `$automatis-<name>`).

This repo remains a Claude Code marketplace (`automatis@automatis-tools`). The marketplace is the source package: `/plugin install` copies skills; it does **not** register `/automatis-<name>` on Claude (plugin components are colon-namespaced). Product repos get the hyphen slash command by vendoring. The colon form `/automatis:fix-pr` is retired.

The marketplace schema supports multiple plugins, but this one deliberately ships only `automatis` so team members get every command from a single source package.

## Structure

```
.claude-plugin/
└── marketplace.json              # Plugin catalog (one entry: automatis)

automatis/
├── .claude-plugin/plugin.json
└── skills/
    ├── automatis-fix-pr/SKILL.md          # → /automatis-fix-pr
    ├── automatis-ports-release/SKILL.md   # → /automatis-ports-release
    └── automatis-git-cleanup/SKILL.md     # → /automatis-git-cleanup

scripts/
└── vendor-automatis-commands     # copy skills into product repos; --check validates this repo
```

There is no `automatis/commands/`. Plugin `commands/` would produce `/automatis:<name>`.

## Naming Convention

- **Plugin**: always `automatis`. New commands go inside this plugin as skills — do not create sibling plugin directories unless there's a strong reason.
- **Skills**: folder and frontmatter `name:` are `automatis-<action>` (kebab-case after the prefix): `automatis-fix-pr`, `automatis-ports-release`, `automatis-git-cleanup`.
- **Usage** (in a product repo): `/automatis-<name>` (e.g. `/automatis-fix-pr`). Codex: `$automatis-<name>`.

## Adding a Command (common case)

1. Create `automatis/skills/automatis-<name>/SKILL.md` with `name: automatis-<name>` following the house style in [Skill File Structure](#skill-file-structure) below.
2. Run `./scripts/vendor-automatis-commands --check`.
3. Commit in this repo.
4. In each product repo, run `./scripts/vendor-automatis-commands <product-repo>` from this checkout and commit the vendored files there.

Deleting a command: remove the skill folder here, then run the vendor script with `--prune` in each product repo.

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

Do not add `automatis/commands/`. Plugin slash commands are colon-namespaced (`/automatis:<name>`); product repos get `/automatis-<name>` from vendored `.claude/commands/`.

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

CI (`.github/workflows/lint.yml`) runs the same tests and `--check`.

## Git hooks

Point this worktree at the tracked hooks so pre-push runs `--check`:

```bash
git config core.hooksPath .githooks
```

`.githooks/pre-push` runs `python3 -m unittest discover -s tests -v` then `./scripts/vendor-automatis-commands --check`. Never `--no-verify`.
