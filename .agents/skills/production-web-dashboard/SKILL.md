---
name: production-web-dashboard
description: >
  Comprehensive skill for creating production-grade, modular, component-based
  webpages and dashboards wired to real live data. Enforces zero hardcoded mock data,
  production-ready CSS design token systems, reactive state architectures,
  reusable UI components, resilient API pipelines, real-time polling/SSE,
  and premium glassmorphic/dark-mode aesthetics.
---

# Production Webpage & Dashboard Builder Skill

Use this skill when building, refactoring, or extending web applications, client portals, admin panels, and real-time operational dashboards.

This skill ensures every frontend interface is:
1. **100% Real Data Driven** — Zero hardcoded mock arrays or fake data in production code; dynamically fetched from real API endpoints, FastAPI/Pydantic schemas, or live event streams.
2. **Modular & Component-Based** — Composed of isolated, reusable, self-contained UI components with standard lifecycles (`init`, `fetch`, `render`, `bindEvents`, `destroy`).
3. **Production-Grade & Resilient** — Includes skeleton loading states, error boundaries, optimistic updates, automatic retries, and accessibility compliance.
4. **Visually Stunning & Modern** — Designed with custom CSS token systems, sleek dark palettes, glassmorphic card elevations, micro-animations, and clean typography.

---

## The 5 Core Golden Rules

| # | Rule | Requirement |
|---|------|-------------|
| 1 | **NO MOCK DATA IN PRODUCTION** | Always bind components to actual backend endpoints (`/api/...`), database query models, or live webhooks. Use dynamic data-driven rendering. |
| 2 | **NO HARDCODED VALUES** | Extract configuration, API endpoints, auth keys, colors, and styling into environment configs and CSS Custom Properties (`:root { ... }`). |
| 3 | **ISOLATED COMPONENT ARCHITECTURE** | Each component owns its template, styling hooks, event listeners, and data-binding logic. No monolithic 3,000-line spaghetti files. |
| 4 | **RESILIENT DATA LIFECYCLE** | Every data-driven widget MUST handle 4 distinct states: **Loading (Skeleton)**, **Error (Retry prompt)**, **Empty (Clear CTA)**, and **Success (Rich Data)**. |
| 5 | **PREMIUM RICH AESTHETICS** | Build with high-contrast readable dark modes, subtle borders, translucent cards, glowing accents, polished badges, and micro-transitions. |

---

## The 5-Layer Frontend Architecture

When assembling a production dashboard or webpage, organize code into these five discrete layers:

```
┌────────────────────────────────────────────────────────┐
│ 1. DESIGN TOKEN & THEME LAYER (CSS Variables)          │
├────────────────────────────────────────────────────────┤
│ 2. API CLIENT & DATA ADAPTER LAYER (Fetch / Auth)      │
├────────────────────────────────────────────────────────┤
│ 3. REACTIVE STATE STORE / EVENT BUS                    │
├────────────────────────────────────────────────────────┤
│ 4. MODULAR COMPONENT REGISTRY (Widgets, Tables, Cards) │
├────────────────────────────────────────────────────────┤
│ 5. PAGE ORCHESTRATOR & ROUTING (Mounting & Layout)     │
└────────────────────────────────────────────────────────┘
```

---

## Layer 1: Design Tokens & Styling System

Never write arbitrary hardcoded hex codes or ad-hoc margins. Define a centralized `:root` design token system in the base stylesheet.

### Standard Production Token Palette

```css
:root {
  /* Surface & Background Colors */
  --bg-primary: #070d18;
  --bg-surface: #0f172a;
  --bg-surface-elevated: #162238;
  --bg-surface-hover: #1e2e4a;
  --bg-glass: rgba(15, 23, 42, 0.75);
  --backdrop-blur: blur(12px);

  /* Borders & Dividers */
  --border-subtle: #1e2e4a;
  --border-medium: #2c4266;
  --border-highlight: #38bdf8;

  /* Typography */
  --font-main: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --text-primary: #f0f6fc;
  --text-secondary: #8ca0be;
  --text-muted: #566d8f;

  /* Semantic Brand & Accents */
  --accent-cyan: #38bdf8;
  --accent-cyan-glow: rgba(56, 189, 248, 0.15);
  --status-success: #10b981;
  --status-success-glow: rgba(16, 185, 129, 0.15);
  --status-warning: #f59e0b;
  --status-warning-glow: rgba(245, 158, 11, 0.15);
  --status-danger: #ef4444;
  --status-danger-glow: rgba(239, 68, 68, 0.15);
  --status-purple: #a855f7;

  /* Layout & Spacing */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-full: 9999px;
  --shadow-card: 0 4px 20px -2px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 15px var(--accent-cyan-glow);
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
```

---

## Layer 2: API Client & Resilient Data Adapter

The API client encapsulates all REST/JSON endpoints, auth tokens (Clerk / Bearer), automatic retries with exponential backoff, and JSON parsing.

```javascript
/**
 * Production API Client with Auth, Timeout, and Retry support
 */
class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  async getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (window.Clerk && window.Clerk.session) {
      const token = await window.Clerk.session.getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}, retries = 2) {
    const url = `${this.baseUrl}${endpoint}`;
    const authHeaders = await this.getAuthHeaders();
    
    const config = {
      ...options,
      headers: {
        ...authHeaders,
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        const errBody = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errBody.detail || `HTTP error ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      if (retries > 0 && (!options.method || options.method === 'GET')) {
        await new Promise(res => setTimeout(res, 800));
        return this.request(endpoint, options, retries - 1);
      }
      throw err;
    }
  }

  get(endpoint) { return this.request(endpoint, { method: 'GET' }); }
  post(endpoint, body) { return this.request(endpoint, { method: 'POST', body: JSON.stringify(body) }); }
  put(endpoint, body) { return this.request(endpoint, { method: 'PUT', body: JSON.stringify(body) }); }
  delete(endpoint) { return this.request(endpoint, { method: 'DELETE' }); }
}

window.apiClient = new ApiClient();
```

---

## Layer 3: Reactive State Store & Event Bus

Decouple components using an event bus and single-source-of-truth state container so that filtering, row selection, or data updates trigger instant updates across all widgets without tight coupling.

```javascript
class StateStore {
  constructor(initialState = {}) {
    this.state = { ...initialState };
    this.listeners = new Map();
  }

  getState() {
    return this.state;
  }

  setState(partialState) {
    const prevState = { ...this.state };
    this.state = { ...this.state, ...partialState };
    this.notify('*', this.state, prevState);
    
    Object.keys(partialState).forEach(key => {
      if (prevState[key] !== partialState[key]) {
        this.notify(key, partialState[key], prevState[key]);
      }
    });
  }

  subscribe(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    this.listeners.get(key).add(callback);
    return () => this.listeners.get(key).delete(callback);
  }

  notify(key, newValue, oldValue) {
    if (this.listeners.has(key)) {
      this.listeners.get(key).forEach(cb => cb(newValue, oldValue));
    }
  }
}

window.appStore = new StateStore({
  currentFeed: null,
  leads: [],
  filters: { search: '', status: 'all', timeframe: '30d' },
  metrics: null,
  selectedLeadId: null,
  isLoading: false
});
```

---

## Layer 4: Standard Component Lifecycle Specification

Every UI component must implement the standard Component Contract:

```javascript
class BaseComponent {
  constructor(containerId, props = {}) {
    this.container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    this.props = props;
    this.state = {};
    this.subscriptions = [];
  }

  init() {
    // Initial subscriptions & fetch
  }

  renderSkeleton() {
    // Render loading shimmer placeholder
  }

  renderError(errorMessage, retryCallback) {
    // Render standardized error state with retry CTA
  }

  renderEmpty(emptyMessage) {
    // Render empty state with icon and action
  }

  render(data) {
    // Render real data into DOM
  }

  bindEvents() {
    // Attach event listeners
  }

  destroy() {
    // Unsubscribe listeners and cleanup timers
    this.subscriptions.forEach(unsub => unsub());
    this.subscriptions = [];
  }
}
```

---

## Layer 5: Production-Ready Component Blueprints

### 1. KPI Metric Card Grid (`MetricGridComponent`)
Renders live metrics with change indicators, glowing trend tags, and shimmer skeleton loading.

```javascript
class MetricGridComponent extends BaseComponent {
  init() {
    this.renderSkeleton();
    this.subscriptions.push(
      window.appStore.subscribe('metrics', (metrics) => {
        if (metrics) this.render(metrics);
      })
    );
  }

  renderSkeleton() {
    this.container.innerHTML = `
      <div class="metrics-grid">
        ${[1, 2, 3, 4].map(() => `
          <div class="metric-card skeleton-pulse">
            <div class="skeleton-line sm w-40"></div>
            <div class="skeleton-line lg w-60 my-2"></div>
            <div class="skeleton-line sm w-30"></div>
          </div>
        `).join('')}
      </div>
    `;
  }

  render(metrics) {
    const cards = [
      { label: 'Total Records Discovered', value: metrics.total_discovered?.toLocaleString() || '0', change: metrics.discovery_rate_pct, icon: 'database' },
      { label: 'Verified Qualified Leads', value: metrics.qualified_leads?.toLocaleString() || '0', change: metrics.qualification_rate_pct, icon: 'shield-check' },
      { label: 'Delivered to Destination', value: metrics.delivered_count?.toLocaleString() || '0', change: metrics.delivery_rate_pct, icon: 'send' },
      { label: 'Pipeline Health', value: metrics.pipeline_health || 'Optimal', status: metrics.health_status || 'good', icon: 'activity' }
    ];

    this.container.innerHTML = `
      <div class="metrics-grid">
        ${cards.map(c => `
          <div class="metric-card">
            <div class="metric-header">
              <span class="metric-label">${c.label}</span>
              <span class="metric-badge ${c.change >= 0 ? 'badge-pos' : 'badge-neg'}">
                ${c.change ? `${c.change > 0 ? '+' : ''}${c.change}%` : 'Active'}
              </span>
            </div>
            <div class="metric-value">${c.value}</div>
            <div class="metric-footer">
              <span class="metric-subtext">Live synced from backend</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }
}
```

### 2. Live Filterable Data Table (`LiveDataTableComponent`)
Supports client/server-side search, real-time filtering, dynamic sorting, column formatting, and row click drawer inspection.

```javascript
class LiveDataTableComponent extends BaseComponent {
  init() {
    this.renderSkeleton();
    this.subscriptions.push(
      window.appStore.subscribe('leads', (leads) => this.render(leads)),
      window.appStore.subscribe('filters', () => this.applyFilters())
    );
  }

  renderSkeleton() {
    this.container.innerHTML = `
      <div class="table-container">
        <div class="skeleton-table">
          <div class="skeleton-row header"></div>
          ${[1, 2, 3, 4, 5].map(() => `<div class="skeleton-row"></div>`).join('')}
        </div>
      </div>
    `;
  }

  render(leads) {
    if (!leads || leads.length === 0) {
      return this.renderEmpty('No records found for current filters.');
    }

    this.rawLeads = leads;
    this.applyFilters();
  }

  applyFilters() {
    const { search, status } = window.appStore.getState().filters;
    let filtered = this.rawLeads || [];

    if (search) {
      const q = search.toLowerCase();
      filtered = filtered.filter(row => 
        JSON.stringify(row).toLowerCase().includes(q)
      );
    }

    if (status && status !== 'all') {
      filtered = filtered.filter(row => row.status === status);
    }

    this.renderTableData(filtered);
  }

  renderTableData(rows) {
    if (rows.length === 0) {
      return this.renderEmpty('No matching records found.');
    }

    const columns = Object.keys(rows[0]).slice(0, 7); // First 7 attributes

    this.container.innerHTML = `
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              ${columns.map(col => `<th>${col.replace(/_/g, ' ').toUpperCase()}</th>`).join('')}
              <th class="text-right">ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map(row => `
              <tr class="table-row" data-id="${row.id || row.lead_id}">
                ${columns.map(col => `
                  <td>
                    ${col === 'status' ? `<span class="status-pill status-${row[col]}">${row[col]}</span>` : (row[col] ?? '—')}
                  </td>
                `).join('')}
                <td class="text-right">
                  <button class="btn-action view-btn" data-id="${row.id || row.lead_id}">Inspect</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
    this.bindEvents();
  }

  bindEvents() {
    this.container.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = e.currentTarget.dataset.id;
        window.appStore.setState({ selectedLeadId: id });
      });
    });
  }

  renderEmpty(msg) {
    this.container.innerHTML = `
      <div class="empty-state-box">
        <div class="empty-icon">📂</div>
        <h3>No Data Available</h3>
        <p class="text-muted">${msg}</p>
      </div>
    `;
  }
}
```

### 3. Real-Time Activity Log Stream (`ActivityFeedComponent`)
Renders live telemetry, timestamps, severity tags, and auto-scrolls on new log arrivals.

```javascript
class ActivityFeedComponent extends BaseComponent {
  init() {
    this.container.innerHTML = `
      <div class="feed-card">
        <div class="feed-header">
          <span class="live-dot"></span>
          <h4>Live Ingestion Telemetry</h4>
        </div>
        <div class="feed-body" id="feedLogsContainer">
          <div class="log-entry system">Connecting to live feed stream...</div>
        </div>
      </div>
    `;
    this.logsContainer = this.container.querySelector('#feedLogsContainer');
  }

  addLog(entry) {
    const div = document.createElement('div');
    div.className = `log-entry log-${entry.level || 'info'}`;
    div.innerHTML = `
      <span class="log-time">${new Date().toLocaleTimeString()}</span>
      <span class="log-tag tag-${entry.level || 'info'}">[${entry.source || 'SYS'}]</span>
      <span class="log-msg">${entry.message}</span>
    `;
    this.logsContainer.appendChild(div);
    this.logsContainer.scrollTop = this.logsContainer.scrollHeight;
  }
}
```

---

## Step-by-Step Implementation Workflow

When asked to create or upgrade a webpage or dashboard, execute this rigorous workflow:

### Step 1: Inspect Backend Schema & API Routes
1. Read the FastAPI router, Pydantic models, or database schemas (`domain.py`, `routes/`, `storage.py`).
2. Map out real endpoints for:
   - Data list & pagination: `/api/...`
   - Single item detail: `/api/.../{id}`
   - Action mutations: `POST /api/.../run`, `PUT /api/.../settings`
   - Export endpoints: `/api/.../export.csv`

### Step 2: Establish Design Tokens (`styles.css` / `<style>`)
1. Implement standard CSS custom properties for palette, typography, glass elevations, and shadows.
2. Define base resets, layout grids, and utility classes.

### Step 3: Instantiate ApiClient & StateStore
1. Provide the centralized `ApiClient` handling authentication, retry loops, and JSON transformation.
2. Set up `appStore` holding global filters, active entity, and data arrays.

### Step 4: Build Modular Component Classes
1. Build individual component classes (`HeaderComponent`, `MetricGridComponent`, `FilterBarComponent`, `LiveDataTableComponent`, `DetailDrawerComponent`, `ToastManager`).
2. Ensure each component handles skeleton, error, empty, and populated states.

### Step 5: Wire Real Data Fetching & Polling
1. Connect `init()` to fetch real payload from the backend API.
2. If real-time updates are needed, set up a non-blocking `setInterval` or SSE/WebSocket listener with exponential backoff on errors.
3. Eliminate all placeholder/mock strings.

### Step 6: Polish UI/UX & Responsive Behaviors
1. Add subtle hover micro-interactions (`transform: translateY(-2px)`, glowing borders).
2. Ensure mobile and tablet responsiveness with flexible CSS Grid/Flexbox layouts.
3. Test edge cases (empty search results, large datasets, slow connections).

---

## Quality Checklist for Reviewing Webpages & Dashboards

Before marking any web page or dashboard task complete, verify every item on this checklist:

- [ ] **Zero Mock Data**: Is all data rendered directly from backend responses without hardcoded fallback arrays?
- [ ] **No Hardcoded Constants**: Are colors, API paths, and auth parameters driven by CSS tokens and dynamic config?
- [ ] **4-State UI Coverage**: Does every widget implement Loading Skeleton, Error with Retry, Empty State, and Active Data?
- [ ] **Modular Separation**: Are components organized in self-contained classes or modules with standard lifecycles?
- [ ] **Reactive Event Communication**: Do filters, search bars, and pagination update the table via state events without page reloads?
- [ ] **Production Error Handling**: Do network failures trigger user-friendly toast alerts or retry cards instead of unhandled console errors?
- [ ] **Accessibility & Semantics**: Are standard HTML5 tags (`<main>`, `<header>`, `<section>`, `<table>`, `<button>`) and ARIA labels used properly?
- [ ] **Responsive & Modern Styling**: Does the UI render cleanly on both desktop and mobile screens with dark glassmorphism and clean typography?
