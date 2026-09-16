import React from 'react';

export default function ActivitySubTab({
  warmupActivity,
  loadWarmupActivity,
}) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#fff', margin: 0 }}>
            📜 Real-time Email Dispatch &amp; Warmup Stream
          </h3>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>
            Live feed of peer warmup handshakes and cold outreach dispatches with anti-spam jitter latency.
          </div>
        </div>
        <button className="btn btn-outline" style={{ fontSize: '12px', padding: '6px 12px' }} onClick={loadWarmupActivity}>
          🔄 Refresh Log
        </button>
      </div>

      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Type</th>
              <th>Sender Account</th>
              <th>Recipient</th>
              <th>Status</th>
              <th>Jitter Delay</th>
            </tr>
          </thead>
          <tbody>
            {!warmupActivity?.logs || warmupActivity.logs.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                  No dispatch events recorded in this session.
                </td>
              </tr>
            ) : (
              warmupActivity.logs.map((log, i) => (
                <tr key={log.id || i}>
                  <td>
                    <span style={{ fontSize: '12px', fontFamily: 'var(--mono)', color: 'var(--text-dim)' }}>
                      {log.sent_at || log.timestamp ? new Date(log.sent_at || log.timestamp).toLocaleTimeString() : 'Just now'}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`badge-tag ${
                        log.dispatch_type === 'peer_warmup'
                          ? 'badge-purple'
                          : log.dispatch_type === 'cold_outreach'
                          ? 'badge-cyan'
                          : 'badge-green'
                      }`}
                    >
                      {log.dispatch_type || 'dispatch'}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600, color: '#fff' }}>{log.from_email || log.inbox_id}</span>
                  </td>
                  <td>
                    <span style={{ color: 'var(--cyan)' }}>{log.to_email || log.recipient}</span>
                  </td>
                  <td>
                    <span className={`badge-tag ${log.status === 'SENT' || log.status === 'SUCCESS' ? 'badge-green' : 'badge-yellow'}`}>
                      {log.status || 'SENT'}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--text-dim)' }}>
                      {log.jitter_seconds ? `${log.jitter_seconds}s` : '—'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
