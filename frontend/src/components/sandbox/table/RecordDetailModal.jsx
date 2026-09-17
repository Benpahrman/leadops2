import React from 'react';

export default function RecordDetailModal({
  selectedRecord,
  setSelectedRecord,
  sourceUrl,
  companyName,
  handleCopyJson,
  copiedJson,
}) {
  if (!selectedRecord) return null;

  return (
    <div className="record-drawer-overlay" onClick={() => setSelectedRecord(null)}>
      <div className="record-drawer" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
          <div>
            <span className="badge-tag badge-green" style={{ marginBottom: '8px' }}>
              ✓ AUTHENTIC DOCKET RECORD
            </span>
            <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginTop: '4px' }}>
              {selectedRecord.id || selectedRecord.case_number || selectedRecord.filing_number || 'Filing Details'}
            </h3>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
              {selectedRecord.primary_party || selectedRecord.debtor_name || companyName}
            </div>
          </div>
          <button className="modal-close" onClick={() => setSelectedRecord(null)} style={{ position: 'static' }}>
            ✕
          </button>
        </div>

        {/* Quick Action Links */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
          <a
            href={selectedRecord.source_url || sourceUrl || 'https://data.gov'}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
            style={{ fontSize: '12px', padding: '8px 14px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            <span>Open Government Source Docket</span>
          </a>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => handleCopyJson(selectedRecord)}
            style={{ fontSize: '12px', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            <span>{copiedJson ? '✓ Copied' : 'Copy JSON'}</span>
          </button>
        </div>

        {/* Formatted Key-Value Grid */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--cyan)', textTransform: 'uppercase', marginBottom: '10px', letterSpacing: '0.5px' }}>
            Parsed Record Attributes
          </div>
          {Object.entries(selectedRecord).map(([key, val]) => (
            <div key={key} className="drawer-field-row">
              <span className="drawer-field-label">{key.replace(/_/g, ' ')}</span>
              <span className="drawer-field-value">
                {val === null || val === undefined ? '—' : String(val)}
              </span>
            </div>
          ))}
        </div>

        {/* Raw JSON View */}
        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.5px' }}>
            Raw JSON Payload
          </div>
          <pre style={{
            background: '#040914',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '14px',
            fontSize: '11px',
            fontFamily: 'var(--mono)',
            color: '#a7f3d0',
            maxHeight: '220px',
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}>
            {JSON.stringify(selectedRecord, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
