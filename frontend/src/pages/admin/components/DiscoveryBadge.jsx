import React from 'react';

export default function DiscoveryBadge({ channel, filingCaseNumber }) {
  const norm = (channel || '').toUpperCase().trim();
  const config = {
    COUNTY_FILING_PARTY: { label: '🏛️ County Court Docket', bg: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: 'rgba(234, 179, 8, 0.35)', tooltip: 'Scouted from same-day municipal court / county public filing docket' },
    STATE_BAR_DIRECTORY: { label: '⚖️ State Bar Directory', bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: 'rgba(168, 85, 247, 0.35)', tooltip: 'Identified via licensed state bar attorney directory' },
    SOS_NEW_BUSINESS: { label: '🏢 Secretary of State', bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: 'rgba(56, 189, 248, 0.35)', tooltip: 'Discovered from state Secretary of State commercial registrations' },
    GOOGLE_MAPS_LOCAL: { label: '📍 Google Maps / Local', bg: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', border: 'rgba(34, 197, 94, 0.35)', tooltip: 'Scouted via local business map & review intelligence' },
    JOB_BOARD_INTENT: { label: '💼 Hiring / Job Signals', bg: 'rgba(244, 63, 94, 0.15)', color: '#fb7185', border: 'rgba(244, 63, 94, 0.35)', tooltip: 'Identified via active operations / coordinator hiring requisitions' },
    B2B_WEB_SEARCH: { label: '🌐 Autonomous Web Scout', bg: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: 'rgba(99, 102, 241, 0.35)', tooltip: 'Discovered via autonomous B2B web crawler' },
    INBOUND_REFERRAL: { label: '🤝 Inbound Referral', bg: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: 'rgba(16, 185, 129, 0.35)', tooltip: 'Introduced via existing customer or partner referral' },
    CATALOG_SEARCH: { label: '🏛️ Municipal Open Data', bg: 'rgba(14, 165, 233, 0.15)', color: '#38bdf8', border: 'rgba(14, 165, 233, 0.35)', tooltip: 'Identified from municipal open data registry & public portals' },
  }[norm] || { label: `🔍 ${channel || 'Public Registry'}`, bg: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)', tooltip: 'Discovered via municipal public registry' };

  return (
    <div style={{ marginTop: '5px', display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap' }}>
      <span
        style={{
          fontSize: '10px',
          fontWeight: 700,
          padding: '2px 7px',
          borderRadius: '4px',
          background: config.bg,
          color: config.color,
          border: `1px solid ${config.border}`,
          letterSpacing: '0.02em',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
        }}
        title={config.tooltip}
      >
        {config.label}
      </span>
      {filingCaseNumber && (
        <span
          style={{
            fontSize: '10px',
            fontFamily: 'var(--mono)',
            padding: '2px 5px',
            borderRadius: '4px',
            background: 'rgba(255, 255, 255, 0.05)',
            color: 'var(--text-dim)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
          title={`Public Record Filing: Docket #${filingCaseNumber}`}
        >
          #{filingCaseNumber}
        </span>
      )}
    </div>
  );
}
