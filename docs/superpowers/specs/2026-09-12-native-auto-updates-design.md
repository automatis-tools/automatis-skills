# Native Automatis updates

## Requirements

Support Codex, Claude Code, Gemini CLI, and Grok through their native plugin or extension managers. Kimi is excluded at the user's request because it lacks automatic plugin updates. Do not add a background updater or require users to copy files after releases.

Keep one canonical source: `automatis/skills/automatis-<name>/SKILL.md`. Package skills so agents can select them from their descriptions during broader tasks. Include `automatis-ste100` with the upstream attribution and meaning-preservation safeguards.

## Distribution

- Claude and Grok use the existing `.claude-plugin/marketplace.json` and `automatis/.claude-plugin/plugin.json`.
- Codex gets `.agents/plugins/marketplace.json` and `automatis/.codex-plugin/plugin.json`, both pointing at the same `automatis` package.
- Gemini gets a root `gemini-extension.json`. A generated `automatis.tar.gz` release asset contains that manifest, canonical skill directories at `skills/`, and generated `commands/automatis-*.toml` aliases. Generated files are not authored in the source tree.
- All three package manifests use the same stable semantic version. Release tags equal that version. CI validates packages, builds the Gemini archive, and publishes it with the GitHub release.

Codex and Grok refresh Git marketplaces at session startup. Claude requires third-party marketplace auto-update to be enabled; its manifest version must change for a new cached package. Gemini must be installed from the unpinned GitHub repository with `--auto-update`; it uses the latest release asset. These are host-controlled checks, not a promise of instantaneous delivery. Claude/Grok/Codex follow marketplace changes, while Gemini follows published releases.

Native Claude names are `/automatis:automatis-<name>`. Codex uses `$automatis-<name>`, Grok uses `/automatis-<name>` when unambiguous, and Gemini uses generated `/automatis-<name>` aliases. Description-based agent selection remains available; host consent settings still apply.

## Migration

Previously vendored user or project skills can shadow updated native skills. After installing and verifying native packages, archive only the paths listed in a valid `.automatis-commands.json` whose source is `automatis-tools/automatis-skills`. Validate every name. Move the old skill directories, Claude command files, and ownership manifest into a dated backup outside scanned roots. Support a dry run; preserve unrelated files and reject symlinked parent directories. Product-repository snapshots remain an explicit optional distribution method and do not auto-update.

## Verification and rollout

Use unit tests for archive layout/version agreement, resource preservation, Gemini command generation, and safe migration including rollback on a failed move. Run the existing vendor checks and tests, native manifest validators, and inspect the generated archive. Publish only after the branch is reviewed. Then perform the user's one-time native setup and archive old user copies; the user should not need recurring delivery commands.

Sources checked on 2026-09-12: [Codex plugin manager](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/manager.rs), [Claude auto-updates](https://code.claude.com/docs/en/discover-plugins#configure-auto-updates), [Claude version resolution](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels), [Gemini releases](https://geminicli.com/docs/extensions/releasing/), [Gemini skills](https://geminicli.com/docs/cli/using-agent-skills/), and the installed Grok 1.0.30 user guides `08-skills.md` and `09-plugins.md`.
