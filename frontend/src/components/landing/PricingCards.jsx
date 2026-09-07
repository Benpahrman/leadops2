import React from 'react';
import { useNavigate } from 'react-router-dom';

const plans = [
  {
    name: 'Weekly Batch',
    price: '$250',
    frequency: '/ month',
    desc: 'Best for low-volume jurisdictions and weekly recap pipelines.',
    features: [
      'Weekly automated extraction',
      'Up to 1,500 records / month',
      'Google Sheets synchronization',
      'Standard email support',
      '50% escrow milestone protection',
    ],
    highlight: false,
    cta: 'Start Weekly Sandbox',
  },
  {
    name: 'Daily Production Sync',
    price: '$495',
    frequency: '/ month',
    desc: 'Our flagship daily feed. Fresh filings delivered every morning at 6:00 AM UTC.',
    features: [
      'Daily morning extraction (6:00 AM UTC)',
      'Up to 10,000 records / month',
      'Google Sheets + Webhook dispatch',
      'Priority residential proxy routing',
      'Custom schema mapping (up to 15 fields)',
      'Flexible 30-day pause/resume',
    ],
    highlight: true,
    badge: 'MOST POPULAR',
    cta: 'Launch Daily Sandbox',
  },
  {
    name: 'AI Heavy Extraction',
    price: '$850',
    frequency: '/ month',
    desc: 'For complex dockets requiring multi-page PDF OCR and deep document parsing.',
    features: [
      'Hourly or multi-daily syncs',
      'Unlimited monthly records',
      'Automated AI OCR on PDF filings',
      'Dedicated residential IP pools',
      'Sub-2-hour SLA on DOM breakage',
      'Full API + Webhook integration',
    ],
    highlight: false,
    cta: 'Start Enterprise Feed',
  },
];

export default function PricingCards() {
  const navigate = useNavigate();

  return (
    <section id="pricing" style={{ padding: '70px 0', background: 'var(--bg-surface)' }}>
      <div className="container">
        <div style={{ textAlign: 'center', marginBottom: '44px' }}>
          <span style={{ color: 'var(--green)', fontFamily: 'var(--mono)', fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1px' }}>
            Predictable Flat Pricing
          </span>
          <h2 style={{ fontSize: '32px', fontWeight: 800, color: '#fff', marginTop: '6px' }}>
            50% Milestone Escrow. Pay Rest Only After QA Passes.
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px', maxWidth: '640px', margin: '8px auto 0' }}>
            All custom extractor builds require a $250.00 setup deposit locked in escrow. The remaining balance activates only after you verify 25 live rows.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', alignItems: 'stretch' }}>
          {plans.map((p, i) => (
            <div
              key={i}
              className="card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                borderColor: p.highlight ? 'var(--green)' : 'var(--border)',
                background: p.highlight ? 'linear-gradient(180deg, #162238 0%, #0f172a 100%)' : 'var(--card)',
                boxShadow: p.highlight ? '0 0 30px var(--green-glow)' : 'var(--shadow-card)',
                position: 'relative',
              }}
            >
              {p.badge && (
                <div style={{
                  position: 'absolute',
                  top: '-12px',
                  right: '20px',
                  background: 'var(--green)',
                  color: '#041410',
                  padding: '4px 12px',
                  borderRadius: '12px',
                  fontSize: '11px',
                  fontWeight: 800,
                  fontFamily: 'var(--mono)',
                }}>
                  {p.badge}
                </div>
              )}

              <div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>{p.name}</div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px', minHeight: '36px' }}>
                  {p.desc}
                </div>

                <div style={{ margin: '20px 0' }}>
                  <span style={{ fontSize: '38px', fontWeight: 800, color: '#fff', fontFamily: 'var(--mono)' }}>{p.price}</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}> {p.frequency}</span>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--cyan)', marginBottom: '16px', fontWeight: 600 }}>
                  + $250 setup deposit (50% escrow milestone)
                </div>

                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {p.features.map((feat, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
                      <span style={{ color: 'var(--green)', fontSize: '14px' }}>✓</span>
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                className={`btn ${p.highlight ? 'btn-primary' : 'btn-outline'}`}
                style={{ width: '100%', marginTop: '28px', padding: '12px' }}
                onClick={() => navigate('/p/lead-apex-roofing')}
              >
                {p.cta} ➔
              </button>
            </div>
          ))}
        </div>

        {/* Buyout Note */}
        <div style={{ marginTop: '36px', textAlign: 'center', padding: '20px', background: 'var(--card)', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '14px', color: '#fff', fontWeight: 700 }}>
            Want 100% self-hosted ownership?
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            We offer a <b>$1,500 flat Perpetual Source Code Buyout</b>. You receive the complete standalone Playwright scraper Python codebase (.zip) to run on your own infrastructure forever.
          </div>
        </div>
      </div>
    </section>
  );
}
