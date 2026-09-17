import React from 'react';

export default function AdminHeader({
  pipeline,
  prospector,
  user,
  masterAuth,
  isSignedIn,
  setMasterAuth,
  setCommandPaletteOpen,
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="brand-icon" style={{ width: '32px', height: '32px', fontSize: '16px' }}>⚡</span>
          <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#fff', letterSpacing: '-0.5px' }}>
            LeadOps Command Center
          </h1>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: '12px',
              background: pipeline.metrics?.emergency_stop_active ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
              color: pipeline.metrics?.emergency_stop_active ? '#f87171' : 'var(--green)',
              border: `1px solid ${pipeline.metrics?.emergency_stop_active ? 'rgba(239, 68, 68, 0.4)' : 'rgba(16, 185, 129, 0.4)'}`,
            }}
          >
            {pipeline.metrics?.emergency_stop_active ? '🛑 EMERGENCY STOP ACTIVE' : '● SWARM LIVE'}
          </span>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
          Autonomous 7-Agent Dev Swarms, Live Municipal Extractors, QA Gate &amp; Setup Sprint Vault
        </p>
      </div>

      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-dim)', marginRight: '6px' }}>
          {user?.primaryEmailAddress?.emailAddress ? `👤 ${user.primaryEmailAddress.emailAddress}` : '⚡ Founder Key Active'}
        </span>
        {masterAuth && !isSignedIn && (
          <button
            className="btn btn-outline"
            style={{ fontSize: '11px', padding: '6px 12px' }}
            onClick={() => {
              localStorage.removeItem('leadops_admin_token');
              setMasterAuth(false);
            }}
          >
            Lock Console
          </button>
        )}
        <button
          className="btn btn-outline"
          style={{
            borderColor: pipeline.autoOutreachStatus?.enabled ? 'var(--green)' : 'rgba(148, 163, 184, 0.4)',
            color: pipeline.autoOutreachStatus?.enabled ? 'var(--green)' : '#94a3b8',
            fontSize: '11px',
            padding: '6px 12px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
          }}
          onClick={pipeline.handleToggleAutoOutreach}
          disabled={pipeline.autoOutreachLoading}
          title="When enabled, newly scouted leads auto-send after a 3-minute grace period unless cancelled via mobile Discord/Telegram."
        >
          <span>{pipeline.autoOutreachStatus?.enabled ? '⏱️ Auto-Outreach: ON (3m Grace)' : '⏸️ Auto-Outreach: OFF'}</span>
        </button>
        <button
          className="btn btn-outline"
          style={{
            borderColor: (pipeline.scoutStatus?.run_24_7 ?? true) ? 'var(--green)' : 'rgba(148, 163, 184, 0.4)',
            color: (pipeline.scoutStatus?.run_24_7 ?? true) ? 'var(--green)' : '#94a3b8',
            fontSize: '11px',
            padding: '6px 12px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            background: (pipeline.scoutStatus?.run_24_7 ?? true) ? 'rgba(16, 185, 129, 0.12)' : 'transparent',
          }}
          onClick={pipeline.handleToggleScout247}
          title={(pipeline.scoutStatus?.run_24_7 ?? true) ? "Scout is in 24/7 All-Day mode: continuously discovering prospects without work hours restrictions. Click to toggle office hours." : "Scout respects office hours (8am-5pm CST). Click to enable 24/7 all-day scouting."}
        >
          <span>{(pipeline.scoutStatus?.run_24_7 ?? true) ? '⚡ Scout: 24/7 All-Day Active' : '🌙 Scout: Office Hours Only'}</span>
        </button>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <input
            type="text"
            value={prospector.scoutSearchQuery}
            onChange={(e) => prospector.setScoutSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !prospector.scoutingInProgress) {
                prospector.handleTriggerWebScout();
              }
            }}
            placeholder="🔍 Search query or niche (e.g. Austin probate)..."
            disabled={prospector.scoutingInProgress}
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              borderRadius: '6px',
              color: '#e2e8f0',
              fontSize: '11px',
              padding: '5px 10px',
              width: '220px',
              outline: 'none',
            }}
            title="Enter custom search query or niche. Press Enter or click Scout Now to run until a new lead is found."
          />
          <select
            value={prospector.selectedScoutChannel}
            onChange={(e) => prospector.setSelectedScoutChannel(e.target.value)}
            disabled={prospector.scoutingInProgress}
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              borderRadius: '6px',
              color: 'var(--cyan)',
              fontSize: '11px',
              padding: '5px 8px',
              outline: 'none',
              cursor: 'pointer',
              fontWeight: 600,
            }}
            title="Select High-ROI Prospect Discovery Engine"
          >
            <option value="">🎯 All High-ROI Channels (Auto)</option>
            <option value="county_filing_party">🏛️ County Filing Parties (Priority 1)</option>
            <option value="state_bar">⚖️ State Bar Directories (Priority 2)</option>
            <option value="sos_entity">🏢 SOS New Registrations (Priority 3)</option>
            <option value="local_business">📍 Google Maps / Local (Priority 4)</option>
          </select>

          {/* Batch Count Selector */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              borderRadius: '6px',
              padding: '2px 5px',
            }}
            title="Select number of leads to hunt in this swarm batch"
          >
            <span style={{ fontSize: '10px', color: 'var(--text-dim)', fontWeight: 600, paddingRight: '2px' }}>
              Batch:
            </span>
            {[1, 3, 5].map((cnt) => (
              <button
                key={cnt}
                type="button"
                onClick={() => prospector.setScoutBatchCount(cnt)}
                style={{
                  background: prospector.scoutBatchCount === cnt ? 'var(--cyan)' : 'transparent',
                  color: prospector.scoutBatchCount === cnt ? '#090d16' : 'var(--cyan)',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '11px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                title={`Hunt ${cnt} lead${cnt > 1 ? 's in parallel swarm batch' : ''}`}
              >
                {cnt === 5 ? '⚡5' : cnt}
              </button>
            ))}
          </div>

          <button
            className="btn btn-outline"
            style={{
              borderColor: 'rgba(56, 189, 248, 0.4)',
              color: 'var(--cyan)',
              fontSize: '11px',
              padding: '6px 12px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              background: prospector.scoutBatchCount > 1 ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
            }}
            onClick={() => prospector.handleTriggerWebScout()}
            disabled={prospector.scoutingInProgress}
            title="Trigger autonomous swarm scout to hunt qualified B2B leads."
          >
            <span>
              {prospector.scoutingInProgress
                ? `⏳ Hunting ${prospector.scoutBatchCount > 1 ? `Swarm (${prospector.scoutBatchCount})...` : 'Lead...'}`
                : prospector.scoutBatchCount > 1
                ? `⚡ Swarm Hunt (${prospector.scoutBatchCount} Leads)`
                : '🔎 Scout Now'}
            </span>
          </button>
        </div>

        <button
          className="btn btn-outline"
          style={{
            borderColor: pipeline.metrics?.emergency_stop_active ? 'var(--green)' : 'rgba(239, 68, 68, 0.4)',
            color: pipeline.metrics?.emergency_stop_active ? 'var(--green)' : '#f87171',
          }}
          onClick={pipeline.handleToggleEmergencyStop}
        >
          {pipeline.metrics?.emergency_stop_active ? '▶️ Resume System' : '🛑 Emergency Stop'}
        </button>
        <button
          className="btn btn-outline"
          style={{ borderColor: 'rgba(239, 68, 68, 0.35)', color: '#f87171' }}
          onClick={pipeline.handlePurgeAllData}
          title="Wipes all mock data for a 100% clean live launch"
        >
          🧹 Purge Test Data
        </button>
        <button className="btn btn-outline" onClick={pipeline.loadAdminData}>
          🔄 Refresh Telemetry
        </button>
        <button
          className="btn btn-primary"
          style={{
            fontSize: '11px',
            padding: '6px 14px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(56, 189, 248, 0.15)',
            color: 'var(--cyan)',
            border: '1px solid rgba(56, 189, 248, 0.4)',
          }}
          onClick={() => setCommandPaletteOpen(true)}
          title="Open Command Palette (Cmd+K / Ctrl+K)"
        >
          <span>⚡ ⌘K Omnibar</span>
          <kbd style={{ fontSize: '9px', background: 'rgba(0, 0, 0, 0.3)', padding: '2px 4px', borderRadius: '3px' }}>
            ⌘K
          </kbd>
        </button>
      </div>
    </div>
  );
}
