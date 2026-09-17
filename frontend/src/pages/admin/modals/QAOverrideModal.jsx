import React from 'react';

/**
 * Modal for founder/operator QA gate manual release override.
 */
export default function QAOverrideModal({
  modalState,
  onClose,
  overrideScore,
  setOverrideScore,
  overrideReason,
  setOverrideReason,
  onSubmit,
}) {
  if (!modalState || !modalState.open) return null;

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal-content" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>⚖️ Founder QA Gate Override</h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Manually authorize completion for <b>{modalState.company}</b> ({modalState.leadId}).
        </p>

        <div>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
            Override QA Score (0.0 to 1.0):
          </label>
          <input
            type="number"
            step="0.05"
            min="0.8"
            max="1.0"
            value={overrideScore}
            onChange={(e) => setOverrideScore(parseFloat(e.target.value) || 1.0)}
            style={{
              width: '100%',
              background: 'var(--bg)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              padding: '10px',
              color: '#fff',
            }}
          />
        </div>

        <div style={{ marginTop: '12px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
            Justification / Reason:
          </label>
          <input
            type="text"
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            placeholder="e.g. Verified 10 records manually with founder signoff"
            style={{
              width: '100%',
              background: 'var(--bg)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              padding: '10px',
              color: '#fff',
            }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' }}>
          <button className="btn btn-outline" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={onSubmit}>
            Confirm QA Override
          </button>
        </div>
      </div>
    </div>
  );
}
