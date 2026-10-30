---
name: automatis-audit
description: Use only when the user explicitly invokes automatis-audit by name or command for a repository, package, or directory. Ordinary coding and generic review requests do not activate this skill.
argument-hint: "[repository | package | directory]"
allowed-tools: Read, Grep, Glob
disable-model-invocation: true
license: MIT
---

# Audit a Codebase

Produce one evidence-based report on defects and unnecessary complexity in the requested codebase. This does not enable a persistent mode. Reply in the conversation's language.

When another workflow owns this audit, preserve its target, required checks, and report format. Audit only the assigned scope; do not turn a change review into a repository audit or add a review round. The read-only rules apply to this audit phase; they do not prohibit later fixes the user authorizes.

## When to Use

- The user explicitly requests `automatis-audit` for a repository or subsystem.
- The user explicitly asks this skill to find concrete maintenance risks or unnecessary complexity.

## Arguments

- `/automatis-audit` — audit the current repository.
- `/automatis-audit src/billing` — audit the named subsystem and its connected contracts.
- `$automatis-audit` — Codex invocation.
- Native Claude plugin: `/automatis:automatis-audit`.

## Procedure

### Step 1: Map the Scope

Use the named target; otherwise use the current repository. Start with:

```bash
git rev-parse --show-toplevel
git status --short
rg --files -g '!node_modules' -g '!vendor' -g '!dist' -g '!build'
```

Read repository instructions, README, dependency and deployment configuration, entry points, and tests. Establish intended behavior and expected load. If Git is unavailable, inspect the named directory and say so.

### Step 2: Trace the Important Flows

Follow input, state changes, and output through auth, money, data writes, jobs, and shared resources. For a large repository, prioritize flows where defects have the highest cost; state what was not inspected. In a subsystem audit, read connected callers and contracts without expanding into unrelated cleanup.

Inspect config, registries, dynamic imports, fixtures, exports, and string references before declaring code unused. Reuse evidence only when its revision, scope, checks, and reviewer independence meet the owning workflow's requirements. Self-review does not replace a required independent check.

### Step 3: Rank Concrete Findings

Prioritize correctness, security and data loss, expected load, test gaps, performance, then simplicity.

- A finding needs a reachable situation, source location, and concrete consequence. Separate reproduced behavior from reasoning based on code.
- Judge scaling needs against actual deployment and requirements. A hypothetical future load does not justify a new architecture.
- Name reusable helpers or components by path. Suggest the smallest complete remedy that fits project conventions.
- Preserve behavior, compatibility, useful interfaces, validation, error handling, security, and accessibility. Fewer lines alone do not justify a change.
- Identify tests by the failure they would catch. Keep required TDD and verification; do not substitute token tests for required coverage.
- A documented shortcut is a tradeoff. Report it when requirements exceed its limit or it causes a concrete defect.

### Step 4: Deliver a Brief

Use the owning workflow's report format when specified, preserving all required verdicts and verification gaps. Otherwise, lead with the most important conclusion and what to address first. Normally give at most five numbered findings; include every critical issue. Each compact paragraph contains `path:line`, trigger, consequence, and the smallest complete remedy. Separate optional simplifications from defects. Omit style preferences and invented savings.

In a standalone report, end with inspected scope, checks actually run, and material gaps. A partial audit stays partial. With no actionable findings, say none were found in the inspected scope; do not certify the whole system.

## Safety Rules

1. This is an inspection and report. Do not edit code, remove files, install dependencies, alter Git state, post findings, or change settings.
2. Recommendations do not authorize implementation, publishing, or merging.
3. Run checks only when safe in the current environment. User and repository instructions remain authoritative.
4. Shell inspection uses normal host permissions. The tool metadata does not enforce a read-only sandbox.

Adapted from [Ponytail](https://github.com/DietrichGebert/ponytail/blob/96608e078b2d5ea607c5c3b8b5a54d1c1fba6846/skills/ponytail-audit/SKILL.md), copyright 2026 DietrichGebert. See [LICENSE](LICENSE).
