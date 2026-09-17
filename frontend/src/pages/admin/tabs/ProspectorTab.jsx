import React from 'react';

export default function ProspectorTab({
  countyOrchestrator,
  orchestratorLoading,
  handleSetStateFocus,
  handleAdvanceCountyCursor,
  prospectorStatus,
  prospectorLoading,
  handlePauseProspector,
  handleResumeProspector,
  handleStartProspector,
  handleToggleProspector247,
  burstLeadCount,
  setBurstLeadCount,
  selectedProspectorChannel,
  setSelectedProspectorChannel,
  handleTriggerBurst,
  handleBatchRefreshStale,
  sweepingStaleRecords,
  pipeline = [],
  backlogLeads = [],
  candidateScope = 'STAGED',
  setCandidateScope,
  candidateEvaluations = [],
  evaluationsLoading = false,
  loadCandidateEvaluations,
  searchQuery,
  setSearchQuery,
  backlogPage,
  setBacklogPage,
  backlogPageSize = 10,
  freshnessRefreshingLeadId,
  renderDiscoveryBadge,
  handleRefreshFreshness,
  setScoreModal,
  handleAdvance,
  actionInProgress = {},
}) {
  return (
    <div>
      {/* 50-State & County-by-County Swarm Prospecting Card */}
      <div style={{ background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.08) 0%, rgba(59, 130, 246, 0.05) 50%, rgba(139, 92, 246, 0.08) 100%)', border: '1px solid rgba(6, 182, 212, 0.3)', borderRadius: 'var(--radius-md)', padding: '20px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>🗺️</span> 50-State &amp; County-by-County Swarm Prospecting Engine
              </h3>
              <span className="badge-tag badge-cyan">
                {countyOrchestrator?.active_jurisdiction?.is_state_locked
                  ? `🔒 Locked: ${countyOrchestrator.active_jurisdiction.locked_state}`
                  : `🌎 50-State Sweep (National Cycle #${countyOrchestrator?.active_jurisdiction?.cycle_count || 0})`}
              </span>
              <span className="badge-tag badge-purple">
                🏛️ State {((countyOrchestrator?.active_jurisdiction?.state_index ?? 0) + 1)} of {countyOrchestrator?.active_jurisdiction?.total_states || 50} ({countyOrchestrator?.active_jurisdiction?.state_code || 'WA'})
              </span>
              <span className="badge-tag badge-green">
                📍 County {((countyOrchestrator?.active_jurisdiction?.county_index ?? 0) + 1)} of {countyOrchestrator?.active_jurisdiction?.total_counties_in_state || 39}
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-dim)', margin: '6px 0 0' }}>
              Scout sweeps nationwide jurisdiction by jurisdiction across all 50 states and municipal counties. In each county, Scout extracts live court/clerk dockets and locates local commercial prospects (probate attorneys, estate planners, contractors, title agents).
            </p>
          </div>

          {/* Orchestrator Controls */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', background: 'var(--bg)', border: '1px solid rgba(6, 182, 212, 0.4)', borderRadius: 'var(--radius-sm)', padding: '2px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', paddingLeft: '8px', fontWeight: 600 }}>State Focus:</span>
              <select
                value={countyOrchestrator?.active_jurisdiction?.locked_state || ''}
                onChange={(e) => handleSetStateFocus(e.target.value || null)}
                disabled={orchestratorLoading}
                style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '11px', padding: '6px 8px', cursor: 'pointer' }}
              >
                <option value="">🌎 All 50 States (Continuous Sweep)</option>
                <option value="WA">Washington (WA - 39 Counties)</option>
                <option value="TX">Texas (TX - High Density Metros)</option>
                <option value="FL">Florida (FL - Miami/Orlando/Tampa)</option>
                <option value="CA">California (CA - Bay/LA/SD)</option>
                <option value="AZ">Arizona (AZ - Maricopa/Pima)</option>
                <option value="IL">Illinois (IL - Cook/DuPage)</option>
                <option value="GA">Georgia (GA - Fulton/Gwinnett)</option>
                <option value="NC">North Carolina (NC - Wake/Mecklenburg)</option>
                <option value="OH">Ohio (OH - Franklin/Cuyahoga)</option>
                <option value="CO">Colorado (CO - Denver/Arapahoe)</option>
                <option value="NV">Nevada (NV - Clark/Washoe)</option>
                <option value="NY">New York (NY - NYC/Suffolk)</option>
                <option value="PA">Pennsylvania (PA - Allegheny/Philly)</option>
                <option value="TN">Tennessee (TN - Davidson/Shelby)</option>
                <option value="MI">Michigan (MI - Wayne/Oakland)</option>
              </select>
            </div>

            <button
              className="btn btn-primary"
              style={{ fontSize: '11px', padding: '7px 14px', background: 'linear-gradient(90deg, var(--cyan), #3b82f6)', color: '#000', fontWeight: 700 }}
              onClick={handleAdvanceCountyCursor}
              disabled={orchestratorLoading}
              title="Advance to the next county in active state sequence"
            >
              {orchestratorLoading ? '⏳ Advancing...' : '⏭️ Advance Next County'}
            </button>
          </div>
        </div>

        {/* Current Active Jurisdiction Details Strip */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px', background: 'rgba(0, 0, 0, 0.25)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-sm)', padding: '12px 16px' }}>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.05em' }}>ACTIVE COUNTY</div>
            <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--cyan)', marginTop: '2px' }}>
              {countyOrchestrator?.active_jurisdiction?.county_name || 'King County'}, {countyOrchestrator?.active_jurisdiction?.state_code || 'WA'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.05em' }}>PRIMARY METRO</div>
            <div style={{ fontSize: '14px', fontWeight: 800, color: '#fff', marginTop: '2px' }}>
              {countyOrchestrator?.active_jurisdiction?.primary_city || 'Seattle'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.05em' }}>COUNTY CLERK / DOCKET PORTAL</div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#93c5fd', marginTop: '3px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {countyOrchestrator?.active_jurisdiction?.portal_url ? (
                <a href={countyOrchestrator.active_jurisdiction.portal_url} target="_blank" rel="noopener noreferrer" style={{ color: '#93c5fd', textDecoration: 'underline' }}>
                  🔗 {countyOrchestrator.active_jurisdiction.portal_name || 'County Public Portal'}
                </a>
              ) : (
                <span>🏛️ {countyOrchestrator?.active_jurisdiction?.portal_name || 'Municipal Registry'}</span>
              )}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.05em' }}>COUNTY SWEEP POSITION</div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#a78bfa', marginTop: '2px' }}>
              County {((countyOrchestrator?.active_jurisdiction?.county_index ?? 0) + 1)} / {countyOrchestrator?.active_jurisdiction?.total_counties_in_state || 39} ({Math.round((((countyOrchestrator?.active_jurisdiction?.county_index ?? 0) + 1) / (countyOrchestrator?.active_jurisdiction?.total_counties_in_state || 1)) * 100)}%)
            </div>
          </div>
        </div>
      </div>

      {/* 14-Day Campaign Controller Card */}
      <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '22px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '18px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>🚀</span> 14-Day Autonomous High-Volume Prospector &amp; Backlog Builder
              </h3>
              <span className={`badge-tag ${prospectorStatus?.is_active ? (prospectorStatus?.run_24_7 || prospectorStatus?.is_office_hours ? 'badge-green' : 'badge-yellow') : 'badge-gray'}`}>
                {prospectorStatus?.is_active
                  ? (prospectorStatus?.run_24_7
                      ? '⚡ Active (24/7 All-Day Prospecting)'
                      : (prospectorStatus?.is_office_hours ? '🟢 Active (8:00 AM – 5:00 PM CST)' : '🌙 Off-Hours Standby (Resumes 8 AM)'))
                  : '⏸️ Campaign Paused'}
              </span>
              <span className="badge-tag badge-cyan">
                📅 Day {prospectorStatus?.current_day || 1} of {prospectorStatus?.campaign_duration_days || 14} ({prospectorStatus?.days_remaining ?? 13} Days Left)
              </span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-dim)', margin: '6px 0 0' }}>
              Runs high-throughput multi-channel prospecting round-the-clock or in CST office hours. Strict deduplication blocks duplicates; candidates immediately undergo MX/SPF/DKIM deliverability checks, website due diligence, WAF probe, and bespoke sandbox provisioning.
            </p>
          </div>

          {/* Main Campaign Action Controls */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              className="btn btn-outline"
              style={{
                borderColor: prospectorStatus?.run_24_7 ? 'var(--green)' : 'rgba(148, 163, 184, 0.4)',
                color: prospectorStatus?.run_24_7 ? 'var(--green)' : '#94a3b8',
                fontSize: '12px',
                padding: '8px 14px',
                background: prospectorStatus?.run_24_7 ? 'rgba(16, 185, 129, 0.12)' : 'transparent',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
              onClick={handleToggleProspector247}
              disabled={prospectorLoading}
              title={prospectorStatus?.run_24_7 ? "24/7 All-Day Prospecting active. Click to restrict to CST Office Hours only." : "Office Hours Mode active. Click to enable 24/7 All-Day Prospecting."}
            >
              <span>{prospectorStatus?.run_24_7 ? '⚡ 24/7 All-Day Active' : '🌙 Office Hours Only'}</span>
            </button>

            {prospectorStatus?.is_active ? (
              <button
                className="btn btn-outline"
                style={{ borderColor: 'rgba(245, 158, 11, 0.4)', color: '#fbbf24', fontSize: '12px', padding: '8px 14px' }}
                onClick={handlePauseProspector}
                disabled={prospectorLoading}
              >
                ⏸️ Pause Campaign
              </button>
            ) : (
              <button
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '8px 16px', background: 'var(--cyan)', color: '#000', fontWeight: 700 }}
                onClick={() => handleStartProspector(14, 3)}
                disabled={prospectorLoading}
              >
                ▶️ Start 14-Day Campaign
              </button>
            )}

            <div style={{ display: 'inline-flex', alignItems: 'center', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '2px' }}>
              <select
                value={burstLeadCount}
                onChange={(e) => setBurstLeadCount(Number(e.target.value))}
                style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '11px', padding: '6px 8px' }}
              >
                <option value={3}>3 Leads Burst</option>
                <option value={5}>5 Leads Burst</option>
                <option value={10}>10 Leads Burst</option>
              </select>
              <button
                className="btn btn-outline"
                style={{ fontSize: '11px', padding: '6px 12px', borderColor: 'transparent', color: 'var(--cyan)' }}
                onClick={() => handleTriggerBurst(burstLeadCount, selectedProspectorChannel)}
                disabled={prospectorLoading}
              >
                {prospectorLoading ? '⏳ Hunting...' : '⚡ Run Burst Now'}
              </button>
            </div>

            <button
              className="btn btn-outline"
              style={{ fontSize: '11px', padding: '8px 14px', borderColor: 'rgba(168, 85, 247, 0.4)', color: '#c084fc' }}
              onClick={handleBatchRefreshStale}
              disabled={sweepingStaleRecords}
              title="Pre-outreach gatekeeper: Sweep all backlog leads and pull same-day filings before email dispatch"
            >
              {sweepingStaleRecords ? '⏳ Sweeping...' : '🔄 Sweep & Refresh All Stale'}
            </button>
          </div>
        </div>

        {/* Progress Bar for 14 Days */}
        <div style={{ marginTop: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-dim)', marginBottom: '4px' }}>
            <span>Campaign Window Progress</span>
            <span>{Math.round(((prospectorStatus?.current_day || 1) / (prospectorStatus?.campaign_duration_days || 14)) * 100)}% Complete</span>
          </div>
          <div style={{ height: '6px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
            <div
              style={{
                height: '100%',
                width: `${Math.min(100, Math.max(5, Math.round(((prospectorStatus?.current_day || 1) / (prospectorStatus?.campaign_duration_days || 14)) * 100)))}%`,
                background: 'linear-gradient(90deg, var(--cyan) 0%, var(--purple) 100%)',
                borderRadius: '3px',
                transition: 'width 0.4s ease',
              }}
            />
          </div>
        </div>
      </div>

      {/* Deduplication & Audit Telemetry 4-Card Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '20px' }}>
        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px 18px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700 }}>CANDIDATES EVALUATED</div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#fff', marginTop: '2px' }}>
            {prospectorStatus?.metrics?.total_evaluated ?? pipeline.length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--cyan)', marginTop: '2px' }}>
            Across 5 public-record channels
          </div>
        </div>

        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px 18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '11px', color: '#fbbf24', fontWeight: 700 }}>DUPLICATES BLOCKED</div>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Zero-Dup Shield</span>
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#fbbf24', marginTop: '2px' }}>
            {prospectorStatus?.metrics?.duplicates_blocked ?? 0}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Co: {prospectorStatus?.metrics?.duplicates_by_reason?.DUPLICATE_COMPANY ?? 0} • Dom: {prospectorStatus?.metrics?.duplicates_by_reason?.DUPLICATE_DOMAIN ?? 0} • Mail: {prospectorStatus?.metrics?.duplicates_by_reason?.DUPLICATE_EMAIL ?? 0}
          </div>
        </div>

        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px 18px' }}>
          <div style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 700 }}>DELIVERABILITY AUDIT PASS</div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--green)', marginTop: '2px' }}>
            {prospectorStatus?.metrics?.deliverability_passed ?? pipeline.filter((l) => l.deliverability_score >= 60).length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
            MX + SPF + DKIM + DMARC + SMTP Safe
          </div>
        </div>

        <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px 18px' }}>
          <div style={{ fontSize: '11px', color: '#c084fc', fontWeight: 700 }}>VETTED BACKLOG STAGED</div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#c084fc', marginTop: '2px' }}>
            {backlogLeads.length}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
            Ready for cold outreach launch
          </div>
        </div>
      </div>

      {/* Backlog Table Toolbar & Scope Switcher */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '14px', background: 'var(--card)', padding: '14px 16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
        {/* Row 1: Scope Switcher Tabs */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', borderBottom: '1px solid rgba(255, 255, 255, 0.06)', paddingBottom: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700, marginRight: '4px' }}>VIEW SCOPE:</span>
          {[
            { key: 'STAGED', label: '🎯 Staged Backlog', count: pipeline.filter(l => l.outreach_status === 'BACKLOG_VETTED' || ['REVIEW', 'PITCH_PENDING_APPROVAL', 'PROSPECTING'].includes(l.state)).length },
            { key: 'ALL', label: '📋 All Active Leads', count: pipeline.filter(l => l.state !== 'ARCHIVED').length },
            { key: 'OUTREACH_SENT', label: '📬 Outreach Sent', count: pipeline.filter(l => l.state === 'OUTREACH_SENT').length },
            { key: 'EVALUATED', label: '🔍 Evaluated Candidates Audit Log', count: prospectorStatus?.metrics?.total_evaluated ?? (candidateEvaluations.length || pipeline.length) },
          ].map((scope) => {
            const isActive = (candidateScope || 'STAGED') === scope.key;
            return (
              <button
                key={scope.key}
                className={`btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
                style={{
                  fontSize: '11px',
                  padding: '5px 12px',
                  borderRadius: '6px',
                  fontWeight: isActive ? 700 : 500,
                  background: isActive ? 'var(--cyan)' : 'transparent',
                  color: isActive ? '#000' : 'var(--text)',
                }}
                onClick={() => {
                  if (setCandidateScope) setCandidateScope(scope.key);
                  setBacklogPage(1);
                  if (scope.key === 'EVALUATED' && loadCandidateEvaluations) {
                    loadCandidateEvaluations();
                  }
                }}
              >
                {scope.label} <span style={{ opacity: 0.8, fontSize: '10px', marginLeft: '4px' }}>({scope.count})</span>
              </button>
            );
          })}
        </div>

        {/* Row 2: Search & Channel Filter */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder={candidateScope === 'EVALUATED' ? "🔍 Search evaluated candidates by company, email, or jurisdiction..." : "🔍 Search backlog by company, contact, or jurisdiction..."}
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setBacklogPage(1); }}
            style={{ flex: '1 1 240px', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', color: '#fff', fontSize: '12px' }}
          />
          <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700 }}>CHANNEL:</span>
            {['ALL', 'COUNTY_FILING_PARTY', 'STATE_BAR', 'SOS_ENTITY', 'LOCAL_BUSINESS'].map((c) => (
              <button
                key={c}
                className={`btn ${selectedProspectorChannel === c ? 'btn-primary' : 'btn-outline'}`}
                style={{ fontSize: '10px', padding: '4px 8px', borderRadius: '4px' }}
                onClick={() => { setSelectedProspectorChannel(c); setBacklogPage(1); }}
              >
                {c.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Backlog / Evaluated Table with Pagination */}
      <div className="table-responsive" style={{ background: 'var(--card)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
        {candidateScope === 'EVALUATED' ? (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Candidate Company</th>
                <th>Channel</th>
                <th>Verdict / Status</th>
                <th>Disqualification / Pass Reason</th>
                <th>Jurisdiction</th>
                <th>Evaluated Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {evaluationsLoading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--cyan)' }}>
                    ⏳ Loading candidate evaluation audit trail...
                  </td>
                </tr>
              ) : candidateEvaluations.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No candidate evaluations recorded yet. Run a scout burst or 24/7 autonomous loop to record evaluations.
                  </td>
                </tr>
              ) : (
                candidateEvaluations
                  .filter(ev => {
                    const q = (searchQuery || '').toLowerCase().trim();
                    if (!q) return true;
                    return (
                      (ev.company_name && ev.company_name.toLowerCase().includes(q)) ||
                      (ev.contact_email && ev.contact_email.toLowerCase().includes(q)) ||
                      (ev.jurisdiction && ev.jurisdiction.toLowerCase().includes(q)) ||
                      (ev.reason && ev.reason.toLowerCase().includes(q))
                    );
                  })
                  .slice((backlogPage - 1) * backlogPageSize, backlogPage * backlogPageSize)
                  .map((ev) => {
                    const isQualified = ev.status === 'QUALIFIED';
                    const isDup = ev.status?.includes('DUPLICATE');
                    const isGov = ev.status?.includes('GOVERNMENT');
                    const isUndeliv = ev.status?.includes('UNDELIVERABLE') || ev.status?.includes('EMAIL');

                    const badgeColor = isQualified
                      ? 'var(--green)'
                      : isDup
                      ? '#fbbf24'
                      : isGov
                      ? 'var(--purple)'
                      : 'var(--red)';

                    return (
                      <tr key={ev.id}>
                        <td>
                          <div style={{ fontWeight: 700, color: '#fff' }}>{ev.company_name}</div>
                          {ev.contact_email && (
                            <div style={{ fontSize: '11px', color: 'var(--cyan)', fontFamily: 'var(--mono)' }}>
                              {ev.contact_email}
                            </div>
                          )}
                          {ev.lead_id && (
                            <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
                              {ev.lead_id}
                            </div>
                          )}
                        </td>
                        <td>
                          <span className="badge-tag badge-cyan" style={{ fontSize: '10px' }}>
                            {(ev.channel || 'SCOUT').replace(/_/g, ' ')}
                          </span>
                        </td>
                        <td>
                          <span
                            style={{
                              display: 'inline-block',
                              padding: '2px 8px',
                              borderRadius: '4px',
                              fontSize: '11px',
                              fontWeight: 700,
                              color: badgeColor,
                              border: `1px solid ${badgeColor}`,
                              background: 'rgba(255, 255, 255, 0.04)',
                            }}
                          >
                            {isQualified ? '✅ QUALIFIED' : isDup ? '⏭️ BLOCKED DUP' : isGov ? '🏛️ GOV ENTITY' : isUndeliv ? '❌ UNDELIVERABLE' : ev.status}
                          </span>
                        </td>
                        <td>
                          <div style={{ fontSize: '12px', color: isQualified ? 'var(--green)' : 'var(--text-dim)', maxWidth: '380px' }}>
                            {ev.reason || 'Candidate evaluated'}
                          </div>
                        </td>
                        <td>
                          <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                            {ev.jurisdiction || 'N/A'}
                          </div>
                        </td>
                        <td>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {ev.evaluated_at ? new Date(ev.evaluated_at).toLocaleString() : 'Recent'}
                          </div>
                        </td>
                      </tr>
                    );
                  })
              )}
            </tbody>
          </table>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Company &amp; Decision Maker</th>
                <th>Discovery Channel &amp; Docket Proof</th>
                <th>Deliverability &amp; ESP</th>
                <th>Opportunity Score</th>
                <th>Same-Day Freshness</th>
                <th>Sandbox Link</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {backlogLeads.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No vetted backlog leads match the current filters. Click "Run Burst Now" to scout fresh leads.
                  </td>
                </tr>
              ) : (
              backlogLeads
                .slice((backlogPage - 1) * backlogPageSize, backlogPage * backlogPageSize)
                .map((lead) => {
                  const slug = lead.slug || lead.lead_id;
                  const opp = lead.automation_opportunity_score || 75;
                  const isRefreshing = freshnessRefreshingLeadId === lead.lead_id;
                  const todayStr = new Date().toISOString().slice(0, 10);
                  const isFresh = (
                    lead.research?.freshness_verified === true ||
                    lead.research?.filing_date === todayStr ||
                    lead.sample_data?.[0]?.filing_date === todayStr
                  );

                  return (
                    <tr key={lead.lead_id}>
                      <td>
                        <div style={{ fontWeight: 700, color: '#fff' }}>{lead.company_name}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                          {lead.contact_name ? `${lead.contact_name} (${lead.contact_role || 'Exec'})` : 'Executive Contact'}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--cyan)', fontFamily: 'var(--mono)' }}>
                          {lead.contact_email || 'Verified on file'}
                        </div>
                      </td>
                      <td>
                        {renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                          {lead.target_portal_name || lead.jurisdiction || 'County Court Docket'}
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span className={`badge-tag ${lead.deliverability_score >= 80 ? 'badge-green' : 'badge-yellow'}`}>
                            {lead.deliverability_score || 95}% Safe
                          </span>
                          <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                            {lead.email_provider || 'Google/MS'}
                          </span>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontWeight: 800, color: opp >= 75 ? '#fbbf24' : opp >= 65 ? 'var(--cyan)' : '#94a3b8' }}>
                            {opp}/100
                          </span>
                          <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                            {opp >= 70 ? 'Hot Fit' : 'Nurture'}
                          </span>
                        </div>
                      </td>
                      <td>
                        {isFresh ? (
                          <span className="badge-tag badge-green" style={{ fontSize: '10px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <span>🟢</span> Same-Day Fresh
                          </span>
                        ) : (
                          <span className="badge-tag badge-yellow" style={{ fontSize: '10px', display: 'inline-flex', alignItems: 'center', gap: '4px' }} title="Records older than 24h will be automatically re-scraped before cold outreach dispatch">
                            <span>🟡</span> Stale (&gt;24h • Auto-refreshes)
                          </span>
                        )}
                      </td>
                      <td>
                        <a
                          href={`/sandbox/${slug}`}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-outline"
                          style={{ fontSize: '10px', padding: '3px 8px' }}
                        >
                          🔗 Open Sandbox
                        </a>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                          <button
                            className="btn btn-outline"
                            style={{ fontSize: '10px', padding: '4px 8px' }}
                            onClick={() => handleRefreshFreshness(lead.lead_id)}
                            disabled={isRefreshing}
                            title="Manually trigger 10-second micro-scrape to pull fresh same-day filings for this county"
                          >
                            {isRefreshing ? '⏳' : '🔄 Refresh'}
                          </button>
                          <button
                            className="btn btn-outline"
                            style={{ fontSize: '10px', padding: '4px 8px' }}
                            onClick={() => setScoreModal({ open: true, lead })}
                          >
                            🔎 Dossier
                          </button>
                          <button
                            className="btn btn-primary"
                            style={{ fontSize: '10px', padding: '4px 8px', background: 'var(--cyan)', color: '#000', fontWeight: 700 }}
                            onClick={() => handleAdvance(lead.lead_id)}
                            disabled={actionInProgress[lead.lead_id]}
                            title="Approve & dispatch Touch 1 (freshness verified automatically)"
                          >
                            🚀 Send
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
            )}
            </tbody>
          </table>
        )}

        {/* Backlog / Evaluation Pagination Footer */}
        {((candidateScope === 'EVALUATED' ? candidateEvaluations.length : backlogLeads.length) > 0) && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 18px', borderTop: '1px solid var(--border)', fontSize: '12px', color: 'var(--text-dim)' }}>
            <div>
              {candidateScope === 'EVALUATED'
                ? `Showing ${(backlogPage - 1) * backlogPageSize + 1} to ${Math.min(backlogPage * backlogPageSize, candidateEvaluations.length)} of ${candidateEvaluations.length} evaluated candidate records`
                : `Showing ${(backlogPage - 1) * backlogPageSize + 1} to ${Math.min(backlogPage * backlogPageSize, backlogLeads.length)} of ${backlogLeads.length} vetted prospects`}
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                className="btn btn-outline"
                style={{ fontSize: '11px', padding: '4px 10px' }}
                disabled={backlogPage <= 1}
                onClick={() => setBacklogPage((p) => Math.max(1, p - 1))}
              >
                ◀ Previous
              </button>
              <span>
                Page {backlogPage} of {Math.ceil((candidateScope === 'EVALUATED' ? candidateEvaluations.length : backlogLeads.length) / backlogPageSize) || 1}
              </span>
              <button
                className="btn btn-outline"
                style={{ fontSize: '11px', padding: '4px 10px' }}
                disabled={backlogPage >= Math.ceil((candidateScope === 'EVALUATED' ? candidateEvaluations.length : backlogLeads.length) / backlogPageSize)}
                onClick={() => setBacklogPage((p) => p + 1)}
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
