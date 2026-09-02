---
name: design-decisions
description: "Structure consequential design, architecture, implementation, product, policy, build-vs-buy, and tool-selection decisions by comparing multiple viable options against concrete evidence and writing a defensible rationale. Use when trade-offs, uncertain assumptions, hard constraints, or multiple plausible approaches matter; when a user asks what to choose or why; or when producing or challenging an ADR. Skip trivial, cosmetic, or cheaply reversible choices."
---

# Design Decisions

Use this skill as a cross-domain design governor, not as a scoring worksheet.
The goal is to make a choice inspectable, evidence-driven, and easy to revisit.

The presentation is flexible. A Markdown table, bullets, a diagram, JSON, or an
ADR can all work. Preserve this semantic structure:

> viable options × concrete criteria → evidence → explicit rationale

The matrix helps think; it does not make the decision.

## Right-Size The Analysis

Use the full workflow when a decision is expensive to reverse, has meaningful
failure or security consequences, affects a public contract, contains decisive
unknowns, or has several credible approaches.

Use a compact comparison for moderate, reversible decisions. Make trivial,
cosmetic, or cheaply reversible choices directly instead of manufacturing a
matrix. Decision rigor should reduce risk, not create ceremony.

## Workflow

### 1. Define The Decision Contract

Before comparing solutions, state:

- the exact decision being made now;
- the target workload, users, environment, and time horizon;
- success and unacceptable failure;
- hard constraints and budgets;
- what is explicitly out of scope;
- how costly the choice is to reverse.

Do not silently turn preferences into constraints. Distinguish facts,
estimates, preferences, and unknowns.

Handle assumptions by consequences rather than by asking for permission:

1. If assumption A is true, what changes?
2. If A is false, what changes?
3. Does the preferred option change?

If the choice is unchanged, the assumption is not currently decisive. If the
choice flips, investigate or test A before committing when practical.

### 2. Generate Real Alternatives

Compare at least two genuinely viable approaches. Include the status quo,
simplest baseline, hybrid, staged, or reversible option when relevant.

Do not construct one working proposal and several strawmen. If only one option
passes an obvious `works at all` row, continue designing unless an external hard
constraint truly leaves no alternative. Partial proposals may remain during
brainstorming when they reveal a better design, but do not present them as equal
finalists.

### 3. Choose Decision-Relevant Criteria

Use criteria that expose differences under the stated workload. Separate:

- **Gates:** non-negotiable requirements or unacceptable thresholds.
- **Discriminators:** latency, cost, complexity, capacity, usability, accuracy,
  or other values on which viable options differ.
- **Operational consequences:** failure behavior, observability, security,
  privacy, maintainability, migration cost, reversibility, and blast radius.

For each criterion, define as many of these as matter:

- precise meaning;
- direction of preference;
- unit or bounded scale;
- scenario or workload;
- unacceptable threshold.

Prefer measured numbers, explicit units, asymptotic behavior, and concrete
states. Defined qualitative scales and booleans are acceptable when they retain
meaning. Treat vague labels such as `simple`, `robust`, `flexible`, `elegant`,
`handles resources`, or `solves the problem` as prompts to define what would be
observed.

Keep only criteria that could affect the choice. More rows are not inherently
more rigorous.

### 4. Populate Values With Evidence

Evaluate every finalist against the same criteria. Label values when useful as:

- measured;
- derived;
- sourced;
- estimated;
- unknown.

Preserve provenance and confidence for decisive claims. Never invent a value to
complete the matrix, and do not hide uncertainty behind precise-looking scores.
An unknown is useful when it identifies the next measurement, prototype,
benchmark, document check, or user test.

Use tools and domain skills to gather evidence when the result could change the
decision. Do not ask the user for information that is already available in the
workspace or authoritative sources.

### 5. Iterate Through Missing Rows And Columns

When the comparison does not support a choice, diagnose why:

- Missing row: an important consequence or threshold is not represented.
- Missing column: another architecture, hybrid, baseline, or staged option is
  needed.
- Missing value: research or a focused experiment is needed.
- Wrong scope: the workload, boundary, or time horizon is underspecified.

Adding a row or column should trigger useful research, not decorative expansion.
If two choices are close, test the uncertain criterion most likely to flip the
outcome. If small plausible changes flip the result, report the decision as
sensitive rather than certain.

### 6. Decide By Gates And Priorities

Apply hard gates first. Among remaining options, identify the decisive
`(criterion, value, context)` tuples and explain their priority.

Do not:

- count green and red cells;
- vote by number of advantages;
- default to an arbitrary weighted sum;
- treat every criterion as equally important;
- claim that the winner was the only correct solution.

A weighted utility model is appropriate only when the weights and normalization
have real semantics and stakeholders accept the implied trade-offs. It must not
hide veto conditions, uncertainty, or a criterion that dominates in the target
workload.

Prefer rationales of these forms:

- Option B is rejected because its value V on criterion M crosses threshold T
  under workload W.
- Option A is preferred because `(M1, V1)` matters more in context C than its
  disadvantage `(M2, V2)`.
- A reversible option is chosen temporarily because the decisive value is still
  unknown; experiment E will resolve it by date D.

### 7. Record The Decision

Produce a concise decision record containing:

1. decision and status;
2. context, workload, and constraints;
3. viable alternatives considered;
4. decisive evidence;
5. choice and rationale;
6. why the strongest alternatives lost;
7. assumptions and residual risks;
8. follow-up actions;
9. evidence or conditions that should trigger reconsideration.

The accumulated comparisons and rationales become the design document. Read
[references/decision-record-template.md](references/decision-record-template.md)
when a durable ADR or reusable decision artifact is requested.

## Stop Conditions

Stop analysis when:

- multiple credible options have been considered, or the reason only one exists
  is explicit;
- hard gates have been evaluated;
- decisive unknowns are resolved enough for the decision's reversibility and
  stakes;
- the rationale identifies actual values and priorities;
- residual risk and revisit triggers are recorded.

Do not continue merely to make the artifact look comprehensive. Under a real
deadline, prefer an explicitly provisional, reversible choice over false
certainty.

## Output Contract

Lead with the recommendation when the user asked for one. Then show only the
evidence needed to audit it. A normal response should contain:

- **Decision**
- **Context and constraints**
- **Options considered**
- **Decisive comparison**
- **Rationale**
- **Risks / unknowns**
- **Revisit when**

Use a table only when it improves comparison. If the user requests prose, retain
the same semantics in bullets. Report evidence and concise rationale; do not
pad the answer with performative deliberation.

## Guardrails

- Do not substitute a pros-and-cons list for common criteria.
- Do not confuse formatting quality with decision quality.
- Do not smuggle a preferred answer into criteria, thresholds, or estimates.
- Do not bury a hard constraint inside an average score.
- Do not compare options under different workloads without saying so.
- Do not optimize only the happy path; include relevant failure and operational
  behavior.
- Do not let sunk cost decide among current alternatives.
- Do not turn every engineering choice into an ADR.
- Do not replace domain expertise, security review, experiments, or user
  research with a matrix.

## Relationship To Other Skills

This skill owns decision structure. Domain and tool skills supply the criteria,
evidence, execution workflow, and validation details. Apply both when needed.
For example, `rust-systems-style` can govern systems-code invariants and risk
while this skill makes an explicit choice among competing designs.
