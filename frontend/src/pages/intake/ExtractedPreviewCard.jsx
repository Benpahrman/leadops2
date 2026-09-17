import React from 'react';

export default function ExtractedPreviewCard({
  extractedResult,
  onOpenCheckout,
  onNavigateSandbox,
}) {
  if (!extractedResult || !extractedResult.sample_records || extractedResult.sample_records.length === 0) {
    return null;
  }

  const records = extractedResult.sample_records;
  const cols = Object.keys(records[0] || {}).slice(0, 6);

  return (
    <div style={{
      marginTop: '32px',
      background: 'rgba(15, 23, 42, 0.9)',
      border: '1px solid var(--border-highlight)',
      borderRadius: '12px',
      padding: '24px 28px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '18px' }}>
        <div>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(16, 185, 129, 0.15)',
            color: 'var(--green)',
            fontSize: '11px',
            fontWeight: 800,
            padding: '3px 10px',
            borderRadius: '12px',
            marginBottom: '6px',
          }}>
            <span>✓</span> {records.length} LIVE SOURCED RECORDS EXTRACTED
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>
            Authentic Sample Filings Harvested from Target Portal
          </h3>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Source: <a href={extractedResult.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--cyan)' }}>{extractedResult.source_url}</a>
          </span>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onOpenCheckout}
            style={{ fontWeight: 800, padding: '10px 20px', fontSize: '13px', background: 'linear-gradient(135deg, #10b981, #059669)' }}
          >
            ⚡ Authorize $99 &amp; Enter Customer Portal ➔
          </button>

          <button
            type="button"
            className="btn btn-outline"
            onClick={onNavigateSandbox}
            style={{ fontWeight: 700, padding: '10px 18px', fontSize: '13px' }}
          >
            🔍 View Full Sandbox
          </button>
        </div>
      </div>

      <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
          <thead>
            <tr style={{ background: 'rgba(255, 255, 255, 0.04)', borderBottom: '1px solid rgba(255, 255, 255, 0.08)' }}>
              {cols.map((col) => (
                <th key={col} style={{ padding: '10px 14px', color: 'var(--cyan)', fontWeight: 700, textTransform: 'capitalize' }}>
                  {col.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.slice(0, 5).map((row, rIdx) => (
              <tr key={rIdx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                {cols.map((col) => (
                  <td key={col} style={{ padding: '10px 14px', color: '#cbd5e1' }}>
                    {String(row[col] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
