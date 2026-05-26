# Learning Science Reference

Use these principles to design or adjust learning workflows.

## Evidence-Backed Defaults

### Retrieval Practice

Testing is not only assessment; it is a learning event. Prefer short-answer questions, explanation prompts, trace interpretation, and transfer questions over recognition-only checks.

Implementation:

- Teach a small unit.
- Ask the learner to explain or apply it without looking.
- Give corrective feedback.
- Log the exact misconception if the answer is weak.

Source anchors:

- Dunlosky et al. (2013): practice testing is high utility.
- Roediger & Karpicke (2006): retrieval after studying prose improved later retention.

### Distributed Practice and Successive Relearning

Spacing matters. Review should happen after a gap, and practice should continue until the learner can retrieve to criterion.

Implementation:

- Keep error items `open`, `review`, or `closed`.
- Review open items after time has passed or when the user asks.
- Close only after repeated correct retrieval in separate sessions.
- Do not force a rigid schedule that annoys the user.

Source anchors:

- Cepeda et al. (2006): spacing effects are broadly supported, with optimal gaps depending on retention interval.
- Rawson & Dunlosky (2022): successive relearning combines spaced sessions and retrieval to criterion, but cost-benefit matters.

### Formative Feedback

Feedback should answer: where is the learner going, how are they doing, and what should happen next. Feedback should explain the correction, not only mark right/wrong.

Implementation:

- Score answers with a transparent rubric.
- Write the corrected model.
- Add a next review action.
- Avoid generic praise or vague criticism.

Source anchors:

- Shute (2007): formative feedback varies by type and timing; effective feedback includes explanation, hints, or worked examples depending on task and learner.

### Cognitive Load

Learning complex technical material fails when working memory is overloaded by disorganized sources, unnecessary notation, scattered files, or too many simultaneous objectives.

Implementation:

- Convert sources into readable text.
- Create a reading sequence.
- Teach in small units.
- Use worked examples before independent problems for novices.
- Fade support as competence rises.

Source anchors:

- Sweller, van Merrienboer, & Paas (1998): instructional design should account for working-memory limits, intrinsic load, extraneous load, and schema construction.
- Kalyuga (2007): learner prior knowledge changes which instructional support helps; too much guidance can hurt advanced learners.

### Active Learning and ICAP

Do not confuse "interactive chat" with active learning. The learner must generate, explain, compare, debug, or transfer.

Implementation:

- Require the learner to explain in their own words.
- Ask transfer questions: "what tool next?", "what field/module does this become?", "what failure mode follows?"
- Prefer constructive and interactive activities over passive reading.

Source anchors:

- Freeman et al. (2014): active learning improved STEM outcomes in a large meta-analysis.
- Chi & Wylie (2014): ICAP orders engagement from passive to active to constructive to interactive.

## Critique of the Folder + Sources + Logs Pipeline

The pipeline is strong because it creates source grounding, retrieval, feedback, and cumulative error memory. It should be adjusted in four ways:

1. Do not over-collect. Start with a minimum viable corpus, then collect more when a question demands it.
2. Do not over-convert. Convert enough for AI use; keep raw originals and indexes rather than rewriting entire books.
3. Do not over-log. Log misconceptions that would cause future failure, not every stylistic weakness.
4. Do not over-schedule review. Use spaced review as a tool, but let the user trigger heavy review unless a deadline requires a plan.

## Practical Design Rule

A good learning workspace has exactly four persistent memories:

1. Source memory: what materials exist and where.
2. Goal memory: what the learner is trying to become able to do.
3. Progress memory: what has been covered and scored.
4. Error memory: what the learner got wrong and how to revisit it.

