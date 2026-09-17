import React from 'react';

/**
 * Modal for real-time swarm build telemetry and logs.
 */
export default function SwarmProgressModal({ modalState, onClose }) {
  if (!modalState || !modalState.open) return null;

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>
            🤖 Swarm Telemetry: {modalState.company}
          </h3>
          <button
            className="btn btn-outline"
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={onClose}
          >
            ✕ Close
          </button>
        </div>
        <pre className="code-viewer" style={{ marginTop: '12px' }}>
          {JSON.stringify(modalState.data || { note: 'No real-time build logs active' }, null, 2)}
        </pre>
      </div>
    </div>
  );
}
