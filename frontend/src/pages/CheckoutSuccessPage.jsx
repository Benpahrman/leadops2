import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function CheckoutSuccessPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [leadId, setLeadId] = useState(() => {
    return searchParams.get('lead_id') || localStorage.getItem('leadops_active_lead_id') || 'primary-feed';
  });

  const [timestamp] = useState(() => new Date().toUTCString());

  useEffect(() => {
    if (leadId && leadId !== 'primary-feed') {
      localStorage.setItem('leadops_active_lead_id', leadId);
    }
  }, [leadId]);

  return (
    <main style={{ padding: '60px 0 100px', textAlign: 'center' }}>
      <div className="container" style={{ maxWidth: '680px' }}>
        <div style={{ fontSize: '54px', marginBottom: '16px' }}>🎉</div>
        
        <div className="badge-tag badge-green" style={{ fontSize: '13px', padding: '6px 14px', marginBottom: '12px' }}>
          ✓ 50% MILESTONE ESCROW LOCKED ($250.00 USD)
        </div>

        <h1 style={{ fontSize: '32px', fontWeight: 800, color: '#fff', marginBottom: '10px' }}>
          Payment Confirmed — Autonomous Dev Swarm Initiated
        </h1>

        <p style={{ fontSize: '15px', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '28px' }}>
          Your milestone deposit is safely held in third-party escrow. Our 7-agent engineering swarm has started DOM analysis, stealth proxy assignment, and code compilation for your custom feed.
        </p>

        {/* Binding Statement of Work (SOW) Digital Acceptance Receipt */}
        <div className="card" style={{ textAlign: 'left', background: 'var(--card-alt)', border: '1px solid var(--border-highlight)', marginBottom: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#fff' }}>
              📋 Statement of Work (SOW) Digital Acceptance Receipt
            </h3>
            <span style={{ fontSize: '11px', color: 'var(--green)', fontFamily: 'var(--mono)', fontWeight: 700 }}>
              VERIFIED &amp; EXECUTED
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', fontSize: '12px', lineHeight: 1.6 }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Client Feed ID:</span>
              <div style={{ color: '#fff', fontWeight: 700, fontFamily: 'var(--mono)' }}>{leadId}</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Escrow Deposit:</span>
              <div style={{ color: 'var(--green)', fontWeight: 700, fontFamily: 'var(--mono)' }}>$250.00 USD (50% Milestone)</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Timestamp:</span>
              <div style={{ color: '#fff', fontFamily: 'var(--mono)' }}>{timestamp}</div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Delivery SLA:</span>
              <div style={{ color: 'var(--cyan)', fontWeight: 700 }}>Daily by 08:00 AM UTC to Sheets / Webhook</div>
            </div>
          </div>

          <div style={{ marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '12px', fontSize: '11px', color: 'var(--text-muted)' }}>
            ✓ <b>Binding Legal Agreement:</b> By authorizing payment, Client consented to the <a href="/terms" target="_blank" style={{ color: 'var(--cyan)', textDecoration: 'underline' }}>Terms of Service</a>. Final balance ($250.00) is payable strictly upon &gt;=95.0% QA sample verification.
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary btn-lg"
            onClick={() => navigate(`/dashboard/${leadId}`)}
          >
            Launch Customer Dashboard &amp; Configure Feed ➔
          </button>
          <a
            href={`/api/dashboard/${leadId}/invoice`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-outline btn-lg"
          >
            📄 View &amp; Print Receipt
          </a>
        </div>
      </div>
    </main>
  );
}
