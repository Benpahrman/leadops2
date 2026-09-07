import React from 'react';
import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <span style={{ color: '#fff', fontWeight: 800 }}>OmniLeadFeeder</span>
            <span>•</span>
            <span style={{ color: 'var(--green)', fontFamily: 'var(--mono)', fontSize: '11px', fontWeight: 700 }}>
              100% ZERO-MOCK GUARANTEE
            </span>
          </div>
          <div style={{ color: 'var(--text-dim)', fontSize: '12px' }}>
            Autonomous public-records extraction engine. 08:00 AM daily delivery to Google Sheets &amp; CRM webhooks.
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '18px', fontSize: '12px', flexWrap: 'wrap' }}>
          <Link to="/terms" style={{ color: 'var(--cyan)' }}>
            📄 Terms &amp; SOW
          </Link>
          <Link to="/privacy" style={{ color: 'var(--cyan)' }}>
            🔒 Privacy Policy
          </Link>
          <a href="mailto:support@omnileadfeeder.tech" style={{ color: 'var(--text-muted)' }}>
            support@omnileadfeeder.tech
          </a>
        </div>
      </div>
    </footer>
  );
}
