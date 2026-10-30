# AGENTS.md

This repository authors Automatis Agent Skills and distributes them through native Codex, Claude Code, Antigravity CLI, and Grok plugins. Kimi Code can load the canonical skills directory directly. Product vendoring is an optional snapshot workflow.

Layout, invocation, vendor CLI, and how to add a command: see [CLAUDE.md](CLAUDE.md) (same rules for every harness).

Quick facts:

- Author `automatis/skills/automatis-<name>/SKILL.md` only. Do not add `automatis/commands/`.
- Invoke `/automatis-<name>` (Codex: `$automatis-<name>`; native Claude: `/automatis:automatis-<name>`).
- Kimi Code: `/skill:automatis-<name>`. Review and audit require explicit invocation on every host.
- For optional product snapshots: `./scripts/vendor-automatis-commands /path/to/product-repo`
- Validate: `./scripts/vendor-automatis-commands --check`, `./scripts/build-automatis-release --check`, and `python3 -m unittest discover -s tests -v`
- Validate Antigravity locally: `agy plugin validate ./automatis`. Its native manifest is `automatis/plugin.json`.
- Enable hooks: `git config core.hooksPath .githooks`

Shell-safety rules for bash/Python blocks inside skills are in CLAUDE.md → **Shell Safety**. Copy those blocks exactly; never rewrite `jq` with `!=` from memory.
