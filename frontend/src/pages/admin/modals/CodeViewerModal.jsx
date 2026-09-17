import React from 'react';

/**
 * Modal to display and copy Python scraper source code.
 */
export default function CodeViewerModal({ modalState, onClose, showToast }) {
  if (!modalState || !modalState.open) return null;

  const handleCopy = () => {
    if (modalState.code) {
      navigator.clipboard.writeText(modalState.code);
      if (showToast) {
        showToast('Python source code copied to clipboard!', 'success');
      }
    }
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>{modalState.title}</h3>
          <button
            className="btn btn-outline"
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={onClose}
          >
            ✕ Close
          </button>
        </div>
        <pre className="code-viewer">{modalState.code}</pre>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button className="btn btn-outline" onClick={handleCopy}>
            📋 Copy Code
          </button>
        </div>
      </div>
    </div>
  );
}
