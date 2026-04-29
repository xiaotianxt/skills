---
name: gh-review-workflow
description: Inspect GitHub pull request review state, including latest PR comments, review submissions, unresolved inline threads, and post-fix thread resolution. Use when Codex needs to check "latest PR comments", summarize actionable review feedback, inspect the current branch PR, or resolve review threads after fixes are pushed.
---

# GH Review Workflow

Use this skill when the user wants the real review state of a GitHub PR, not just flat issue comments. Prefer GitHub connector/MCP tools for repository and PR metadata. Use the bundled scripts or `gh api graphql` when you need inline review threads, `isResolved`, `isOutdated`, or file and line anchors.

## Workflow

1. Resolve the target PR.
- If the user provides a PR URL or repo plus PR number, use that directly.
- If the task is about the current branch PR, run `gh auth status` and then use the bundled `scripts/fetch_review_state.py` with no arguments.
- If the task is about the latest PR in a repo, first use GitHub metadata tools to list PRs sorted by create time.

2. Inspect metadata and flat comments.
- Use GitHub connector data for PR title, head/base branches, and top-level PR comments.
- Do not treat flat PR comments as complete review state.

3. Inspect review threads.
- Run `python3 ~/.codex/skills/gh-review-workflow/scripts/fetch_review_state.py` for the current branch PR.
- Or run `python3 ~/.codex/skills/gh-review-workflow/scripts/fetch_review_state.py --owner OWNER --repo REPO --number 123`.
- Read `review_threads` first. That is the source of truth for inline review comments and resolution state.

4. Summarize actionability.
- Group duplicate comments by behavior or file instead of answering each line independently.
- Separate real blockers from style suggestions and "reply only" items.
- Call out whether a thread is still current or already `isOutdated`.

5. After fixes.
- Verify code locally before pushing.
- Push the branch.
- If the user asked to resolve addressed threads, run `python3 ~/.codex/skills/gh-review-workflow/scripts/resolve_review_threads.py THREAD_ID...`.
- If the user wants to resolve all unresolved threads captured in a saved JSON dump, run `python3 ~/.codex/skills/gh-review-workflow/scripts/resolve_review_threads.py --from-json review_state.json`.

## Interpretation Rules

- `conversation_comments` are top-level PR comments.
- `reviews` are submitted or draft review objects. `PENDING` means there is a draft review even if no formal review event was submitted yet.
- `review_threads` hold inline review comments, anchors, and resolution state.
- `isOutdated: true` means the original diff context moved or changed; decide whether the underlying concern is already addressed before ignoring it.
- Repeated comments like "can we reuse X?" often map to one design decision. Cluster them.

## Write Safety

- Do not comment on GitHub or resolve review threads unless the user explicitly asked for a write.
- Do not reject a suggestion vaguely. If keeping the current design, explain the ABI, spec, or ownership reason concretely.
- For review requests, prioritize behavioral bugs, regressions, and missing validation over cosmetic style changes.

## Resources

- Read [workflow.md](references/workflow.md) for the tool split and response template.
- Use `scripts/fetch_review_state.py` for thread-aware reads.
- Use `scripts/resolve_review_threads.py` for post-fix cleanup.
