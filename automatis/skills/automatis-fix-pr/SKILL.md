---
name: automatis-fix-pr
description: Fix open review comments on a GitHub PR and follow bot re-reviews until approval
argument-hint: "[pr-url | pr-number] [--review=ID] [--severity=high,medium,low,critical]"
allowed-tools: Bash, Read, Edit, Grep, Glob
---

# Fix PR Review Comments

Fetch PR review comments from GitHub, fix the identified issues, reply, and push without further confirmation. When a bot wrote the review, follow its re-reviews and repeat the cycle until the bot approves. Hand over to the user only when you and the bot cannot agree or a stop condition occurs.

## When to Use

- After receiving PR review feedback
- To address automated code review comments (AI reviewers, linters)
- To systematically work through review issues
- To drive a bot-reviewed PR to bot approval

## Shell Safety

See `CLAUDE.md` → **Shell Safety** at the repo root. Copy the bash/Python blocks below exactly — do not rewrite from memory.

## Arguments

Invoke as `/automatis-fix-pr` (Codex: `$automatis-fix-pr`).

The user can provide:
- `/automatis-fix-pr https://github.com/owner/repo/pull/123` - Full PR URL
- `/automatis-fix-pr 123` - PR number (uses current repo)
- `/automatis-fix-pr` - Prompts for PR URL or number

Optional flags in the argument:
- `--review=ID` - Focus on specific review ID
- `--severity=high,medium` - Filter by severity. Accepted: `critical`, `high`, `medium`, `low`. `critical` is treated as `high`.
- `--unresolved` - Only show comments without replies (default: true)

## Procedure

### Step 1: Parse Input and Bind Shell Variables

Bind three shell variables that every later step uses:

```bash
# Case A — full URL like https://github.com/ACME/webapp/pull/123:
#   OWNER=ACME  REPO=webapp  PR_NUMBER=123
# Case B — bare PR number (uses the current repo):
OWNER=$(gh repo view --json owner --jq '.owner.login')
REPO=$(gh repo view --json name --jq '.name')
PR_NUMBER=<pr-number>
```

Every subsequent `gh api` call uses these explicit variables (`repos/$OWNER/$REPO/pulls/$PR_NUMBER/...`). Do not rely on `gh`'s native `{owner}`/`{repo}` templating — it breaks when the target PR is in a different repo than the current directory.

**CRITICAL**: This skill commits and pushes without asking. Make sure the local checkout is the PR head branch before you edit anything:

```bash
PR_BRANCH=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '.head.ref')
CURRENT_BRANCH=$(git branch --show-current)
echo "PR branch: $PR_BRANCH, current branch: $CURRENT_BRANCH"
```

If the two names differ, stop and ask the user which checkout to use.

### Step 2: Comment Schema

Step 4 does the actual filtered fetch. For reference, the comments endpoint is `repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments?per_page=100` (append `&page=2` etc. for >100 comments). The fields Claude cares about per comment: `id`, `pull_request_review_id`, `path`, `line`, `body`, `user.login`, `in_reply_to_id`, `created_at`. **CRITICAL**: never drop `per_page=100` — the default page size hides comments.

### Step 3: Fetch Review Summaries

Get the review summaries to understand context:

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" \
  --jq '.[] | {
    id: .id,
    state: .state,
    body: .body,
    user: .user.login,
    user_type: .user.type,
    submitted_at: .submitted_at
  }'
```

### Step 4: Identify OPEN Comments (No Author Reply)

**CRITICAL**: Only process comments that are truly OPEN (have no reply from the PR author).

**Definition of OPEN comment:**
1. It's a top-level review comment (`in_reply_to_id` is null)
2. There is **NO reply from the PR author** to that comment

**Skip comments with an author reply on later runs**, even if the reply says "won't fix" or "not applicable". This filtering rule does not resolve or close the GitHub discussion. Reviewer replies inside those threads are handled by Step 11.

**IMPORTANT: Only process comments from the SPECIFIED or LATEST review**

GitHub shows comments from the most recent review. Older reviews' comments are hidden/superseded even if they're on valid lines. The API returns ALL comments from ALL reviews, but users only see the latest.

**ALWAYS filter by review ID:**

```bash
# Set REVIEW_ID from one of:
#   (a) User-provided review URL like .../pull/123#pullrequestreview-3684614038
#       → extract the trailing number, e.g. REVIEW_ID=3684614038
#   (b) A new review ID reported by Step 11 (re-review rounds)
#   (c) Latest review on the PR (default if user gave no review URL):
REVIEW_ID=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews" --jq '
  sort_by(.submitted_at) | last | .id // empty
')

# Guard: if PR has no reviews at all, REVIEW_ID is empty — nothing to do.
if [ -z "$REVIEW_ID" ]; then
  echo "PR #$PR_NUMBER has no reviews — nothing to process."
  exit 0
fi

# Reviewer identity — Step 11 follows re-reviews only when REVIEWER_TYPE is "Bot".
# Bind these in the first round only; later rounds keep the same reviewer.
REVIEWER=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews/$REVIEW_ID" --jq '.user.login')
REVIEWER_TYPE=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews/$REVIEW_ID" --jq '.user.type')
echo "Reviewer: $REVIEWER ($REVIEWER_TYPE)"
```

**Complete filter for OPEN + CURRENT REVIEW comments (Python — do NOT rewrite as jq):**
```bash
# Assumes REVIEW_ID is already set (see block above). PR_AUTHOR fetched fresh.
PR_AUTHOR=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER" --jq '.user.login')

OPEN_REVIEW_COMMENTS=$(gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments?per_page=100" | python3 -c "
import sys, json
comments = json.load(sys.stdin)
author = '$PR_AUTHOR'
review_id = $REVIEW_ID
replied_ids = set(
    c['in_reply_to_id'] for c in comments
    if c['user']['login'] == author and c.get('in_reply_to_id')
)
open_comments = [
    c for c in comments
    if c.get('pull_request_review_id') == review_id
    and c.get('in_reply_to_id') is None
    and c['id'] not in replied_ids
]
print(json.dumps(open_comments, indent=2))
")
```

Severity detection patterns:
- **CRITICAL/HIGH**: `:warning:`, `**HIGH**`, `CRITICAL`, `🔴`, `🟠`
- **MEDIUM**: `:large_orange_diamond:`, `**MEDIUM**`, `🟡`
- **LOW**: `:large_blue_diamond:`, `**LOW**`, `🔵`

If the review has no open inline comments but its body contains actionable requests, treat each request as an issue. Reply to these requests with a PR conversation comment in Step 9.

### Step 5: Group Issues by File

Organize unresolved comments by file path:

```
internal/browser/pool.go:
  - Line 339: [MEDIUM] Proxy credentials logged with insufficient masking
  - Line 346: [LOW] Proxy verification blocks on synchronous network call

pkg/captcha/solver.go:
  - Line 299: [LOW] Misleading invariant comment about error handling
```

### Step 6: Present Issues and Choose Scope

**First round only.** Show the user:
1. Total number of unresolved issues by severity
2. Grouped list of issues by file
3. Ask which issues to fix (all, by severity, or specific ones)

```
Found 3 unresolved review comments:
- MEDIUM: 1
- LOW: 2

Which issues do you want to fix?
1. All issues
2. Only HIGH/MEDIUM severity
3. Specific files (list them)
4. Let me review each one
```

This is the last routine question in the run. In re-review rounds (Step 11), apply the same scope rule to the new comments and do not ask again. Comments outside the scope still get a reply in Step 9 that explains why they were skipped.

### Step 7: Fix Each Issue

For each issue to fix:

1. **Read the relevant code** around the line number
2. **Understand the issue** from the review comment
3. **Determine the fix**:
   - If the comment includes a suggestion, apply it
   - If it's a code smell, refactor appropriately
   - If you disagree on technical grounds, do not change the code; prepare a reply with concrete reasoning
   - If the intent is unclear or the change needs a product or architecture decision, stop and ask the user
4. **Apply the fix** using Edit tool
5. **Track what was done** — remember the comment ID and a brief description of the fix for Step 9

### Step 8: Verify and Commit

1. **Run tests/lint** that the project provides. Fix every failure before you continue.
2. **Commit** the changes locally with a descriptive message that references the PR. Do not push yet.

Run `git add`, `git commit`, and `git push` (Step 10) as separate commands. Never use `--no-verify`. If a hook fails, fix the cause.

If no file changed in this round (every reply explains a disagreement or a skip), skip the commit and Step 10.

### Step 9: Reply to Comments

Post the replies **without asking the user for confirmation**.

**IMPORTANT**: Reply to ALL processed comments BEFORE pushing the branch. This ensures the reviewer sees your explanations before being notified of new commits.

**CRITICAL**: Never resolve or close GitHub review discussions through the UI or any API. Leave each thread's resolution state unchanged after replying. The reviewer reads the reply and decides whether to resolve the discussion.

Record the round start time first. Step 11 uses it to find reviewer activity that comes after your replies:

```bash
ROUND_ANCHOR=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

For each processed comment, reply with a brief description of the actual fix applied:

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR_NUMBER/comments" \
  -X POST \
  -f body="Fixed: <brief description of what was changed and why>" \
  -f in_reply_to=$COMMENT_ID  # set per-comment in your loop
```

For an actionable request in a review body (no inline thread), post a PR conversation comment:

```bash
gh api "repos/$OWNER/$REPO/issues/$PR_NUMBER/comments" \
  -X POST \
  -f body="<what was changed for which request>"
```

**Guidelines for reply content:**
- Be specific about what was changed (e.g. "Fixed: replaced raw credential logging with masked output using `sanitize()` helper")
- If you disagreed with the suggestion and took a different approach, explain why
- If a comment was skipped, reply explaining the reason (e.g. "Not applicable because..." or "Skipped — outside the agreed scope")

### Step 10: Push Changes

Push the PR head branch **without asking the user for confirmation**:

```bash
git push origin "HEAD:$PR_BRANCH"
```

**CRITICAL**: Only push AFTER replies are posted. If you push first, the reviewer gets notified of new commits and may start re-reviewing before seeing your reply context. Never force-push.

### Step 11: Follow the Bot Re-Review

If `REVIEWER_TYPE` is not `Bot`, go to Step 12. A human reviewer decides in their own time.

If the reviewer is a bot, do not stop after the push. The PR already had remarks, so stay with it until the bot approves or a stop condition occurs.

**11.1 Wait for reviewer activity.** The block polls every 30 seconds for up to 8 minutes. Give the Bash call a 600000 ms timeout, or run it in the background when the host supports this and wait for the result.

```bash
python3 - "$OWNER" "$REPO" "$PR_NUMBER" "$REVIEWER" "$ROUND_ANCHOR" <<'PY'
import json, subprocess, sys, time

owner, repo, pr, reviewer, anchor = sys.argv[1:6]
base = f"repos/{owner}/{repo}/pulls/{pr}"

def api(path):
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return json.loads(out)

def snapshot():
    reviews = [
        r for r in api(f"{base}/reviews?per_page=100")
        if r["user"]["login"] == reviewer and (r.get("submitted_at") or "") > anchor
    ]
    replies = [
        c for c in api(f"{base}/comments?per_page=100")
        if c["user"]["login"] == reviewer
        and c.get("in_reply_to_id")
        and c["created_at"] > anchor
    ]
    return reviews, replies

deadline = time.time() + 480
reviews, replies = snapshot()
while not (reviews or replies) and time.time() < deadline:
    time.sleep(30)
    reviews, replies = snapshot()
if reviews or replies:
    time.sleep(60)  # let the bot finish posting the whole batch
    reviews, replies = snapshot()

reviews.sort(key=lambda r: r["submitted_at"])
if reviews and reviews[-1]["state"] == "APPROVED":
    status = "APPROVED"
elif reviews or replies:
    status = "ACTIVITY"
else:
    status = "WAITING"
print(json.dumps({
    "status": status,
    "reviews": [{k: r.get(k) for k in ("id", "state", "body", "submitted_at", "commit_id")} for r in reviews],
    "thread_replies": [{k: c.get(k) for k in ("id", "in_reply_to_id", "path", "line", "body", "created_at")} for c in replies],
}, indent=2))
PY
```

**11.2 Act on the result:**

| Status | Action |
|--------|--------|
| `APPROVED` | Go to Step 12. Do not process further comments from the approving review; list them in the summary. |
| `WAITING` | Run 11.1 again. After four `WAITING` results in a row (about 30 minutes), stop and hand over. |
| `ACTIVITY` | Start a new round (11.3). |

**11.3 Run a new round:**

1. For each review ID in `reviews`, run the Step 4 filter with `REVIEW_ID` set to that ID. Reviews that only carry thread replies give an empty list.
2. For each item in `thread_replies` (the bot answered one of your replies, `in_reply_to_id` is the thread root):
   - The bot accepts your reply or only acknowledges it → no action and no reply.
   - The bot's objection is valid → fix it (Step 7) and reply `Fixed: ...`.
   - You still disagree → reply once with concrete technical reasoning: code references, test results, constraints.
3. Run Steps 5, 7, 8, 9, and 10 for the new work, with the Step 6 scope from the first round. Step 9 sets a new `ROUND_ANCHOR`.
4. Go back to 11.1.

**11.4 Stop and hand over to the user** when one of these occurs:

- **No agreement**: in one thread you already replied twice with reasoning (not `Fixed:`), and the bot still insists.
- The bot asks for something that contradicts an earlier bot comment, the PR goal, or the user's instructions.
- A comment needs a product or architecture decision, or changes outside the PR scope.
- Tests, lint, or git hooks fail and you cannot fix the cause.
- The bot posts a review without open comments and without `APPROVED` (some bots cannot approve).
- No reviewer activity for about 30 minutes after the push.
- Five rounds have passed without approval.

When you hand over, give the user the thread links, the bot's position, your position with evidence, and the options you see.

### Step 12: Summary

Report:
- Number of rounds and the final review state (approved by the bot, waiting for a human reviewer, or handed over)
- Number of issues fixed
- Files modified
- Replies posted (count and any notable ones)
- Any issues skipped and why
- Branch push status and the last pushed commit
- For a hand-over: the open disagreements from Step 11.4

## Safety Rules

1. Read the code before applying any suggested fix; ask when intent is unclear.
2. Run tests/lint before every commit. Never use `--no-verify`; fix the cause of a hook failure.
3. Post replies and push without asking for confirmation, always replies first (Step 9 `IMPORTANT`, Step 10 `CRITICAL`).
4. Push only to the PR head branch. Never force-push.
5. Never resolve or close review discussions. Leave thread resolution to the reviewer after they inspect your reply (Step 9 `CRITICAL`).
6. Never approve, merge, or change the draft status of the PR, and never dismiss or re-request reviews.
7. Do not reply to bot acknowledgments. Each reply to the bot must contain a fix or new technical evidence.
8. Do not keep arguing with the bot. Hand over to the user under the Step 11.4 conditions.

## Example Session

```
User: /automatis-fix-pr https://github.com/owner/repo/pull/4

Claude: 3 unresolved comments in review #3684614038 by coderabbitai[bot]:
  MEDIUM × 1 (pool.go:339)
  LOW × 2 (pool.go:346, solver.go:299)
Fix all?

User: yes

Claude: [fixes each, runs tests, commits]
[posts 3 replies, pushes]
Round 1 done. Waiting for coderabbitai[bot] to re-review...
[bot review #3684700001: 1 new comment; bot replied in the pool.go:346 thread]
Round 2: fixed solver.go:310, replied "Fixed: ...";
  pool.go:346 — bot objection is valid, moved timeout to config, replied "Fixed: ...". Pushed.
[bot review #3684712345: APPROVED]

Claude: PR #4 approved by coderabbitai[bot] after 2 rounds. 5 issues fixed,
4 files modified, 5 replies posted. Review discussions left unchanged for the reviewer.
```
