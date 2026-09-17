import React from 'react';

export default function AdminStatsBar({ pipeline, inboxes }) {
  const deliverabilityReport = inboxes?.deliverabilityReport;
  const inboxesList = inboxes?.inboxes || [];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
      <div className="stat-card stat-green">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{ color: 'var(--green)' }}>🏦 Down Payments Held</div>
          <span className="pulse-dot-green" title="Milestone #1 deposits credited to Month 1" />
        </div>
        <div className="stat-value" style={{ color: 'var(--green)' }}>
          ${pipeline.depositTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
          <span>Milestone #1 ($99 deposits)</span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{pipeline.pipeline.filter((l) => l.deposit_paid).length} secured</span>
        </div>
      </div>

      <div className="stat-card stat-cyan">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{ color: 'var(--cyan)' }}>💰 Released Milestone #2</div>
          <span className="pulse-dot-cyan" title="Auto-charged on ≥95% QA pass" />
        </div>
        <div className="stat-value" style={{ color: 'var(--cyan)' }}>
          ${pipeline.releasedTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
          <span>Passed QA Gate (≥95%)</span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{pipeline.pipeline.filter((l) => l.final_paid).length} verified</span>
        </div>
      </div>

      <div className="stat-card stat-purple">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{ color: '#c084fc' }}>📈 Active Retainer MRR</div>
          <span style={{ fontSize: '12px' }}>🟣</span>
        </div>
        <div className="stat-value" style={{ color: 'var(--purple)' }}>
          ${pipeline.activeMrr.toLocaleString('en-US', { minimumFractionDigits: 2 })}/mo
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
          <span>Recurring cashflow</span>
          <span style={{ color: '#fff', fontWeight: 600 }}>{pipeline.pipeline.filter((l) => l.subscription_active).length} retainers</span>
        </div>
      </div>

      <div className="stat-card stat-yellow">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{ color: '#fbbf24' }}>🎯 Active Pipeline Deals</div>
          <span className="pulse-dot-amber" title="Active pipeline load" />
        </div>
        <div className="stat-value" style={{ color: '#fbbf24' }}>
          {pipeline.pipeline.filter((l) => l.state !== 'ARCHIVED').length}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
          <span>{pipeline.activeBuilds.length} dev builds active</span>
          <span style={{ color: 'var(--text-muted)' }}>{pipeline.archivedLeads.length} in vault</span>
        </div>
      </div>

      <div className={`stat-card ${
        deliverabilityReport?.fleet_status === 'HEALTHY'
          ? 'stat-green'
          : deliverabilityReport?.fleet_status === 'WARNING'
          ? 'stat-yellow'
          : deliverabilityReport?.fleet_status === 'CRITICAL'
          ? 'stat-red'
          : 'stat-cyan'
      }`}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="stat-label" style={{
            color: deliverabilityReport?.fleet_status === 'HEALTHY'
              ? 'var(--green)'
              : deliverabilityReport?.fleet_status === 'WARNING'
              ? '#fbbf24'
              : deliverabilityReport?.fleet_status === 'CRITICAL'
              ? '#f87171'
              : 'var(--cyan)'
          }}>
            🛡️ 4-Vector Deliverability Suite
          </div>
          <span className={
            deliverabilityReport?.fleet_status === 'HEALTHY'
              ? 'pulse-dot-green'
              : deliverabilityReport?.fleet_status === 'CRITICAL'
              ? 'pulse-dot-red'
              : 'pulse-dot-amber'
          } />
        </div>
        <div className="stat-value" style={{
          color: deliverabilityReport?.fleet_status === 'HEALTHY'
            ? 'var(--green)'
            : deliverabilityReport?.fleet_status === 'WARNING'
            ? '#fbbf24'
            : deliverabilityReport?.fleet_status === 'CRITICAL'
            ? '#f87171'
            : '#fff',
          fontSize: '20px',
          display: 'flex',
          alignItems: 'baseline',
          gap: '6px',
        }}>
          <span>{deliverabilityReport?.fleet_status || 'ARMED'}</span>
          {deliverabilityReport?.average_score !== undefined && (
            <span style={{ fontSize: '13px', color: 'var(--cyan)', fontWeight: 700 }}>({deliverabilityReport.average_score}%)</span>
          )}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
          <span>{deliverabilityReport?.healthy_count ?? inboxesList.length} healthy inboxes</span>
          <span style={{ color: 'var(--green)', fontWeight: 600 }}>0% Spam Trap</span>
        </div>
      </div>
    </div>
  );
}
