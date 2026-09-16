import React from 'react';
import FleetSubTab from './inbox/FleetSubTab';
import InboundSubTab from './inbox/InboundSubTab';
import ReceiversSubTab from './inbox/ReceiversSubTab';
import ActivitySubTab from './inbox/ActivitySubTab';

export default function InboxesAndWarmupTab(props) {
  const {
    inboxes,
    loadInboxes,
    inboxesLoading,
    warmupTargets,
    loadWarmupTargets,
    warmupTargetsLoading,
    inboundStream,
    loadInboundStream,
    inboundLoading,
    warmupActivity,
    loadWarmupActivity,
    warmupActivityLoading,
    inboxSubTab,
    setInboxSubTab,
    handleStartWarmup,
    startingWarmup,
    handleDispatchWarmupBatch,
    dispatchingWarmup,
    handleFlushOutreachQueue,
    flushingQueue,
    showToast,
    showAddReceiverModal,
    setShowAddReceiverModal,
    receiverFormData,
    setReceiverFormData,
    handleSaveReceiver,
    showAddInboxModal,
    setShowAddInboxModal,
    inboxFormData,
    setInboxFormData,
    handleSaveInbox,
  } = props;

  return (
    <div>
      {/* Header & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px', background: 'var(--card)', padding: '20px 24px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', margin: 0 }}>
              📬 Email Infrastructure &amp; Warmup Engine
            </h2>
            <span className="badge-tag badge-cyan">{inboxes?.length || 0} Sending Inboxes</span>
            <span className="badge-tag badge-green">{warmupTargets?.length || 0} Warm Receivers</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px', marginBottom: 0 }}>
            End-to-end management for outbound sending identities, inbound prospect replies, and peer network warm receivers.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            className="btn btn-outline"
            style={{ fontSize: '12px', padding: '8px 14px' }}
            onClick={() => { loadInboxes(); showToast('🔄 Refreshed all inbox telemetry and live streams!', 'info'); }}
            disabled={inboxesLoading || inboundLoading || warmupTargetsLoading}
          >
            {inboxesLoading ? '🔄 Refreshing...' : '🔄 Refresh Telemetry'}
          </button>
          <button
            className="btn btn-primary"
            style={{
              fontSize: '12px',
              padding: '8px 16px',
              background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
              border: '1px solid #fbbf24',
              boxShadow: '0 0 12px rgba(245, 158, 11, 0.3)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onClick={handleStartWarmup}
            disabled={startingWarmup}
            title="Initialize Day 1 warmup schedule and synchronize across all inboxes"
          >
            <span>🔥</span>
            <span>{startingWarmup ? '⏳ Starting Warmup...' : 'Start / Re-sync Warmup'}</span>
          </button>
          <button
            className="btn btn-secondary"
            style={{
              fontSize: '12px',
              padding: '8px 14px',
              borderColor: '#38bdf8',
              color: '#38bdf8',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onClick={() => handleDispatchWarmupBatch(3)}
            disabled={dispatchingWarmup}
            title="Immediately dispatch a batch of 3 peer warmup emails across available inboxes"
          >
            <span>⚡</span>
            <span>{dispatchingWarmup ? '⏳ Dispatching...' : 'Run Warmup Batch (3)'}</span>
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '8px 14px', borderColor: 'var(--accent)' }}
            onClick={handleFlushOutreachQueue}
            disabled={flushingQueue}
            title="Flush pending outreach queue immediately across inboxes with anti-spam jitter"
          >
            {flushingQueue ? '⏳ Dispatching...' : '⚡ Flush Outreach Queue'}
          </button>
          {inboxSubTab === 'receivers' ? (
            <button
              className="btn btn-primary"
              style={{ fontSize: '12px', padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              onClick={() => setShowAddReceiverModal(true)}
            >
              <span>+</span> Add Warm Receiver Inbox
            </button>
          ) : (
            <button
              className="btn btn-primary"
              style={{ fontSize: '12px', padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              onClick={() => setShowAddInboxModal(true)}
            >
              <span>+</span> Add Sending Inbox
            </button>
          )}
        </div>
      </div>

      {/* Sub-Navigation Tabs Bar */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '24px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '14px', flexWrap: 'wrap' }}>
        <button
          type="button"
          className={`btn ${inboxSubTab === 'fleet' ? 'btn-primary' : 'btn-outline'}`}
          style={{
            fontSize: '13px',
            padding: '9px 18px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: inboxSubTab === 'fleet' ? 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)' : 'rgba(255,255,255,0.03)',
            border: inboxSubTab === 'fleet' ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
            boxShadow: inboxSubTab === 'fleet' ? '0 0 14px rgba(56, 189, 248, 0.3)' : 'none',
          }}
          onClick={() => setInboxSubTab('fleet')}
        >
          <span>🚀</span>
          <span>Outbound Warming Fleet ({inboxes?.length || 0})</span>
        </button>

        <button
          type="button"
          className={`btn ${inboxSubTab === 'inbound' ? 'btn-primary' : 'btn-outline'}`}
          style={{
            fontSize: '13px',
            padding: '9px 18px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: inboxSubTab === 'inbound' ? 'linear-gradient(135deg, #10b981 0%, #047857 100%)' : 'rgba(255,255,255,0.03)',
            border: inboxSubTab === 'inbound' ? '1px solid #34d399' : '1px solid rgba(255,255,255,0.1)',
            boxShadow: inboxSubTab === 'inbound' ? '0 0 14px rgba(16, 185, 129, 0.3)' : 'none',
          }}
          onClick={() => { setInboxSubTab('inbound'); loadInboundStream(); }}
        >
          <span>📥</span>
          <span>Inbound Reply Center ({inboundStream?.metrics?.total_received || 0})</span>
          {(inboundStream?.metrics?.interested_count || 0) > 0 && (
            <span style={{ fontSize: '10px', background: '#ef4444', color: '#fff', padding: '1px 6px', borderRadius: '10px', fontWeight: 800 }}>
              {inboundStream.metrics.interested_count} Warm
            </span>
          )}
        </button>

        <button
          type="button"
          className={`btn ${inboxSubTab === 'receivers' ? 'btn-primary' : 'btn-outline'}`}
          style={{
            fontSize: '13px',
            padding: '9px 18px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: inboxSubTab === 'receivers' ? 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)' : 'rgba(255,255,255,0.03)',
            border: inboxSubTab === 'receivers' ? '1px solid #a78bfa' : '1px solid rgba(255,255,255,0.1)',
            boxShadow: inboxSubTab === 'receivers' ? '0 0 14px rgba(139, 92, 246, 0.3)' : 'none',
          }}
          onClick={() => { setInboxSubTab('receivers'); loadWarmupTargets(); }}
        >
          <span>🤝</span>
          <span>Warm Receiver Inboxes ({warmupTargets?.length || 0})</span>
        </button>

        <button
          type="button"
          className={`btn ${inboxSubTab === 'activity' ? 'btn-primary' : 'btn-outline'}`}
          style={{
            fontSize: '13px',
            padding: '9px 18px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: inboxSubTab === 'activity' ? 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)' : 'rgba(255,255,255,0.03)',
            border: inboxSubTab === 'activity' ? '1px solid #fbbf24' : '1px solid rgba(255,255,255,0.1)',
            boxShadow: inboxSubTab === 'activity' ? '0 0 14px rgba(245, 158, 11, 0.3)' : 'none',
          }}
          onClick={() => { setInboxSubTab('activity'); loadWarmupActivity(); }}
        >
          <span>📜</span>
          <span>Live Activity Stream ({warmupActivity?.logs?.length || 0})</span>
        </button>
      </div>

      {/* Sub-Tabs Rendering */}
      {inboxSubTab === 'fleet' && <FleetSubTab {...props} />}
      {inboxSubTab === 'inbound' && <InboundSubTab {...props} />}
      {inboxSubTab === 'receivers' && <ReceiversSubTab {...props} />}
      {inboxSubTab === 'activity' && <ActivitySubTab {...props} />}

      {/* Add Warm Receiver Modal */}
      {showAddReceiverModal && (
        <div className="admin-modal-overlay" onClick={() => setShowAddReceiverModal(false)}>
          <div className="admin-modal-content" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0 }}>
                🤝 Add Peer Warm Receiver Inbox
              </h3>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setShowAddReceiverModal(false)}
              >
                ✕ Close
              </button>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
              Add a seed mailbox to receive daily warmup emails from our <code>olfmailer.com</code> fleet. Providing app passwords enables autonomous 2-way spam rescues and AI reply loops.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Receiver Email Address *
                </label>
                <input
                  type="email"
                  placeholder="e.g. receiver@yourdomain.com"
                  value={receiverFormData.email}
                  onChange={(e) => setReceiverFormData((p) => ({ ...p, email: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Contact / Display Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Ben Pahrman"
                  value={receiverFormData.name}
                  onChange={(e) => setReceiverFormData((p) => ({ ...p, name: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Mailbox Provider:
                </label>
                <select
                  value={receiverFormData.provider}
                  onChange={(e) => setReceiverFormData((p) => ({ ...p, provider: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                >
                  <option value="gmail">🔵 Gmail / Google Workspace</option>
                  <option value="outlook">🟧 Microsoft Outlook / Hotmail</option>
                  <option value="yahoo">🟣 Yahoo Mail</option>
                  <option value="custom">⚪ Custom IMAP</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  App-Specific Password (Optional, enables 2-way spam extraction &amp; AI reply)
                </label>
                <input
                  type="password"
                  placeholder="App password"
                  value={receiverFormData.password}
                  onChange={(e) => setReceiverFormData((p) => ({ ...p, password: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
              <button
                className="btn btn-outline"
                style={{ fontSize: '12px', padding: '8px 16px' }}
                onClick={() => setShowAddReceiverModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '8px 18px', background: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)', border: 'none' }}
                onClick={handleSaveReceiver}
              >
                Save Warm Receiver ➔
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Inbox Modal */}
      {showAddInboxModal && (
        <div className="admin-modal-overlay" onClick={() => setShowAddInboxModal(false)}>
          <div className="admin-modal-content" style={{ maxWidth: '520px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0 }}>
                📬 Connect New Email Inbox
              </h3>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setShowAddInboxModal(false)}
              >
                ✕ Close
              </button>
            </div>

            {/* OLFMAILER Guidance Callout */}
            <div
              style={{
                background: 'rgba(56, 189, 248, 0.12)',
                border: '1px solid rgba(56, 189, 248, 0.35)',
                borderRadius: 'var(--radius-sm)',
                padding: '12px 14px',
                fontSize: '12px',
                color: '#e0f2fe',
                lineHeight: 1.5,
                marginBottom: '18px',
              }}
            >
              <b>🚀 olfmailer.com &amp; Azure Email Setup</b>:
              <br />
              Outbound sending runs over <b>Azure Communication Services</b> with Cloudflare SPF, DKIM, and DMARC verification. Inbound prospect replies to <code>*@olfmailer.com</code> are routed through Cloudflare Email Routing directly to your watched inbox.
            </div>

            {/* Form Fields */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Provider Preset:
                </label>
                <select
                  value={inboxFormData.provider}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, provider: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                >
                  <option value="olfmailer">🚀 olfmailer.com (Azure Communication Services + Cloudflare)</option>
                  <option value="gmail">🔵 Google / Gmail (smtp.gmail.com:465 / imap.gmail.com:993)</option>
                  <option value="outlook">🟧 Microsoft Outlook / 365 (smtp-mail.outlook.com:587 / outlook.office365.com:993)</option>
                  <option value="smtp_generic">⚪ Generic Custom SMTP / IMAP</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Inbox Email Address *
                </label>
                <input
                  type="email"
                  placeholder="e.g. alex@olfmailer.com or ben@olfmailer.com"
                  value={inboxFormData.email_address}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, email_address: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  {inboxFormData.provider === 'outlook' ? 'Outlook App Password *' : inboxFormData.provider === 'gmail' ? 'Google App Password *' : 'App-Specific Password (Optional for Azure ACS)'}
                </label>
                <input
                  type="password"
                  placeholder="App password (if applicable)"
                  value={inboxFormData.password}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, password: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Sender Display Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Alex | OmniLeadFeeder"
                  value={inboxFormData.from_name}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, from_name: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Daily Outreach Warmup Limit (emails/day)
                </label>
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={inboxFormData.daily_limit}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, daily_limit: parseInt(e.target.value) || 25 }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>
            </div>

            {/* Modal Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '22px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
              <button
                className="btn btn-outline"
                style={{ fontSize: '12px', padding: '8px 16px' }}
                onClick={() => setShowAddInboxModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '8px 18px' }}
                onClick={handleSaveInbox}
              >
                Save &amp; Verify Connection ➔
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
