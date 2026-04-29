# Review Workflow Reference

## Tool split

- Use GitHub metadata tools for:
  - latest PR lookup
  - PR title, state, branch mapping
  - top-level PR comments
- Use `gh api graphql` for:
  - inline review threads
  - `isResolved`
  - `isOutdated`
  - thread file and line anchors
  - resolving review threads

## Minimal workflow

1. Resolve the PR:
   - explicit repo plus PR number if provided
   - otherwise current branch PR through `gh pr view`
2. Fetch review state:
   - `python3 ~/.codex/skills/gh-review-workflow/scripts/fetch_review_state.py`
3. Read these sections in order:
   - `review_threads`
   - `reviews`
   - `conversation_comments`
4. Collapse duplicates:
   - many inline comments may represent one shared design concern
5. After code changes:
   - verify locally
   - push
   - resolve the addressed threads if the user asked

## Response shape

- Start with actionable findings.
- Mention file or behavior area.
- State which threads are already outdated.
- Distinguish:
  - must fix
  - reasonable suggestion
  - explanation only

## Common pitfalls

- Looking only at top-level PR comments misses most real review feedback.
- `get_pull_request_reviews` style data may be incomplete for thread state; always verify with GraphQL thread reads.
- Resolving threads before pushing verified fixes makes the PR history confusing.
