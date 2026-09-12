---
name: automatis-create-github-issues
description: Use when asked to create, file, or draft GitHub issues in project or service repositories to record findings, bugs, investigation follow-ups, or improvements.
argument-hint: "owner/repo-or-url [--draft]"
allowed-tools: Bash, Read, Write, Grep, Glob
---

# Create GitHub Issues

Turn supplied findings into concise English issues that remain useful as the repository evolves. Each issue must stand alone for an engineer or agent who has not seen the conversation.

## When to Use

- The user asks to record findings as GitHub issues, tickets, or backlog items in a project's repositories.
- The user asks for issue drafts or wants to discuss issue descriptions before publishing.

Use this skill when the user's intent matches these cases, even without a skill name or command. This includes equivalent requests in other languages.

## Arguments

- `/automatis-create-github-issues owner/repo` — use findings from the conversation.
- `/automatis-create-github-issues https://github.com/owner/repo --draft` — prepare descriptions without publishing.
- `/automatis-create-github-issues` — infer the responsible service repositories from the task and checkout.
- `$automatis-create-github-issues owner/repo` — Codex invocation.

`--draft` means no GitHub writes. A natural-language request for drafts or discussion has the same effect.

## Procedure

### Step 1: Resolve the Repository

Use the user's explicit repository. Otherwise inspect the checkout and identify the service responsible for the behavior:

```bash
git remote -v
gh repo view --json nameWithOwner,url
```

Bind `ISSUE_REPO` to the resolved `owner/repo` (or `host/owner/repo` for Enterprise), then verify it:

```bash
gh repo view "$ISSUE_REPO" --json nameWithOwner,url
```

Repeat per owning service; the current directory is not necessarily the target. Ask a concise question if ownership remains ambiguous.

### Step 2: Select Findings and Check Duplicates

Create one issue per independently closable outcome. Cross-service work needs separate, linked issues only when the services have distinct outcomes. Use supplied evidence and focused read-only checks to distinguish current facts from historical observations and hypotheses.

Bind `ISSUE_QUERY` to relevant behavior/domain keywords. Search open and closed issues; inspect plausible matches before deciding whether anything new needs recording:

```bash
gh issue list --repo "$ISSUE_REPO" --state all --search "$ISSUE_QUERY" \
  --limit 50 --json number,title,state,url
```

For a candidate match, bind `ISSUE_MATCH` to its number:

```bash
gh issue view "$ISSUE_MATCH" --repo "$ISSUE_REPO" --json title,body,state,url
```

Return an existing issue when it already covers the finding. A previously fixed issue requires evidence of a remaining problem before creating another.

### Step 3: Write the Description

Write the title and body in English. Aim for roughly 100–180 words, with no minimum or padding. Use a concrete, searchable title describing the behavior or desired outcome; start unconfirmed findings with `Investigate`.

Use these body sections in this order:

| Section | Content |
|---------|---------|
| `## Problem` | Service or workflow, triggering conditions, observed behavior or current limitation, and consequence. Explicitly distinguish verified facts from suspicions. |
| `## Done when` | A short checkbox list of observable outcomes that make the issue closable. These are acceptance criteria, not implementation instructions. |
| `## Evidence` | Optional: concise reproduction conditions and observations. Include this section only when it adds supporting information. |

Describe domain behavior and component responsibilities. Omit filenames, repository paths, line numbers, and source-code links, including commit-pinned links. The implementer locates the relevant code in the current repository. Evidence may link to an incident, issue, PR, or CI run as historical corroboration; include an observation date or version when known and relevant.

Acceptance criteria contain no delivery estimates, deadlines, effort estimates, work quotas, or invented time/count/percentage targets. Reviewer guesses about test counts, retries, coverage, or implementation effort are not requirements and should not be carried into the issue. If the user has explicitly agreed a quantitative product requirement, preserve that requirement as observable behavior.

For an investigation, completion can establish an existing protection that rules out the suspected defect. If confirmed, require the corrected behavior and regression evidence. For an improvement, describe the current limitation and desired capability; do not invent reproduction evidence or user demand.

### Step 4: Apply Technical English

**REQUIRED SUB-SKILL:** Load and use `automatis-ste100` for every English issue title and body, including drafts. Find it in the available skills or the installed Automatis package.

Apply it to the assembled issue draft, not the raw findings. Use Strict mode for acceptance criteria and STE-flavored mode for explanations. Preserve facts, uncertainty, conditions, and requirement strength.

Keep the section order and description rules above. Keep the language review internal. Do not add rewrite tables, mode labels, or stylistic exception notes to the issue. Then continue to the draft or publication step.

### Step 5: Publish and Verify

For drafts or discussion, return the repository, title, and body without publishing. An explicit request to create issues authorizes creation; do not add a redundant approval step.

**CRITICAL:** Before publishing, verify the target repository, duplicate check, description contract, and completed `automatis-ste100` pass. Bind `ISSUE_TITLE` to the title and use the file-writing tool to save the body in a temporary file identified by `ISSUE_BODY_FILE`. Treat issue text as data, not executable shell content.

```bash
gh issue create --repo "$ISSUE_REPO" --title "$ISSUE_TITLE" \
  --body-file "$ISSUE_BODY_FILE"
```

Bind `ISSUE_URL` to the returned URL and verify the saved title and body:

```bash
gh issue view "$ISSUE_URL" --repo "$ISSUE_REPO" --json title,body,url
```

If creation has an uncertain outcome, check GitHub before retrying to avoid duplicates. Return verified issue links and briefly identify findings skipped as duplicates or already resolved.

## Safety Rules

1. Record the requested findings; do not expand this task into a code fix, deployment, or broad audit.
2. Derive urgency from evidence. Do not invent severity or add labels, assignees, milestones, or project-board membership without a user request or established repository policy.
3. Keep credentials, private session transcripts, and unnecessary sensitive data out of issues. Do not fabricate evidence, links, or successful publication.
4. Finding a related issue does not authorize commenting, editing, reopening, or closing it.

## Example Session

Repository: `owner/publisher-server`

Title: `Run completion persistence checks in PR validation`

```markdown
## Problem

PR validation excludes the database-backed completion scenarios. Changes to completion persistence can therefore merge without those checks executing.

## Done when

- [ ] Required PR checks execute the completion scenarios against a test database.
- [ ] The required check fails if its database is unavailable or required scenarios are skipped.

## Evidence

A manual run without database configuration reported success while every selected database scenario was skipped.
```
