---
name: canvas
description: "Use when Codex needs to work with Canvas LMS / Instructure through the Canvas API: listing courses, finding course IDs, reading syllabi, assignments, modules, pages, files, submissions, grades, rubrics, due dates, or calculating current/final/maximum course grades. Also use when a user asks to submit Canvas assignments or download Canvas course materials, while keeping Canvas tokens in macOS Keychain or environment variables."
---

# Canvas

Use Canvas through the REST API first. Prefer API calls over browser automation for courses, grades, files, modules, pages, assignments, submissions, and syllabus data.

This is a Canvas data-access skill. For full exam preparation planning, use
`course-exam-review-planner` as the workflow owner and use this skill only for
Canvas-specific data gathering and grade calculations.

## Authentication

- Default CMU Canvas base URL: `https://canvas.cmu.edu`.
- Prefer a token in macOS Keychain at service `codex.canvas`, account `credential`.
- Use `CANVAS_TOKEN_COMMAND='keychain-secret get codex.canvas credential'` or a local script that reads the same Keychain entry.
- One-time migration from 1Password, when needed: `keychain-secret import-op codex.canvas credential 'op://Private/Canvas/credential'`.
- Do not print Canvas tokens, auth headers, raw cookies, or secret values.
- Use 1Password only as a scoped import/fallback source when the Keychain entry is missing.

## Existing Local Helper

Reuse the existing helper, but locate it instead of assuming a fixed Documents
path because the course-materials tree may move:

```bash
CANVAS_HELPER="$(rg --files "$HOME/Documents" 2>/dev/null | rg '/canvas-api-research/canvas_api\.py$' | head -n 1)"
test -n "$CANVAS_HELPER"
```

Always override the helper's legacy token command with the Keychain command.

Useful commands:

```bash
CANVAS_TOKEN_COMMAND='keychain-secret get codex.canvas credential' python3 "$CANVAS_HELPER" whoami
CANVAS_TOKEN_COMMAND='keychain-secret get codex.canvas credential' python3 "$CANVAS_HELPER" courses --include-completed
CANVAS_TOKEN_COMMAND='keychain-secret get codex.canvas credential' python3 "$CANVAS_HELPER" raw-get /api/v1/users/self/courses --param per_page=100 --param 'include[]=total_scores' --param 'include[]=term'
CANVAS_TOKEN_COMMAND='keychain-secret get codex.canvas credential' python3 "$CANVAS_HELPER" raw-get /api/v1/courses/COURSE_ID/assignment_groups --param 'include[]=assignments' --param 'include[]=submission'
CANVAS_TOKEN_COMMAND='keychain-secret get codex.canvas credential' python3 "$CANVAS_HELPER" sync-course COURSE_ID --out OUT_DIR
```

Quote parameters containing `[]` in zsh, such as `'include[]=total_scores'`, or zsh will treat them as glob patterns.

## Workflow

1. Identify the course with the paginated `/api/v1/users/self/courses`, including `term` and `total_scores`. Start without `enrollment_state` or `state[]` filters when searching across terms.
2. Canvas may return enrolled-course stubs whose `name` and `course_code` are null. Hydrate every such ID with `GET /api/v1/courses/:id` and, if useful, `/api/v1/courses/:id/sections`. A `403` leaves the ID inaccessible/unresolved; it does not prove the requested course is absent.
3. Fetch course details with `include[]=syllabus_body,total_scores` and verify whether `apply_assignment_group_weights` is true.
4. Fetch assignment groups with `include[]=assignments` and `include[]=submission`.
5. Summarize large JSON locally before showing results. Avoid dumping assignment descriptions, discussion bodies, attachment URLs, or secure params unless the user explicitly needs them.
6. For grade questions, inspect the syllabus PDF or page for grade cutoffs, rounding rules, drop rules, late penalties, and optional or extra-credit treatment.
7. Reconcile Canvas enrollment scores with local calculations. Canvas may apply muted grades, drop rules, optional assignments, hidden rules, excused submissions, or grading-period settings.

## Grade Calculation Notes

- If `apply_assignment_group_weights` is true, calculate each group separately and multiply by `group_weight`.
- Exclude unpublished assignments and assignments with `omit_from_final_grade=true`.
- Treat `excused` submissions as excluded.
- Distinguish current score from final score:
  - Current score usually ignores ungraded assignments.
  - Final score often treats ungraded assignments as zero.
  - Maximum possible score gives full credit for remaining ungraded assignments.
- Always check syllabus rules for drops. Canvas assignment group API may not fully explain the visible gradebook calculation unless group rules are included or inferred from the syllabus.
- When answering "can I get an A?", report the current Canvas score, final score, remaining assignments, required score on remaining work, and the grade cutoff/rounding rule with exact dates when relevant.

## Files And Syllabus

- A syllabus page may link to a full syllabus PDF through a Canvas file endpoint. Fetch file metadata from `/api/v1/courses/:course_id/files/:file_id`, then download the `url` field.
- Use `pdftotext` when available to extract grade intervals and policy details from syllabus PDFs.
- Course files and media may be external LTI systems. Canvas often exposes only the link, iframe, or file metadata, not the original video or external resource.

## References

- Read `references/canvas-api.md` for endpoint patterns, pagination, output shaping, and the lessons learned from prior Canvas grade work.
