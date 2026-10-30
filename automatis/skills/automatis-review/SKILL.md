---
name: automatis-review
description: Use only when the user explicitly invokes automatis-review by name or command. Generic requests for review, fixes, or simpler code do not activate this skill.
argument-hint: "[uncommitted | staged | branch | commit | PR URL | paths]"
allowed-tools: Bash, Read, Grep, Glob
disable-model-invocation: true
license: MIT
---

# Review a Change

Review one change for concrete defects and unnecessary complexity. This is a one-shot report, not a session mode. Reply in the conversation's language.

## When to Use

- The user explicitly requests `automatis-review` for a change or PR.
- The user explicitly requests this skill's assessment of unnecessary complexity.

## Arguments

- `/automatis-review staged` — review staged changes.
- `/automatis-review <branch | commit | PR URL | paths>` — review the named target.
- `$automatis-review` — Codex; inspect pending changes.
- Native Claude plugin: `/automatis:automatis-review`.

## Procedure

### Step 1: Bind the Scope

Use the named target. With no target, start with:

```bash
git status --short
git diff
git diff --cached
git ls-files --others --exclude-standard
```

Include relevant untracked source files. With no pending changes, report that; do not silently substitute a commit or whole-repo audit. For a branch or PR, establish its actual base and head before reading the diff.

### Step 2: Trace the Change

Read repository instructions, affected callers, callees, contracts, and tests. Follow changed data through the real path: a defect may be in an unchanged caller. Inspect registries, config, dynamic imports, fixtures, and exports before calling code unused.

Use existing review evidence for the same revision. Check new evidence or gaps instead of repeating an equivalent review; this skill adds no mandatory review round or subagent workflow.

### Step 3: Assess the Evidence

Prioritize correctness, security and data loss, expected load, test gaps, performance, then simplicity.

- Each finding needs a reachable input or situation, affected code, and concrete consequence. Distinguish reproduced behavior from conclusions based on reading code.
- Judge load against the project's documentation and deployment. State assumptions that affect findings.
- Suggest reuse by path. Prefer established project patterns, then standard library or platform features. Require a concrete need for new abstractions or dependencies.
- Treat fewer lines as a possible result, not a target. Preserve behavior, compatibility, useful interfaces, validation, error handling, security, and accessibility.
- Describe a test gap through the regression it would catch. Preserve required TDD and verification; a small self-check does not replace required coverage.
- Raise a documented shortcut when requirements exceed its limit or it causes a concrete defect.

### Step 4: Report

Lead with the verdict. Give numbered findings in severity order, normally at most five; include every critical issue. Each compact paragraph contains `path:line`, trigger, consequence, and the smallest complete remedy. Separate optional simplifications from defects. Omit style preferences, speculative scale concerns, and invented line-count savings.

With no actionable findings, state the checked scope. End with relevant checks and material gaps. Keep the report brief unless the user requests detail.

## Safety Rules

1. Inspect and report only. Do not edit code, remove files, install dependencies, alter Git state, post findings, or change settings.
2. A remedy is a proposal. It does not authorize execution, publishing, or merging.
3. Run checks only when safe in the current environment. Report what actually ran. Existing user and repository instructions remain authoritative.

Adapted from [Ponytail](https://github.com/DietrichGebert/ponytail/blob/96608e078b2d5ea607c5c3b8b5a54d1c1fba6846/skills/ponytail-review/SKILL.md), copyright 2026 DietrichGebert. See [LICENSE](LICENSE).
