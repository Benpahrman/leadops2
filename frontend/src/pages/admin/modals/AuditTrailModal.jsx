import React from 'react';

/**
 * Modal displaying immutable lifecycle events and AI orchestration telemetry for a lead.
 */
export default function AuditTrailModal({ modalState, onClose }) {
  if (!modalState || !modalState.open) return null;

  const events = modalState.events || [];

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal-content" style={{ maxWidth: '680px' }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '14px' }}>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0 }}>📜 {modalState.title}</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Immutable lifecycle events &amp; AI orchestration telemetry</span>
          </div>
          <button
            className="btn btn-outline"
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={onClose}
          >
            ✕ Close
          </button>
        </div>

        <div style={{ maxHeight: '460px', overflowY: 'auto', marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {events.length === 0 ? (
            <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <p style={{ margin: 0, fontSize: '14px' }}>No audit events recorded for this lead.</p>
              <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>State transitions and AI agent dispatches will appear here automatically.</p>
            </div>
          ) : (
            events.map((ev, i) => {
              const actionStr = typeof ev.action === 'string' ? ev.action : (typeof ev.event === 'string' ? ev.event : 'Lifecycle Transition');
              const timeRaw = ev.timestamp || ev.created_at || ev.at || '';
              let timeStr = '';
              if (timeRaw) {
                try {
                  timeStr = new Date(timeRaw).toLocaleString();
                } catch {
                  timeStr = String(timeRaw);
                }
              }
              let detailStr = '';
              if (typeof ev.detail === 'string' && ev.detail) {
                detailStr = ev.detail;
              } else if (typeof ev.reason === 'string' && ev.reason) {
                detailStr = ev.reason;
              } else if (ev.detail && typeof ev.detail === 'object') {
                detailStr = JSON.stringify(ev.detail);
              } else if (ev.reason && typeof ev.reason === 'object') {
                detailStr = JSON.stringify(ev.reason);
              } else {
                detailStr = 'Automated lifecycle transition';
              }

              return (
                <div key={i} style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--cyan)', fontWeight: 600 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: 'var(--green)' }}>●</span>
                      {actionStr}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{timeStr}</span>
                  </div>
                  <div style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '12px', lineHeight: 1.4 }}>{detailStr}</div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
