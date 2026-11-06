# SceneSteward Analytics Subsystem — Dashboard User Guide

Welcome to the SceneSteward Operational Intelligence & Consent Insights Dashboard. This guide walks directors, producers, and production teams through using the analytics interface.

---

## 1. Accessing the Dashboard

1. Navigate to the top navigation bar and click **Analytics** (or go to `/analytics`).
2. The user must be authenticated with an authorized role (`admin`, `director`, `producer`, or `crew`).
3. If signed in as a `participant`, the analytics interface displays an ethical boundary access denial, directing you to your personal participant care portal.

---

## 2. Global Controls & Filters

At the top of the analytics dashboard, the control bar allows real-time scoping:

- **Project Selector**:
  - `All Projects`: Aggregates metrics across all productions accessible to your account.
  - *Specific Project*: Limits all metrics, charts, and exports strictly to the selected documentary project.
- **Time Range Selector**:
  - `All Time`: Evaluates all recorded project data.
  - `Last 7 Days`: Scopes activity and metrics to the past week.
  - `Last 30 Days`: Evaluates 30-day operational velocity and trends.
  - `Last 90 Days`: Quarterly production review.
- **Refresh Button**:
  - Re-executes live database queries and updates all metrics instantly.
- **Export Report Button**:
  - Opens the Report Export dialog to generate downloadable CSV or JSON reports.

---

## 3. Executive KPI Cards

The top section provides an at-a-glance health check of the production:

- **Active Participants**: Total individuals currently tracked in the documentary production.
- **Discussion Coverage**: Percentage of all 15 canonical categories with an explicitly recorded discussion status ($N \times 15$ basis).
- **Overall Approval Rate**: Percentage of applicable categories granted explicit consent (`agreed`).
- **Resolution Rate**: Percentage of categories with a definitive conclusion (`agreed` or `declined`).
- **Pending Reviews**: Editorial queue items awaiting human review.
- **Open Operational Tasks**: Crew tasks pending completion (with badge highlighting urgent tasks).
- **Active Withdrawals**: Critical alerts if any participant has requested withdrawal or revocation.

---

## 4. Dashboard Tabs

The analytics dashboard is organized into four intuitive tabs:

### Tab 1: Overview
- **Production Status Summary**: High-level comparison across consent, reviews, and operations.
- **Active Projects Portfolio**: When viewing "All Projects", displays individual project cards summarizing participants, coverage, approval rates, and pending reviews.
- **Quick Links**: Direct shortcuts to project detail views.

### Tab 2: Consent & 15 Categories
- **Metric Definitions Banner**: Explains the mathematical definitions of coverage, approval, and resolution rates.
- **Category Progress Matrix**: A visual breakdown of all 15 canonical categories:
  - Multi-colored segmented progress bars representing agreed (green), declined (red), undecided (yellow), and not discussed (slate).
  - Individual coverage and approval percentages per category.
  - Highlights categories requiring urgent editorial or interview follow-up.

### Tab 3: Reviews & Operations
- **Human Review Pipeline**:
  - Breakdown by review status (`approved`, `pending`, `in_review`, `changes_requested`, `rejected`).
  - Average review turnaround time in hours.
  - Editorial completion rate percentage.
- **Operational Task & Participant Care**:
  - Task status distribution (`open`, `in_progress`, `completed`, `blocked`).
  - Urgent task alerts.
  - Interview status tracking (`scheduled`, `in_progress`, `completed`).
  - Participants with open action items.
- **Withdrawal & Revocation Triage**:
  - Active and confirmed withdrawals.
  - Triage urgency breakdown (High, Medium, Low).

### Tab 4: AI Advisory & Trends
- **AI Advisory vs Human Review Concordance**:
  - Concordance rate (%) measuring how frequently human editorial decisions align with AI advisory classifications.
  - Total advisories evaluated and average AI confidence score.
  - Explicit disclaimer: *AI recommendations are strictly advisory and do not constitute authorized consent without human clearance.*
- **Activity Trends Time-Series Chart**:
  - Responsive multi-line chart visualizing production velocity over time.
  - Tracks daily/weekly consent records created, reviews completed, and tasks resolved.

