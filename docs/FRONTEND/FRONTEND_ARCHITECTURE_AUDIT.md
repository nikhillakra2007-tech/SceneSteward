# SceneSteward Frontend Subsystem — Architecture Audit & Route Inventory

This document provides a comprehensive engineering audit of the SceneSteward Next.js frontend application as of Mission 34.

---

## 1. System Overview

- **Framework**: Next.js 14.2.35 (App Router)
- **UI Library**: React 18.3.1
- **Styling**: Tailwind CSS 3.4.17 with PostCSS and custom dark-theme tokens
- **Icons**: Lucide React 0.460.0
- **TypeScript**: Strict configuration (`tsconfig.json`)
- **API Client**: Centralized native client in `frontend/src/lib/api.ts` connecting to FastAPI backend
- **Authentication**: JWT Bearer tokens persisted in `localStorage` under key `scenesteward_token`

---

## 2. Route Inventory & Component Audit

### Route 1: `/` (Home / Landing Page)
- **Path**: `frontend/src/app/page.tsx`
- **Page Purpose**: Platform overview, ethical mission statement, non-transitive consent invariants, backend connectivity status, and quick access to active projects.
- **Intended User Roles**: Public, All authenticated production roles (Director, Producer, Care Lead, Legal, Crew).
- **API Dependencies**:
  - `api.getMe()`: Validates current token and fetches user profile.
  - `api.listProjects()`: Loads project summaries for authenticated users.
  - `api.getMetrics()`: Checks live backend health and connectivity status.
- **Components Used**:
  - `Navbar`: Header and authentication control.
  - Tailwind hero sections, gradient cards, Lucide icons (`ShieldCheck`, `Film`, `Users`, `Lock`, `AlertTriangle`, `CheckCircle2`, `ArrowRight`, `Server`).
- **Actions Available**:
  - Navigate to `/projects`.
  - Open project detail workspace cards.
  - View live backend connection state.
- **Loading Behavior**: Spinner/skeleton state while loading user session and metrics.
- **Error Behavior**: Graceful fallback to unauthenticated welcome state if token is missing or expired; connectivity indicator reflects offline/standalone state without crashing.
- **Empty-State Behavior**: Displays descriptive message explaining how to create the first project workspace.
- **Responsive Behavior**: Responsive grid (`grid-cols-1 md:grid-cols-3` for principles; `grid-cols-1 md:grid-cols-2 lg:grid-cols-3` for projects).
- **Existing Test Coverage**: Covered in Playwright E2E suites (`workflow.spec.ts`, `staging_e2e_acceptance.spec.ts`).
- **Identified Weaknesses**:
  - Relied on static text for dev quick-login guidance.
  - Lacked unified toast notifications for authentication state changes.

---

### Route 2: `/projects` (Project Portfolio Workspace)
- **Path**: `frontend/src/app/projects/page.tsx`
- **Page Purpose**: Central index of all documentary projects accessible to the authenticated user.
- **Intended User Roles**: Authenticated roles (`project_owner`, `director`, `producer`, `care_lead`, `legal_counsel`, `crew`).
- **API Dependencies**:
  - `api.listProjects()`: Fetches project records scoped by PostgreSQL RLS.
  - `api.createProject()`: Submits new project workspace metadata.
- **Components Used**:
  - `Navbar`
  - Project card grid
  - New project modal form
- **Actions Available**:
  - View all projects.
  - Search/filter projects.
  - Create new documentary project.
  - Navigate to individual project workspaces (`/projects/[id]`).
- **Loading Behavior**: Loading message during initial fetch.
- **Error Behavior**: Banner displaying error details if API fails or authentication is missing.
- **Empty-State Behavior**: Dedicated card with call-to-action button to create first project.
- **Responsive Behavior**: Flex header and multi-column grid adapting from 1 column on mobile to 3 columns on desktop.
- **Identified Weaknesses**:
  - Form submission failure previously triggered browser `alert()`.
  - Lacked client-side project search filtering.
  - Modal lacked accessible dialog semantics (`role="dialog"`, `aria-modal="true"`, Escape key handling).

---

### Route 3: `/projects/[id]` (Documentary Production Workspace)
- **Path**: `frontend/src/app/projects/[id]/page.tsx`
- **Page Purpose**: Comprehensive operational workspace for a documentary production. Manages participant rosters, canonical consent records across 15 categories, release document uploads with antivirus status, proposed uses and automated comparison engine analysis, human review decision queues, operational tasks, participant care communications, and immutable audit timeline.
- **Intended User Roles**: Project Owner, Director, Producer, Care Lead, Legal Counsel, Crew.
- **API Dependencies**:
  - `api.getProject(id)`
  - `api.listParticipants(id)`
  - `api.createParticipant(id, data)`
  - `api.getParticipantConsents(participantId)`
  - `api.createConsentRecord(participantId, data)`
  - `api.listDocuments(id)`
  - `api.createUploadUrl(participantId, data)`
  - `api.completeUpload(participantId, data)`
  - `api.extractDocument(documentId)`
  - `api.listProposedUses(id)`
  - `api.createProposedUse(id, data)`
  - `api.analyseProposedUse(useId)`
  - `api.getAgentFindings(useId)`
  - `api.listReviews(id)`
  - `api.recordHumanDecision(reviewId, data)`
  - `api.listTasks(id)`
  - `api.updateTask(taskId, data)`
  - `api.listCommunications(id)`
  - `api.createDraftCommunication(id, data)`
  - `api.approveCommunication(commId)`
  - `api.sendCommunication(commId)`
  - `api.issueParticipantToken(participantId)`
  - `api.getProjectTimeline(id)`
- **Components Used**:
  - `ChoiceBadge`, `OutcomeBadge`
  - 9 Tab panels (Overview, Participants, Consents, Documents, Proposed Uses, Reviews, Tasks, Communications, Timeline)
  - 4 Modals (Add Participant, Record Consent, Propose Use, Upload Document)
- **Actions Available**:
  - Register participants with preferred language and contact methods.
  - Record 15-category consent choices.
  - Submit proposed footage uses and execute 63-matrix comparison engine.
  - View advisory agent findings.
  - Record human review decisions with mandatory rationale.
  - Upload scanned release agreements (ClamAV verified).
  - Update task progress and urgency flags.
  - Draft and approve participant care messages.
  - Generate signed participant portal access links.
  - Inspect cryptographic audit timeline.
- **Identified Weaknesses**:
  - Multiple `alert()` calls for errors and successes.
  - Sending communications failed closed with a raw error rather than an explanatory UI message explaining that external SMTP/SMS providers are not configured.
  - Modal overlays lacked focus restoration and keyboard escape handling.
  - Participant and task tables lacked search/filter controls.

---

### Route 4: `/participant/[id]` (Participant Dignity & Transparency Portal)
- **Path**: `frontend/src/app/participant/[id]/page.tsx`
- **Page Purpose**: Participant-facing self-service portal. Allows documentary participants to review their recorded consent choices across all 15 canonical categories, understand ethical invariants, switch languages (English / Hindi), submit clarification inquiries, and issue formal consent withdrawals before picture lock.
- **Intended User Roles**: Participant (authenticated via cryptographic token or linked user), Public/Auditor view.
- **API Dependencies**:
  - `api.getParticipantPortalAccess(id, token)`
  - `api.getParticipantConsents(id, token)`
  - `api.getParticipantTimeline(id, token)`
  - `api.submitClarificationRequest(id, data, token)`
- **Components Used**:
  - `ChoiceBadge`
  - Bilingual dictionary (`en`, `hi`)
  - Consent category grid
  - Clarification / Withdrawal submission form
  - Personal audit event list
- **Actions Available**:
  - Toggle between English and Hindi language modes.
  - Review status of all 15 canonical categories.
  - Submit clarification questions to participant care team.
  - Submit formal withdrawal notices with urgent priority flagging.
  - Review personal immutable audit timeline.
- **Identified Weaknesses**:
  - Error states used `alert()` on submission failures.
  - Language switcher needed smoother transitions and improved accessible labeling.

---

### Route 5: `/analytics` (Operational Intelligence & Insights Dashboard)
- **Path**: `frontend/src/app/analytics/page.tsx`
- **Page Purpose**: Real-time operational intelligence, consent analytics across 15 canonical categories, human review velocity, task backlog, withdrawal triage, AI advisory concordance, historical trends, and RFC 4180 compliance report generation.
- **Intended User Roles**: Admin, Director, Producer, Crew (Exports restricted to Admin, Director, Producer; Participant role strictly denied HTTP 403).
- **API Dependencies**:
  - `api.getAnalyticsOverview(filters)`
  - `api.getProjectsAnalyticsSummary()`
  - `api.getConsentAnalytics(filters)`
  - `api.getConsentCategoriesBreakdown(filters)`
  - `api.getReviewAnalytics(filters)`
  - `api.getOperationsAnalytics(filters)`
  - `api.getWithdrawalAnalytics(filters)`
  - `api.getAdvisoryAnalytics(filters)`
  - `api.getTrendsAnalytics(filters)`
  - `api.exportAnalytics(payload)`
- **Components Used**:
  - `MetricCard`
  - `ConsentCategoryChart`
  - `TrendsChart`
  - `AnalyticsExportDialog`
  - 4 Tab views (Overview, Consent & 15 Categories, Reviews & Operations, AI Advisory & Trends)
- **Actions Available**:
  - Filter by project and time range (`all`, `7d`, `30d`, `90d`).
  - Refresh live database metrics.
  - Export CSV / JSON compliance reports.
  - Inspect category breakdown progress bars.
  - Review AI advisory concordance and disclaimer.
- **Identified Weaknesses**:
  - Lacked responsive mobile overflow handling for wide tables and chart containers.
  - Navigation link was desktop-only in Navbar.

---

## 3. Global Components & Design System Tokens

1. **`Navbar.tsx`**:
   - Manages top-level navigation, active tab styling, identity switching modal, and quick persona logins.
   - Identified deficiency: Lacked mobile drawer/hamburger navigation on screens < 768px.
2. **`ConsentBadge.tsx`**:
   - Renders semantic status pills for canonical consent choices (`agreed`, `declined`, `not_discussed`, `needs_clarification`).
   - Strong color semantics: Green (Agreed), Red (Declined), Slate (Not Discussed), Amber (Needs Clarification).
3. **`AnalyticsExportDialog.tsx`**:
   - Modal for selecting report type (`overview`, `consent_matrix`, `reviews`, `operations`, `withdrawals`) and format (`csv`, `json`).
4. **`ConsentCategoryChart.tsx`**:
   - Horizontal segmented progress bars showing percentage distribution across categories.
5. **`TrendsChart.tsx`**:
   - Responsive SVG time-series visualization.

