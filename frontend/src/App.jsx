import { useEffect, useMemo, useState } from 'react';

const backendUrl = 'https://aca-leadops-api-production.delightfulbay-8f60d181.centralus.azurecontainerapps.io';

const navItems = ['Platform', 'Workflow', 'Coverage', 'Pricing', 'Security'];

const metrics = [
  { value: '7-agent', label: 'autonomous swarm' },
  { value: '95%', label: 'QA gatekeeper pass' },
  { value: '50/50', label: 'escrow protection' },
  { value: '24/7', label: 'programmatic monitoring' },
];

const features = [
  {
    title: 'Real-time public records intake',
    text: 'Capture county filings, docket changes, and deed activity across jurisdictions without manual monitoring.',
  },
  {
    title: 'Autonomous dev team',
    text: 'AI workflows monitor, test, and deploy data extraction pipelines across the whole records lifecycle.',
  },
  {
    title: 'Escrow-backed delivery',
    text: 'Structured data is quality-gated before it reaches your team or downstream integrations.',
  },
  {
    title: 'Operational dashboards',
    text: 'Track lead generation, flow health, and per-jurisdiction performance in a single operational view.',
  },
];

const workflowSteps = [
  'Source county, court, and registry feeds',
  'Normalize records and validate missing fields',
  'Grade and QA each extraction pass',
  'Deliver structured data to your pipeline',
];

const useCases = [
  'Property and lien tracking',
  'Probate and estate monitoring',
  'Commercial permits and filings',
  'Litigation and claim intelligence',
];

function App() {
  const [health, setHealth] = useState({ status: 'Checking', ok: false });

  useEffect(() => {
    const controller = new AbortController();

    const loadHealth = async () => {
      try {
        const response = await fetch(`${backendUrl}/health`, { signal: controller.signal });
        const payload = await response.json();
        setHealth({ status: payload?.status || 'ok', ok: response.ok });
      } catch (error) {
        if (error.name !== 'AbortError') {
          setHealth({ status: 'offline', ok: false });
        }
      }
    };

    loadHealth();
    return () => controller.abort();
  }, []);

  const badgeLabel = useMemo(() => {
    return health.ok ? 'API online' : health.status === 'offline' ? 'API offline' : 'Checking API';
  }, [health]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="container nav-wrap">
          <a href="#top" className="brand" aria-label="LeadOps home">
            <span className="brand-mark">L</span>
            <span>LeadOps</span>
          </a>

          <nav className="main-nav" aria-label="Primary navigation">
            {navItems.map((item) => (
              <a key={item} href={`#${item.toLowerCase()}`}>
                {item}
              </a>
            ))}
          </nav>

          <div className="topbar-actions">
            <button className="button secondary">Book demo</button>
            <button className="button primary">Get started</button>
          </div>
        </div>
      </header>

      <main id="top">
        <section className="hero section">
          <div className="container hero-inner">
            <span className="status-pill" data-live={health.ok ? 'online' : 'pending'}>
              <span className="dot" />
              {badgeLabel}
            </span>

            <h1>
              Turn slow public-records work into a <span>real-time ops engine</span>.
            </h1>

            <p className="subtitle">
              OmniLeadFeeder turns county portals, filings, and lead discovery into structured, verified data streams that your team can act on immediately.
            </p>

            <div className="cta-row">
              <button className="button primary large">Launch sandbox</button>
              <button className="button secondary large">Explore workflow</button>
            </div>

            <div className="stats-grid" aria-label="Key metrics">
              {metrics.map((item) => (
                <div key={item.label} className="stat-box">
                  <strong>{item.value}</strong>
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="platform" className="section">
          <div className="container">
            <div className="section-header">
              <span className="eyebrow">Platform</span>
              <h2>Built for operational teams that need reliable public records data.</h2>
            </div>

            <div className="feature-grid">
              {features.map((feature) => (
                <article key={feature.title} className="feature-card">
                  <div className="feature-icon">✦</div>
                  <h3>{feature.title}</h3>
                  <p>{feature.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="workflow" className="section alt">
          <div className="container workflow-grid">
            <div>
              <span className="eyebrow">Workflow</span>
              <h2>From intake to action in a single autonomous loop.</h2>
            </div>

            <div className="workflow-list">
              {workflowSteps.map((step, index) => (
                <div key={step} className="workflow-item">
                  <span className="step-index">0{index + 1}</span>
                  <p>{step}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="coverage" className="section">
          <div className="container coverage-grid">
            <div className="coverage-card panel">
              <span className="eyebrow">Coverage</span>
              <h3>Built to support high-velocity public data monitoring.</h3>
              <ul>
                {useCases.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>

            <div className="coverage-card panel accent">
              <span className="eyebrow">API status</span>
              <h3>{health.status}</h3>
              <p>
                {health.ok
                  ? 'The LeadOps backend is responding normally.'
                  : 'The service may still be warming or unreachable from this static deployment.'}
              </p>
              <a href={`${backendUrl}/health`} className="inline-link">
                Open backend health endpoint
              </a>
            </div>
          </div>
        </section>

        <section id="pricing" className="section alt">
          <div className="container pricing-wrap">
            <div className="section-header center">
              <span className="eyebrow">Pricing</span>
              <h2>Simple deployment for teams that need speed without the spreadsheet chaos.</h2>
            </div>

            <div className="pricing-card panel">
              <div>
                <span className="pricing-label">Starter</span>
                <h3>$0</h3>
                <p>Sandbox access and workflow preview</p>
              </div>
              <button className="button primary">Try live demo</button>
            </div>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="container footer-row">
          <div>© 2026 LeadOps</div>
          <div>Ops-grade dataset extraction for modern public records teams</div>
        </div>
      </footer>
    </div>
  );
}

export default App;
