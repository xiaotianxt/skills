---
name: course-exam-review-planner
description: Build an evidence-driven review plan for a course exam or final. Use when the user wants to prepare for a new course exam by collecting recordings/transcripts, identifying the official exam scope, mining homework/practice exams/past exams/forums, and turning the result into a concrete study plan or Things 3 project.
---

# Course Exam Review Planner

Use this skill when planning how to review for a course exam, especially when the course has lecture recordings, transcripts, homeworks, practice exams, previous exams, or forum discussions.

## Core Principle

Do not start by making a generic day-by-day schedule. First reconstruct the exam contract:

1. What is definitely in scope?
2. What question formats are likely?
3. What skills are repeatedly tested?
4. What artifacts best train those skills?
5. What should be converted into retrieval drills, an error log, and a final cheat sheet?

Treat evidence by priority:

1. Official exam page, final guide, syllabus, instructor announcement.
2. The lecture or recording that explicitly describes the final exam.
3. Latest official practice exam and solutions.
4. Homework, projects, recitations, quizzes, and midterms that overlap the final scope.
5. Older official exams from the same course/instructor.
6. Online forums, Reddit, reviews, and student notes as weak signals only. Use them to discover likely pain points, not to override official materials.

## Inputs To Gather

Ask for or locate:

- Course name/number and term.
- Exam date, time, location, duration, allowed materials, grading weight.
- Course website, LMS/exported folder, syllabus, final guide, announcements.
- Full lecture recordings and transcripts. If recordings are on Panopto, use the `panopto-mp4-bulk-download` skill when bulk download is needed.
- Homework PDFs, solution PDFs, quizzes, midterm/final practice exams, previous exams.
- Existing notes, cheat sheet constraints, and user time availability.
- User's target outcome: pass, high grade, or mastery.

## Workflow

1. Build the corpus.
   - Ensure all recordings are downloaded or accessible.
   - Ensure every recording has a transcript or searchable text.
   - Collect PDFs and HTML pages into a single course material directory when possible.
   - Make local files searchable with filenames that preserve topic, date, and artifact type.

2. Find the exam contract.
   - Search transcripts for phrases like `final exam`, `scope`, `cumulative`, `practice final`, `cheat sheet`, `allowed`, `logistics`, `review`.
   - Identify the recording or lecture segment that most directly describes the final.
   - Extract concrete facts: covered lectures, textbook chapters, excluded topics, exam length, question count, point count, allowed materials, date/time/location.
   - If relative dates appear, convert them into exact dates.

3. Map official scope to artifacts.
   - Create a table with columns: topic, official source, lecture numbers, textbook sections, homework questions, practice exam questions, older exam questions.
   - Prefer the newest practice exam as the primary diagnostic.
   - Use homework only where it trains concepts that appear in the final scope.
   - Use older exams to add coverage for recurring question archetypes.

4. Mine external and historical signals.
   - Search official archives first.
   - Then search online forums, Reddit, course reviews, and public notes for recurring complaints, surprise topics, or highly emphasized question types.
   - Mark these as weak evidence unless they are confirmed by official materials.
   - Do not overfit to rumors or outdated terms.

5. Classify question archetypes.
   - For each practice/past exam question, record: topic, required procedure, common trap, source artifact, and whether it is calculation, proof, design, debugging, short answer, or concept recognition.
   - Convert each archetype into a closed-book drill template.
   - Prioritize procedural templates that can be repeated cold.

6. Plan backward from the exam.
   - Day 1: run the newest practice exam cold by topic clusters; grade immediately; create error log.
   - Middle days: backfill misses using homework, lectures, textbook sections, and older exams.
   - Final day: redo every missed practice subpart cold; finalize the cheat sheet; stop learning new content.
   - Keep review blocks tied to artifacts and completion criteria, not vague labels like "study transactions".

7. Maintain an error log.
   - Columns: question, missed rule, corrected rule, next drill.
   - Every wrong or uncertain answer gets a rule-level entry.
   - The final-day review is driven from the error log, not from rereading slides.

8. Build the cheat sheet.
   - Include distilled rules, formulas, state machines, algorithms, and decision tables.
   - Exclude copied slides or long explanations.
   - Every cheat-sheet line should answer a known question archetype or correct an error-log miss.

9. Produce an action plan.
   - Group tasks by date and topic cluster.
   - Each task should name exact files, questions, and completion criteria.
   - If using Things 3, create a project with headings by day/topic and verify the import with `things3-manager`.

## Output Shape

For a normal planning request, produce:

1. A short summary of the confirmed exam contract.
2. A scope map from official topics to course artifacts.
3. A prioritized review plan by day.
4. A list of closed-book drill templates.
5. A cheat-sheet outline.
6. A Things-ready task breakdown when the user wants task management output.

## Lessons From The 15-445 Final Review Plan

In the 15-445 run, the useful pattern was:

1. Confirm the official final scope from the final guide: textbook chapters, lecture numbers, date/time/location, duration, point count, and allowed notes.
2. Treat the newest S26 practice final as the main diagnostic and solution source.
3. Split the exam into topic clusters: query processing/joins, transactions/MVCC, recovery/ARIES, distributed systems.
4. Attach each cluster to specific practice questions, homework backfills, older exam drills, and cheat-sheet blocks.
5. Make an error log the central artifact.
6. Schedule the final pass around redoing misses cold, completing the handwritten note page, and packing exam materials.
7. Import the resulting project into Things and verify that the tasks exist.

## Guardrails

- Never rely on forum posts as the source of truth for scope.
- Do not spend time on pre-scope or explicitly excluded content unless it is prerequisite knowledge for an in-scope procedure.
- Do not reread lectures passively when there are practice questions available.
- Do not build a plan without exact artifacts and completion criteria.
- When current course pages, forum posts, or online archives may have changed, browse or verify before citing them.
