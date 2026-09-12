# Native Automatis Updates Implementation Plan

> **For agentic workers:** Use the linked specification and execute the independent packaging and migration tasks alongside the manifest and documentation work. Review the integrated result before publication.

**Goal:** Deliver new Automatis skills through native automatic updates in Codex, Claude Code, Gemini CLI, and Grok.

**Architecture:** Retain one canonical skill tree. Add Codex metadata, generate a Gemini release archive, and publish versioned releases. Retire stale copied installations with a reversible migration command.

**Tech Stack:** Python standard library, JSON/TOML metadata, GitHub Actions, native host CLIs.

**Spec:** `docs/superpowers/specs/2026-09-12-native-auto-updates-design.md`

## Global Constraints

- Author skills only under `automatis/skills/automatis-<name>/SKILL.md`.
- No background updater; no Kimi support in the primary installation documentation.
- Preserve unrelated local files and make legacy migration reversible.
- No generated source duplication; build release assets in a temporary/output directory.
- Keep versions and release tags identical; first new version is `1.1.0`.

## Tasks

- [ ] Add Codex marketplace/plugin metadata and the Gemini root manifest. Update the existing Claude plugin version and STE skill catalogue entry.
- [ ] Implement `scripts/build-automatis-release --check`, `--output DIR`, and `--tag VERSION`. Validate all manifests, generate `automatis.tar.gz` with root manifest, complete `skills/` trees, and TOML slash aliases. Test version/tag mismatch, preserved resources, parseable wrappers, and excluded source files.
- [ ] Implement `scripts/migrate-automatis-install TARGET [--dry-run]`. Validate ownership and names before moving anything, archive exact managed paths plus manifest, roll back failures, reject symlinked parents, and preserve unrelated paths. Test real filesystem migrations and refusal cases.
- [ ] Add tag-driven release CI and archive verification to PR CI/hooks. Rewrite README and repository guidance around native installs, update behavior, names, releases, and migration; keep product snapshots explicitly optional.
- [ ] Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`, vendor `--check`, release `--check`, native validators, and build/archive smoke checks. Obtain independent code review, address material findings, and prepare a reviewable branch/PR.
- [ ] After publication is authorized and complete, enable native updates in the installed hosts, verify discovery, and archive old user copies. Record any host that cannot be activated locally.
