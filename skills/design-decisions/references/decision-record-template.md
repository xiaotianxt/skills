# Decision Record Template

Use the smallest version that preserves the decision's evidence and rationale.
Delete headings that do not affect the choice.

## Compact Decision Note

```markdown
# <Decision>

Status: proposed | accepted | provisional | superseded
Date: YYYY-MM-DD

## Decision

Choose <option>.

## Context And Constraints

- Workload / scenario:
- Success:
- Unacceptable failure:
- Hard constraints:
- Reversibility:

## Decisive Comparison

| Criterion | Threshold or direction | Option A | Option B | Evidence / confidence |
| --- | --- | --- | --- | --- |
| <criterion> | <threshold> | <value> | <value> | <source or unknown> |

## Rationale

Choose A because <criterion/value/context>. B's strongest advantage is
<criterion/value>, but it matters less because <reason>.

## Risks And Revisit Triggers

- Residual risk:
- Follow-up:
- Reconsider if:
```

## Full Architecture Decision Record

```markdown
# ADR-NNN: <Decision title>

- Status: proposed | accepted | provisional | deprecated | superseded
- Date: YYYY-MM-DD
- Owners:
- Supersedes / superseded by:

## Decision Contract

Decision being made:

Out of scope:

Target workload, users, environment, and time horizon:

Success conditions:

Unacceptable outcomes:

Hard constraints and budgets:

Cost of reversal:

## Assumptions

| Assumption | If true | If false | Could flip decision? | Evidence / next check |
| --- | --- | --- | --- | --- |
| <A> | <effect> | <effect> | yes/no | <source or experiment> |

## Alternatives

### A. <Name>

One-sentence mechanism and boundary.

### B. <Name>

One-sentence mechanism and boundary.

### C. <Name>

One-sentence mechanism and boundary.

## Comparison

| Criterion | Kind | Definition / scenario | Threshold or direction | A | B | C | Evidence / confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <criterion> | gate/discriminator/operations | <meaning> | <threshold> | <value> | <value> | <value> | <source> |

Use `unknown` instead of a fabricated value. Add a focused evidence-gathering
action for unknowns that could change the result.

## Decision And Rationale

Choose <option>.

- Gate results:
- Decisive `(criterion, value, context)` tuples:
- Why these criteria dominate in this workload:
- Why the strongest rejected alternative lost:
- Sensitivity: what plausible change would flip the decision?

## Consequences

Positive consequences:

Negative consequences and residual risk:

Migration, rollback, or reversibility plan:

## Validation And Follow-Up

- Measurement, prototype, benchmark, or user test:
- Implementation checkpoint:
- Decision owner and date:

## Revisit Triggers

Reconsider this decision if any of the following occurs:

- workload or scale crosses <threshold>;
- assumption <A> is disproved;
- measured value <M> crosses <threshold>;
- constraint, vendor, regulation, or public contract changes;
- rollback or migration becomes materially cheaper or more expensive.
```

## Evidence Labels

Use labels only when they clarify uncertainty:

- **Measured:** observed directly in the relevant environment.
- **Derived:** follows from code, protocol, mathematics, or an explicit model.
- **Sourced:** stated by an authoritative document or stakeholder.
- **Estimated:** reasoned approximation with stated assumptions.
- **Unknown:** not yet known; attach a next check if it could be decisive.

Confidence is not a substitute for provenance. `High confidence` without a
source or derivation is still weak evidence.

## Rationale Test

A reviewer should be able to answer:

1. What choice was made?
2. Under which workload and constraints?
3. Which actual values ruled options in or out?
4. Why were those criteria more important than the losing option's advantages?
5. What new fact would cause reconsideration?

If the record cannot answer these questions, improve the decision semantics
rather than the document's appearance.
