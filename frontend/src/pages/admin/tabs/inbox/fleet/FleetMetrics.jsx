import React from 'react';

export default function FleetMetrics({ inboxes = [], warmupCycle }) {
  const activeInboxes = inboxes.filter((i) => i.is_active);
  const olfInboxes = inboxes.filter(
    (i) => i.provider === 'olfmailer' || i.provider === 'custom' || i.email_address?.includes('olfmailer.com')
  );
  const fleetCapacity = activeInboxes.reduce(
    (sum, i) => sum + (i.daily_limit || (warmupCycle?.per_inbox_daily_limit || 5)),
    0
  ) || 15;
  const sentToday = inboxes.reduce((sum, i) => sum + (i.sent_today || 0), 0);
  const sendingQuota = inboxes
    .filter((i) => i.is_active && (i.provider === 'olfmailer' || i.inbox_id !== 'primary'))
    .reduce((sum, i) => sum + (i.daily_limit || (warmupCycle?.per_inbox_daily_limit || 5)), 0) || 15;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
      <div className="stat-card stat-green">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{ color: 'var(--green)' }}>⚡ Active Inboxes</div>
          <span className="pulse-dot-green" title="Active sending accounts" />
        </div>
        <div className="stat-value" style={{ color: 'var(--green)' }}>
          {activeInboxes.length} / {inboxes.length}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
          Participating in rotation
        </div>
      </div>

      <div className="stat-card stat-purple">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{ color: 'var(--cyan)' }}>🚀 olfmailer.com Inboxes</div>
          <span style={{ fontSize: '12px' }}>🔒</span>
        </div>
        <div className="stat-value" style={{ color: 'var(--cyan)' }}>
          {olfInboxes.length || 3}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
          olfmailer.com sending pool
        </div>
      </div>

      <div className="stat-card stat-cyan">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{ color: 'var(--cyan)' }}>📈 Fleet Daily Capacity</div>
          <span className="pulse-dot-cyan" title="Warmup daily limit" />
        </div>
        <div className="stat-value" style={{ color: 'var(--cyan)' }}>
          {fleetCapacity}/day
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
          olfmailer.com inboxes × {warmupCycle?.per_inbox_daily_limit || 5}/day (Stage 1 Warmup)
        </div>
      </div>

      <div className="stat-card stat-yellow">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{ color: '#fbbf24' }}>📨 Dispatched Today</div>
          <span className="pulse-dot-amber" title="Fleet sends today" />
        </div>
        <div className="stat-value" style={{ color: '#fbbf24' }}>
          {sentToday} / {sendingQuota}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
          Across all active inboxes
        </div>
      </div>
    </div>
  );
}
