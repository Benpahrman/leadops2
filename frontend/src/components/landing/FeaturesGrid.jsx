import React from 'react';

const features = [
  {
    iconSvg: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
        <polyline points="9 22 9 12 15 12 15 22"/>
      </svg>
    ),
    title: 'Zero Mock Data, 1-Click Verification',
    text: 'Every extracted filing connects directly to the authentic municipal open data docket. Click the verification link to inspect official county proof instantly in your browser.',
  },
  {
    iconSvg: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
        <rect x="9" y="9" width="6" height="6"/>
        <line x1="9" y1="1" x2="9" y2="4"/>
        <line x1="15" y1="1" x2="15" y2="4"/>
        <line x1="9" y1="20" x2="9" y2="23"/>
        <line x1="15" y1="20" x2="15" y2="23"/>
        <line x1="20" y1="9" x2="23" y2="9"/>
        <line x1="20" y1="14" x2="23" y2="14"/>
        <line x1="1" y1="9" x2="4" y2="9"/>
        <line x1="1" y1="14" x2="4" y2="14"/>
      </svg>
    ),
    title: '7-Agent Autonomous Dev Swarm',
    text: 'Our specialized AI swarm (Planner, DOM Architect, Stealth Engineer, Systems Architect, Junior Dev, QA Gatekeeper) synthesizes, tests, and hardens extraction ASTs automatically.',
  },
  {
    iconSvg: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    ),
    title: '100% Escrow Guarantee ($99 Setup Sprint)',
    text: 'Authorize your $99 setup sprint deposit safely in third-party escrow (100% credited to Month 1). Balance activates only after 25 live rows pass >=95% QA verification.',
  },
  {
    iconSvg: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
    ),
    title: 'Automated Google Sheets & Webhook Sync',
    text: 'Receive fresh records directly into your Google Spreadsheet, or stream clean JSON payloads into your CRM, PostgreSQL database, or webhook endpoint every morning at 06:00 UTC.',
  },
  {
    iconSvg: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6"/>
        <polyline points="8 6 2 12 8 18"/>
      </svg>
    ),
    title: 'Perpetual Source Code Buyout',
    text: 'Never feel vendor-locked. Purchase the standalone Playwright extractor Python codebase (.zip) anytime for a flat $1,500 one-time fee to run indefinitely on your private servers.',
  },
  {
    iconSvg: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="10" y1="15" x2="10" y2="9"/>
        <line x1="14" y1="15" x2="14" y2="9"/>
      </svg>
    ),
    title: '30-Day Flexible Pause & Resume',
    text: 'Experiencing a seasonal lull or pipeline migration? Pause deliveries for up to 30 days from your self-service portal with zero penalty while preserving all selectors and field mappings.',
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
            Built to navigate CAPTCHAs, shifting DOMs, Cloudflare anti-bot WAF defenses, and multi-county dockets without human intervention.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
          {features.map((f, i) => (
            <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid var(--border)',
                display: 'grid',
                placeItems: 'center',
                marginBottom: '8px',
              }}>
                {f.iconSvg}
              </div>
              <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#fff' }}>{f.title}</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6 }}>{f.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

