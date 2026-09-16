import React from 'react';

export default function AccountingTab({
  pipeline = [],
  depositTotal = 0,
  releasedTotal = 0,
  activeMrr = 0,
}) {
  return (
    <div>
      {/* Accounting Breakdown Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        <div className="stat-card" style={{ borderLeft: '4px solid var(--green)' }}>
          <div className="stat-label">🏦 Total Setup Sprint Deposits ($99)</div>
          <div className="stat-value" style={{ color: 'var(--green)' }}>
            ${depositTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            {pipeline.filter((l) => l.deposit_paid).length} deposits held ($99 each)
          </div>
        </div>

        <div className="stat-card" style={{ borderLeft: '4px solid var(--cyan)' }}>
          <div className="stat-label">💰 Released Milestone #2 Funds</div>
          <div className="stat-value" style={{ color: 'var(--cyan)' }}>
            ${releasedTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            {pipeline.filter((l) => l.final_paid).length} completions unlocked ($151 each)
          </div>
        </div>

        <div className="stat-card" style={{ borderLeft: '4px solid var(--purple)' }}>
          <div className="stat-label">📈 Active Monthly Subscriptions</div>
          <div className="stat-value" style={{ color: 'var(--purple)' }}>
            ${activeMrr.toLocaleString('en-US', { minimumFractionDigits: 2 })}/mo
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            PayPal automated recurring billing
          </div>
        </div>

        <div className="stat-card" style={{ borderLeft: '4px solid var(--yellow)' }}>
          <div className="stat-label">💳 Gross Pipeline Value</div>
          <div className="stat-value" style={{ color: '#fff' }}>
            ${(depositTotal + releasedTotal + activeMrr).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
            Total processed &amp; under contract
          </div>
        </div>
      </div>

      {/* Customer Ledger */}
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Customer Organization</th>
              <th>Plan Tier</th>
              <th>Milestone #1 ($99 Deposit)</th>
              <th>Milestone #2 ($151 Balance)</th>
              <th>Recurring Retainer</th>
              <th>PayPal Provider</th>
              <th style={{ textAlign: 'right' }}>Official Invoice</th>
            </tr>
          </thead>
          <tbody>
            {pipeline.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                  No customer accounting records logged yet.
                </td>
              </tr>
            ) : (
              pipeline.map((lead) => (
                <tr key={lead.lead_id}>
                  <td>
                    <div style={{ fontWeight: 700, color: '#fff' }}>{lead.company_name || 'Client'}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{lead.lead_id}</div>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600, color: 'var(--purple)' }}>{lead.tier_name || lead.tier_key || 'Weekly Sync'}</span>
                  </td>
                  <td>
                    <span style={{ color: lead.deposit_paid ? 'var(--green)' : 'var(--text-dim)', fontWeight: 600 }}>
                      {lead.deposit_paid ? `✓ $${(lead.deposit_amount_usd || 99.0).toFixed(2)} PAID (SPRINT DEPOSIT)` : 'Pending'}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: lead.final_paid ? 'var(--green)' : 'var(--text-dim)', fontWeight: 600 }}>
                      {lead.final_paid ? `✓ $${(lead.next_payment_amount || 151.0).toFixed(2)} RELEASED` : 'Pre-authorized'}
                    </span>
                  </td>
                  <td>
                    <span style={{ color: lead.subscription_active ? 'var(--cyan)' : 'var(--text-dim)', fontWeight: 600 }}>
                      {lead.subscription_active ? '⚡ Active Recurring' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                      {lead.deposit_paid || lead.final_paid ? 'PayPal Live Vault' : '—'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <a
                      href={`/api/dashboard/${lead.lead_id}/invoice`}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-outline"
                      style={{ padding: '6px 12px', fontSize: '12px', borderColor: 'var(--cyan)', color: 'var(--cyan)' }}
                    >
                      📄 Printable PDF Invoice
                    </a>
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
