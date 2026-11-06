# SceneSteward Frontend Subsystem — Developer Guide

This guide provides technical onboarding for engineers contributing to the SceneSteward Next.js frontend.

---

## 1. Project Structure

```
frontend/
├── src/
│   ├── app/                         # Next.js 14 App Router routes
│   │   ├── layout.tsx               # Root layout (ToastProvider, Navbar, Footer)
│   │   ├── page.tsx                 # Home / Landing page
│   │   ├── globals.css              # Tailwind base, dark-mode CSS variables
│   │   ├── projects/
│   │   │   ├── page.tsx             # Project index & search
│   │   │   └── [id]/page.tsx        # Documentary production workspace (9 tabs)
│   │   ├── participant/
│   │   │   └── [id]/page.tsx        # Participant dignity & transparency portal
│   │   └── analytics/
│   │       └── page.tsx             # Operational intelligence & analytics dashboard
│   ├── components/
│   │   ├── Navbar.tsx               # Header, mobile drawer, auth modal
│   │   ├── Toast.tsx                # Accessible toast notification system
│   │   ├── ConsentBadge.tsx         # Canonical category status badges
│   │   └── analytics/               # Analytics components
│   │       ├── MetricCard.tsx
│   │       ├── ConsentCategoryChart.tsx
│   │       ├── TrendsChart.tsx
│   │       └── AnalyticsExportDialog.tsx
│   └── lib/
│       ├── api.ts                   # Centralized API client & TypeScript interfaces
│       └── analytics-types.ts       # Analytics schemas & report types
├── e2e/                             # Playwright end-to-end test suites
│   ├── workflow.spec.ts
│   ├── staging_e2e_acceptance.spec.ts
│   └── comprehensive_product_experience.spec.ts
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

---

## 2. Development Workflow

### Starting the Development Server
```bash
cd frontend
npm install
npm run dev
```
The application runs locally on `http://localhost:3000`.

### Type-Checking & Production Build
```bash
npm run build
```
Ensures strict TypeScript compilation, CSS optimization, and static page generation.

### Running End-to-End Tests
```bash
npx playwright test
```

---

## 3. Key Conventions & Rules

1. **Centralized API Client**:
   - Always call backend endpoints through `api.*` methods in `frontend/src/lib/api.ts`.
   - Never write ad-hoc `fetch()` calls in components.
2. **No Browser Alerts**:
   - Use the `useToast()` hook (`const { success, error, info } = useToast()`) for user feedback. Never call `window.alert()` or `window.confirm()`.
3. **Canonical Consent Invariant**:
   - Never default missing consent categories to `agreed`. Unrecorded categories must be represented as `not_discussed`.
4. **Modal Dialogs**:
   - Always include `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, and listen for the `Escape` key to close.

