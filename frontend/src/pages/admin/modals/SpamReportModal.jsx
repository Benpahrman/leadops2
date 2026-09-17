import React from 'react';

/**
 * Modal to view SpamAssassin deliverability reports, rule triggers, and placement telemetry.
 */
export default function SpamReportModal({ report, onClose }) {
  if (!report) return null;

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div
        className="admin-modal-content"
        style={{ maxWidth: '650px', background: 'var(--card)', border: '1px solid var(--border)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '24px' }}>🛡️</span>
            <div>
              <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#fff', margin: 0 }}>
                SpamAssassin Deliverability Report
              </h3>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {report.email_address}
              </div>
            </div>
          </div>
          <button
            className="btn btn-outline"
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={onClose}
          >
            ✕ Close
          </button>
        </div>

        {/* Metric Pills */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '18px' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>SPF Status</div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: report.spf?.includes('pass') ? 'var(--green)' : '#f87171', marginTop: '4px' }}>
              {report.spf?.toUpperCase() || 'UNKNOWN'}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>DKIM Status</div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: report.dkim?.includes('pass') ? 'var(--green)' : '#fbbf24', marginTop: '4px' }}>
              {report.dkim?.toUpperCase() || 'NONE'}
            </div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Spam Score</div>
            <div style={{ fontSize: '14px', fontWeight: 700, color: (report.spam_score || 0) <= 2.0 ? 'var(--green)' : '#f87171', marginTop: '4px' }}>
              {typeof report.spam_score === 'number' ? report.spam_score.toFixed(1) : report.spam_score}
            </div>
          </div>
        </div>

        {/* Recommendation Callout */}
        {report.recommendation && (
          <div
            style={{
              background: report.status === 'HEALTHY' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
              border: `1px solid ${report.status === 'HEALTHY' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
              borderRadius: 'var(--radius-sm)',
              padding: '12px 14px',
              marginBottom: '16px',
              fontSize: '12px',
              color: report.status === 'HEALTHY' ? 'var(--green)' : '#fbbf24',
              lineHeight: 1.5,
            }}
          >
            <b>💡 Recommendation:</b> {report.recommendation}
          </div>
        )}

        {/* Raw SpamAssassin Report Output */}
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
            SpamAssassin Rule Triggers &amp; Telemetry:
          </div>
          <pre
            style={{
              background: '#090d16',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              padding: '14px',
              fontSize: '11px',
              color: '#e2e8f0',
              fontFamily: 'var(--mono)',
              maxHeight: '260px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.5,
              margin: 0,
            }}
          >
            {report.spam_report || 'No SpamAssassin rule triggers recorded. Clean message score.'}
          </pre>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <button
            className="btn btn-primary"
            style={{ fontSize: '12px', padding: '8px 18px' }}
            onClick={onClose}
          >
            Close Report
          </button>
        </div>
      </div>
    </div>
  );
}
