# Refero-Grade Design System Specification
# Project: Enterprise Application | Style: Obsidian

Extracted and extended from **Refero Styles (`styles.refero.design`)** and world-class product benchmarks (Mobbin, Saaspo, PageFlows, Godly, Land-book, Dribbble, Behance, UI Sources, Lapa Ninja).

---

## 1. Tailwind CSS v4 Native Theme Configuration

```css
/* app/globals.css - Tailwind CSS v4 Native @theme Directive */
@import "tailwindcss";

@theme {
  /* Primary Brand & Accent Colors */
  --color-brand-primary: var(--brand-primary);
  --color-brand-primary-hover: var(--brand-primary-hover);
  --color-brand-accent: var(--brand-accent);
  --color-brand-accent-subtle: var(--brand-accent-subtle);

  /* Surface Hierarchies */
  --color-surface-base: var(--surface-base);
  --color-surface-subtle: var(--surface-subtle);
  --color-surface-elevated: var(--surface-elevated);
  --color-surface-border: var(--surface-border);
  --color-surface-border-strong: var(--surface-border-strong);

  /* Semantic Typography Colors */
  --color-text-primary: var(--text-primary);
  --color-text-secondary: var(--text-secondary);
  --color-text-muted: var(--text-muted);

  /* Typography Scales */
  --font-display: "Geist", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-mono: "Geist Mono", monospace;

  /* Elevation Shadows */
  --shadow-subtle: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-card: 0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.06);
  --shadow-elevated: 0 20px 25px -5px rgb(0 0 0 / 0.12), 0 8px 10px -6px rgb(0 0 0 / 0.08);

  /* Fluid Motion & Animation */
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-smooth: cubic-bezier(0.22, 1, 0.36, 1);
  --duration-instant: 100ms;
  --duration-fast: 150ms;
  --duration-normal: 250ms;
}

/* CSS Custom Properties / Design Tokens */
:root {
  --brand-primary: #18181b;
  --brand-primary-hover: #27272a;
  --brand-accent: #6366f1;
  --brand-accent-subtle: #e0e7ff;

  --surface-base: #ffffff;
  --surface-subtle: #f8fafc;
  --surface-elevated: #ffffff;
  --surface-border: #e2e8f0;
  --surface-border-strong: #cbd5e1;

  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
}

[data-theme="dark"] {
  --brand-primary: #f8fafc;
  --brand-primary-hover: #e2e8f0;
  --brand-accent: #818cf8;
  --brand-accent-subtle: #312e81;

  --surface-base: #09090b;
  --surface-subtle: #18181b;
  --surface-elevated: #1e1e24;
  --surface-border: #27272a;
  --surface-border-strong: #3f3f46;

  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
}
```

---

## 2. Core Component Variants & Micro-Interactions

### Button System (with Double-Submit Concurrency Guard)
- **Primary Action**:
  `bg-brand-primary text-surface-base hover:bg-brand-primary-hover active:scale-[0.98] transition-all duration-fast ease-spring rounded-lg px-4 py-2.5 font-medium shadow-subtle disabled:opacity-50 disabled:pointer-events-none`
- **Secondary Subtle**:
  `bg-surface-subtle border border-surface-border text-text-primary hover:bg-surface-border/50 active:scale-[0.98] transition-all duration-fast ease-spring rounded-lg px-4 py-2.5 font-medium`
- **Destructive**:
  `bg-red-600 text-white hover:bg-red-700 active:scale-[0.98] transition-all duration-fast rounded-lg px-4 py-2.5 font-medium`
- **Execution Guard**: All mutation buttons MUST bind `disabled={isPending || isSubmitting}` and display a spinner while promises remain unsettled.

### Cards & Elevation
- **Interactive Container**:
  `bg-surface-elevated border border-surface-border hover:border-surface-border-strong transition-colors duration-normal rounded-xl p-6 shadow-card`

### Modal & Dialog System (WCAG 2.1 AA Compliant)
- Mandatory focus traps (`aria-modal="true"`).
- Smooth backdrop blur (`backdrop-blur-sm bg-black/40`).
- Keyboard dismissal via `Escape` key restoring focus to triggering element.

---

## 3. Curated Design Inspiration Benchmarks
- **Refero Styles** (`https://styles.refero.design`): Extracted real-world design systems and tokens.
- **Mobbin** (`https://mobbin.com`): Real-world mobile and web user flows.
- **Saaspo** (`https://saaspo.com`): High-converting SaaS landing pages and component patterns.
- **PageFlows** (`https://pageflows.com`): User journey screen recordings and UX states.
- **Godly** (`https://godly.website`): Creative direction and micro-interaction benchmarks.
- **Land-book** (`https://land-book.com`): Editorial typography and product layouts.
