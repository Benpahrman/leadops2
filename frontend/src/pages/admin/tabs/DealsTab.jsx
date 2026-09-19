import React from 'react';

export default function DealsTab({
  searchQuery,
  setSearchQuery,
  dealsPage,
  setDealsPage,
  dealsPageSize = 15,
  setDealsPageSize,
  stateFilter,
  setStateFilter,
  paymentFilter,
  setPaymentFilter,
  scoreFilter,
  setScoreFilter,
  pipeline = [],
  filteredLeads = [],
  loading = false,
  batchApproving = false,
  handleBatchApprove,
  scoutingInProgress = false,
  handleTriggerWebScout,
  loadAdminData,
  setScoreModal,
  handleCopyText,
  renderDiscoveryBadge,
  handleAdvance,
  handleCancelOutreach,
  handleTriggerSwarm,
  handleViewAudit,
  handleDeleteLead,
  actionInProgress = {},
}) {
  return (
    <div>
      {/* Filter Toolbar */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '18px', background: 'var(--card)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
        <input
          type="text"
          placeholder="🔍 Search company, contact, jurisdiction, lead ID..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setDealsPage(1);
          }}
          style={{
            flex: '1 1 240px',
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            color: '#fff',
            fontSize: '13px',
          }}
        />

        <select
          value={stateFilter}
          onChange={(e) => {
            setStateFilter(e.target.value);
            setDealsPage(1);
          }}
          style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            color: '#fff',
            fontSize: '13px',
          }}
        >
          <option value="ALL">All Lifecycle States</option>
          <option value="PROSPECTING">Prospecting</option>
          <option value="REVIEW">Review</option>
          <option value="PITCH_PENDING_APPROVAL">Pitch Pending Approval</option>
          <option value="OUTREACH_SENT">Outreach Sent</option>
          <option value="CONVERSATIONAL_INTAKE">Conversational Intake</option>
          <option value="SOW_GENERATED">SOW Generated</option>
          <option value="DEPOSIT_PAID">Setup Sprint Paid ($99)</option>
          <option value="DEV_BUILDING">Dev Building (Swarm)</option>
          <option value="ESCROW_PREVIEW">Customer QA Preview (QA Passed)</option>
          <option value="FINAL_PAID">Final Paid</option>
          <option value="DELIVERED">Delivered</option>
          <option value="WARRANTY_ACTIVE">Warranty / Retainer Active</option>
        </select>

        <select
          value={paymentFilter}
          onChange={(e) => {
            setPaymentFilter(e.target.value);
            setDealsPage(1);
          }}
          style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            color: '#fff',
            fontSize: '13px',
          }}
        >
          <option value="ALL">All Payments</option>
          <option value="DEPOSIT_PAID">Deposit Paid ($99)</option>
          <option value="FINAL_PAID">Final Paid ($151)</option>
          <option value="SUBSCRIPTION_ACTIVE">Active Retainer</option>
          <option value="UNPAID">Unpaid / Prospect</option>
        </select>

        <select
          value={scoreFilter}
          onChange={(e) => {
            setScoreFilter(e.target.value);
            setDealsPage(1);
          }}
          style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            color: '#fff',
            fontSize: '13px',
          }}
        >
          <option value="ALL">All AI Lead Scores</option>
          <option value="HIGH">🔥 High Opportunity (≥75)</option>
          <option value="QUALIFIED">⚡ Qualified Fit (≥65)</option>
          <option value="NURTURE">🌱 Nurture (&lt;65)</option>
        </select>

        <select
          value={dealsPageSize}
          onChange={(e) => {
            setDealsPageSize(Number(e.target.value));
            setDealsPage(1);
          }}
          style={{
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            color: 'var(--cyan)',
            fontSize: '13px',
          }}
          title="Rows per page"
        >
          <option value={15}>15 per page</option>
          <option value={25}>25 per page</option>
          <option value={50}>50 per page</option>
          <option value={100}>100 per page</option>
        </select>

        {/* Export to CSV Button */}
        <button
          className="btn btn-outline"
          style={{
            fontSize: '13px',
            padding: '10px 14px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            borderColor: 'var(--cyan)',
            color: 'var(--cyan)',
            background: 'rgba(56, 189, 248, 0.08)',
            fontWeight: 700,
          }}
          onClick={() => {
            const listToExport = filteredLeads.length > 0 ? filteredLeads : pipeline;
            const header = [
              'Company Name',
              'Contact Name',
              'Role',
              'Email',
              'Phone',
              'LinkedIn',
              'Website',
              'Jurisdiction',
              'Channel',
              'Docket Number',
              'Target Portal',
              'Opportunity Score',
              'Deliverability Score',
              'Lifecycle State',
              'Deposit Paid',
              'Final Paid',
              'Subscription Active',
              'Tier',
              'Lead ID',
              'Sandbox URL',
              'Created At',
            ];
            const origin = typeof window !== 'undefined' ? window.location.origin : '';
            const rows = listToExport.map((lead) => [
              `"${(lead.company_name || '').replace(/"/g, '""')}"`,
              `"${(lead.contact_name || '').replace(/"/g, '""')}"`,
              `"${(lead.contact_role || '').replace(/"/g, '""')}"`,
              `"${(lead.contact_email || '').replace(/"/g, '""')}"`,
              `"${(lead.contact_phone || '').replace(/"/g, '""')}"`,
              `"${(lead.decision_maker_linkedin || '').replace(/"/g, '""')}"`,
              `"${(lead.website || '').replace(/"/g, '""')}"`,
              `"${(lead.jurisdiction || '').replace(/"/g, '""')}"`,
              `"${(lead.discovery_channel || '').replace(/"/g, '""')}"`,
              `"${(lead.filing_case_number || '').replace(/"/g, '""')}"`,
              `"${(lead.target_portal_name || '').replace(/"/g, '""')}"`,
              lead.automation_opportunity_score || 75,
              lead.deliverability_score || 95,
              `"${(lead.state || '').replace(/"/g, '""')}"`,
              lead.deposit_paid ? 'Yes' : 'No',
              lead.final_paid ? 'Yes' : 'No',
              lead.subscription_active ? 'Yes' : 'No',
              `"${(lead.tier_key || '').replace(/"/g, '""')}"`,
              `"${(lead.lead_id || '').replace(/"/g, '""')}"`,
              `"${origin}/sandbox/${lead.slug || lead.lead_id}"`,
              `"${(lead.created_at || '').replace(/"/g, '""')}"`,
            ]);
            const csvContent = [header.join(','), ...rows.map((r) => r.join(','))].join('\n');
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `deals_export_${new Date().toISOString().slice(0, 10)}.csv`;
            link.click();
            URL.revokeObjectURL(url);
          }}
          title="Download deals as a CSV spreadsheet (opens directly in Excel or Google Sheets)"
        >
          <span>📥</span> Export to CSV
        </button>

        {pipeline.filter((l) => l.state === 'PITCH_PENDING_APPROVAL').length > 0 && (
          <button
            className="btn btn-primary"
            style={{
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              border: 'none',
              fontWeight: 700,
              fontSize: '13px',
              padding: '10px 16px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 10px rgba(16, 185, 129, 0.3)',
              marginLeft: 'auto',
            }}
            onClick={handleBatchApprove}
            disabled={batchApproving}
            title="Approve and send all pending outreach pitches"
          >
            {batchApproving
              ? '⏳ Dispatching Pitches...'
              : `🚀 Approve All Pending (${pipeline.filter((l) => l.state === 'PITCH_PENDING_APPROVAL').length})`}
          </button>
        )}
      </div>

      {/* Deals Table */}
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Organization / Lead ID</th>
              <th>Origin &amp; Source Portal</th>
              <th>Tier / Retainer</th>
              <th>Lifecycle State</th>
              <th>Payment Status</th>
              <th>AI Scores &amp; QA Gate</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredLeads.length === 0 ? (
              <tr>
                <td colSpan="7" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                  {loading ? (
                    'Fetching live pipeline deals from PostgreSQL...'
                  ) : pipeline.length === 0 ? (
                    <div>
                      <div style={{ fontSize: '32px', marginBottom: '8px' }}>⚡</div>
                      <p style={{ color: '#fff', fontWeight: 700, fontSize: '15px', marginBottom: '6px' }}>
                        Pipeline is Ready for Live Leads
                      </p>
                      <p style={{ fontSize: '12px', color: 'var(--text-dim)', maxWidth: '440px', margin: '0 auto 16px', lineHeight: 1.5 }}>
                        The database is clean with 0 records. Trigger an autonomous Scout discovery cycle to prospect live municipal leads now:
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
                        <button
                          className="btn btn-primary"
                          style={{ padding: '8px 18px', fontSize: '12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                          onClick={handleTriggerWebScout}
                          disabled={scoutingInProgress}
                        >
                          <span>{scoutingInProgress ? '⏳ Scouting In Progress...' : '🚀 Trigger Live Prospecting Run'}</span>
                        </button>
                        <button
                          className="btn btn-outline"
                          style={{ padding: '8px 16px', fontSize: '12px' }}
                          onClick={loadAdminData}
                        >
                          🔄 Refresh Telemetry
                        </button>
                      </div>
                    </div>
                  ) : (
                    'No deals match your search criteria.'
                  )}
                </td>
              </tr>
            ) : (
              filteredLeads
                .slice((dealsPage - 1) * dealsPageSize, dealsPage * dealsPageSize)
                .map((lead) => {
                  const slug = lead.slug || lead.lead_id;
                  const qa = lead.qa_score !== null && lead.qa_score !== undefined ? lead.qa_score : null;

                  return (
                    <tr key={lead.lead_id}>
                      <td>
                        <button
                          type="button"
                          onClick={() => setScoreModal({ open: true, lead })}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            padding: 0,
                            margin: 0,
                            cursor: 'pointer',
                            textAlign: 'left',
                            fontWeight: 700,
                            color: '#fff',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '13px',
                          }}
                          title="Click to view detailed lead intelligence, origin, and scoring"
                        >
                          <span style={{ textDecoration: 'underline', textDecorationColor: 'rgba(56, 189, 248, 0.4)' }}>
                            {lead.company_name || 'Organization Lead'}
                          </span>
                          <span style={{ fontSize: '11px', color: 'var(--cyan)' }}>ℹ️</span>
                        </button>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)', marginTop: '2px', display: 'flex', alignItems: 'center' }}>
                          <span>{lead.lead_id}</span>
                          <button
                            type="button"
                            onClick={() => handleCopyText(lead.lead_id, 'Lead ID')}
                            title="Copy Lead ID"
                            style={{
                              background: 'transparent',
                              border: 'none',
                              cursor: 'pointer',
                              color: 'var(--text-dim)',
                              fontSize: '11px',
                              padding: '0 4px',
                              marginLeft: '4px',
                            }}
                          >
                            📋
                          </button>
                        </div>
                        {lead.contact_email && (
                          <div style={{ fontSize: '11px', color: 'var(--cyan)', marginTop: '2px' }}>
                            ✉️ {lead.contact_email}
                          </div>
                        )}
                        {renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}
                      </td>
                      <td>
                        <div style={{ fontSize: '13px', color: 'var(--text)', fontWeight: 600 }}>
                          {lead.target_portal_name || lead.jurisdiction || 'Municipal Registry'}
                        </div>
                        {lead.jurisdiction && lead.target_portal_name && (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px' }}>
                            📍 {lead.jurisdiction}
                          </div>
                        )}
                        <div style={{ display: 'flex', gap: '8px', marginTop: '5px', flexWrap: 'wrap' }}>
                          {lead.source_url && (
                            <a
                              href={lead.source_url}
                              target="_blank"
                              rel="noreferrer"
                              style={{
                                fontSize: '11px',
                                color: 'var(--cyan)',
                                textDecoration: 'none',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                background: 'rgba(56, 189, 248, 0.08)',
                                padding: '2px 6px',
                                borderRadius: '3px',
                                border: '1px solid rgba(56, 189, 248, 0.2)',
                              }}
                              title="Official municipal / county registry source where records were extracted"
                            >
                              🏛️ Portal ↗
                            </a>
                          )}
                          {lead.website && (
                            <a
                              href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                              target="_blank"
                              rel="noreferrer"
                              style={{
                                fontSize: '11px',
                                color: 'var(--purple)',
                                textDecoration: 'none',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '3px',
                                background: 'rgba(168, 85, 247, 0.08)',
                                padding: '2px 6px',
                                borderRadius: '3px',
                                border: '1px solid rgba(168, 85, 247, 0.2)',
                              }}
                              title="Lead company website"
                            >
                              🌐 Website ↗
                            </a>
                          )}
                        </div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--purple)' }}>
                          {lead.tier_name || lead.tier_key || 'Weekly Sync'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                          ${lead.mrr ? lead.mrr.toFixed(0) : '250'}/month
                        </div>
                      </td>
                      <td>
                        <span className={`badge-tag ${
                          lead.state === 'DELIVERED' || lead.state === 'WARRANTY_ACTIVE' || lead.state === 'ESCROW_PREVIEW'
                            ? 'badge-green'
                            : lead.state === 'DEV_BUILDING'
                            ? 'badge-cyan'
                            : lead.state === 'DEPOSIT_PAID'
                            ? 'badge-purple'
                            : lead.state === 'PITCH_PENDING_APPROVAL'
                            ? 'badge-orange'
                            : lead.state === 'OUTREACH_SENT'
                            ? 'badge-blue'
                            : 'badge-yellow'
                        }`}>
                          {lead.state}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {lead.deposit_paid ? (
                            <span style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600 }}>
                              ✓ M1 Deposit ($99 Paid)
                            </span>
                          ) : (
                            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                              ○ M1 Pending ($99)
                            </span>
                          )}

                          {lead.final_paid ? (
                            <span style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600 }}>
                              ✓ M2 Final ($151 Paid)
                            </span>
                          ) : (
                            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                              ○ M2 Pending ($151)
                            </span>
                          )}

                          {lead.subscription_active && (
                            <span style={{ fontSize: '11px', color: 'var(--purple)', fontWeight: 600 }}>
                              ⚡ Active Monthly Retainer
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <button
                            type="button"
                            onClick={() => setScoreModal({ open: true, lead })}
                            style={{
                              background: 'none',
                              border: 'none',
                              padding: 0,
                              cursor: 'pointer',
                              textAlign: 'left',
                            }}
                            title="Click to view 7-factor BDR scoring breakdown & buyer signals"
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span
                                style={{
                                  fontWeight: 800,
                                  fontSize: '12px',
                                  padding: '2px 7px',
                                  borderRadius: '4px',
                                  background: (lead.automation_opportunity_score || 75) >= 75 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                                  color: (lead.automation_opportunity_score || 75) >= 75 ? 'var(--green)' : 'var(--cyan)',
                                  border: `1px solid ${(lead.automation_opportunity_score || 75) >= 75 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`,
                                }}
                              >
                                ⚡ Opp: {lead.automation_opportunity_score || 75}/100
                              </span>
                              <span style={{ fontSize: '10px', color: 'var(--cyan)', textDecoration: 'underline' }}>
                                📊 Intel ↗
                              </span>
                            </div>
                          </button>

                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: '11px', marginTop: '2px' }}>
                            <span style={{ color: 'var(--purple)', fontWeight: 600 }} title="Buyer Intent Probability">
                              🎯 {lead.purchase_probability || 60}% Intent
                            </span>
                            <span style={{ color: 'var(--text-dim)' }}>•</span>
                            <span style={{ color: 'var(--yellow)', fontWeight: 600 }} title="Operational Pain Severity (1-10)">
                              🔥 {lead.pain_severity || 6}/10 Pain
                            </span>
                          </div>

                          {qa !== null ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                              <span
                                style={{
                                  fontWeight: 700,
                                  fontSize: '11px',
                                  color: qa >= 0.95 ? 'var(--green)' : 'var(--yellow)',
                                }}
                              >
                                🛡️ QA: {(qa * 100).toFixed(0)}%
                              </span>
                              <span style={{ fontSize: '9px', color: 'var(--text-dim)' }}>
                                {qa >= 0.95 ? 'PASSED' : 'REVIEW'}
                              </span>
                            </div>
                          ) : (
                            <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                              🛡️ QA: Pending Build
                            </span>
                          )}
                        </div>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                          <button
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '11px', color: 'var(--cyan)', borderColor: 'rgba(56, 189, 248, 0.4)' }}
                            onClick={() => setScoreModal({ open: true, lead })}
                            title="View 7-factor BDR scoring breakdown, buyer signals, and full lead dossier"
                          >
                            ℹ️ Details
                          </button>
                          <a
                            href={`/p/${slug}`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                            title="Open customer sandbox"
                          >
                            🌐 Portal
                          </a>
                          <a
                            href={`/dashboard/${lead.lead_id}`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                            title="Open customer dashboard"
                          >
                            📈 Dashboard
                          </a>
                          <button
                            className="btn btn-primary"
                            style={{
                              padding: '4px 10px',
                              fontSize: '11px',
                              background: lead.state === 'PITCH_PENDING_APPROVAL' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : undefined,
                              borderColor: lead.state === 'PITCH_PENDING_APPROVAL' ? '#10b981' : undefined,
                            }}
                            onClick={() => handleAdvance(lead.lead_id)}
                            disabled={actionInProgress[lead.lead_id]}
                            title={lead.state === 'PITCH_PENDING_APPROVAL' ? 'Approve pitch and dispatch outreach email' : '1-Click Advance lifecycle stage'}
                          >
                            {lead.state === 'PITCH_PENDING_APPROVAL' ? '✓ Approve Pitch' : '⏩ Advance'}
                          </button>
                          {lead.state === 'PITCH_PENDING_APPROVAL' && (
                            <button
                              className="btn btn-outline"
                              style={{ padding: '4px 8px', fontSize: '11px', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                              onClick={() => handleCancelOutreach(lead.lead_id, lead.company_name)}
                              disabled={actionInProgress[lead.lead_id]}
                              title="Cancel auto-dispatch timer and archive pitch"
                            >
                              ✕ Cancel Outreach
                            </button>
                          )}
                          <button
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                            onClick={() => handleTriggerSwarm(lead.lead_id)}
                            disabled={actionInProgress[lead.lead_id]}
                            title="Launch Autonomous Dev Swarm"
                          >
                            🤖 Swarm
                          </button>
                          <button
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '11px' }}
                            onClick={() => handleViewAudit(lead.lead_id, lead.company_name, lead)}
                            title="View immutable event trail"
                          >
                            📜 Audit
                          </button>
                          <button
                            className="btn btn-outline"
                            style={{ padding: '4px 8px', fontSize: '11px', color: '#ff6b6b', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                            onClick={() => handleDeleteLead(lead.lead_id, lead.company_name)}
                            disabled={actionInProgress[lead.lead_id]}
                            title="Permanently delete lead and sandbox"
                          >
                            🗑️ Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
            )}
          </tbody>
        </table>

        {/* Deals Pagination Footer */}
        {filteredLeads.length > 0 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 18px', borderTop: '1px solid var(--border)', fontSize: '12px', color: 'var(--text-dim)', background: 'var(--card)' }}>
            <div>
              Showing {(dealsPage - 1) * dealsPageSize + 1} to {Math.min(dealsPage * dealsPageSize, filteredLeads.length)} of {filteredLeads.length} deals
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                className="btn btn-outline"
                style={{ fontSize: '11px', padding: '4px 10px' }}
                disabled={dealsPage <= 1}
                onClick={() => setDealsPage((p) => Math.max(1, p - 1))}
              >
                ◀ Previous
              </button>
              <span>Page {dealsPage} of {Math.ceil(filteredLeads.length / dealsPageSize) || 1}</span>
              <button
                className="btn btn-outline"
                style={{ fontSize: '11px', padding: '4px 10px' }}
                disabled={dealsPage >= Math.ceil(filteredLeads.length / dealsPageSize)}
                onClick={() => setDealsPage((p) => p + 1)}
              >
                Next ▶
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
