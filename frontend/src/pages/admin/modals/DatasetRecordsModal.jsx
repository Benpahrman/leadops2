import React from 'react';

/**
 * Modal to preview extracted dataset records in tabular format and export as JSON.
 */
export default function DatasetRecordsModal({ modalState, onClose, showToast }) {
  if (!modalState || !modalState.open) return null;

  const handleDownload = () => {
    try {
      const blob = new Blob([JSON.stringify(modalState.rows || [], null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${modalState.leadId || 'dataset'}_records.json`;
      a.click();
      URL.revokeObjectURL(url);
      if (showToast) {
        showToast('JSON dataset downloaded!', 'success');
      }
    } catch (err) {
      if (showToast) {
        showToast('Failed to download dataset', 'error');
      }
    }
  };

  const rows = modalState.rows || [];
  const firstRow = rows[0] || {};
  const columns = Object.keys(firstRow);

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>{modalState.title}</h3>
            <span style={{ fontSize: '12px', color: 'var(--green)' }}>
              {modalState.count ?? rows.length} Total Records Extracted
            </span>
          </div>
          <button
            className="btn btn-outline"
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={onClose}
          >
            ✕ Close
          </button>
        </div>

        <div style={{ maxHeight: '420px', overflow: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', marginTop: '12px' }}>
          {rows.length === 0 ? (
            <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>No records in dataset.</div>
          ) : (
            <table className="admin-table">
              <thead>
                <tr>
                  {columns.map((k) => (
                    <th key={k}>{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 50).map((r, i) => (
                  <tr key={i}>
                    {Object.values(r).map((v, j) => (
                      <td key={j} style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {String(v ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
          <button className="btn btn-outline" onClick={handleDownload}>
            📥 Download JSON
          </button>
        </div>
      </div>
    </div>
  );
}
