import React from 'react';

const features = [
  {
    icon: '🏛️',
    title: 'Zero Mock Data, 1-Click Verification',
    text: 'Every row pulled connects directly to the official government open data docket or registry portal. Click [Verify Source ↗] to inspect the authentic county record instantly.',
  },
  {
    icon: '🤖',
    title: '7-Agent Autonomous Dev Swarm',
    text: 'Our AI swarm (Planner, DOM Architect, Stealth Engineer, Systems Architect, Junior Dev, QA Gatekeeper) synthesizes, tests, and hardens extraction scripts automatically.',
  },
  {
    icon: '🛡️',
    title: '100% Escrow Guarantee ($99 Setup Sprint)',
    text: 'Authorize your $99 setup sprint deposit locked safely in escrow (100% credited to Month 1). Funds remain protected until live rows pass >=95% QA verification.',
  },
  {
    icon: '🚀',
    title: 'Direct Google Sheets & Webhooks',
    text: 'Receive fresh records directly in your Google Spreadsheet or dispatch clean JSON payloads into your CRM, database, or Slack channel every morning at 06:00 AM UTC.',
  },
  {
    icon: '📦',
    title: 'Perpetual Source Code Buyout',
    text: 'Never feel vendor-locked. Purchase the standalone Playwright extractor Python codebase (.zip) anytime for a flat $1,500 one-time fee to run entirely on your own servers.',
  },
  {
    icon: '⏸️',
    title: '30-Day Flexible Pause & Resume',
    text: 'Slow season or pipeline overhaul? Pause deliveries for 30 days from your self-service dashboard with zero penalty while preserving all selectors and schema configurations.',
  },
];

export default function FeaturesGrid() {
  return (
    <section style={{ padding: '70px 0' }}>
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: '44px' }}>
          <span style={{ color: 'var(--cyan)', fontFamily: 'var(--mono)', fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px' }}>
            Enterprise Reliability
          </span>
          <h2 style={{ fontSize: '32px', fontWeight: 800, color: '#fff', marginTop: '6px' }}>
            Engineered for Flawless Public Records Ingestion
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px' }}>
            Built to handle CAPTCHAs, changing DOMs, anti-bot WAF defenses, and multi-county filings without breaking.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
          {features.map((f, i) => (
            <div key={i} className="card">
              <div style={{ fontSize: '32px', marginBottom: '14px' }}>{f.icon}</div>
              <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>{f.title}</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6 }}>{f.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
