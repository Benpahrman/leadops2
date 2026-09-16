import React from 'react';

export default function KanbanTab({
  pipeline = [],
  handleBatchApprove,
  batchApproving = false,
  setScoreModal,
  renderDiscoveryBadge,
  handleAdvance,
  actionInProgress = {},
  handleViewAudit,
}) {
  const columns = [
    { key: 'PROSPECTING', label: '1. Prospecting', color: 'var(--cyan)', borderTop: '3px solid var(--cyan)', badgeClass: 'badge-cyan' },
    { key: 'REVIEW', label: '2. Enriched / Review', color: '#fbbf24', borderTop: '3px solid #fbbf24', badgeClass: 'badge-yellow' },
    { key: 'PITCH_PENDING_APPROVAL', label: '3. Pitch Pending', color: '#fb923c', borderTop: '3px solid #fb923c', badgeClass: 'badge-orange' },
    { key: 'OUTREACH_SENT', label: '4. Outreach Sent', color: '#60a5fa', borderTop: '3px solid #60a5fa', badgeClass: 'badge-blue' },
    { key: 'DEPOSIT_PAID', label: '5. Setup Sprint ($99)', color: '#c084fc', borderTop: '3px solid #c084fc', badgeClass: 'badge-purple' },
    { key: 'DEV_BUILDING', label: '6. Dev Swarm', color: 'var(--cyan)', borderTop: '3px solid var(--cyan)', badgeClass: 'badge-cyan' },
    { key: 'ESCROW_PREVIEW', label: '7. QA Pass (≥95%)', color: 'var(--green)', borderTop: '3px solid var(--green)', badgeClass: 'badge-green' },
    { key: 'DELIVERED', label: '8. Delivered', color: 'var(--green)', borderTop: '3px solid var(--green)', badgeClass: 'badge-green' },
  ];

  return (
    <div className="kanban-board">
      {columns.map((col) => {
        const colLeads = pipeline.filter((l) => l.state === col.key);

        return (
          <div key={col.key} className="kanban-column" style={{ borderTop: col.borderTop }}>
            <div className="kanban-col-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: col.color, fontWeight: 700 }}>{col.label}</span>
                <span className={`badge-tag ${col.badgeClass}`}>{colLeads.length}</span>
              </div>
              {col.key === 'PITCH_PENDING_APPROVAL' && colLeads.length > 0 && (
                <button
                  className="btn btn-primary"
                  style={{
                    padding: '2px 8px',
                    fontSize: '10px',
                    fontWeight: 700,
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    border: 'none',
                    boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)',
                  }}
                  onClick={handleBatchApprove}
                  disabled={batchApproving}
                  title="Approve and send all pending outreach pitches"
                >
                  {batchApproving ? '⏳ Sending...' : `✓ Approve All (${colLeads.length})`}
                </button>
              )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto' }}>
              {colLeads.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '24px 0', fontSize: '12px', color: 'var(--text-dim)' }}>
                  Empty stage
                </div>
              ) : (
                colLeads.map((lead) => (
                  <div key={lead.lead_id} className="kanban-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div
                        style={{
                          fontWeight: 700,
                          fontSize: '13px',
                          color: '#fff',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                        onClick={() => setScoreModal({ open: true, lead })}
                        title="Click to view full lead intelligence, origin, and scoring"
                      >
                        <span style={{ textDecoration: 'underline', textDecorationColor: 'rgba(56, 189, 248, 0.4)' }}>
                          {lead.company_name || 'Lead'}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--cyan)' }}>ℹ️</span>
                      </div>
                      <span style={{ fontSize: '10px', color: 'var(--purple)', fontWeight: 600 }}>
                        {lead.tier_key || 'weekly'}
                      </span>
                    </div>

                    {renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}

                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span style={{ maxWidth: '170px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={lead.target_portal_name || lead.jurisdiction}>
                        📍 {lead.target_portal_name || lead.jurisdiction || 'Public Records'}
                      </span>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {lead.source_url && (
                          <a
                            href={lead.source_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: 'var(--cyan)', textDecoration: 'none', fontSize: '11px' }}
                            title="Open municipal data portal"
                            onClick={(e) => e.stopPropagation()}
                          >
                            🏛️ ↗
                          </a>
                        )}
                        {lead.website && (
                          <a
                            href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                            target="_blank"
                            rel="noreferrer"
                            style={{ color: 'var(--purple)', textDecoration: 'none', fontSize: '11px' }}
                            title="Visit company website"
                            onClick={(e) => e.stopPropagation()}
                          >
                            🌐 ↗
                          </a>
                        )}
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', fontSize: '11px' }}>
                      <span style={{ color: lead.deposit_paid ? 'var(--green)' : 'var(--text-dim)' }}>
                        {lead.deposit_paid ? '✓ $99 Sprint Credited' : '○ $99 Sprint Pending'}
                      </span>
                      {lead.qa_score !== null && lead.qa_score !== undefined && (
                        <span style={{ color: lead.qa_score >= 0.95 ? 'var(--green)' : 'var(--yellow)', fontWeight: 700 }}>
                          QA: {(lead.qa_score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>

                    {/* AI Opportunity & Buyer Signals Badges */}
                    <div
                      style={{ display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap', marginTop: '7px', cursor: 'pointer' }}
                      onClick={() => setScoreModal({ open: true, lead })}
                      title="Click to view full BDR 7-factor scoring & buyer signals"
                    >
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: (lead.automation_opportunity_score || 75) >= 75 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                          color: (lead.automation_opportunity_score || 75) >= 75 ? 'var(--green)' : 'var(--cyan)',
                          border: `1px solid ${(lead.automation_opportunity_score || 75) >= 75 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`,
                        }}
                      >
                        ⚡ Opp: {lead.automation_opportunity_score || 75}/100
                      </span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 600,
                          padding: '2px 5px',
                          borderRadius: '4px',
                          background: 'rgba(168, 85, 247, 0.15)',
                          color: 'var(--purple)',
                          border: '1px solid rgba(168, 85, 247, 0.3)',
                        }}
                        title="Buyer Purchase Intent"
                      >
                        🎯 {lead.purchase_probability || 60}%
                      </span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 600,
                          padding: '2px 5px',
                          borderRadius: '4px',
                          background: 'rgba(245, 158, 11, 0.15)',
                          color: 'var(--yellow)',
                          border: '1px solid rgba(245, 158, 11, 0.3)',
                        }}
                        title="Operational Pain Severity (1-10)"
                      >
                        🔥 {lead.pain_severity || 6}/10
                      </span>
                    </div>

                    <div style={{ display: 'flex', gap: '5px', marginTop: '8px', flexWrap: 'wrap' }}>
                      <button
                        className="btn btn-primary"
                        style={{
                          padding: '4px 8px',
                          fontSize: '11px',
                          flex: 1,
                          minWidth: '80px',
                          background: lead.state === 'PITCH_PENDING_APPROVAL' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : undefined,
                          borderColor: lead.state === 'PITCH_PENDING_APPROVAL' ? '#10b981' : undefined,
                        }}
                        onClick={() => handleAdvance(lead.lead_id)}
                        disabled={actionInProgress[lead.lead_id]}
                      >
                        {lead.state === 'PITCH_PENDING_APPROVAL' ? '✓ Approve' : '⏩ Advance'}
                      </button>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '4px 7px', fontSize: '11px', color: 'var(--cyan)', borderColor: 'rgba(56, 189, 248, 0.3)' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setScoreModal({ open: true, lead });
                        }}
                        title="View full lead intelligence & BDR breakdown"
                      >
                        ℹ️ Info
                      </button>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '4px 7px', fontSize: '11px' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleViewAudit(lead.lead_id, lead.company_name, lead);
                        }}
                        title="View immutable audit trail"
                      >
                        📜 Audit
                      </button>
                      <a
                        href={`/p/${lead.slug || lead.lead_id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-outline"
                        style={{ padding: '4px 8px', fontSize: '11px' }}
                        title="Open customer portal"
                      >
                        🌐
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
