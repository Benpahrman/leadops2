import React from 'react';

export default function EmailCsvSection({
  emailRecipient,
  setEmailRecipient,
  emailEnabled,
  setEmailEnabled,
  isSaving,
  isTesting,
  handleSave,
  handleSendTestEmail,
}) {
  return (
    <div>
      <div style={{ background: 'rgba(34, 197, 94, 0.08)', border: '1px solid rgba(34, 197, 94, 0.25)', borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
        <div style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: 1.6 }}>
          📧 <b>Automated Email CSV Delivery</b> dispatches an executive HTML summary and full attached CSV spreadsheet directly to your team's inbox every morning at 06:00 AM UTC.
        </div>
      </div>

      <div style={{ marginBottom: '18px' }}>
        <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
          Recipient Email Address
        </label>
        <input
          type="email"
          className="form-input"
          placeholder="operations@yourcompany.com"
          value={emailRecipient}
          onChange={(e) => setEmailRecipient(e.target.value)}
          style={{ width: '100%', fontSize: '13px' }}
        />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '24px' }}>
        <input
          type="checkbox"
          id="emailEnabledCheckbox"
          checked={emailEnabled}
          onChange={(e) => setEmailEnabled(e.target.checked)}
          style={{ width: '16px', height: '16px', accentColor: 'var(--cyan)' }}
        />
        <label htmlFor="emailEnabledCheckbox" style={{ fontSize: '13px', color: '#fff', cursor: 'pointer', fontWeight: 600 }}>
          Enable automated morning CSV email delivery
        </label>
      </div>

      {/* Email Actions */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Saving Settings...' : '💾 Save Email Destination'}
        </button>
        <button className="btn btn-cyan" onClick={handleSendTestEmail} disabled={isTesting}>
          {isTesting ? '📧 Dispatching Test Email...' : '⚡ Send Test Export to My Email'}
        </button>
      </div>
    </div>
  );
}
