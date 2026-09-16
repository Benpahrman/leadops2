import React from 'react';

export default function DailyDeliveryTab({
  loadDailyGrid,
  pipeline = [],
  handleTriggerDailyDelivery,
}) {
  const activeFeeds = pipeline.filter(
    (l) => l.state === 'DELIVERED' || l.state === 'WARRANTY_ACTIVE' || l.subscription_active
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Automated 6:00 AM UTC Daily Data Deliveries (Google Sheets, Webhooks, CSV Deliveries)
        </p>
        <button className="btn btn-outline" onClick={loadDailyGrid}>
          🔄 Refresh Grid
        </button>
      </div>

      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Customer Feed</th>
              <th>Schedule</th>
              <th>Destination Type</th>
              <th>Last Status</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {activeFeeds.length === 0 ? (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                  No delivered feeds currently scheduled for daily automation.
                </td>
              </tr>
            ) : (
              activeFeeds.map((lead) => (
                <tr key={lead.lead_id}>
                  <td>
                    <div style={{ fontWeight: 700, color: '#fff' }}>{lead.company_name}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{lead.lead_id}</div>
                  </td>
                  <td>
                    <span style={{ color: 'var(--purple)', fontWeight: 600 }}>Daily 6:00 AM UTC</span>
                  </td>
                  <td>
                    <span className="badge-tag">Google Sheets + Webhook</span>
                  </td>
                  <td>
                    <span style={{ color: 'var(--green)', fontWeight: 600 }}>✓ Healthy</span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-primary"
                      style={{ padding: '6px 12px', fontSize: '12px' }}
                      onClick={() => handleTriggerDailyDelivery(lead.lead_id)}
                    >
                      🚀 Run Delivery Now
                    </button>
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
