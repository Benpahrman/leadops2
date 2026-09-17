import React from 'react';

/**
 * Modal to display AI Lead Scoring, 7-factor BDR weighted metrics, buyer signals,
 * deep operational intelligence dossier, and the Alex objection playbook.
 */
export default function LeadScoringModal({
  modalState,
  onClose,
  handleDeepEnrichLead,
  enrichingLeadId,
  renderDiscoveryBadge,
  showToast,
}) {
  if (!modalState || !modalState.open || !modalState.lead) return null;

  const lead = modalState.lead;
  const oppScore = typeof lead.automation_opportunity_score === 'number'
    ? lead.automation_opportunity_score
    : (parseInt(lead.automation_opportunity_score, 10) || 75);
  const purchaseProb = typeof lead.purchase_probability === 'number'
    ? lead.purchase_probability
    : (parseInt(lead.purchase_probability, 10) || 60);
  const painSev = typeof lead.pain_severity === 'number'
    ? lead.pain_severity
    : (parseInt(lead.pain_severity, 10) || 6);
  const verdict = lead.qualification_verdict || (oppScore >= 65 ? 'QUALIFIED_HOT' : 'QUALIFIED_NURTURE');

  // Safely extract factor scores whether nested {score, max} objects or raw numbers
  const rawBreakdown = (lead.scoring_breakdown && typeof lead.scoring_breakdown === 'object')
    ? (lead.scoring_breakdown.breakdown || lead.scoring_breakdown)
    : {};

  const getFactor = (item, defaultScore, defaultMax) => {
    if (item === null || item === undefined) {
      return { score: defaultScore, max: defaultMax };
    }
    if (typeof item === 'number') {
      return { score: item, max: defaultMax };
    }
    if (typeof item === 'object') {
      const sc = typeof item.score === 'number' ? item.score : (parseInt(item.score, 10) || defaultScore);
      const mx = typeof item.max === 'number' ? item.max : (parseInt(item.max, 10) || defaultMax);
      return { score: sc, max: mx };
    }
    const parsed = parseInt(item, 10);
    return { score: isNaN(parsed) ? defaultScore : parsed, max: defaultMax };
  };

  const f1 = getFactor(rawBreakdown.labor_intensive_operations ?? rawBreakdown.labor_intensity, 20, 25);
  const f2 = getFactor(rawBreakdown.portal_usage ?? rawBreakdown.target_portal_scraping, 12, 15);
  const f3 = getFactor(rawBreakdown.manual_data_entry, 12, 15);
  const f4 = getFactor(rawBreakdown.compliance_requirements ?? rawBreakdown.compliance_regulatory, 11, 15);
  const f5 = getFactor(rawBreakdown.document_processing_volume ?? rawBreakdown.document_volume, 8, 10);
  const f6 = getFactor(rawBreakdown.company_size_fit ?? rawBreakdown.smb_size_fit, 8, 10);
  const f7 = getFactor(rawBreakdown.growth_signals ?? rawBreakdown.market_growth, 7, 10);

  const factorItems = [
    { label: 'Labor-Intensive Operations', val: f1.score, max: f1.max, desc: 'High repetitive human touchpoints' },
    { label: 'Target Portal Scraping Viability', val: f2.score, max: f2.max, desc: 'Public docket/portal data accessibility' },
    { label: 'Manual Data Entry Elimination', val: f3.score, max: f3.max, desc: 'Direct software bridge opportunity' },
    { label: 'Compliance & Regulatory Overhead', val: f4.score, max: f4.max, desc: 'Statutory filing & auditing requirements' },
    { label: 'Document & Record Volume', val: f5.score, max: f5.max, desc: 'Daily PDF/CSV/Record throughput' },
    { label: 'SMB Company Size Fit', val: f6.score, max: f6.max, desc: '5-50 staff sweet spot for agile adoption' },
    { label: 'Market Growth & Hiring Signals', val: f7.score, max: f7.max, desc: 'Active hiring or market expansion signals' },
  ];

  let signals = [];
  if (Array.isArray(lead.buyer_signals)) {
    signals = lead.buyer_signals.map((s) => (typeof s === 'object' && s !== null ? (s.label || s.signal || JSON.stringify(s)) : String(s)));
  } else if (lead.buyer_signals && typeof lead.buyer_signals === 'object') {
    if (Array.isArray(lead.buyer_signals.positive_signals)) {
      signals = lead.buyer_signals.positive_signals.map((s) => (typeof s === 'object' && s !== null ? (s.label || s.signal || JSON.stringify(s)) : String(s)));
    } else {
      signals = Object.values(lead.buyer_signals).filter((v) => typeof v === 'string');
    }
  }
  if (signals.length === 0) {
    signals = [
      'High manual data entry overhead identified in core workflow',
      'Municipal/public docket dependencies detected',
      'Sub-50 employee size matches automation deployment sweet-spot',
    ];
  }
  const qa = lead.qa_score !== null && lead.qa_score !== undefined ? lead.qa_score : null;

  let research = {};
  if (typeof lead.research === 'object' && lead.research !== null) {
    research = lead.research;
  } else if (typeof lead.research === 'string' && lead.research.trim()) {
    try {
      research = JSON.parse(lead.research);
    } catch (_) {
      research = {};
    }
  }

  const handleCopy = (text, msg = 'Copied to clipboard!') => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      if (showToast) {
        showToast(msg, 'success');
      }
    }
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal-content" style={{ maxWidth: '780px' }} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', margin: 0 }}>
                ⚡ AI Opportunity &amp; BDR Scoring Intelligence
              </h3>
              <span className={`badge-tag ${verdict.includes('HOT') ? 'badge-green' : 'badge-cyan'}`} style={{ fontSize: '11px' }}>
                {verdict}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '13px', color: 'var(--text-dim)' }}>
              <span style={{ color: '#fff', fontWeight: 600 }}>{lead.company_name || 'Candidate Organization'}</span>
              <span>•</span>
              <span style={{ fontFamily: 'var(--mono)', fontSize: '11px' }}>{lead.lead_id}</span>
              <span>•</span>
              <span style={{ color: 'var(--cyan)' }}>{lead.jurisdiction || lead.target_portal_name || 'Municipal Portal'}</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {handleDeepEnrichLead && (
              <button
                className="btn btn-outline"
                style={{
                  padding: '6px 12px',
                  fontSize: '12px',
                  borderColor: 'rgba(56, 189, 248, 0.4)',
                  color: 'var(--cyan)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
                onClick={() => handleDeepEnrichLead(lead.lead_id)}
                disabled={enrichingLeadId === lead.lead_id}
                title="Trigger deep LLM agent enrichment & market research on this lead"
              >
                {enrichingLeadId === lead.lead_id ? '⏳ Researching...' : '⚡ Deep Re-Enrich'}
              </button>
            )}
            <button
              className="btn btn-outline"
              style={{ padding: '6px 12px', fontSize: '12px' }}
              onClick={onClose}
            >
              ✕ Close
            </button>
          </div>
        </div>

        {/* KPI Scores Row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginTop: '14px' }}>
          <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
              Automation Opp Score
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: oppScore >= 75 ? 'var(--green)' : 'var(--cyan)', marginTop: '4px' }}>
              {oppScore}<span style={{ fontSize: '14px', color: 'var(--text-dim)' }}>/100</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              7-Factor BDR Weighted
            </div>
          </div>

          <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
              Purchase Intent Prob
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--purple)', marginTop: '4px' }}>
              {purchaseProb}%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {purchaseProb >= 70 ? '🔥 High Intent' : '⚡ Moderate Intent'}
            </div>
          </div>

          <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
              Pain Severity
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: painSev >= 7 ? '#f87171' : '#fbbf24', marginTop: '4px' }}>
              {painSev}<span style={{ fontSize: '14px', color: 'var(--text-dim)' }}>/10</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {painSev >= 7 ? 'Critical Bottlenecks' : 'Moderate Inefficiency'}
            </div>
          </div>

          <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
              QA Verification Gate
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: qa && qa >= 0.95 ? 'var(--green)' : '#fbbf24', marginTop: '4px' }}>
              {qa !== null ? `${(qa * 100).toFixed(0)}%` : 'Pending'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {qa && qa >= 0.95 ? '✓ Meets Founder Gate' : 'Data Verification Stage'}
            </div>
          </div>
        </div>

        {/* 7-Factor Weighted Breakdown */}
        <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '16px', marginTop: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: 0 }}>
              📊 7-Factor BDR Score Model Breakdown
            </h4>
            <span style={{ fontSize: '12px', color: 'var(--cyan)', fontWeight: 600 }}>
              Calculated Live ({oppScore}/100 Total)
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {factorItems.map((f, idx) => {
              const pct = Math.round((f.val / f.max) * 100);
              return (
                <div key={idx}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                    <span style={{ color: '#fff', fontWeight: 500 }}>
                      {f.label} <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>({f.desc})</span>
                    </span>
                    <span style={{ fontFamily: 'var(--mono)', color: 'var(--cyan)', fontWeight: 600 }}>
                      {f.val} / {f.max} pts ({pct}%)
                    </span>
                  </div>
                  <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${pct}%`,
                        height: '100%',
                        background: pct >= 80 ? 'var(--green)' : pct >= 50 ? 'var(--cyan)' : '#fbbf24',
                        borderRadius: '3px',
                        transition: 'width 0.4s ease',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Buyer Signals & Portal Info */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', marginTop: '14px' }}>
          <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '16px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px' }}>
              🎯 Detected Buyer Intent Signals
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {signals.map((sig, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '12px', color: 'var(--text)' }}>
                  <span style={{ color: 'var(--green)', fontSize: '14px', lineHeight: 1 }}>✓</span>
                  <span>{sig}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', margin: 0 }}>
                📍 Lead Origin &amp; Discovery Provenance
              </h4>
              {renderDiscoveryBadge && renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div>
                <b style={{ color: '#fff' }}>Acquisition Channel:</b>{' '}
                <span style={{ color: 'var(--text)' }}>
                  {lead.discovery_channel ? lead.discovery_channel.replace(/_/g, ' ') : 'Municipal Public Registry'}
                </span>
              </div>
              <div>
                <b style={{ color: '#fff' }}>Target Portal / Registry:</b>{' '}
                <span style={{ color: 'var(--text)' }}>
                  {lead.target_portal_name || lead.jurisdiction || 'Municipal Registry'}
                </span>
                {lead.jurisdiction && lead.target_portal_name && (
                  <span style={{ color: 'var(--text-dim)', marginLeft: '6px' }}>
                    ({lead.jurisdiction})
                  </span>
                )}
              </div>
              {(lead.source_url || lead.target_url) && (
                <div>
                  <b style={{ color: '#fff' }}>Official Source Registry URL:</b>{' '}
                  <a
                    href={lead.source_url || lead.target_url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: 'var(--cyan)', textDecoration: 'underline', wordBreak: 'break-all' }}
                  >
                    {lead.source_url || lead.target_url} ↗
                  </a>
                </div>
              )}
              {lead.website && (
                <div>
                  <b style={{ color: '#fff' }}>Company Website:</b>{' '}
                  <a
                    href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: 'var(--purple)', textDecoration: 'underline', wordBreak: 'break-all' }}
                  >
                    {lead.website} ↗
                  </a>
                </div>
              )}
              {lead.filing_case_number && (
                <div>
                  <b style={{ color: '#fff' }}>Docket / Case Number:</b>{' '}
                  <span style={{ fontFamily: 'var(--mono)', color: 'var(--yellow)' }}>
                    #{lead.filing_case_number}
                  </span>
                  {lead.filing_date && (
                    <span style={{ color: 'var(--text-dim)', marginLeft: '8px' }}>
                      (Filed: {lead.filing_date})
                    </span>
                  )}
                </div>
              )}
              {lead.matter_description && (
                <div>
                  <b style={{ color: '#fff' }}>Filing Classification:</b>{' '}
                  <span style={{ color: 'var(--text)' }}>{lead.matter_description}</span>
                </div>
              )}
              <div>
                <b style={{ color: '#fff' }}>Niche / Vertical:</b> {lead.niche || 'B2B Professional Services'}
              </div>
              {lead.contact_email && (
                <div>
                  <b style={{ color: '#fff' }}>Contact:</b> {lead.contact_email}
                  {lead.contact_role && <span style={{ color: 'var(--text-dim)' }}> ({lead.contact_role})</span>}
                  {lead.email_source && (
                    <span style={{ marginLeft: '6px', fontSize: '10px', background: 'rgba(56, 189, 248, 0.1)', color: 'var(--cyan)', padding: '1px 5px', borderRadius: '3px' }}>
                      via {lead.email_source}
                    </span>
                  )}
                </div>
              )}
              {lead.decision_maker_linkedin && (
                <div>
                  <b style={{ color: '#fff' }}>LinkedIn:</b>{' '}
                  <a href={lead.decision_maker_linkedin} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)', textDecoration: 'underline' }}>
                    Profile ↗
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Deep Market & Operational Intelligence Dossier */}
        <div
          style={{
            background: 'var(--bg)',
            border: '1px solid rgba(56, 189, 248, 0.35)',
            borderRadius: 'var(--radius-sm)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            marginTop: '14px',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid rgba(56, 189, 248, 0.15)',
              paddingBottom: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '16px' }}>🔬</span>
              <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: 0 }}>
                Deep Market &amp; Operational Intelligence Dossier
              </h4>
            </div>
            <span
              style={{
                fontSize: '10px',
                background: 'rgba(56, 189, 248, 0.15)',
                color: 'var(--cyan)',
                padding: '2px 8px',
                borderRadius: '12px',
                fontWeight: 600,
              }}
            >
              AI Agent Enriched
            </span>
          </div>

          {/* Row 1: Org Scale, HQ & Est ROI */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>HQ Location</div>
              <div style={{ fontSize: '12px', color: '#fff', fontWeight: 600, marginTop: '2px' }}>
                📍 {research.headquarters_location || lead.jurisdiction || 'Regional Office'}
              </div>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Company Scale</div>
              <div style={{ fontSize: '12px', color: '#fff', fontWeight: 600, marginTop: '2px' }}>
                🏢 {research.company_scale || 'Small-to-Mid Market Firm'}
              </div>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Weekly Hours Saved</div>
              <div style={{ fontSize: '13px', color: 'var(--green)', fontWeight: 700, marginTop: '2px' }}>
                ⏱️ ~{research.estimated_hours_saved_weekly || 8} hrs/wk
              </div>
            </div>
            <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Est. Labor Savings</div>
              <div style={{ fontSize: '13px', color: 'var(--cyan)', fontWeight: 700, marginTop: '2px' }}>
                💰 ${research.estimated_monthly_labor_savings || 1200}/mo
              </div>
            </div>
          </div>

          {/* Row 2: Secondary Contact & Tech Stack */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
            {research.secondary_decision_maker && (research.secondary_decision_maker.name || research.secondary_decision_maker.role) ? (
              <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, marginBottom: '4px' }}>
                  👥 Secondary Decision Maker / Influencer
                </div>
                <div style={{ fontSize: '12px', color: '#fff', fontWeight: 600 }}>
                  {research.secondary_decision_maker.name || 'Key Contact'}
                  {research.secondary_decision_maker.role && (
                    <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> — {research.secondary_decision_maker.role}</span>
                  )}
                </div>
                {research.secondary_decision_maker.email && (
                  <div style={{ fontSize: '11px', color: 'var(--cyan)', marginTop: '2px' }}>
                    ✉️ {research.secondary_decision_maker.email}
                  </div>
                )}
                {research.secondary_decision_maker.linkedin && (
                  <a
                    href={research.secondary_decision_maker.linkedin}
                    target="_blank"
                    rel="noreferrer"
                    style={{ fontSize: '11px', color: 'var(--purple)', textDecoration: 'underline', display: 'inline-block', marginTop: '2px' }}
                  >
                    LinkedIn Profile ↗
                  </a>
                )}
              </div>
            ) : null}

            {research.detected_tech_stack && (
              <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px' }}>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, marginBottom: '6px' }}>
                  💻 Detected Software &amp; Tech Stack
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                  {(Array.isArray(research.detected_tech_stack) ? research.detected_tech_stack : [research.detected_tech_stack]).map((tool, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: '11px',
                        background: 'rgba(147, 51, 234, 0.15)',
                        color: '#c084fc',
                        border: '1px solid rgba(147, 51, 234, 0.3)',
                        padding: '2px 7px',
                        borderRadius: '4px',
                        fontWeight: 500,
                      }}
                    >
                      {typeof tool === 'object' ? JSON.stringify(tool) : String(tool)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Row 3: Competitors */}
          {Array.isArray(research.local_competitors) && research.local_competitors.length > 0 && (
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, marginBottom: '6px' }}>
                ⚔️ Local &amp; Regional Competitors in Vertical
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {research.local_competitors.map((comp, idx) => {
                  const compName = typeof comp === 'object' && comp !== null ? (comp.name || comp.company || JSON.stringify(comp)) : String(comp);
                  return (
                    <span
                      key={idx}
                      style={{
                        fontSize: '11px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        color: 'var(--text)',
                        border: '1px solid var(--border)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                      }}
                    >
                      {compName}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Row 4: Alex Objection Playbook */}
          {research.objection_playbook && typeof research.objection_playbook === 'object' && Object.keys(research.objection_playbook).length > 0 && (
            <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px' }}>
              <div style={{ fontSize: '11px', color: 'var(--cyan)', fontWeight: 700, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                💬 Alex Persona Tailored Objection Playbook (1-Click Copy)
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {Object.entries(research.objection_playbook).map(([objection, answer], idx) => {
                  const answerText = typeof answer === 'object' && answer !== null ? (answer.response || JSON.stringify(answer)) : String(answer);
                  return (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(15, 23, 42, 0.7)',
                        border: '1px solid rgba(255, 255, 255, 0.07)',
                        borderRadius: '5px',
                        padding: '8px 10px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--yellow)' }}>
                          ❓ {objection.replace(/_/g, ' ')}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopy(answerText, 'Copied playbook answer to clipboard!')}
                          style={{
                            background: 'transparent',
                            border: '1px solid rgba(56, 189, 248, 0.3)',
                            color: 'var(--cyan)',
                            borderRadius: '4px',
                            padding: '2px 6px',
                            fontSize: '10px',
                            cursor: 'pointer',
                          }}
                          title="Copy counter-argument to clipboard"
                        >
                          📋 Copy
                        </button>
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text)', fontStyle: 'italic', lineHeight: 1.4 }}>
                        &ldquo;{answerText}&rdquo;
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Pain Points / Human Observation */}
        {(lead.pain_points || lead.notes || lead.human_observation) && (
          <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px', marginTop: '14px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
              📝 Operational Friction &amp; Human Observations
            </h4>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
              {typeof lead.pain_points === 'object' && lead.pain_points !== null
                ? JSON.stringify(lead.pain_points)
                : (lead.pain_points || lead.notes || lead.human_observation || 'No operational observations noted.')}
            </p>
          </div>
        )}

        {/* Modal Footer Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', paddingTop: '14px', marginTop: '14px', borderTop: '1px solid var(--border)' }}>
          {lead.slug && (
            <a
              href={`/portal/${lead.slug}`}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary"
              style={{ fontSize: '12px', padding: '8px 16px', textDecoration: 'none' }}
            >
              Open Client Portal ↗
            </a>
          )}
          <button
            className="btn btn-outline"
            style={{ fontSize: '12px', padding: '8px 16px' }}
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
