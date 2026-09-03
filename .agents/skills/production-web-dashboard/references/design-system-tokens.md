# Design System Tokens & Glassmorphic Dark UI Guide

This reference defines the production-grade CSS variable architecture, elevation levels, typography scales, micro-animations, and skeleton loading styles.

---

## 1. Complete CSS Design Token Hierarchy

```css
:root {
  /* Surface Layers (Dark Mode Hierarchy) */
  --bg-app: #070d18;             /* Deepest canvas */
  --bg-surface: #0f172a;         /* Main card background */
  --bg-surface-raised: #162238;  /* Elevated elements, dropdowns, nested cards */
  --bg-surface-hover: #1e2e4a;   /* Interactive hover state */
  --bg-glass: rgba(15, 23, 42, 0.82);
  --bg-glass-card: rgba(22, 34, 56, 0.65);
  
  /* Filter & Glass Effects */
  --backdrop-blur: blur(12px);
  --glass-border: 1px solid rgba(255, 255, 255, 0.08);

  /* Border Tokens */
  --border-subtle: #1e2e4a;
  --border-medium: #2c4266;
  --border-strong: #3b5580;
  --border-accent: #38bdf8;

  /* Typography Colors */
  --text-primary: #f0f6fc;
  --text-secondary: #8ca0be;
  --text-muted: #566d8f;
  --text-inverse: #070d18;

  /* Typography Families */
  --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Typography Scales */
  --text-xs: 0.75rem;    /* 12px */
  --text-sm: 0.875rem;   /* 14px */
  --text-base: 1rem;     /* 16px */
  --text-lg: 1.125rem;   /* 18px */
  --text-xl: 1.25rem;    /* 20px */
  --text-2xl: 1.5rem;    /* 24px */
  --text-3xl: 1.875rem;  /* 30px */

  /* Semantic Brand & Status Accents */
  --accent-cyan: #38bdf8;
  --accent-cyan-hover: #0ea5e9;
  --accent-cyan-glow: rgba(56, 189, 248, 0.18);

  --accent-purple: #a855f7;
  --accent-purple-glow: rgba(168, 85, 247, 0.18);

  --status-success: #10b981;
  --status-success-bg: rgba(16, 185, 129, 0.12);
  --status-success-glow: rgba(16, 185, 129, 0.25);

  --status-warning: #f59e0b;
  --status-warning-bg: rgba(245, 158, 11, 0.12);
  --status-warning-glow: rgba(245, 158, 11, 0.25);

  --status-danger: #ef4444;
  --status-danger-bg: rgba(239, 68, 68, 0.12);
  --status-danger-glow: rgba(239, 68, 68, 0.25);

  /* Elevation Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 12px -2px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 12px 28px -4px rgba(0, 0, 0, 0.5);
  --shadow-glow-cyan: 0 0 20px rgba(56, 189, 248, 0.2);

  /* Border Radii */
  --radius-xs: 4px;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --radius-pill: 9999px;

  /* Transitions */
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-smooth: 250ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

---

## 2. Skeleton Loading Animation System

Use these CSS rules for shimmer animations across all components when loading data:

```css
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.skeleton-shimmer {
  background: linear-gradient(
    90deg,
    var(--bg-surface-raised) 25%,
    var(--bg-surface-hover) 50%,
    var(--bg-surface-raised) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.6s infinite ease-in-out;
  border-radius: var(--radius-sm);
}

.skeleton-text {
  height: 14px;
  width: 100%;
  margin: 6px 0;
}

.skeleton-heading {
  height: 24px;
  width: 60%;
  margin: 8px 0;
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-pill);
}

.skeleton-card {
  padding: 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
```

---

## 3. Standard Glassmorphism Card & Interactive Button Utility

```css
/* Glass Card */
.glass-card {
  background: var(--bg-glass-card);
  backdrop-filter: var(--backdrop-blur);
  -webkit-backdrop-filter: var(--backdrop-blur);
  border: var(--glass-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  transition: transform var(--transition-smooth), border-color var(--transition-smooth), box-shadow var(--transition-smooth);
}

.glass-card:hover {
  transform: translateY(-2px);
  border-color: var(--border-strong);
  box-shadow: var(--shadow-lg);
}

/* Primary Button */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(135deg, var(--accent-cyan), #0284c7);
  color: #030712;
  font-weight: 600;
  font-size: var(--text-sm);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  box-shadow: var(--shadow-glow-cyan);
  transition: all var(--transition-fast);
}

.btn-primary:hover {
  background: linear-gradient(135deg, #7dd3fc, var(--accent-cyan));
  transform: translateY(-1px);
  box-shadow: 0 0 25px rgba(56, 189, 248, 0.35);
}

.btn-primary:active {
  transform: translateY(0);
}
```
