import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function HeroSection() {
  const navigate = useNavigate();

  return (
    <section style={{ padding: '70px 0 50px', textAlign: 'center' }}>
      <div className="container" style={{ maxWidth: '880px' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'var(--card-alt)', border: '1px solid var(--border)', padding: '6px 14px', borderRadius: '24px', fontSize: '12px', marginBottom: '24px' }}>
          <span style={{ color: 'var(--green)' }}>✓</span>
          <span style={{ color: 'var(--text-muted)' }}>Verified Public Records Stream</span>
          <span style={{ color: 'var(--border-light)' }}>|</span>
          <span style={{ color: 'var(--cyan)', fontFamily: 'var(--mono)' }}>Zero Manual Portal Lookups</span>
        </div>

        <h1 style={{ fontSize: '44px', fontWeight: 800, lineHeight: 1.15, letterSpacing: '-1px', marginBottom: '20px', color: '#fff' }}>
          Turn Slow County Dockets Into{' '}
          <span style={{ background: 'linear-gradient(135deg, var(--green), var(--cyan))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Automated Live Data Feeds
          </span>
        </h1>

        <p style={{ fontSize: '17px', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '32px' }}>
          We synthesize custom Playwright crawlers that extract daily county filings and legal dockets, verified with 1-click proof links, and delivered straight to Google Sheets or your custom Webhook.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary btn-lg"
            onClick={() => navigate('/p/lead-apex-roofing')}
          >
            Explore Live Sample Sandbox ➔
          </button>
          <a href="#roi-calculator" className="btn btn-outline btn-lg">
            Calculate Your ROI
          </a>
        </div>

        {/* Quick proof stats bar */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginTop: '48px', textAlign: 'left' }}>
          <div className="stat-card">
            <div className="stat-label">Verification Proof</div>
            <div className="stat-value" style={{ color: 'var(--green)', fontSize: '20px' }}>1-Click Dockets</div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>Direct links on every row</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Milestone Guarantee</div>
            <div className="stat-value" style={{ color: 'var(--cyan)', fontSize: '20px' }}>$99 Sprint</div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>100% credited to Month 1 in escrow</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Delivery Target</div>
            <div className="stat-value" style={{ color: '#fff', fontSize: '20px' }}>06:00 AM UTC</div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>Google Sheets &amp; Webhooks</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Autonomy</div>
            <div className="stat-value" style={{ color: 'var(--purple)', fontSize: '20px' }}>7-Agent Swarm</div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>Hardened Playwright scripts</div>
          </div>
        </div>
      </div>
    </section>
  );
}
