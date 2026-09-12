# Automatis Skills

Agent skills for Codex, Claude Code, Gemini CLI, and Grok. Install the Automatis plugin or extension once; each tool manages later updates. Agents can also select a relevant skill from its description without an explicit command.

## Install once

Adding a marketplace makes its plugins available. Install **automatis** from it to receive the skills. If the marketplace is already configured, skip its add command.

### Codex

```bash
codex plugin marketplace add automatis-tools/automatis-skills
codex plugin add automatis@automatis-tools
```

Codex refreshes Git marketplaces at startup and refreshes their installed plugins. Use the GitHub source above so this installation follows the repository.

### Claude Code

```bash
claude plugin marketplace add automatis-tools/automatis-skills
claude plugin install automatis@automatis-tools --scope user
```

In Claude Code, open `/plugin` → **Marketplaces** → **automatis-tools** → **Enable auto-update**. Third-party marketplace updates are disabled by default. Claude checks in the background after startup; open a new session after an update to use the new version. [Claude update behavior](https://code.claude.com/docs/en/discover-plugins#configure-auto-updates).

### Gemini CLI

```bash
gemini extensions install https://github.com/automatis-tools/automatis-skills --auto-update
```

Install from the repository URL without `--ref`. Gemini downloads the latest GitHub release package, which contains both skills and slash-command aliases. Auto-update is enabled by the install flag. Gemini can request consent when an update changes the extension's permissions or advertised components. [Gemini releases and updates](https://geminicli.com/docs/extensions/releasing/).

### Grok

```bash
grok plugin marketplace add automatis-tools/automatis-skills
grok plugin install automatis --trust
grok plugin enable automatis
```

Grok refreshes marketplaces and plugins at session startup by default. Reload the Plugins tab or start a new session after installation.

## Use

| Tool | Example |
|------|---------|
| Codex | `$automatis-ste100 docs/setup.md` |
| Claude Code | `/automatis:automatis-ste100 docs/setup.md` |
| Gemini CLI | `/automatis-ste100 docs/setup.md` |
| Grok | `/automatis-ste100 docs/setup.md` |

Claude prefixes native plugin skills with the plugin name. Grok also offers a qualified name when another skill has the same name. Gemini's slash aliases activate the corresponding skill; skill activation can request consent. Each host can select skills implicitly from their descriptions under its own settings.

| Skill | Purpose |
|-------|---------|
| `automatis-fix-pr` | Fix GitHub PR review comments |
| `automatis-ports-release` | Release port conflicts on macOS |
| `automatis-git-cleanup` | Clean up local Git branches |
| `automatis-ste100` | Clarify English documentation, prompts, and agent handoffs while preserving meaning |

Examples below use the canonical command name; use the Claude prefix from the table when invoking its native plugin.

```text
/automatis-fix-pr https://github.com/owner/repo/pull/123
/automatis-ports-release 8000 8001
/automatis-git-cleanup --dry-run
/automatis-ste100 docs/setup.md --mode=ste-flavored --show-diff
```

## Migrate from the previous README

The previous installation copied files into `~/.agents/skills` and `~/.claude/commands`. Those copies do not update and can take precedence over native plugin skills. Following that README did not enable plugin updates.

After installing and verifying Automatis in your tools, run this **once** from this checkout:

```bash
./scripts/migrate-automatis-install "$HOME" --dry-run
./scripts/migrate-automatis-install "$HOME"
```

The migration moves only files listed in `~/.automatis-commands.json` to `~/.automatis-migration-backups/<timestamp>/`, including any local edits. It preserves unrelated skills. Open new tool sessions after migration. If a product repo contains older copies that you want to replace with the user-level plugins, run the migration against that repo too; repository skills can take precedence over user plugins.

## How releases reach your tools

A release contains the same canonical skills for all four tools. Codex, Claude, and Grok follow the Git marketplace; Gemini follows the latest published GitHub release. Updates arrive when the host checks for them, rather than immediately when a tag is pushed. Active sessions can retain a loaded skill until a new session begins.

Each release bumps the package versions in the marketplace branch and publishes a matching tag. Claude uses the plugin version to identify new cached packages. Gemini needs the generated `automatis.tar.gz` release asset because its archive requires `skills/` at the root. Do not pin an installation to a commit or release tag if you want it to advance automatically. No recurring vendor command or separate updater is needed.

## Product-repository snapshots (optional)

For a deliberately pinned copy shared through a product repository:

```bash
./scripts/vendor-automatis-commands /path/to/product-repo
./scripts/vendor-automatis-commands /path/to/product-repo --dry-run
./scripts/vendor-automatis-commands /path/to/product-repo --prune
```

Commit the generated `.agents/skills/`, `.claude/commands/`, and `.automatis-commands.json`. These snapshots are updated manually and can override native plugin skills. They are separate from the automatic installation above.

## Contributing and releasing

1. Author `automatis/skills/automatis-<name>/SKILL.md` with matching frontmatter `name`. Keep a description that lets agents recognize when to use it.
2. Run the checks below.
3. For a release, set the same version in `automatis/.claude-plugin/plugin.json`, `automatis/.codex-plugin/plugin.json`, and `gemini-extension.json`; update `.claude-plugin/marketplace.json` metadata too.
4. Merge the reviewed changes into `main`. Tag that commit with the exact version, such as `1.1.0`, and push the tag. The release workflow validates the version and publishes the Gemini archive with the GitHub release. Do not reuse a released version.

```bash
./scripts/vendor-automatis-commands --check
./scripts/build-automatis-release --check
python3 -m unittest discover -s tests -v
```

To inspect a package before release, run `./scripts/build-automatis-release --tag 1.1.0 --output dist`. The builder generates the Gemini skill tree and command aliases from canonical sources; do not author duplicate files at the repository root.

See [CLAUDE.md](CLAUDE.md) and [AGENTS.md](AGENTS.md) for house style, shell safety, and Git hooks.

## License

MIT. The STE skill retains the upstream attribution and license in its [SKILL.md](automatis/skills/automatis-ste100/SKILL.md).
