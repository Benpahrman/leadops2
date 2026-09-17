import React from 'react';

export default function GoogleSheetsSection({
  sheetUrl,
  setSheetUrl,
  sheetsInfo,
  showAppsScript,
  setShowAppsScript,
  isSaving,
  isTesting,
  handleCopy,
  handleSave,
  handleTestGoogleSheets,
}) {
  return (
    <div>
      <div style={{ background: 'rgba(14, 165, 233, 0.08)', border: '1px solid rgba(14, 165, 233, 0.25)', borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--cyan)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              1. Share Your Google Sheet
            </div>
            <div style={{ fontSize: '13px', color: '#e2e8f0', marginTop: '4px' }}>
              Grant <b>Editor</b> access in your Google Sheet to our automated sync identity:
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '13px', color: 'var(--cyan)', fontWeight: 700, marginTop: '4px' }}>
              {sheetsInfo.service_account_email}
            </div>
          </div>
          <button
            className="btn btn-outline btn-sm"
            onClick={() => handleCopy(sheetsInfo.service_account_email, 'Service Account Email')}
            style={{ whiteSpace: 'nowrap' }}
          >
            📋 Copy Service Email
          </button>
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
          2. Target Google Sheet URL
        </label>
        <input
          type="url"
          className="form-input"
          placeholder="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
          value={sheetUrl}
          onChange={(e) => setSheetUrl(e.target.value)}
          style={{ width: '100%', fontSize: '13px' }}
        />
        <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
          Paste the full URL from your browser's address bar. We'll automatically identify the sheet and append new rows each morning.
        </div>
      </div>

      {/* Google Sheets Actions */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '20px' }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
          {isSaving ? 'Saving Settings...' : '💾 Save Google Sheet Destination'}
        </button>
        <button className="btn btn-cyan" onClick={handleTestGoogleSheets} disabled={isTesting}>
          {isTesting ? '⚡ Verifying Connection...' : '⚡ Test Google Sheet Handshake'}
        </button>
        <button
          className="btn btn-outline"
          onClick={() => setShowAppsScript(!showAppsScript)}
        >
          {showAppsScript ? 'Hide Apps Script Webhook Fallback' : '⚡ Use Apps Script Webhook Fallback'}
        </button>
      </div>

      {/* Expandable Apps Script Fallback */}
      {showAppsScript && (
        <div style={{ marginTop: '20px', background: 'var(--card-alt)', border: '1px solid var(--border-light)', borderRadius: '10px', padding: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ fontWeight: 700, color: '#fff', fontSize: '14px' }}>
              🛠️ Zero-Config Apps Script Webhook Receiver
            </div>
            <button
              className="btn btn-outline btn-sm"
              onClick={() => handleCopy(sheetsInfo.apps_script_template || '', 'Google Apps Script')}
            >
              📋 Copy Script Code
            </button>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '12px' }}>
            If you do not wish to share your sheet with a service account, you can deploy this lightweight Google Apps Script Web App in 30 seconds:
          </p>
          <ol style={{ fontSize: '12px', color: 'var(--text-muted)', paddingLeft: '20px', lineHeight: 1.7, margin: '0 0 14px 0' }}>
            <li>Open your Google Sheet → Go to <b>Extensions → Apps Script</b>.</li>
            <li>Replace all contents with the code below and click <b>Save</b>.</li>
            <li>Click <b>Deploy → New deployment</b> → Select type: <b>Web app</b>.</li>
            <li>Set <i>'Execute as: Me'</i> and <i>'Who has access: Anyone'</i>, then click <b>Deploy</b>.</li>
            <li>Copy your Web App URL and paste it in the <b>Webhook</b> tab!</li>
          </ol>
          <pre style={{ background: '#0b1329', padding: '12px', borderRadius: '6px', fontSize: '11px', color: 'var(--cyan)', overflowX: 'auto', maxHeight: '200px' }}>
            {sheetsInfo.apps_script_template}
          </pre>
        </div>
      )}
    </div>
  );
}
