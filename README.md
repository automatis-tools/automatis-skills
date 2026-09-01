# Automatis Skills

Public commands for Claude Code, Grok, Codex, Gemini, and Kimi.

| Tool | Run |
|------|-----|
| Claude Code, Grok, Gemini, Kimi | `/automatis-fix-pr` |
| Codex | `$automatis-fix-pr` |
| Kimi fallback | `/skill:automatis-fix-pr` |

The old colon form `/automatis:fix-pr` is gone.

## Install (your machine, every repo)

```bash
git clone https://github.com/automatis-tools/automatis-skills.git
cd automatis-skills
./scripts/vendor-automatis-commands "$HOME"
```

That writes:

- `~/.agents/skills/automatis-*/` — Grok, Codex, Gemini, Kimi
- `~/.claude/commands/automatis-*.md` — Claude Code (`/automatis-fix-pr`)
- `~/.automatis-commands.json` — names this script manages

Open a new session and type `/` (or `$` in Codex). To update: `git pull` in the clone, then run the vendor command again.

Do not use `/plugin install automatis@automatis-tools` if you want `/automatis-fix-pr`. Claude plugin commands are namespaced as `/automatis:…`.

## Install into a product repo (optional)

If the team should get the commands by cloning the product repo, vendor there instead of `$HOME`:

```bash
./scripts/vendor-automatis-commands /path/to/product-repo
./scripts/vendor-automatis-commands /path/to/product-repo --dry-run
./scripts/vendor-automatis-commands /path/to/product-repo --prune
```

Commit the generated `.agents/skills/`, `.claude/commands/`, and `.automatis-commands.json` in that repo.

## Commands

| Command | Description |
|---------|-------------|
| `/automatis-fix-pr` | Fix GitHub PR review comments |
| `/automatis-ports-release` | Release port conflicts on macOS |
| `/automatis-git-cleanup` | Clean up local git branches |

### /automatis-fix-pr

```bash
/automatis-fix-pr https://github.com/owner/repo/pull/123
/automatis-fix-pr 123
/automatis-fix-pr
```

### /automatis-ports-release

```bash
/automatis-ports-release 8000
/automatis-ports-release 8000 8001
/automatis-ports-release
```

### /automatis-git-cleanup

```bash
/automatis-git-cleanup
/automatis-git-cleanup --dry-run
/automatis-git-cleanup --no-pr
```

## Contributing

1. Add `automatis/skills/automatis-<name>/SKILL.md` with `name: automatis-<name>`.
2. Run `./scripts/vendor-automatis-commands --check`.
3. Commit here, then vendor into `$HOME` or each product repo.

See [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md) for house style, shell-safety, and git hooks.

## License

MIT
