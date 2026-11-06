# SceneSteward — Analytics Metric Dictionary & Registry

**Status:** Authoritative Specification  
**Date:** 2026-11-06  
**Auditors:** Principal Software Architect, Application Security Lead, QA Lead  
**Scope:** Metric Definitions, Mathematical Formulas, Boundaries, Deduplication & Null Handling  

---

## 1. Registry Invariants & Principles

Every metric displayed in the SceneSteward dashboard or exported in reports strictly adheres to these definitions:

1. **Non-Equivalence of Absence and Approval:** An absent record or `not_discussed` status is mathematically distinct from `agreed`.
2. **Explicit Denominators:** Denominators for percentage calculations are derived exclusively from actual applicable entities (e.g. $N_{\text{participants}} \times 15$ canonical categories).
3. **No Synthetic Backfilling:** Missing historical timestamps or unrecorded data yield `null` or explicit `0`, never fabricated interpolations.

---

## 2. Project & Portfolio Metrics

### `PRJ-01`: Total Projects
- **Formula:** $\text{COUNT}(\text{DISTINCT } \text{projects.id})$ where user has active membership in `project_memberships`.
- **Source:** `projects` JOIN `project_memberships` ON `projects.id = project_memberships.project_id`.
- **Filters:** `project_memberships.user_id = :current_user_id`, `project_memberships.membership_status = 'active'`.
- **Null Handling:** Returns `0` if user belongs to no projects.

### `PRJ-02`: Active Projects
- **Formula:** $\text{COUNT}(\text{DISTINCT } \text{projects.id})$ WHERE `status = 'active'`.
- **Purpose:** Identifies ongoing documentary productions currently capturing footage or seeking consent clearances.

### `PRJ-03`: Completed Projects
- **Formula:** $\text{COUNT}(\text{DISTINCT } \text{projects.id})$ WHERE `status = 'completed'`.
- **Purpose:** Documentary projects that have reached final release lock and completed their festival / distribution run.

---

## 3. Participant Roster Metrics

### `PRT-01`: Total Participants
- **Formula:** $\text{COUNT}(\text{DISTINCT } \text{participants.id})$ within the scoped project(s).
- **Source:** `participants`.
- **Purpose:** Overall size of the documentary contributor roster.

### `PRT-02`: Active Participants
- **Formula:** $\text{COUNT}(\text{participants.id})$ WHERE `participant_status = 'active'`.
- **Purpose:** Contributors whose interview, likeness, or private materials are actively being edited or reviewed.

### `PRT-03`: Withdrawn Participants
- **Formula:** $\text{COUNT}(\text{participants.id})$ WHERE `participant_status = 'withdrawn'`.
- **Purpose:** Participants who have formally revoked participation from the project.

---

## 4. Consent Coverage & Category Metrics

### `CNS-01`: Discussion Coverage Rate (%)
- **Definition:** The percentage of applicable consent categories that have been actively discussed and recorded (whether agreed, declined, explained, or in need of clarification) across all active participants.
- **Formula:**
  $$\text{Discussion Coverage} = \frac{\sum \text{Discussed Category Choices}}{\text{Total Active Participants} \times 15} \times 100$$
  where $\text{Discussed Choice} \in \{\text{'agreed'}, \text{'declined'}, \text{'needs\_clarification'}, \text{'explained'}, \text{'awaiting\_confirmation'}\}$.
- **Source:** Latest confirmed `consent_records` and `consent_choices`.
- **Zero Case:** If $\text{Total Active Participants} = 0$, returns `0.0`.

### `CNS-02`: Explicit Approval Rate (%)
- **Definition:** The proportion of applicable categories where the participant explicitly granted permission (`choice = 'agreed'`).
- **Formula:**
  $$\text{Approval Rate} = \frac{\sum \text{Choices with choice = 'agreed'}}{\text{Total Active Participants} \times 15} \times 100$$
- **Distinction:** Never includes `not_discussed`, `needs_clarification`, or absent records.

### `CNS-03`: Resolution Rate (%)
- **Definition:** The proportion of applicable categories that have reached a definitive conclusion (`agreed` or `declined`).
- **Formula:**
  $$\text{Resolution Rate} = \frac{\sum \text{Choices with choice } \in \{\text{'agreed'}, \text{'declined'}\}}{\text{Total Active Participants} \times 15} \times 100$$
- **Purpose:** Measures the certainty of production rights clearances.

### `CNS-04`: Unresolved Categories Count
- **Formula:** $(\text{Total Active Participants} \times 15) - \sum \text{Choices with choice } \in \{\text{'agreed'}, \text{'declined'}\}$.
- **Purpose:** The total number of open questions or clearance hurdles remaining before picture lock.

---

## 5. Proposed-Use & Human Review Metrics

### `REV-01`: Total Proposed Uses
- **Formula:** $\text{COUNT}(\text{proposed_uses.id})$ within project scope.
- **Source:** `proposed_uses`.

### `REV-02`: Pending Human Reviews
- **Formula:** $\text{COUNT}(\text{reviews.id})$ WHERE `review_status = 'pending'` AND `reviewer_type = 'human'`.
- **Source:** `reviews`.
- **Purpose:** Reviews in the active queue awaiting human editorial or legal decision.

### `REV-03`: Completed Reviews
- **Formula:** $\text{COUNT}(\text{reviews.id})$ WHERE `review_status = 'completed'`.

### `REV-04`: Average Review Turnaround (Hours)
- **Formula:** $\text{AVG}(\text{EXTRACT(EPOCH FROM (decided_at - created_at))} / 3600.0)$ for completed reviews with valid timestamps.
- **Source:** `reviews`.

---

## 6. Participant Care & Operational Task Metrics

### `OPS-01`: Urgent Care Tasks
- **Formula:** $\text{COUNT}(\text{tasks.id})$ WHERE `priority = 'urgent'` AND `status IN ('open', 'in_progress', 'blocked')`.
- **Purpose:** High-priority items (such as participant withdrawal notices or critical safety concerns) requiring immediate intervention.

### `OPS-02`: Open Follow-Up Tasks
- **Formula:** $\text{COUNT}(\text{tasks.id})$ WHERE `task_type = 'participant_follow_up'` AND `status IN ('open', 'in_progress')`.

### `OPS-03`: Overdue Tasks
- **Formula:** $\text{COUNT}(\text{tasks.id})$ WHERE `due_at < NOW()` AND `status IN ('open', 'in_progress', 'blocked')`.
- **Purpose:** Identifies operational backlog exceeding production commitments.

---

## 7. Advisory Agent Operational Metrics

### `ADV-01`: Total Advisory Runs
- **Formula:** $\text{COUNT}(\text{agent_runs.id})$ within project scope.

### `ADV-02`: Agent Alignment Rate (%)
- **Definition:** Percentage of human review decisions that concorded with the structured advisory recommendation from agent runs on the same proposed use.
- **Explicit Invariant & Disclaimer:**
  > [!IMPORTANT]
  > AI advisory outputs are strictly informational. Human decisions are authoritative. High or low agreement rates reflect workflow concordance, not legal validity or ethical correctness.

