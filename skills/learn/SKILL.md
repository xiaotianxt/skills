---
name: learn
description: Build and run evidence-based learning workflows. Use when Codex needs to create or continue a study workspace, collect and convert learning materials, design goals, teach from sources, quiz the user, score answers, track progress, maintain an error log, or run spaced review for subjects such as courses, books, technical topics, exams, or career prep.
---

# Learn

Use this skill to turn a topic into a source-grounded, interactive learning system.

## Core Principles

- Start from a learning goal, but allow it to change as evidence of the learner's needs emerges.
- Prefer source-grounded teaching over generic explanation. Identify the exact source chunk before teaching.
- Teach in small units, then ask retrieval questions before marking progress.
- Treat mistakes as the main signal. Log wrong, vague, overconfident, or ungrounded answers.
- Use spaced review, but usually only when the user asks to review or when resuming after a noticeable gap.
- Avoid material hoarding. Collect enough sources to cover the goal; do not delay learning indefinitely.

Read `references/learning-science.md` when designing a new workflow, defending the method, or revising the learning loop.

## New Learning Workspace

When creating a new study workspace, use:

```bash
python3 /path/to/learn/scripts/init_learning_workspace.py TOPIC --path /target/parent --goal "..."
```

The script creates:

- `materials/` for source files and web caches
- `notes/` for lesson plans and ordinary notes
- `cases/` for worked examples or problem traces
- `outputs/` for compiled PDFs or exports
- `AGENTS.md` for local study rules
- `tasklog.typ` for progress, scores, and next steps
- `errorlog.typ` for misconceptions and review actions
- `workbook.typ` for worked examples, section notes, verification questions, and corrections
- `materials/source-index.md` for collected sources
- `notes/reading-sequence.md` for the first pass route

If the workspace already exists, inspect `AGENTS.md`, then `tasklog.typ`, then `errorlog.typ` before teaching.

## Source Collection

For each topic, build a source index before deep teaching:

1. Gather likely authoritative materials: books, official docs, papers, syllabi, lectures, slides, assignments, transcripts, examples, and prior notes.
2. Prefer primary sources: official docs, textbook chapters, course pages, papers, source code, specs.
3. Convert materials into AI-readable form:
   - PDFs/books: text extraction or OCR as needed.
   - Videos/audio: transcripts with timestamps when possible.
   - Slides/images: OCR plus image references.
   - Web pages: URL plus local cache or concise source notes.
4. Record every source in `materials/source-index.md` with purpose, priority, and local path.
5. Do not copy large copyrighted texts into notes. Store local references and write original summaries.

Use specialized skills when appropriate, for example OCR/document skills for PDFs or screenshots.

## Tracking Files

Use `tasklog.typ` for:

- learning goal and current assumptions
- scoring rubric
- lesson/chapter table
- session log
- next action

Use `errorlog.typ` for:

- misconception category
- original question
- learner answer, preserving the error
- correction
- domain-specific consequence or rule
- review action and status

Use `workbook.typ` for:

- section-level notes
- worked examples
- verification questions
- corrected explanations
- drills or transfer exercises

## Teaching Loop

For each section, chapter, lecture, or case:

1. Select a small unit from the reading sequence.
2. Read the relevant source material first.
3. Explain in the learner's language with all essential knowledge points for that unit.
4. Include at least one concrete example or system mapping.
5. Name common wrong interpretations before the quiz.
6. Ask verification questions that require retrieval and transfer, not just recognition.
7. Stop and wait for the learner's answer.
8. Score answers using the local rubric.
9. Update `tasklog.typ`.
10. Add or update `errorlog.typ` for every weak answer.
11. Only mark a unit `done` when the learner can explain, apply, and avoid the key trap.

## Review Loop

When the user asks to review, or resumes after a meaningful gap:

1. Read open/review items in `errorlog.typ`.
2. Ask questions that test the old misconception without showing the correction first.
3. If answered correctly twice across separate reviews, mark the item `closed`.
4. If still weak, keep it `review` and add a sharper review action.

Avoid unsolicited heavy review sessions; offer a brief review option when stale errors are visible.

## Failure Modes To Avoid

- Turning learning into passive summaries.
- Collecting too many materials before starting.
- Rigid goals that ignore what the learner discovers.
- Overly broad lessons with no retrieval.
- Marking progress without questions.
- Logging every tiny imperfection until the workflow becomes maintenance-heavy.
- Letting AI answer from memory when source grounding is available.
