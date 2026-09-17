import React from 'react';

export default function DirectDownloadSection({ leadId }) {
  return (
    <div>
      <div style={{ background: 'var(--card-alt)', borderRadius: '10px', padding: '20px', border: '1px solid var(--border-light)', marginBottom: '20px' }}>
        <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#fff', margin: '0 0 8px 0' }}>
          📥 Instant Multi-Format Data Downloads
        </h4>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, margin: '0 0 16px 0' }}>
          Export your full dataset directly in Excel (.xlsx), CSV, JSON, or streaming JSONL formats.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
          <a
            href={`/api/dashboard/${leadId}/export/xlsx`}
            download={`leadops_feed_${leadId}.xlsx`}
            className="btn btn-primary"
            style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
          >
            📗 Download Excel (.xlsx)
          </a>
          <a
            href={`/api/dashboard/${leadId}/export/csv`}
            download={`leadops_feed_${leadId}.csv`}
            className="btn btn-cyan"
            style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
          >
            📊 Download CSV (.csv)
          </a>
          <a
            href={`/api/dashboard/${leadId}/export/json`}
            download={`leadops_feed_${leadId}.json`}
            className="btn btn-outline"
            style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
          >
            📦 Download JSON (.json)
          </a>
          <a
            href={`/api/dashboard/${leadId}/export/jsonl`}
            download={`leadops_feed_${leadId}.jsonl`}
            className="btn btn-outline"
            style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
          >
            📜 Download JSONL (.jsonl)
          </a>
        </div>
      </div>
    </div>
  );
}
