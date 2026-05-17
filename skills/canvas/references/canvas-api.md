# Canvas API Reference

## Token And Sandbox

- Prefer macOS Keychain service `codex.canvas`, account `credential`, for the Canvas API token.
- Use `keychain-secret get codex.canvas credential` in `CANVAS_TOKEN_COMMAND`.
- If the Keychain entry is missing, import it once with `keychain-secret import-op codex.canvas credential 'op://Private/Canvas/credential'`.
- Never print the token or `Authorization: Bearer ...` header.

## Common Endpoints

- Current user: `GET /api/v1/users/self`
- Courses: `GET /api/v1/users/self/courses`
  - Useful params: `enrollment_state=active`, `include[]=term`, `include[]=total_scores`, `include[]=teachers`, `per_page=100`
- Course details: `GET /api/v1/courses/:course_id`
  - Useful params: `include[]=syllabus_body`, `include[]=total_scores`, `include[]=term`, `include[]=teachers`
- Assignment groups: `GET /api/v1/courses/:course_id/assignment_groups`
  - Useful params: `include[]=assignments`, `include[]=submission`, `include[]=rules`, `per_page=100`
- Assignments: `GET /api/v1/courses/:course_id/assignments`
  - Useful params: `include[]=submission`, `include[]=rubric`, `per_page=100`
- Single submission: `GET /api/v1/courses/:course_id/assignments/:assignment_id/submissions/self`
- Modules: `GET /api/v1/courses/:course_id/modules`
  - Useful params: `include[]=items`, `include[]=content_details`, `per_page=100`
- Pages: `GET /api/v1/courses/:course_id/pages`, then `GET /api/v1/courses/:course_id/pages/:url`
- Files: `GET /api/v1/courses/:course_id/files` or `GET /api/v1/courses/:course_id/files/:file_id`
- Announcements: `GET /api/v1/announcements?context_codes[]=course_:course_id`
- Discussions: `GET /api/v1/courses/:course_id/discussion_topics`

Always quote zsh args containing brackets:

```bash
--param 'include[]=total_scores'
```

## Pagination

Canvas uses HTTP `Link` headers for pagination. Prefer a helper that follows `rel="next"`. Set `per_page=100` for list calls.

## Output Shaping

Canvas assignment objects can contain huge HTML descriptions, rubrics, discussion entries, secure params, and attachment metadata. For user-facing answers, reduce to:

- `id`, `name`, `due_at`, `points_possible`
- assignment group name and weight
- submission `score`, `grade`, `workflow_state`, `submitted_at`, `graded_at`
- `late`, `missing`, `excused`, `points_deducted`
- flags: `muted`, `omit_from_final_grade`, `published`, `locked_for_user`

Do not dump discussion bodies or secure params unless the task requires them.

## Grade Workflows

For "what grade can I get?" questions:

1. Fetch course list with total scores and identify the course ID.
2. Fetch `assignment_groups` with assignments and submissions.
3. Pull syllabus body. If it links a PDF syllabus, download it through the file endpoint and extract text with `pdftotext`.
4. Find:
   - grade intervals and rounding rules
   - assignment group weights
   - drop rules for quizzes, discussions, and in-class work
   - late-day credits and final-assignment penalties
5. Calculate:
   - current weighted score from graded work only
   - final score with ungraded work as zero
   - max score if remaining work earns full credit
   - required score on remaining work for each relevant letter cutoff
6. Compare against Canvas `computed_current_score` and `computed_final_score`. If they differ, explain likely causes and prefer Canvas enrollment numbers when they directly answer current/final displayed grade.

## Lessons From 17-629

- CMU Canvas course `Product Management Essentials II` used group weights: Product Assignments 74%, In-Class Exercises 10%, Short Quizzes 10%, Discussions 6%.
- The syllabus PDF, not just the Canvas syllabus HTML excerpt, contained grade intervals and rounding rules.
- The course had drop rules: lowest two in-class activities, lowest quiz, lowest discussion.
- A raw assignment-groups response was too large for direct display. A temporary summarizer was the right pattern.
- Canvas displayed `computed_current_score` and `computed_final_score`; the answer needed both and a required remaining-assignment score.
