# Gradescope Page Reading

Read this reference for online assignments, submitted answers, grading views,
and autograder/test-result pages. The selectors and failure modes below were
validated on a logged-in Gradescope online assignment and its submitted view on
2026-08-28; prefer semantic labels when Gradescope markup changes.

## Proven Blind Spots

- `innerText` lists every radio choice but does not encode which choice is
  checked. Accessibility output may expose only the save buttons, not values.
- In the submitted view, checked radio buttons are the selected answers.
  Disabled state is not a substitute: observed unselected choices were disabled
  while selected choices were not.
- The submitted view can contain both full question bodies and a second
  submission outline. Count leaf questions once.
- On an online assignment, the screen-reader text `Grading comment:` can label
  the student's displayed response. Treat text as grader feedback only when its
  surrounding rubric/feedback semantics support that interpretation.
- `/submissions/new` can contain already-saved answers and link to a submitted
  attempt. “new” in the path does not prove the page is blank or unsubmitted.
- `Ungraded` and `- / N pts` mean no released score, not zero points.
- Presentation buttons such as `Submission History` may open a dialog without
  exposing `aria-expanded`. Detect the new dialog/content, then read it with
  `get_page_text` or `read_page(filter:"all")`; the interactive-only tree can
  omit table rows.

## Online Assignment DOM

Use these as hints, with visible headings and control labels as fallbacks:

- Leaf question: `.onlineAssignment--question` excluding
  `.onlineAssignment--question-parent`.
- Question title/number: `.questionHeading--title`.
- Possible points: `.questionHeading--points`.
- Editable response: non-hidden `input`, `textarea`, or `select` inside the leaf
  question.
- Selected choice: `input[type=radio]:checked` or
  `input[type=checkbox]:checked`; resolve its text through `element.labels` or
  the nearest `label`.
- Read-only written response:
  `.form--textInput-readOnly, .form--textArea-readOnly`.
- Saved timestamp: `.question--submittedAt` when present.
- Nested question group: a container with
  `.onlineAssignment--question-parent`; do not count it as another answered
  leaf.

Run this small page-state snapshot before extracting individual questions:

```javascript
(() => {
  const clean = value => (value || "").trim().replace(/\s+/g, " ");
  const body = document.body.innerText;
  const answered = body.match(/(\d+)\s*\/\s*(\d+)\s*Questions Answered/i);
  const score = body.match(/(-|\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)\s*pts/i);
  const saved = body.match(/Saved\s+on\s+([^\n]+)/i);
  const actionNodes = new Set(document.querySelectorAll(
    "form button, form a, button.actionBar--action, a.actionBar--action"
  ));

  return {
    title: document.title,
    path: location.pathname,
    assignment: clean(document.querySelector("h1")?.innerText),
    answered: answered ? { current: +answered[1], total: +answered[2] } : null,
    gradingState: /\bUngraded\b/i.test(body)
      ? "ungraded"
      : score && score[1] !== "-"
        ? "graded"
        : "unknown",
    score: score ? { earned: score[1], possible: score[2] } : null,
    savedAt: saved ? clean(saved[1]) : null,
    actions: [...actionNodes]
      .map(node => clean(node.innerText || node.getAttribute("aria-label")))
      .filter(text => /save|submit|resubmit|regrade|history/i.test(text))
      .filter((text, index, values) => values.indexOf(text) === index),
  };
})()
```

The following `javascript_tool` expression is read-only. It inventories leaf
questions and preserves answer state that text extraction loses:

```javascript
(() => {
  const clean = value => (value || "").trim().replace(/\s+/g, " ");
  const label = control => clean(
    control.labels?.[0]?.innerText || control.closest("label")?.innerText
  );
  const numberOf = title =>
    title.match(/^Q(?:uestion\s+)?(\d+(?:\.\d+)*)\b/i)?.[1] || "";
  let parent = null;
  const questions = [...document.querySelectorAll(".onlineAssignment--question")]
    .flatMap(node => {
      const title = clean(node.querySelector(".questionHeading--title")?.innerText);
      const number = numberOf(title);
      if (node.classList.contains("onlineAssignment--question-parent")) {
        parent = { number, title };
        return [];
      }
      const parentGroup = parent && number.startsWith(`${parent.number}.`)
        ? parent.title
        : "";
      if (!parentGroup) parent = null;
      return [{ node, number, parentGroup }];
    });

  return {
    title: document.title,
    path: location.pathname,
    questions: questions.map(({ node, number, parentGroup }) => {
      const controls = [...node.querySelectorAll(
        'input:not([type="hidden"]), textarea, select'
      )];
      const choices = controls
        .filter(control => control.type === "radio" || control.type === "checkbox")
        .map(control => ({
          text: label(control),
          selected: control.checked,
          disabled: control.disabled,
        }));
      const written = controls.find(control =>
        control.tagName === "TEXTAREA" ||
        control.tagName === "SELECT" ||
        ["text", "number", "email", "url"].includes(control.type)
      );
      const readOnly = node.querySelector(
        ".form--textInput-readOnly, .form--textArea-readOnly"
      );
      const prompt = [...node.querySelectorAll(".markdownText.u-preserveWhitespace")]
        .filter(part => !part.closest(".form--choice"))
        .map(part => clean(part.innerText))
        .filter(Boolean);

      return {
        number,
        parentGroup,
        title: clean(node.querySelector(".questionHeading--title")?.innerText),
        points: clean(node.querySelector(".questionHeading--points")?.innerText),
        prompt,
        responseType: choices.length
          ? controls.some(control => control.type === "checkbox")
            ? "checkbox"
            : "radio"
          : written?.tagName === "TEXTAREA"
            ? "textarea"
            : written
              ? "text"
              : readOnly
                ? "read-only-text"
                : "unknown",
        answer: choices.length
          ? choices.filter(choice => choice.selected).map(choice => choice.text)
          : written?.value ?? clean(readOnly?.innerText),
        controlState: written
          ? { disabled: written.disabled, readOnly: written.readOnly }
          : readOnly
            ? { disabled: true, readOnly: true }
            : null,
        choices,
        savedAt: clean(node.querySelector(".question--submittedAt")?.innerText),
      };
    }),
  };
})()
```

Check the returned question count against the page's answered summary. If no
`.onlineAssignment--question` nodes exist, the page is another Gradescope type;
fall back to headings, accessibility controls, and the test-result procedure
below instead of broadening the selectors blindly.

## Submission And Grading Views

1. Capture assignment title, attempt identity, submitted time, state, and total
   exactly as displayed.
2. Read each full question body. Ignore the later submission outline when it
   repeats question titles and possible points.
3. Recover selected choices from `:checked`; recover written responses from the
   read-only response selectors above.
4. Classify score, rubric selection, and grader feedback only from explicit
   score/rubric/feedback containers or labels. Do not relabel the student's
   response because nearby screen-reader text says `Grading comment:`.
5. If the page is ungraded, preserve possible points but leave earned points
   unknown.

## Autograder And Test Results

Autograder markup varies by assignment. Use semantics before CSS selectors:

1. Locate headings, rows, tabs, or buttons containing `Autograder`, `Tests`,
   `Test Cases`, `Results`, `Output`, `stdout`, `stderr`, `Expected`, or
   `Actual`.
2. Read `aria-expanded` and nearby test/group labels. Expand only controls that
   reveal presentation content; never activate `Resubmit`, `Rerun`, or similar
   state-changing actions.
3. After each expansion, reread with `get_page_text` or
   `read_page(filter:"all")`, then record test group/name, visible status,
   earned/possible points, and released diagnostics.
4. Keep three states distinct: empty output, output not rendered, and output
   intentionally hidden.
5. Do not use network bodies, page scripts, or guessed endpoints to recover
   hidden tests or unreleased feedback.

## Final Reconciliation

- Question/test count matches the page summary or discrepancies are explicit.
- Selected choices come from `checked`, never from visual order or `disabled`.
- Draft, saved, submitted, ungraded, and graded states remain distinct.
- Possible points are not reported as earned points.
- Duplicate outline entries are excluded.
- Edit/submitted answer comparisons ignore presentation-only whitespace.
- Sensitive identifiers and full answer text are omitted unless the user needs
  them.
