import React from 'react';

export default function SwarmTab({
  pipeline = [],
  renderDiscoveryBadge,
  handleViewSwarmProgress,
  handleOpenQaOverride,
  handleTriggerSwarm,
  actionInProgress = {},
}) {
  return (
    <div>
      {/* 7-Agent Architecture Banner */}
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '24px', marginBottom: '28px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#fff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>🤖</span> Autonomous 7-Agent Synthesis &amp; QA Pipeline
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
          {[
            { step: '1', name: 'Synthesizer', icon: '🏛️', desc: 'Schema Contract' },
            { step: '2', name: 'Scout', icon: '🔍', desc: 'DOM Traversal' },
            { step: '3', name: 'Engineer', icon: '⚙️', desc: 'Python Crawler' },
            { step: '4', name: 'Normalizer', icon: '🔄', desc: 'Dedup & Clean' },
            { step: '5', name: 'Resiliency', icon: '🛡️', desc: 'Proxy Evasion' },
            { step: '6', name: 'QA Gate', icon: '🧪', desc: '≥95% Verified' },
            { step: '7', name: 'Courier', icon: '🚚', desc: 'Feed Delivery' },
          ].map((a) => (
            <div key={a.step} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px', textAlign: 'center' }}>
              <div style={{ fontSize: '20px', marginBottom: '4px' }}>{a.icon}</div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>Agent #{a.step}</div>
              <div style={{ fontSize: '11px', color: 'var(--cyan)' }}>{a.name}</div>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>{a.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Active Builds & QA Table */}
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Target Feed / Lead ID</th>
              <th>Tier / Jurisdiction</th>
              <th>Swarm Build Status</th>
              <th>QA Gatekeeper Score</th>
              <th>Auto-Charge Condition</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pipeline.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                  No dev swarms currently active or logged.
                </td>
              </tr>
            ) : (
              pipeline.map((lead) => {
                const qa = lead.qa_score !== null && lead.qa_score !== undefined ? lead.qa_score : null;
                const isPassing = qa !== null && qa >= 0.95;

                return (
                  <tr key={lead.lead_id}>
                    <td>
                      <div style={{ fontWeight: 700, color: '#fff' }}>{lead.company_name || 'Feed Target'}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{lead.lead_id}</div>
                      {renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}
                    </td>
                    <td>
                      <div>{lead.tier_name || lead.tier_key || 'Weekly'}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{lead.jurisdiction || 'Portal'}</div>
                    </td>
                    <td>
                      <span className={`badge-tag ${
                        lead.state === 'DEV_BUILDING' ? 'badge-cyan' : isPassing ? 'badge-green' : 'badge-yellow'
                      }`}>
                        {lead.state === 'DEV_BUILDING' ? '⚡ Active Swarm Synthesizing' : lead.state}
                      </span>
                    </td>
                    <td>
                      {qa !== null ? (
                        <div>
                          <span style={{ fontSize: '15px', fontWeight: 800, color: isPassing ? 'var(--green)' : 'var(--yellow)' }}>
                            {(qa * 100).toFixed(0)}%
                          </span>
                          <div style={{ fontSize: '10px', color: isPassing ? 'var(--green)' : 'var(--yellow)' }}>
                            {isPassing ? '✓ Passed Schema Floor (≥95%)' : '⚠️ Below 95% Floor'}
                          </div>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>Awaiting Swarm Run</span>
                      )}
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', color: lead.final_paid ? 'var(--green)' : 'var(--text-muted)' }}>
                        {lead.final_paid ? '✓ Milestone #2 Balance Paid ($151)' : 'Milestone #2 balance ($151 due upon ≥95% QA)'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        <button
                          className="btn btn-outline"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                          onClick={() => handleViewSwarmProgress(lead.lead_id, lead.company_name)}
                        >
                          📊 Progress Logs
                        </button>
                        <button
                          className="btn btn-outline"
                          style={{ padding: '4px 8px', fontSize: '11px', color: 'var(--yellow)', borderColor: 'rgba(245, 158, 11, 0.4)' }}
                          onClick={() => handleOpenQaOverride(lead.lead_id, lead.company_name)}
                        >
                          ⚖️ Override QA
                        </button>
                        <button
                          className="btn btn-primary"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                          onClick={() => handleTriggerSwarm(lead.lead_id)}
                          disabled={actionInProgress[lead.lead_id]}
                        >
                          🚀 Launch
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
