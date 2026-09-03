---
name: canvas
description: "Use when Codex needs to work with Canvas LMS / Instructure through the Canvas API: listing courses, finding course IDs, reading syllabi, assignments, modules, pages, files, submissions, grades, rubrics, due dates, or calculating current/final/maximum course grades. Also use when a user asks to submit Canvas assignments or download Canvas course materials, while keeping Canvas tokens in macOS Keychain or environment variables."
---

# Canvas

Use Canvas through the REST API first. Prefer API calls over browser automation for courses, grades, files, modules, pages, assignments, submissions, and syllabus data.

This is a Canvas data-access skill. For full exam preparation planning, use
`exam-review` as the workflow owner and use this skill only for
Canvas-specific data gathering and grade calculations.

## Authentication

- Default CMU Canvas base URL: `https://canvas.cmu.edu`.
- Prefer a token in macOS Keychain at service `codex.canvas`, account `credential`.
- Use `CANVAS_TOKEN_COMMAND='keychain-secret get codex.canvas credential'` or a local script that reads the same Keychain entry.
- One-time migration from 1Password, when needed: `keychain-secret import-op codex.canvas credential 'op://Private/Canvas/credential'`.
- Do not print Canvas tokens, auth headers, raw cookies, or secret values.
- Use 1Password only as a scoped import/fallback source when the Keychain entry is missing.

## Bundled CLI

Use `scripts/canvas_api.py` from this skill. Resolve it relative to this
`SKILL.md` and invoke that absolute path; never search old course directories
for a helper. The script uses only the Python standard library and defaults to
the Keychain token command above.

```bash
CANVAS_API="<absolute path to this skill>/scripts/canvas_api.py"
python3 "$CANVAS_API" whoami
python3 "$CANVAS_API" courses
python3 "$CANVAS_API" raw-get /api/v1/users/self/courses --paginate --param per_page=100 --param 'include[]=total_scores' --param 'include[]=term'
python3 "$CANVAS_API" raw-get /api/v1/courses/COURSE_ID/assignment_groups --paginate --param 'include[]=assignments' --param 'include[]=submission'
python3 "$CANVAS_API" sync-course COURSE_ID --out OUT_DIR
```

`sync-course` refreshes metadata and downloads visible files by default. It:

- preserves the Canvas folder hierarchy under `OUT_DIR/course-files/`
- skips byte-identical files recorded in `course-files-manifest.json`
- downloads new or changed files atomically and verifies Canvas-reported sizes
- stores SHA-256 checksums and remote `updated_at` values in the file manifest
- records sync time and any inaccessible endpoints in `canvas-sync.json`
- redacts Canvas verifier/token query parameters from saved metadata

Use `--metadata-only` only when files are intentionally unnecessary, and
`--force` only when every visible file must be downloaded again. Quote
parameters containing `[]` in zsh, such as `'include[]=total_scores'`, or zsh
will treat them as glob patterns.

## Workflow

1. Identify the course with `python3 "$CANVAS_API" courses`, which paginates `/api/v1/users/self/courses` and starts without enrollment/state filters. Use `--active-only` only when the request is explicitly limited to active courses.
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

- For “download/update the course materials,” use bundled `sync-course` rather than manually fetching file URLs.
- A syllabus page may link to a full syllabus PDF through a Canvas file endpoint. The sync command inventories API-linked files; use `raw-get` for individual metadata only when needed.
- Use `pdftotext` when available to extract grade intervals and policy details from syllabus PDFs.
- Course files and media may be external LTI systems. Canvas often exposes only the link, iframe, or file metadata, not the original video or external resource.
- Never print or persist live Canvas verifier URLs. The bundled CLI uses them only during download and redacts them from saved JSON and terminal output.

## References

- Read `references/canvas-api.md` for endpoint patterns, pagination, output shaping, and the lessons learned from prior Canvas grade work.
