import React from 'react';

export default function FleetInboxesTable({
  inboxes = [],
  handleTestInbox,
  testingInboxId,
  handleDeleteInbox,
}) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#fff', margin: 0 }}>
          📋 All Configured Sending Inboxes ({inboxes.length})
        </h3>
      </div>

      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Sender Identity</th>
              <th>Provider &amp; Transport</th>
              <th>Daily Quota</th>
              <th>Status</th>
              <th>Sent Today</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {inboxes.map((ib) => (
              <tr key={ib.inbox_id}>
                <td>
                  <div style={{ fontWeight: 700, color: '#fff' }}>{ib.email_address}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{ib.from_name || 'Alex | OmniLeadFeeder'}</div>
                </td>
                <td>
                  <span className="badge-tag badge-cyan">
                    {ib.provider === 'olfmailer' ? '🚀 Azure ACS' : ib.provider === 'gmail' ? '🔵 Gmail IMAP' : '🟧 Outlook'}
                  </span>
                </td>
                <td>
                  <span style={{ fontWeight: 700, color: 'var(--cyan)' }}>{ib.daily_limit || 5} / day</span>
                </td>
                <td>
                  <span className={`badge-tag ${ib.is_active ? 'badge-green' : 'badge-yellow'}`}>
                    {ib.is_active ? '● ACTIVE' : '○ PAUSED'}
                  </span>
                </td>
                <td>
                  <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, color: '#fff' }}>
                    {ib.sent_today || 0}
                  </span>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <div style={{ display: 'inline-flex', gap: '6px' }}>
                    <button
                      className="btn btn-outline"
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                      onClick={() => handleTestInbox(ib.inbox_id)}
                      disabled={testingInboxId === ib.inbox_id}
                    >
                      {testingInboxId === ib.inbox_id ? '⏳ Testing...' : '🔌 Test'}
                    </button>
                    <button
                      className="btn btn-outline"
                      style={{ padding: '4px 8px', fontSize: '11px', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                      onClick={() => handleDeleteInbox(ib.inbox_id, ib.email_address)}
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
