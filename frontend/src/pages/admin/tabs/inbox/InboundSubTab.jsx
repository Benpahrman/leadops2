import React from 'react';

export default function InboundSubTab({
  inboundStream,
  loadInboundStream,
  inboundLoading = false,
}) {
  return (
    <div>
      {/* Watched Inbound Listener Telemetry Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(6, 78, 59, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%)',
          border: '1px solid rgba(16, 185, 129, 0.4)',
          borderRadius: 'var(--radius-md)',
          padding: '20px 24px',
          marginBottom: '24px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.36), 0 0 16px rgba(16, 185, 129, 0.1)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '46px',
                height: '46px',
                borderRadius: '12px',
                background: 'rgba(16, 185, 129, 0.2)',
                border: '1px solid rgba(16, 185, 129, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '24px',
              }}
            >
              📥
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0 }}>
                  Primary Inbound Watched Inbox: {inboundStream?.watched_inbox?.email_address || 'alex@olfmailer.com'}
                </h3>
                <span className="badge-tag badge-green">
                  🟢 {inboundStream?.watched_inbox?.watcher_enabled ? 'POLLING ACTIVE' : 'CONNECTED'}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#a7f3d0', marginTop: '3px' }}>
                Provider: <b>{inboundStream?.watched_inbox?.provider || 'Google Workspace / Gmail (IMAP)'}</b> • Auto-poll: every {inboundStream?.watched_inbox?.poll_interval_seconds || 60}s • Host: {inboundStream?.watched_inbox?.imap_host || 'imap.gmail.com'}:{inboundStream?.watched_inbox?.imap_port || 993}
              </div>
            </div>
          </div>

          <button
            className="btn btn-outline"
            style={{ fontSize: '12px', padding: '8px 16px', borderColor: 'rgba(52, 211, 153, 0.4)', color: '#34d399' }}
            onClick={loadInboundStream}
            disabled={inboundLoading}
          >
            {inboundLoading ? '🔄 Syncing Inbound...' : '🔄 Poll Mailbox Now'}
          </button>
        </div>
      </div>

      {/* Intent Breakdown Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="stat-card stat-purple">
          <div className="stat-label" style={{ color: 'var(--cyan)' }}>Total Inbound Replies</div>
          <div className="stat-value" style={{ color: 'var(--cyan)' }}>
            {inboundStream?.metrics?.total_received || 0}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            Received across all campaigns
          </div>
        </div>

        <div className="stat-card stat-green">
          <div className="stat-label" style={{ color: 'var(--green)' }}>🔥 Interested / Hot Leads</div>
          <div className="stat-value" style={{ color: 'var(--green)' }}>
            {inboundStream?.metrics?.interested_count || 0}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            Ready for sandbox / SOW
          </div>
        </div>

        <div className="stat-card stat-cyan">
          <div className="stat-label" style={{ color: '#38bdf8' }}>❓ Questions / Intake</div>
          <div className="stat-value" style={{ color: '#38bdf8' }}>
            {inboundStream?.metrics?.classified_counts?.question || 0}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            AI Auto-draft generated
          </div>
        </div>

        <div className="stat-card stat-yellow">
          <div className="stat-label" style={{ color: '#fbbf24' }}>🛑 Unsubscribes / Opt-outs</div>
          <div className="stat-value" style={{ color: '#fbbf24' }}>
            {inboundStream?.metrics?.unsubscribe_count || 0}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            Suppressed automatically
          </div>
        </div>
      </div>

      {/* Real-time Inbound Messages Table */}
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#fff', margin: 0 }}>
            💬 Incoming Prospect Messages &amp; AI Classification ({inboundStream?.inbound_emails?.length || 0})
          </h3>
        </div>

        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Sender &amp; Lead</th>
                <th>Subject &amp; Message Snippet</th>
                <th>AI Intent</th>
                <th>Received At</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!inboundStream?.inbound_emails || inboundStream.inbound_emails.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                    No inbound replies received yet. As prospect responses arrive at <b>{inboundStream?.watched_inbox?.email_address || 'alex@olfmailer.com'}</b>, they will appear here live with AI classification.
                  </td>
                </tr>
              ) : (
                inboundStream.inbound_emails.map((msg, idx) => (
                  <tr key={msg.id || idx}>
                    <td>
                      <div style={{ fontWeight: 700, color: '#fff' }}>{msg.from_name || msg.from_address}</div>
                      <div style={{ fontSize: '11px', color: 'var(--cyan)' }}>{msg.from_address}</div>
                      {msg.lead_id && (
                        <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'var(--mono)', marginTop: '2px' }}>
                          Lead: {msg.lead_id}
                        </div>
                      )}
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: '#fff', fontSize: '13px' }}>{msg.subject || '(No Subject)'}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px', maxHeight: '40px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {msg.body_snippet || msg.body_plain || '—'}
                      </div>
                    </td>
                    <td>
                      <span
                        className={`badge-tag ${
                          msg.intent === 'warm_lead' || msg.intent === 'interested'
                            ? 'badge-green'
                            : msg.intent === 'question'
                            ? 'badge-cyan'
                            : msg.intent === 'unsubscribe'
                            ? 'badge-red'
                            : 'badge-yellow'
                        }`}
                      >
                        {msg.intent || 'Unclassified'}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
                        {msg.received_at ? new Date(msg.received_at).toLocaleString() : 'Recent'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {msg.lead_id ? (
                        <a
                          href={`/p/${msg.lead_id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-outline"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                        >
                          🌐 View Sandbox
                        </a>
                      ) : (
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Direct Reply</span>
                      )}
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
