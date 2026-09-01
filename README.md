# Automatis Tools

Team commands for Claude Code, Grok, Codex, Gemini, and Kimi. Author once as Agent Skills in this repo; vendor a copy into each product repo.

## Invocation

| Tool | Example |
|------|---------|
| Claude Code, Grok, Gemini, Kimi | `/automatis-fix-pr` |
| Codex | `$automatis-fix-pr` |
| Kimi fallback | `/skill:automatis-fix-pr` |

The colon form `/automatis:fix-pr` is retired.

## Vendor into a product repo

From this checkout:

```bash
./scripts/vendor-automatis-commands /path/to/product-repo
./scripts/vendor-automatis-commands /path/to/product-repo --dry-run
./scripts/vendor-automatis-commands /path/to/product-repo --prune
```

That writes:

- `.agents/skills/automatis-<name>/` — Codex, Grok, Gemini, Kimi
- `.claude/commands/automatis-<name>.md` — Claude Code (`/automatis-<name>`)
- `.automatis-commands.json` — names this script manages

Commit those files in the product repo. Re-run the script when a command changes here.

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

## Claude marketplace (source package)

This repo remains a Claude Code marketplace. Installing the plugin copies skills; it does **not** register `/automatis-fix-pr` on Claude (plugin components are colon-namespaced). Product repos should vendor as above.

```bash
/plugin marketplace add automatis-tools/automatis-skills
/plugin install automatis@automatis-tools
```

## Contributing

1. Add `automatis/skills/automatis-<name>/SKILL.md` with `name: automatis-<name>`.
2. Run `./scripts/vendor-automatis-commands --check`.
3. Commit here, then vendor into each product repo.

See [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md) for house style, shell-safety, and git hooks.

## License

MIT
