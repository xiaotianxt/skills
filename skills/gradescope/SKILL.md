---
name: gradescope
description: "Read logged-in Gradescope course, online-assignment, submission, score, rubric, autograder, test-result, and regrade pages through bro. Use when the user asks to inspect, verify, extract, or summarize Gradescope page content; keep the workflow read-only unless the user separately authorizes an action."
---

# Gradescope Reader

Read the user's logged-in Gradescope state through `bro-browser`. Generic web
fetches cannot reliably see authenticated or dynamically rendered content.

## Read Boundary

- Reading includes text extraction, DOM/accessibility inspection, and opening a
  presentation-only expander needed to reveal already-visible feedback.
- Do not save answers, submit, resubmit, request a regrade, delete an attempt,
  upload a file, or change course/account state without separate authorization.
- Never try to reveal hidden tests, solutions, rubric items, or feedback the
  user's Gradescope UI does not expose.
- Treat student identity, answers, grades, course URLs, submission IDs, and
  downloaded artifacts as sensitive. Never expose cookies, CSRF values, signed
  URLs, request headers, or bro credentials.

## Read A Page

1. Target the page. If the user says the page is currently open, start with
   `browser.current.extract` using a generous `maxChars`. If the active page is
   not Gradescope, the result is ambiguous, or a raw DOM read is needed, call
   `browsers_context` and `tabs_context`, then pin both `browserId` and `tabId`.
   When multiple Gradescope tabs are open:

   - If exactly one matches the requested course/assignment, use it.
   - If edit and submitted-view tabs share the same course and assignment IDs,
     treat them as two views of one assignment and reconcile them when the user
     asks for its current answers or state.
   - If tabs belong to different courses or assignments and the request does
     not identify one, ask which target to read.

   Confirm the target is on `gradescope.com` and record its title and path. This
   step is complete when later reads cannot drift to another active tab.

2. Classify the visible page by path and semantics:

   - `/courses/:course_id`: course dashboard.
   - `/courses/:course_id/assignments/:assignment_id/submissions/new`: editable
     online assignment or saved draft.
   - `/courses/:course_id/assignments/:assignment_id/submissions/:submission_id`:
     submitted attempt, grading view, or autograder/test results.
   - `/courses/:course_id/regrade_requests`: regrade list or detail.
   - Any other path: classify from the page title, headings, score labels, and
     controls rather than guessing from the URL alone.

   This step is complete when the page type and visible state—draft, saved,
   submitted, ungraded, graded, or unavailable—are explicit.

3. Make two read-only passes. First use `browser.current.extract` before target
   discovery or `get_page_text` after pinning an existing tab. If
   `get_page_text` fails or is clearly partial, fall back once to
   `read_page(filter:"all")`; if both fail, record the narrative as unavailable
   and continue only with safe DOM state that can still be verified. Then
   reconcile state that plain text drops with `javascript_tool`: selected radio/checkbox
   controls, input and textarea values, disabled/read-only state, expanded
   panels, per-item scores, and save/submission status. For online assignments,
   submitted answers, or test-result pages, read
   [references/page-reading.md](references/page-reading.md) before this pass.

   Use `read_page` only when semantic controls, collapsed panels, or labels are
   still unclear. A presentation-only click must target a pinned tab and a
   specific expander; reread the affected region immediately afterward with
   `get_page_text` or `read_page(filter:"all")`. Do not use the interactive-only
   tree for an expanded table or feedback panel. If one expansion does not
   change `aria-expanded`, open a dialog, or reveal new content, stop and record
   that panel as unavailable rather than clicking repeatedly. This step is
   complete when every visible question or test row is captured, or is
   explicitly recorded as hidden, collapsed-but-unreadable, or unavailable.

4. Normalize without overclaiming:

   - Page: course, assignment, page type, attempt/submission identity when
     needed, and visible state.
   - Summary: answered count, submitted/saved time, overall score and possible
     points, grading status, and late status when displayed.
   - Questions: number, parent group, prompt/title, points, response type,
     selected or written response, save state, awarded points, rubric result,
     and visible grader feedback.
   - Autograder tests: group, test name, pass/fail/error status, earned/possible
     points, and visible expected/actual output, stdout/stderr, runtime, or
     feedback. Keep hidden tests as `hidden`; do not infer their contents.
   - Gaps: content not rendered, not released, hidden, inaccessible, or omitted
     because the page was truncated.

5. Verify the result against independent page signals. Reconcile leaf-question
   count with “Questions Answered,” per-item points with the displayed total,
   and saved/submitted state with timestamps or action labels. Deduplicate any
   submission-outline copy of the same questions. When comparing edit and
   submitted views, normalize presentation whitespace but preserve substantive
   answer text. Distinguish `Ungraded` or `- / N` from a zero. This step is
   complete only when counts agree or every discrepancy is named.

## Response Shape

Lead with the page state and material result. Use a compact table for multiple
questions/tests when it improves comparison. Include raw HTML, internal IDs, or
full personal answers only when the user explicitly needs them.

If reading cannot be completed, report the exact boundary: wrong tab, logged
out, page not loaded, content hidden by course policy, or bro unavailable.
