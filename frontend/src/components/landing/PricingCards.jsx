import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export default function PricingCards() {
  const navigate = useNavigate();
  const [isAnnual, setIsAnnual] = useState(false);

  const plans = [
    {
      id: 'starter',
      name: 'Starter Docket Feed',
      monthlyPrice: 150,
      annualPrice: 120,
      tierBadge: 'ENTRY TIER',
      desc: 'Engineered for single-county municipal registries, boutique legal teams, or weekly recap pipelines.',
      highlight: false,
      features: [
        'Weekly automated extraction (4x / month)',
        'Up to 2,000 verified filings / month',
        'Direct Google Sheets auto-synchronization',
        'Official government docket proof links on every row',
        '$99 Setup Sprint deposit (100% credited to Month 1)',
        'Standard email support (24-hour SLA)',
      ],
      cta: 'Configure Starter Pipeline',
    },
    {
      id: 'production',
      name: 'Production Feed',
      monthlyPrice: 250,
      annualPrice: 199,
      tierBadge: 'MOST POPULAR • FLAGSHIP',
      desc: 'Our flagship automated pipeline. Fresh court filings and building permits extracted and delivered every morning at 06:00 UTC.',
      highlight: true,
      features: [
        'Daily morning automated extraction (06:00 UTC)',
        'Up to 15,000 verified filings / month',
        'Google Sheets + Webhook + REST API dispatch',
        'Automated Cloudflare & WAF anti-bot bypass',
        'Custom schema mapping (up to 20 portal fields)',
        'Autonomous AST self-healing on portal DOM changes',
        '$99 Setup Sprint (100% credited to Month 1)',
        '$151 balance due only upon >=95% QA pass',
        '30-Day flexible pause/resume anytime',
      ],
      cta: 'Launch Production Pipeline',
    },
    {
      id: 'enterprise',
      name: 'Enterprise Swarm',
      monthlyPrice: 590,
      annualPrice: 470,
      tierBadge: 'MULTI-JURISDICTION',
      desc: 'For high-volume legal intelligence, continuous multi-county monitoring, and automated multi-page PDF OCR extraction.',
      highlight: false,
      features: [
        'Hourly or continuous multi-jurisdiction sync',
        'Unlimited monthly records & filings',
        'Automated AI OCR on PDF filings & blueprints',
        'Dedicated private residential IP proxy pool',
        'Sub-2-hour SLA response on portal DOM alterations',
        'Direct PostgreSQL / Snowflake / BigQuery ingestion',
        'Custom webhook signing & HMAC authentication',
        'Dedicated enterprise pipeline engineer',
      ],
      cta: 'Deploy Enterprise Swarm',
    },
  ];

  return (
    <section id="pricing" style={{ padding: '80px 0', background: 'var(--bg-surface)' }}>
      <div className="container">
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.25)', padding: '4px 12px', borderRadius: '20px', fontSize: '11px', fontWeight: 700, color: 'var(--cyan)', textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: '14px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--cyan)' }}></span>
            Predictable Institutional Pricing
          </div>
          <h2 style={{ fontSize: '36px', fontWeight: 800, color: '#fff', letterSpacing: '-0.8px', lineHeight: 1.2 }}>
            Zero-Risk Escrow. Pay Balance Only After QA Verification.
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '12px', maxWidth: '720px', margin: '12px auto 0', lineHeight: 1.6 }}>
            Every custom extractor begins with a <b style={{ color: '#fff' }}>$99 Setup Sprint deposit</b> protected in third-party escrow and credited 100% toward Month 1. The net balance ($151 on Production) activates only after you inspect 25 live government filings with &ge;95% schema conformance.
          </p>
        </div>

        {/* Monthly vs Annual Toggle */}
        <div style={{ textAlign: 'center' }}>
          <div className="pricing-toggle-container">
            <button
              type="button"
              className={`pricing-toggle-pill ${!isAnnual ? 'active' : ''}`}
              onClick={() => setIsAnnual(false)}
            >
              Monthly Billing
            </button>
            <button
              type="button"
              className={`pricing-toggle-pill ${isAnnual ? 'active' : ''}`}
              onClick={() => setIsAnnual(true)}
            >
              Annual Billing
              <span style={{ fontSize: '10px', background: 'var(--green)', color: '#041410', padding: '2px 6px', borderRadius: '10px', fontWeight: 800 }}>
                SAVE 20%
              </span>
            </button>
          </div>
        </div>

        {/* Pricing Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))', gap: '24px', alignItems: 'stretch' }}>
          {plans.map((p) => {
            const price = isAnnual ? p.annualPrice : p.monthlyPrice;
            return (
              <div
                key={p.id}
                className={`pricing-card-luxury ${p.highlight ? 'pricing-card-featured' : ''}`}
              >
                {p.highlight && (
                  <div style={{
                    position: 'absolute',
                    top: '-13px',
                    right: '24px',
                    background: 'linear-gradient(135deg, #0284c7 0%, #10b981 100%)',
                    color: '#fff',
                    padding: '4px 14px',
                    borderRadius: '12px',
                    fontSize: '11px',
                    fontWeight: 800,
                    letterSpacing: '0.5px',
                    boxShadow: '0 4px 14px rgba(2, 132, 199, 0.4)',
                  }}>
                    {p.tierBadge}
                  </div>
                )}

                <div>
                  {!p.highlight && (
                    <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '4px' }}>
                      {p.tierBadge}
                    </div>
                  )}

                  <h3 style={{ fontSize: '22px', fontWeight: 800, color: '#fff' }}>{p.name}</h3>
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px', minHeight: '44px', lineHeight: 1.5 }}>
                    {p.desc}
                  </p>

                  <div style={{ margin: '24px 0 16px', display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                    <span style={{ fontSize: '42px', fontWeight: 800, color: '#fff', fontFamily: 'var(--mono)', letterSpacing: '-1px' }}>
                      ${price}
                    </span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '13px', fontWeight: 600 }}>/ month</span>
                    {isAnnual && (
                      <span style={{ fontSize: '11px', color: 'var(--green)', marginLeft: '4px' }}>
                        (billed annually)
                      </span>
                    )}
                  </div>

                  {/* Setup sprint callout */}
                  <div style={{
                    background: 'rgba(56, 189, 248, 0.08)',
                    border: '1px solid rgba(56, 189, 248, 0.2)',
                    borderRadius: '6px',
                    padding: '8px 12px',
                    fontSize: '12px',
                    color: 'var(--cyan)',
                    fontWeight: 600,
                    marginBottom: '20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    </svg>
                    <span>
                      {isAnnual
                        ? 'Setup Sprint Fee Waived on Annual'
                        : '$99 Setup Sprint Deposit (100% credited to Month 1)'}
                    </span>
                  </div>

                  <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {p.features.map((feat, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', fontSize: '13px', color: 'var(--text)' }}>
                        <svg style={{ flexShrink: 0, marginTop: '2px', color: p.highlight ? 'var(--cyan)' : 'var(--green)' }} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        <span style={{ lineHeight: 1.4 }}>{feat}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  className={`btn ${p.highlight ? 'btn-primary' : 'btn-outline'}`}
                  style={{
                    width: '100%',
                    marginTop: '32px',
                    padding: '13px',
                    fontWeight: 700,
                    fontSize: '13px',
                    boxShadow: p.highlight ? '0 4px 20px rgba(16, 185, 129, 0.35)' : 'none',
                  }}
                  onClick={() => navigate(`/get-started?plan=${p.id}`)}
                >
                  {p.cta} ➔
                </button>
              </div>
            );
          })}
        </div>

        {/* Perpetual Source Code Buyout Card */}
        <div style={{
          marginTop: '36px',
          padding: '28px 32px',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(17, 29, 51, 0.9))',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid #1e3355',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '20px',
        }}>
          <div style={{ flex: 1, minWidth: '300px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ fontSize: '11px', fontWeight: 800, background: 'rgba(168, 85, 247, 0.15)', color: '#d8b4fe', padding: '3px 9px', borderRadius: '4px', border: '1px solid rgba(168, 85, 247, 0.3)', fontFamily: 'var(--mono)' }}>
                PERPETUAL OWNERSHIP
              </span>
              <span style={{ color: 'var(--text-dim)' }}>•</span>
              <span style={{ fontSize: '12px', color: 'var(--green)', fontWeight: 700 }}>Zero Vendor Lock-in</span>
            </div>
            <h4 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>
              100% Self-Hosted Source Code Buyout &mdash; $1,500 One-Time
            </h4>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px', maxWidth: '720px', lineHeight: 1.5 }}>
              Prefer complete infrastructure independence? Receive the full standalone Playwright &amp; Python AST pipeline codebase repository (.zip) with complete selector definitions and WAF bypass modules to run forever on your own cloud servers.
            </p>
          </div>

          <button
            className="btn btn-outline"
            style={{ padding: '11px 22px', fontSize: '13px', fontWeight: 700, borderColor: 'var(--purple)', color: '#d8b4fe', background: 'rgba(168, 85, 247, 0.08)' }}
            onClick={() => navigate('/get-started?plan=buyout')}
          >
            Inquire Source Buyout ➔
          </button>
        </div>

        {/* 4-Pillar Enterprise Trust Matrix */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
          marginTop: '32px',
          paddingTop: '24px',
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>Stripe Escrow Protected</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>$99 held until QA certification</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>100% Zero-Mock Guarantee</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Direct government open data links</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>Self-Healing AST Swarm</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Auto-repairs on portal markup changes</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>Flexible 30-Day Pause</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Zero penalty pause/resume anytime</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

