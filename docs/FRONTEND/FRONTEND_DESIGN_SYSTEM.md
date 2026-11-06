# SceneSteward Frontend Subsystem — Design System & Component Specifications

This document defines the consolidated design tokens, visual styling patterns, and reusable component specifications for SceneSteward.

---

## 1. Design Principles & Theme Philosophy

SceneSteward adopts a **dark-mode-first documentary production aesthetic**:
- High-contrast typography on deep slate surfaces (`slate-950` background, `slate-900` cards).
- Emerald accent (`emerald-500` / `emerald-600`) symbolizing positive clearance, dignity, and verified consent.
- Amber and rose accents used strictly for ethical boundaries, cautionary restrictions, and participant withdrawals.
- Subdued borders (`slate-800`) providing clean dimensional structure without visual distraction.

---

## 2. Core Design Tokens

### Color Palette

| Token Name | Tailwind Class | Hex Value | Purpose |
| :--- | :--- | :--- | :--- |
| `background` | `bg-slate-950` | `#080d1a` | Primary window background |
| `surface` | `bg-slate-900` | `#0f172a` | Card and container background |
| `surface-elevated` | `bg-slate-850` | `#151e2e` | Modals, dropdowns, and flyouts |
| `surface-sunken` | `bg-slate-950/60` | `#080d1a99` | Code blocks, inner textareas, table bodies |
| `border-subtle` | `border-slate-800` | `#1e293b` | Default container borders |
| `border-interactive` | `border-slate-700` | `#334155` | Input borders, hover states |
| `text-primary` | `text-slate-100` / `text-white` | `#f1f5f9` / `#ffffff` | Headings and primary body copy |
| `text-muted` | `text-slate-400` | `#94a3b8` | Supporting copy, labels, secondary metadata |
| `text-faint` | `text-slate-500` | `#64748b` | Timestamps, micro-copy, inactive tabs |
| `brand-primary` | `bg-emerald-600` | `#16a34a` | Primary call to action, active navigation |
| `brand-accent` | `text-emerald-400` | `#4ade80` | Status highlights, icons, links |
| `warning` | `text-amber-400`, `bg-amber-950` | `#fbbf24`, `#451a03` | Unresolved categories, pending reviews |
| `danger` | `text-rose-400`, `bg-rose-950` | `#fb7185`, `#4c0519` | Declined categories, withdrawals, errors |

### Typography Scale

- **Display**: `text-3xl` to `text-4xl` (`font-extrabold`), letter-spacing `tracking-tight`.
- **Page Heading**: `text-2xl` (`font-bold`).
- **Section Heading**: `text-base` to `text-lg` (`font-bold`).
- **Body**: `text-sm` (`leading-relaxed`).
- **Supporting / Table Text**: `text-xs`.
- **Micro-copy & Badges**: `text-[10px]` or `text-[11px]` (`font-mono` where applicable).

---

## 3. Reusable Component Specifications

### 3.1. Buttons
- **Primary**: `bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs px-3.5 py-2 rounded-lg transition disabled:opacity-50`.
- **Secondary**: `bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold px-3 py-2 rounded-lg transition`.
- **Danger / Urgent**: `bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs px-3.5 py-1.5 rounded-lg transition`.
- **Ghost / Link**: `text-emerald-400 hover:text-emerald-300 font-semibold text-xs hover:underline`.

### 3.2. Form Controls
- **Input & Select**: `w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white text-xs focus:outline-none focus:border-emerald-500 transition placeholder:text-slate-500`.
- **Textarea**: Same as input with `rows={3}` or `rows={4}` and `font-sans` or `font-mono`.
- **Label**: `block text-xs font-semibold text-slate-300 mb-1`.
- **Inline Error**: `text-xs text-rose-400 mt-1 flex items-center space-x-1`.

### 3.3. Modals & Dialogs
- **Backdrop**: `fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm`.
- **Container**: `w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 space-y-4 shadow-2xl animate-in fade-in-50 zoom-in-95`.
- **Header**: Border-bottom with `h3 font-bold text-white` and `✕` close button.
- **Escape Key Handling**: Closes modal automatically on `Escape` key press.

### 3.4. Semantic Badges (`ChoiceBadge`)
- `agreed`: `bg-emerald-950 text-emerald-400 border border-emerald-800`
- `declined`: `bg-rose-950 text-rose-400 border border-rose-800`
- `not_discussed`: `bg-slate-900 text-slate-400 border border-slate-800`
- `needs_clarification`: `bg-amber-950 text-amber-400 border border-amber-800`
- `withdrawn`: `bg-rose-950 text-rose-300 border border-rose-700 font-bold`

### 3.5. Toast Notification System
- Replaces non-standard browser `alert()` with non-blocking, accessible alert toasts (`ToastProvider`).
- Types: `success` (emerald), `error` (rose), `info` (blue), `warning` (amber).
- Auto-dismiss after 4 seconds with manual close button.

---

## 4. Responsive Breakpoints

- `sm`: 640px (single-column cards to 2-column)
- `md`: 768px (mobile navigation drawer expands to horizontal navbar)
- `lg`: 1024px (3-column project grid, expanded charts)
- `xl`: 1280px (maximum container width `max-w-7xl mx-auto`)

