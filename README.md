# Automatis Skills

Engineering skills for Codex, Claude Code, Antigravity CLI, and Grok. One **automatis** plugin distributes the canonical skills from [`automatis/skills/`](automatis/skills/).

## Skills

| Skill | Purpose |
|-------|---------|
| [`automatis-create-github-issues`](automatis/skills/automatis-create-github-issues/SKILL.md) | Create GitHub issues from findings or prepare drafts |
| [`automatis-fix-pr`](automatis/skills/automatis-fix-pr/SKILL.md) | Address GitHub PR review comments |
| [`automatis-ports-release`](automatis/skills/automatis-ports-release/SKILL.md) | Identify and release port conflicts on macOS |
| [`automatis-git-cleanup`](automatis/skills/automatis-git-cleanup/SKILL.md) | Clean up local branches, including squash-merged work |
| [`automatis-ste100`](automatis/skills/automatis-ste100/SKILL.md) | Clarify technical English while preserving meaning |

GitHub workflows require Git, `python3`, and authenticated `gh`. Port release requires macOS and `lsof`.

## Install

Use your tool's native manager. Adding the marketplace alone does not install Automatis. Skip the marketplace add command if it is already configured.

### Codex

```bash
codex plugin marketplace add automatis-tools/automatis-skills
codex plugin add automatis@automatis-tools
```

To refresh the Git marketplace, run `codex plugin marketplace upgrade automatis-tools`. See the [official OpenAI documentation](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli).

### Claude Code

```bash
claude plugin marketplace add automatis-tools/automatis-skills
claude plugin install automatis@automatis-tools --scope user
```

Enable auto-update in `/plugin` → **Marketplaces** → **automatis-tools**. [Third-party updates are off by default](https://code.claude.com/docs/en/discover-plugins).

### Antigravity CLI

```bash
git clone https://github.com/automatis-tools/automatis-skills.git
agy plugin install ./automatis-skills/automatis
```

Skip cloning if you already have a checkout. Install its `automatis/` directory as a [local Antigravity plugin](https://www.antigravity.google/docs/plugins?tab=cli). Custom marketplace auto-updates are not available in `agy 1.3.3`.

### Grok

```bash
grok plugin marketplace add automatis-tools/automatis-skills
grok plugin install automatis --trust
grok plugin enable automatis
```

[Grok checks for updates at session startup](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/09-plugins.md) unless configuration or managed policy disables them.

Start a new session after installation or updates to load the current skills.

## Use

| Tool | Example |
|------|---------|
| Codex | `$automatis-ste100 docs/setup.md` |
| Claude Code | `/automatis:automatis-ste100 docs/setup.md` |
| Antigravity CLI / Grok | `/automatis-ste100 docs/setup.md` |

Replace `automatis-ste100` with the skill you need. Follow its linked instructions for arguments and options. Agents can also select skills from their descriptions.

## Existing copies

Older copies in `.agents/skills/` or `.claude/commands/` can override native plugins and require manual updates. After verifying the native installation, preview and archive manifest-owned copies from an Automatis checkout:

```bash
./scripts/migrate-automatis-install "$HOME" --dry-run
./scripts/migrate-automatis-install "$HOME"
```

Use a product repository path instead of `"$HOME"` to migrate its copies. The script preserves local edits in `.automatis-migration-backups/` and leaves unrelated skills in place. Without `.automatis-commands.json`, it does nothing.

## Contributing

Author `automatis/skills/automatis-<name>/SKILL.md` with matching frontmatter `name`. Use Python 3.11 or later for repository checks:

```bash
./scripts/vendor-automatis-commands --check
./scripts/build-automatis-release --check
python3 -m unittest discover -s tests -v
```

Enable tracked hooks with `git config core.hooksPath .githooks`. Submit changes as a draft PR. The maintainer controls review readiness and merging.

See [CLAUDE.md](CLAUDE.md) for skill structure, shell safety, release packaging, and optional product snapshots. The same rules apply to every tool. [AGENTS.md](AGENTS.md) summarizes agent instructions.

## License

MIT. The STE skill retains its upstream attribution and license in [SKILL.md](automatis/skills/automatis-ste100/SKILL.md).
