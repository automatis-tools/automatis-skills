# Multi-harness Automatis commands

Status: approved design (implementation plan at `docs/superpowers/plans/2026-09-01-multi-harness-automatis-commands.md`)

This repository today is a Claude Code marketplace that ships one plugin, `automatis`, with slash commands invoked as `/automatis:<name>`. The team also uses Codex, Grok, Kimi, and Gemini. Those tools must run the same procedures, from files checked into each Automatis product repo, without a personal marketplace install.

## Goal

One procedure per command, authored once as an Agent Skill. A vendor script copies it into product repos. Teammates invoke it with a hyphenated Automatis prefix:

| Tool | Invocation |
|------|------------|
| Claude Code | `/automatis-fix-pr` |
| Grok | `/automatis-fix-pr` |
| Gemini | `/automatis-fix-pr` |
| Kimi | `/automatis-fix-pr` (fallback `/skill:automatis-fix-pr`) |
| Codex | `$automatis-fix-pr` |

Codex does not allow custom `/` commands. `$automatis-fix-pr` is the native equivalent. Every other listed tool uses `/automatis-<name>`.

The colon form `/automatis:fix-pr` is retired. It is not kept as an alias.

## Current state

```
.claude-plugin/marketplace.json
automatis/
  .claude-plugin/plugin.json
  commands/
    fix-pr.md
    ports-release.md
    git-cleanup.md
```

Claude Code plugin commands are namespaced as `/<plugin>:<filename>`. That is why today’s commands are `/automatis:fix-pr`. Plugin `commands/` cannot produce `/automatis-fix-pr`. Product-repo Claude files at `.claude/commands/automatis-fix-pr.md` can.

`git-cleanup` exists on disk and is missing from `README.md`. The README is updated as part of this work.

## Requirements

1. Same procedure text for every tool. Native invocation per tool is acceptable only where a tool cannot register `/automatis-<name>` (Codex: `$automatis-<name>`).
2. Commands are vendored into each product repo so cloning is enough. No personal marketplace install is required to use them in a product repo.
3. This plugin repo remains the source of truth. Product repos pick up updates by re-running a vendor script and committing the copies.
4. The Claude marketplace stays as the source package (`automatis@automatis-tools`). It is not how product-repo users get `/automatis-fix-pr`.
5. Authors edit one `SKILL.md` per command. They do not hand-edit generated Claude command markdown.

## Architecture

Canonical files are Agent Skills inside the existing plugin directory so `/plugin install` still copies them (Claude installs the plugin folder only).

```
automatis/skills/automatis-<name>/SKILL.md
        │
        ├── vendor script ──► <product>/.agents/skills/automatis-<name>/
        │                      (Codex, Grok, Gemini, Kimi)
        │
        └── vendor script ──► <product>/.claude/commands/automatis-<name>.md
                               (Claude Code project slash command /automatis-<name>)
```

`.agents/skills/` is the shared Agent Skills directory those four tools already scan. No `.grok/`, `.codex/`, `.gemini/`, or `.kimi-code/` trees are written. No Gemini `.toml` commands.

This plugin repo does **not** contain `automatis/commands/`. Those files created `/automatis:<name>`.

## Repository layout (this repo)

```
automatis/
  .claude-plugin/plugin.json
  skills/
    automatis-fix-pr/SKILL.md
    automatis-ports-release/SKILL.md
    automatis-git-cleanup/SKILL.md
scripts/
  vendor-automatis-commands
.claude-plugin/marketplace.json
AGENTS.md
CLAUDE.md
README.md
.github/workflows/lint.yml
```

Marketplace `source` stays `./automatis`. Plugin manifest keeps `name: "automatis"`. Update `description` (and README/marketplace blurbs) so they are not Claude-only and they mention `git-cleanup`.

Optional `scripts/`, `references/`, and `assets/` under a skill folder are allowed and copied with the skill.

## Skill format

`automatis/skills/automatis-fix-pr/SKILL.md`:

```markdown
---
name: automatis-fix-pr
description: Fix open review comments on a GitHub PR
argument-hint: "[pr-url | pr-number] [--review=ID] [--severity=high,medium,low,critical]"
allowed-tools: Bash, Read, Edit, Grep, Glob
---

# Fix PR Review Comments
…
```

Rules:

- `name` and `description` are required. `name` equals the folder name.
- Folder and `name` use the `automatis-<command>` pattern (`automatis-fix-pr`, `automatis-ports-release`, `automatis-git-cleanup`).
- `argument-hint` and `allowed-tools` are kept. Claude and Grok honor them; other tools ignore unknown keys.
- Do not set `disable-model-invocation`. Skill-based tools may auto-trigger from `description`.
- Body keeps the current house style: When to Use, Arguments, Procedure (exact bash/Python blocks), Safety Rules, optional Example Session.
- Shell-safety rules stay in `CLAUDE.md` / `AGENTS.md`, not copied into every skill.
- Arguments and examples in the body use `/automatis-fix-pr` (and `$automatis-fix-pr` once in Arguments so Codex users see the native trigger). No `{{placeholders}}`. No rewrite pass on generate.

Existing `automatis/commands/*.md` bodies are moved into these skills, not rewritten. Slash examples that say `/automatis:fix-pr` are changed to `/automatis-fix-pr` as part of that move.

### Generated Claude command (product repo only)

`.claude/commands/automatis-fix-pr.md`:

```markdown
---
description: <skill description>
argument-hint: <if present>
allowed-tools: <if present>
---
<skill body unchanged>
```

`name` is omitted (Claude commands use the filename). Filename is `automatis-<name>.md`, which is the slash command `/automatis-<name>`.

## Vendor script

Path: `scripts/vendor-automatis-commands`. Python 3, standard library only, executable shebang.

```bash
./scripts/vendor-automatis-commands <product-repo>
./scripts/vendor-automatis-commands <product-repo> --dry-run
./scripts/vendor-automatis-commands <product-repo> --prune
./scripts/vendor-automatis-commands --check
```

No target path prints usage and exits non-zero. There is no in-plugin generate mode.

### Writes into `<product-repo>`

| Path | Content |
|------|---------|
| `.agents/skills/automatis-<name>/` | Full skill directory (SKILL.md plus any `scripts/`, `references/`, `assets/`) |
| `.claude/commands/automatis-<name>.md` | Generated command markdown as above |
| `.automatis-commands.json` | Manifest of names this script manages |

Manifest shape:

```json
{
  "source": "automatis-tools/automatis-skills",
  "skills": [
    "automatis-fix-pr",
    "automatis-ports-release",
    "automatis-git-cleanup"
  ]
}
```

### Behavior

- Discover skills as immediate child directories of `automatis/skills/` that contain `SKILL.md`.
- Validate every skill before writing anything. Then copy/generate. Do not leave a half-applied vendor if validation fails.
- Re-run overwrites those named folders and command files in place. That is how product repos take updates.
- Names not in this repo’s skill list are never overwritten or deleted, except `--prune`.
- `--prune` deletes files/directories listed in the product-repo manifest that are no longer shipped here, then rewrites the manifest to the current list.
- `--dry-run` prints the planned copies, overwrites, and prunes; writes nothing.
- `--check` validates this repo’s skills (see Verification). Writes nothing.

### Safety

- Refuse if the target is missing, not a directory, or resolves to this plugin repository.
- Do not execute skill bodies. Copy and generate files only.
- Parse frontmatter without PyYAML or `jq`. Support the simple `key: value` lines this repo uses (quoted or unquoted strings). Fail if `---` fences are missing, if `name`/`description` are missing, or if `name` does not match the folder.
- Create parent directories (`.agents/skills`, `.claude/commands`) as needed.

## Marketplace and breaking change

The marketplace catalog stays. Plugin install still works as `automatis@automatis-tools`. The plugin ships `skills/` only.

Product-repo users get `/automatis-fix-pr` from vendored `.claude/commands/`, not from plugin `commands/`.

Optional `/plugin install` without vendoring is not the supported way to get the hyphen slash command on Claude: plugin components are namespaced as `/automatis:…`. Document vendor-into-the-product-repo as the Claude path. Do not ship a second colon command to “cover” marketplace users.

**Breaking:** `/automatis:fix-pr`, `/automatis:ports-release`, and `/automatis:git-cleanup` are removed. README, `CLAUDE.md`, `AGENTS.md`, and skill bodies use `/automatis-…` (and `$automatis-…` for Codex).

## Documentation in this repo

- `README.md` — multi-harness overview, invocation table (including Codex `$`), vendor-script usage, current command list including `git-cleanup`.
- `CLAUDE.md` — authoring is `automatis/skills/automatis-<name>/SKILL.md`; adding a command no longer means creating `commands/<name>.md`; marketplace notes remain; shell-safety rules remain; verification includes `--check` and JSON parse.
- `AGENTS.md` — short portable copy of the same authoring and vendor conventions so Codex/Grok sessions on this repo see them. Do not fork house style into two conflicting documents: `AGENTS.md` can point at `CLAUDE.md` for shell-safety detail and restate the layout, invocation table, and vendor CLI.

Do not inject `AGENTS.md` / `CLAUDE.md` snippets into product repos.

## Adding a command

1. Create `automatis/skills/automatis-<name>/SKILL.md` with `name: automatis-<name>`.
2. Run `./scripts/vendor-automatis-commands --check`.
3. Commit in this repo.
4. In each product repo, run `./scripts/vendor-automatis-commands <product-repo>` from this checkout and commit the vendored files there.

Deleting a command: remove the skill folder here, then run the vendor script with `--prune` in each product repo.

## Verification

`--check` fails unless:

- every `automatis/skills/*/SKILL.md` has `name` and `description`
- `name` matches the directory
- `name` starts with `automatis-`
- marketplace.json and `automatis/.claude-plugin/plugin.json` parse as JSON
- marketplace plugin `source` is `./automatis` and that directory exists
- `automatis/commands/` does not exist (legacy layout must be gone)

CI (`.github/workflows/lint.yml`) runs the same checks as `--check`, not only JSON parse.

This repository has no local pre-push hook today. Track `.githooks/pre-push` that runs `./scripts/vendor-automatis-commands --check`. Document `git config core.hooksPath .githooks` in `CLAUDE.md` and `AGENTS.md`. CI runs the same `--check` so a missing local hook still fails the PR. Do not use `--no-verify`.

Manual check after implementation: vendor into a throwaway directory, confirm `.agents/skills/automatis-fix-pr/SKILL.md` and `.claude/commands/automatis-fix-pr.md` exist, and confirm `--check` fails if `name` is wrong.

## Implementation scope

This spec is implemented in **this plugin repository**. Deliverables: skills, vendor script, docs, CI `--check`, `.githooks/pre-push`.

Running the vendor script against Automatis product repos is how those repos consume the work. This spec does not name those repos and does not require changing them in the same change set.

## Out of scope

- Gemini `.toml` under `.gemini/commands/`
- Extra copies under `.grok/`, `.codex/`, or `.kimi-code/`
- Git submodules
- Renaming this git repository
- User-global installs (`~/.claude/commands`, `~/.codex/skills`, …) as the distribution model
- Keeping `/automatis:<name>` as a compatibility alias
- Making Codex accept `/automatis-<name>`

## Key decisions

1. **Agent Skills are canonical.** Four of five tools already load `SKILL.md`. Claude gets a generated project command from the same file.
2. **Hyphen prefix, not colon.** `/automatis-fix-pr` is valid as a skill `name`, a Claude project command filename, and a Grok/Gemini/Kimi slash command. `/automatis:fix-pr` is a Claude plugin-namespace artifact and is retired.
3. **Vendor into product repos.** Distribution is clone-the-product-repo, not a personal plugin install. This repo stays the authoring and marketplace source.
4. **Two destinations per product repo.** `.agents/skills/` covers Codex, Grok, Gemini, and Kimi. `.claude/commands/` covers Claude Code. No per-harness extra trees.
5. **Codex uses `$automatis-<name>`.** Custom `/` commands are not available there.
6. **No generated `automatis/commands/`.** Regenerating plugin commands would restore the colon slash form.
7. **Marketplace remains, skills-only plugin.** `/plugin install automatis@automatis-tools` still copies skills. Supported Claude UX in product repos is the vendored `/automatis-<name>` command.

## Migration of existing commands

| Today | After |
|-------|--------|
| `automatis/commands/fix-pr.md` → `/automatis:fix-pr` | `automatis/skills/automatis-fix-pr/SKILL.md`; vendored `/automatis-fix-pr` |
| `automatis/commands/ports-release.md` → `/automatis:ports-release` | `automatis/skills/automatis-ports-release/SKILL.md`; vendored `/automatis-ports-release` |
| `automatis/commands/git-cleanup.md` → `/automatis:git-cleanup` | `automatis/skills/automatis-git-cleanup/SKILL.md`; vendored `/automatis-git-cleanup` |

`automatis/commands/` is deleted once the skills exist.

## Error handling

| Situation | Result |
|-----------|--------|
| Skill missing `name` or `description` | `--check` and vendor abort; no partial write |
| `name` ≠ folder | abort |
| Target missing / not a directory / is this repo | abort |
| `--prune` with no manifest in the product repo | treat managed set as empty; copy current skills; write a new manifest |
| Extra files under `.agents/skills/` or `.claude/commands/` | left untouched unless they match a managed name |
| Frontmatter uses unsupported YAML (nested maps, multiline `|` blocks) | abort with a parse error; this repo’s skills stay on single-line keys |
