import React from 'react';

export default function ArchivedLeadsTab({
  archivedLeads = [],
  loadArchivedLeads,
  handleBatchEnrichArchived,
  batchEnriching = false,
  enrichingLeadId,
  handleEnrichLead,
  handleDeleteLead,
}) {
  return (
    <div>
      {/* Header & Batch Controls */}
      <div
        style={{
          background: 'var(--card)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          borderRadius: 'var(--radius-md)',
          padding: '20px 24px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
            <span>📦</span> Archived &amp; Recovery Vault
            <span
              style={{
                fontSize: '11px',
                background: 'rgba(245, 158, 11, 0.2)',
                color: '#fde68a',
                padding: '2px 8px',
                borderRadius: '12px',
                border: '1px solid rgba(245, 158, 11, 0.4)',
              }}
            >
              {archivedLeads.length} Isolated Leads
            </span>
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-dim)', margin: '6px 0 0 0', maxWidth: '720px' }}>
            Leads isolated from active Kanban and Deals Funnel due to 45-day duplicate contact suppression,
            bad/undeliverable emails, or delivery bounces. The autonomous <strong>Contact Enricher Researcher Agent</strong>{' '}
            can research corporate filings, team directories, and executive email permutations to recover verified decision-makers.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            className="btn btn-outline"
            onClick={loadArchivedLeads}
            style={{ fontSize: '11px', padding: '7px 12px' }}
          >
            🔄 Refresh
          </button>
          <button
            className="btn btn-primary"
            style={{
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              border: 'none',
              fontSize: '11px',
              fontWeight: 700,
              padding: '8px 16px',
              boxShadow: '0 2px 10px rgba(245, 158, 11, 0.35)',
              color: '#fff',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onClick={handleBatchEnrichArchived}
            disabled={batchEnriching || archivedLeads.length === 0}
            title="Run autonomous Contact Enricher Agent across all archived leads"
          >
            <span>{batchEnriching ? '⏳ Researching All Leads...' : `⚡ Run AI Contact Enricher on All (${archivedLeads.length})`}</span>
          </button>
        </div>
      </div>

      {/* Archived Cards List */}
      {archivedLeads.length === 0 ? (
        <div
          style={{
            background: 'var(--card)',
            border: '1px dashed rgba(255, 255, 255, 0.15)',
            borderRadius: 'var(--radius-md)',
            padding: '60px 24px',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '36px', marginBottom: '12px' }}>✨</div>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
            Zero Archived Leads
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-dim)', maxWidth: '480px', margin: '0 auto' }}>
            All leads currently have deliverable email addresses and active outreach viability.
            Any leads that trigger 45-day cooldowns or deliverability failures will be automatically quarantined here.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
          {archivedLeads.map((lead) => {
            const reason = lead.archive_reason || 'Archived';
            const is45Days = reason.includes('45');
            const isBadEmail = reason.toLowerCase().includes('email') || reason.toLowerCase().includes('deliverability') || reason.toLowerCase().includes('bounce');
            const isEnriching = enrichingLeadId === lead.lead_id;

            return (
              <div
                key={lead.lead_id}
                className="card"
                style={{
                  background: 'rgba(15, 23, 42, 0.65)',
                  border: '1px solid rgba(245, 158, 11, 0.25)',
                  borderRadius: 'var(--radius-md)',
                  padding: '18px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '14px',
                  position: 'relative',
                }}
              >
                <div>
                  {/* Status Badges */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                    <div style={{ fontWeight: 800, fontSize: '15px', color: '#fff' }}>
                      {lead.company_name || 'Prospect Firm'}
                    </div>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '3px 8px',
                        borderRadius: '4px',
                        background: is45Days
                          ? 'rgba(239, 68, 68, 0.18)'
                          : isBadEmail
                          ? 'rgba(245, 158, 11, 0.18)'
                          : 'rgba(148, 163, 184, 0.18)',
                        color: is45Days ? '#f87171' : isBadEmail ? '#fbbf24' : '#cbd5e1',
                        border: `1px solid ${is45Days ? 'rgba(239, 68, 68, 0.35)' : isBadEmail ? 'rgba(245, 158, 11, 0.35)' : 'rgba(148, 163, 184, 0.3)'}`,
                      }}
                    >
                      {is45Days ? '🛑 45-Day Suppression' : isBadEmail ? '⚠️ Bad / Bounced Email' : '📦 Archived'}
                    </span>
                  </div>

                  {/* Contact Info with Strikethrough/Warning */}
                  <div
                    style={{
                      background: 'rgba(0, 0, 0, 0.25)',
                      padding: '10px 12px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      fontSize: '12px',
                      marginBottom: '10px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      <span>Decision Maker:</span>
                      <span style={{ fontWeight: 600, color: '#fff' }}>
                        {lead.contact_name || 'Unknown Officer'} {lead.contact_role ? `(${lead.contact_role})` : ''}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                      <span>Failed / Quarantined Email:</span>
                      <span style={{ color: '#f87171', fontFamily: 'var(--mono)', textDecoration: isBadEmail ? 'line-through' : 'none' }}>
                        {lead.contact_email || 'No email recorded'}
                      </span>
                    </div>
                    {lead.website && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', marginTop: '4px' }}>
                        <span>Domain / Website:</span>
                        <a
                          href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--cyan)', textDecoration: 'none' }}
                        >
                          {lead.website.replace(/^https?:\/\//, '').replace(/\/$/, '')} ↗
                        </a>
                      </div>
                    )}
                  </div>

                  {/* Reason Box */}
                  <div
                    style={{
                      fontSize: '11px',
                      color: '#fbbf24',
                      background: 'rgba(245, 158, 11, 0.08)',
                      padding: '8px 10px',
                      borderRadius: '5px',
                      border: '1px solid rgba(245, 158, 11, 0.2)',
                      lineHeight: 1.4,
                    }}
                  >
                    <strong>Reason:</strong> {reason}
                  </div>

                  {/* Previous Enrichment Attempt Notice */}
                  {lead.recovery_history && (
                    <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '6px', fontStyle: 'italic' }}>
                      Last Agent Run: {lead.recovery_history.attempted_at ? new Date(lead.recovery_history.attempted_at).toLocaleTimeString() : 'Recent'} ({lead.recovery_history.status || 'Executed'})
                    </div>
                  )}
                </div>

                {/* Action Bar */}
                <div style={{ display: 'flex', gap: '8px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <button
                    className="btn btn-primary"
                    style={{
                      flex: 1,
                      background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                      border: 'none',
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '7px 10px',
                      color: '#fff',
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '5px',
                    }}
                    onClick={() => handleEnrichLead(lead.lead_id, lead.company_name)}
                    disabled={isEnriching}
                    title="Trigger Contact Enricher Agent to research and verify substitute contacts"
                  >
                    <span>{isEnriching ? '⏳ Researching Web & MX...' : '🤖 AI Contact Enricher'}</span>
                  </button>
                  <button
                    className="btn btn-outline"
                    style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: '#f87171', fontSize: '11px', padding: '7px 10px' }}
                    onClick={() => handleDeleteLead(lead.lead_id, lead.company_name)}
                    title="Permanently remove lead from database"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
