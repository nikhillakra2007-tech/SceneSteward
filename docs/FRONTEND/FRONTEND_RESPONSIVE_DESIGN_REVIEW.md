# SceneSteward Frontend Subsystem — Responsive Design Review

This document documents responsive behavior across mobile, tablet, and desktop form factors for all SceneSteward interfaces.

---

## 1. Responsive Viewport Strategy

Documentary filmmakers and field researchers frequently access SceneSteward on mobile phones (on set, during field interviews, or in production vehicles) and tablets (in edit suites or production offices). The application is engineered to provide a fully considered experience across all breakpoints:

| Breakpoint | Target Devices | Layout Behavior |
| :--- | :--- | :--- |
| **Mobile (< 640px)** | iPhone SE (375px), iPhone 14/15 (390px), Pixel 8 (412px) | Hamburger navigation drawer; single-column stacked cards; horizontal scrolling tables; full-width modal dialogs. |
| **Small Tablet (640px - 767px)** | iPad Mini portrait, small foldables | 2-column project grids; compact action buttons; stacked header controls. |
| **Tablet / Small Laptop (768px - 1023px)** | iPad Air/Pro (768px - 820px), Surface Pro | Full horizontal navbar; 2-column project cards; expanded category progress bars. |
| **Desktop (>= 1024px)** | MacBook, 1080p / 1440p / 4K displays | 3-column project grid; 5-column canonical category cards; side-by-side KPI dashboards; maximum container width of `max-w-7xl` (`1280px`). |

---

## 2. Page-by-Page Responsive Verification

### 2.1. Navigation (`Navbar.tsx`)
- **Desktop**: Persistent top bar with brand logo, "Projects" and "Analytics" links, active session user chip, switch persona button, and quick dev persona toggles.
- **Mobile**: Collapses horizontal nav into a sleek hamburger button (`Menu` icon). Tapping reveals a slide-down drawer with clear tap targets for all routes.

### 2.2. Landing Page (`/`)
- **Hero Banner**: Gradient background with responsive padding (`p-8 sm:p-10`), fluid typography (`text-3xl sm:text-4xl`), and flex-wrapped action buttons (`flex-wrap gap-3`).
- **Principles Grid**: Transitions from 1 column on mobile to 3 columns on desktop.

### 2.3. Project Portfolio (`/projects`)
- **Search & Action Bar**: Flex-direction shifts from column on mobile (`flex-col`) to row on desktop (`sm:flex-row sm:items-center`).
- **Projects Grid**: Transitions seamlessly from 1 column (`grid-cols-1`) to 2 columns on tablets (`md:grid-cols-2`) and 3 columns on desktops (`lg:grid-cols-3`).

### 2.4. Project Workspace (`/projects/[id]`)
- **Header**: Flex-wrap for action buttons (`+ Participant`, `+ Consent Record`, `+ Propose Use`, `Project Analytics`).
- **Tab Bar**: Horizontal scrollable container (`overflow-x-auto scrollbar-none`) with sticky pill indicators.
- **Data Tables**: Nested inside `overflow-x-auto` wrappers with `min-w-[600px]` to prevent text truncation while maintaining readability on mobile.

### 2.5. Participant Transparency Portal (`/participant/[id]`)
- **Header**: Flex-wrap aligning portal badge, bilingual language switcher, and project link.
- **15 Category Matrix**: Adapts from 1 column on mobile to 2 columns on tablets (`sm:grid-cols-2`) and 3 columns on desktops (`lg:grid-cols-3`).

### 2.6. Operational Intelligence Dashboard (`/analytics`)
- **Control Bar**: Project switcher and time range buttons wrap neatly.
- **KPI Cards**: Responsive grid (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`).
- **Trend Charts**: Responsive SVG with viewBox scaling dynamically with parent width.

