import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function CheckoutCancelPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const slug = searchParams.get('slug') || localStorage.getItem('leadops_active_lead_id') || 'lead-apex-roofing';

  return (
    <main style={{ padding: '70px 0 100px', textAlign: 'center' }}>
      <div className="container" style={{ maxWidth: '640px' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>⏸️</div>

        <div className="badge-tag badge-yellow" style={{ fontSize: '12px', padding: '6px 14px', marginBottom: '14px' }}>
          CHECKOUT PAUSED • NO CHARGES INCURRED
        </div>

        <h1 style={{ fontSize: '30px', fontWeight: 800, color: '#fff', marginBottom: '12px' }}>
          Your Extractor Build Is on Standby
        </h1>

        <p style={{ fontSize: '15px', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '28px' }}>
          No funds were charged. Your custom sandbox and verified 25-row sample dockets are safely preserved.
        </p>

        <div className="card" style={{ textAlign: 'left', background: 'var(--card-alt)', border: '1px solid var(--border)', marginBottom: '28px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#fff', marginBottom: '10px' }}>
            🛡️ Remember Our 100% Escrow Protection:
          </h3>
          <ul style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <li><b>Zero Financial Risk:</b> The $99.00 setup sprint deposit remains locked in third-party escrow (100% credited to Month 1).</li>
            <li><b>QA Gatekeeper Standard:</b> If our 7-agent dev swarm doesn't deliver &gt;=95.0% live verified rows, your deposit is automatically refunded in full.</li>
            <li><b>Final Balance Due Only on Pass:</b> The net balance of $151 is payable only after you verify the stream meets your expectations.</li>
          </ul>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary btn-lg"
            onClick={() => navigate(`/p/${slug}`)}
          >
            Resume Sandbox &amp; Authorize Escrow ➔
          </button>
          <button
            className="btn btn-outline btn-lg"
            onClick={() => navigate('/')}
          >
            Return to Homepage
          </button>
        </div>
      </div>
    </main>
  );
}
