import React from 'react';

export default function ReceiversSubTab({
  warmupTargets = [],
  setShowAddReceiverModal,
  handleDeleteReceiver,
}) {
  return (
    <div>
      {/* Header Callout */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(88, 28, 135, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%)',
          border: '1px solid rgba(168, 85, 247, 0.4)',
          borderRadius: 'var(--radius-md)',
          padding: '20px 24px',
          marginBottom: '24px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.36), 0 0 16px rgba(168, 85, 247, 0.1)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '46px',
                height: '46px',
                borderRadius: '12px',
                background: 'rgba(168, 85, 247, 0.2)',
                border: '1px solid rgba(168, 85, 247, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '24px',
              }}
            >
              🤝
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0 }}>
                  Peer Warmup Receiver Network ({warmupTargets.length} Inboxes)
                </h3>
                <span className="badge-tag badge-purple">
                  {warmupTargets.filter((t) => t.is_monitored).length} Active 2-Way Responders
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#e9d5ff', marginTop: '3px' }}>
                These seed inboxes receive daily warmup dispatches from <code>olfmailer.com</code> senders, autonomously rescue messages from Spam to Inbox, and generate conversational AI replies to build sender domain reputation.
              </div>
            </div>
          </div>

          <button
            className="btn btn-primary"
            style={{ fontSize: '12px', padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)', border: 'none' }}
            onClick={() => setShowAddReceiverModal(true)}
          >
            <span>+</span> Add Warm Receiver
          </button>
        </div>
      </div>

      {/* KPI Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="stat-card stat-purple">
          <div className="stat-label" style={{ color: '#c084fc' }}>Total Peer Receivers</div>
          <div className="stat-value" style={{ color: '#c084fc' }}>{warmupTargets.length}</div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>Registered recipient accounts</div>
        </div>

        <div className="stat-card stat-cyan">
          <div className="stat-label" style={{ color: 'var(--cyan)' }}>2-Way Monitored</div>
          <div className="stat-value" style={{ color: 'var(--cyan)' }}>
            {warmupTargets.filter((t) => t.is_monitored).length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>Un-spam &amp; auto-reply enabled</div>
        </div>

        <div className="stat-card stat-green">
          <div className="stat-label" style={{ color: 'var(--green)' }}>Total Warmup Received</div>
          <div className="stat-value" style={{ color: 'var(--green)' }}>
            {warmupTargets.reduce((sum, t) => sum + (t.total_sent || 0), 0)}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>Exchanges delivered</div>
        </div>

        <div className="stat-card stat-yellow">
          <div className="stat-label" style={{ color: '#fbbf24' }}>Spam Rescues &amp; Replies</div>
          <div className="stat-value" style={{ color: '#fbbf24' }}>
            {warmupTargets.reduce((sum, t) => sum + (t.unspammed_count || 0) + (t.replied_count || 0), 0)}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            {warmupTargets.reduce((sum, t) => sum + (t.unspammed_count || 0), 0)} unspammed + {warmupTargets.reduce((sum, t) => sum + (t.replied_count || 0), 0)} replied
          </div>
        </div>
      </div>

      {/* Warm Receivers Table */}
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '20px 24px' }}>
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Receiver Inbox</th>
                <th>Provider</th>
                <th>2-Way Engine</th>
                <th>Warmup Received</th>
                <th>Spam Rescues</th>
                <th>AI Auto-Replies</th>
                <th>Last Sent</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {warmupTargets.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                    No warm receivers registered yet. Click "+ Add Warm Receiver" to connect seed inboxes.
                  </td>
                </tr>
              ) : (
                warmupTargets.map((target) => (
                  <tr key={target.id || target.email}>
                    <td>
                      <div style={{ fontWeight: 700, color: '#fff' }}>{target.email}</div>
                      {target.name && <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{target.name}</div>}
                    </td>
                    <td>
                      <span className="badge-tag">
                        {target.provider === 'gmail' ? '🔵 Gmail' : target.provider === 'outlook' ? '🟧 Outlook' : target.provider || 'Generic'}
                      </span>
                    </td>
                    <td>
                      <span className={`badge-tag ${target.is_monitored ? 'badge-green' : 'badge-yellow'}`}>
                        {target.is_monitored ? '✓ 2-Way Active' : '○ Recipient Only'}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--cyan)' }}>
                        {target.total_sent || 0}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--green)' }}>
                        {target.unspammed_count || 0}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: 'var(--purple)' }}>
                        {target.replied_count || 0}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
                        {target.last_sent_at ? new Date(target.last_sent_at).toLocaleTimeString() : '—'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '4px 8px', fontSize: '11px', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                        onClick={() => handleDeleteReceiver(target.id, target.email)}
                      >
                        🗑️ Remove
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
