# SceneSteward Analytics Subsystem — Data Quality & Trust Model

This document specifies the data integrity principles, mathematical invariants, and zero-fabrication standards enforced by the SceneSteward Analytics Engine.

---

## 1. Core Trust Invariants

In documentary production and legal clearance workflows, analytics data directly informs whether footage can be safely exhibited, broadcast, or distributed. Misrepresenting consent, conflating lack of discussion with approval, or relying on unverified AI recommendations creates severe legal and ethical liabilities.

The SceneSteward Analytics Engine enforces four cardinal trust invariants:

### Invariant 1: Silence is Never Consent
- If a category is omitted from discussions, absent from recorded interviews, or has no recorded decision, it is classified as `not_discussed`.
- `not_discussed` and `undecided` are strictly excluded from the numerator of `approval_rate`.
- Missing participant records are never defaulted to approved.

### Invariant 2: Mathematical Precision & Denominator Completeness
- Denominator for all platform/project consent calculations:
  $$\text{Total Applicable Choices} = N_{\text{active\_participants}} \times 15$$
- Every participant has 15 canonical categories governed by policy.
- The state breakdown for any category or cohort must sum exactly to the applicable total:
  $$\text{Agreed} + \text{Declined} + \text{Undecided} + \text{Not Discussed} = \text{Total Applicable Choices}$$

### Invariant 3: Single Source of Truth via Live SQL Aggregation
- All metrics are calculated dynamically using live PostgreSQL queries against current operational tables (`consent_records`, `participants`, `interviews`, `human_reviews`, `tasks`, `withdrawals`).
- There are no disconnected cache stores, fake background aggregators, or out-of-sync read replicas.
- When an editorial team updates a review or a participant files a withdrawal, the dashboard reflects the change on the subsequent query.

### Invariant 4: AI is Strictly Advisory
- AI extractions and suggested classifications are recorded with status `needs_review` or advisory confidence scores.
- AI proposals are never counted as approved consent until an authorized human reviewer (`admin`, `director`, or `producer`) marks the review as `approved`.
- The UI and API clearly distinguish between AI advisory suggestions and final human clearances, displaying an explicit compliance disclaimer.

---

## 2. Metric Verification Formulae

| Metric | Formula | Semantic Meaning |
| :--- | :--- | :--- |
| **Discussion Coverage Rate** | $\frac{\text{Discussed Categories}}{N_{\text{participants}} \times 15} \times 100$ | Percentage of possible category questions actively asked and recorded. |
| **Approval Rate** | $\frac{\text{Agreed Categories}}{N_{\text{participants}} \times 15} \times 100$ | Percentage of all possible categories explicitly approved by participants. |
| **Resolution Rate** | $\frac{\text{Agreed} + \text{Declined}}{N_{\text{participants}} \times 15} \times 100$ | Percentage of categories with a definitive conclusion (yes or no). |
| **Review Completion Rate** | $\frac{\text{Approved} + \text{Rejected}}{\text{Total Reviews}} \times 100$ | Human editorial review throughput. |
| **Advisory Concordance Rate** | $\frac{\text{Human Matches}}{\text{Total Concluded Human Reviews}} \times 100$ | Agreement rate between automated AI suggestions and human determinations. |

---

## 3. Data Integrity and Latest Record Deduplication

Participants may have multiple consent records over time (e.g. preliminary interview, follow-up clarification, re-negotiation).

To prevent stale or duplicate records from corrupting analytics calculations:
- The analytics queries employ a PostgreSQL `DISTINCT ON (participant_id, category)` or `ROW_NUMBER() OVER (PARTITION BY participant_id, category ORDER BY created_at DESC)` subquery pattern.
- Only the **most recent confirmed consent state** for each participant and category is evaluated in aggregate metrics.
- Historical consent records remain preserved in the audit log for legal provenance.

---

## 4. Handling Edge Cases and Empty States

1. **Zero Participants ($N = 0$)**:
   - Division by zero is safeguarded at the SQL and Python layers.
   - If $N = 0$, `discussion_coverage_rate = 0.0`, `approval_rate = 0.0`, `resolution_rate = 0.0`.
2. **Missing Dates**:
   - Open intervals default to full available project history.
3. **Partial Discussions**:
   - If an interview covers 3 out of 15 categories, the remaining 12 are counted in `not_discussed`.

