# AGENTS.md

This repository authors Automatis team commands as Agent Skills and vendors them into product repos.

Layout, invocation, vendor CLI, and how to add a command: see [CLAUDE.md](CLAUDE.md) (same rules for every harness).

Quick facts:

- Author `automatis/skills/automatis-<name>/SKILL.md` only. Do not add `automatis/commands/`.
- Invoke `/automatis-<name>` (Codex: `$automatis-<name>`).
- From this checkout: `./scripts/vendor-automatis-commands /path/to/product-repo`
- Validate: `./scripts/vendor-automatis-commands --check` and `python3 -m unittest discover -s tests -v`
- Enable hooks: `git config core.hooksPath .githooks`

Shell-safety rules for bash/Python blocks inside skills are in CLAUDE.md → **Shell Safety**. Copy those blocks exactly; never rewrite `jq` with `!=` from memory.
