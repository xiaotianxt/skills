# Skill Evolution Horizons

Skills are operational memory. They should improve when real work exposes a
repeatable judgment, failure mode, or workflow boundary that the next agent
should inherit.

The main discipline is not to make skills larger. It is to make useful behavior
more likely while keeping context, trigger scope, and maintenance cost small.

## Core Loop

After using a skill on real work, ask:

- Did the skill trigger at the right time?
- Did it shape the work in a way that changed the outcome?
- Did it miss a boundary, risk, validation step, or decision criterion?
- Is the lesson general enough to help outside this exact project?
- Should the lesson live in the skill body, a reference file, a script, or a
  repository-level document?
- Can an older rule be removed, narrowed, or moved out of the hot path?

Only update a skill when the answer changes future behavior. One-off facts,
project notes, and temporary decisions belong in project docs or issues.

## Short-Term: Per-Use Reflection

Short-term updates happen immediately after a skill is used.

Capture only durable deltas:

- Trigger improvements: clearer descriptions, exclusions, or prerequisites.
- Workflow corrections: steps that were missing, out of order, or too vague.
- Validation upgrades: commands, checks, or artifacts that caught real risk.
- Safety boundaries: secrets, private data, risky defaults, or public-surface
  leaks that should be guarded earlier.
- Naming and semantic clarity: words that made a domain boundary obvious or
  confusing.

Keep the edit small. Prefer a single rule, a tighter checklist item, or a link
to a narrow reference over a broad essay.

Do not capture:

- facts that only matter to one repository;
- implementation details that will age quickly;
- long explanations of why the previous attempt happened;
- lessons that merely restate normal engineering competence.

## Long-Term: Portfolio Governance

Long-term work keeps the skill set coherent as a system.

Review skills by responsibility:

- Governor skills define taste and risk posture, such as Rust systems style.
- Tool skills define exact command flows and local integration details.
- Product skills define repeatable shipping and release workflows.
- Companion skills add a narrow decision layer on top of another tool.

Avoid making every useful lesson global. A rule belongs higher in the portfolio
only when it applies across domains and improves default judgment without
making unrelated work noisier.

Watch for portfolio smells:

- overlapping skills that both claim the same trigger;
- broad skills that accumulate project-local folklore;
- tool skills that hide safety policy inside command recipes;
- governor skills that become style manifestos instead of review heuristics;
- scripts or references that are never used because discovery is unclear.

Maintenance should include deletion. A skill can become better by removing a
stale warning, collapsing duplicate guidance, or retiring an obsolete workflow.

## Far-Term: Evaluation And Evolution

Far-term work asks whether the skill system still improves outcomes.

Useful evaluation signals:

- agents choose the right skill without user correction;
- repeated tasks become shorter and safer;
- failures turn into targeted changes, not bigger documents;
- optional debug or diagnostic paths remain tested without entering normal
  release surfaces;
- private schemas, vendor names, secrets, and local data stay behind narrow
  boundaries;
- CI, dependency, and platform warnings are handled before deadline pressure.

For mature skills, use forward tests:

- run a realistic task with only the skill and normal repository context;
- inspect whether the agent took the intended path;
- compare behavior before and after the skill edit;
- keep raw traces or concise notes only when they reveal a reusable failure
  pattern.

The far horizon is portability. A good skill should survive model changes,
toolchain changes, and project churn because it encodes invariants, decision
criteria, and validation habits rather than memorized steps.

## Promotion Rules

Promote a lesson upward only when it clears the right bar:

- Project note: useful in one repository.
- Skill rule: reusable for one domain or tool.
- Governor rule: reusable across many tools or system boundaries.
- Repository policy: affects how skills are curated, installed, evaluated, or
  published.

If the level is unclear, keep the lesson lower and revisit after the next real
use.
