import React, { useState, useEffect } from 'react';
import {
  saveDestinations,
  testDestinationPing,
  fetchGoogleSheetsInfo,
  sendEmailExport,
  exportJsonData,
} from '../../services/api';
import { useToast } from '../../context/ToastContext';

export default function IntegrationsTab({ leadId, dashState, onRefresh, token = '' }) {
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState(
    dashState?.destination?.webhook_url
      ? 'webhook'
      : dashState?.destination?.type === 'email_csv'
      ? 'email_csv'
      : 'google_sheets'
  );

  // Form State
  const [sheetUrl, setSheetUrl] = useState(dashState?.destination?.google_sheet_url || '');
  const [webhookUrl, setWebhookUrl] = useState(dashState?.destination?.webhook_url || '');
  const [webhookSecret, setWebhookSecret] = useState(dashState?.destination?.webhook_secret || '');
  const [emailRecipient, setEmailRecipient] = useState(
    dashState?.destination?.email_csv_recipient || dashState?.contact_email || ''
  );
  const [emailEnabled, setEmailEnabled] = useState(dashState?.destination?.email_csv_enabled ?? true);

  // UI / Testing State
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showAppsScript, setShowAppsScript] = useState(false);
  const [sheetsInfo, setSheetsInfo] = useState({
    service_account_active: false,
    service_account_email: 'service@omnileadfeeder.tech',
    apps_script_template: '',
  });

  useEffect(() => {
    fetchGoogleSheetsInfo()
      .then((data) => {
        if (data) setSheetsInfo(data);
      })
      .catch(() => {});
  }, []);

  const handleCopy = (text, label) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      showToast(`Copied ${label} to clipboard!`, 'success');
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveDestinations(
        leadId,
        {
          destination_type: activeTab === 'direct_download' ? 'google_sheets' : activeTab,
          google_sheet_url: sheetUrl,
          webhook_url: webhookUrl,
          webhook_secret: webhookSecret,
          email_csv_enabled: emailEnabled,
          email_csv_recipient: emailRecipient,
        },
        token
      );
      showToast('Delivery destination settings saved successfully!', 'success');
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast(`Error saving destinations: ${err.message}`, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestGoogleSheets = async () => {
    if (!sheetUrl) {
      showToast('Please enter a Google Sheet URL first', 'warning');
      return;
    }
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testDestinationPing(leadId, 'google_sheets', { url: sheetUrl }, token);
      setTestResult({
        type: 'google_sheets',
        ok: res.ok,
        message: res.message,
        details: res,
      });
      if (res.ok) {
        showToast('Google Sheet connection verified!', 'success');
      } else {
        showToast(`Verification issue: ${res.message}`, 'warning');
      }
    } catch (err) {
      setTestResult({
        type: 'google_sheets',
        ok: false,
        message: err.message,
      });
      showToast(`Test failed: ${err.message}`, 'error');
    } finally {
      setIsTesting(false);
    }
  };

  const handleTestWebhook = async () => {
    if (!webhookUrl) {
      showToast('Please enter a Webhook URL first', 'warning');
      return;
    }
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testDestinationPing(
        leadId,
        'webhook',
        { url: webhookUrl, secret: webhookSecret },
        token
      );
      setTestResult({
        type: 'webhook',
        ok: res.ok,
        message: res.message,
        details: res,
      });
      if (res.ok) {
        showToast(`Webhook verified! Received HTTP ${res.status_code || 200}`, 'success');
      } else {
        showToast(`Webhook issue: ${res.message}`, 'warning');
      }
    } catch (err) {
      setTestResult({
        type: 'webhook',
        ok: false,
        message: err.message,
      });
      showToast(`Test failed: ${err.message}`, 'error');
    } finally {
      setIsTesting(false);
    }
  };

  const handleSendTestEmail = async () => {
    if (!emailRecipient) {
      showToast('Please enter an email address for export', 'warning');
      return;
    }
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await sendEmailExport(leadId, emailRecipient, token);
      setTestResult({
        type: 'email_csv',
        ok: res.ok,
        message: res.message,
        details: res,
      });
      showToast(`Data export emailed to ${emailRecipient}!`, 'success');
    } catch (err) {
      setTestResult({
        type: 'email_csv',
        ok: false,
        message: err.message,
      });
      showToast(`Email export error: ${err.message}`, 'error');
    } finally {
      setIsTesting(false);
    }
  };

  const handleDirectDownloadCsv = () => {
    const records = dashState?.sample_records || dashState?.records || [];
    if (records.length === 0) {
      showToast('No records available to download yet.', 'info');
      return;
    }
    const headers = Object.keys(records[0]);
    const csvLines = [headers.join(',')];
    records.forEach((row) => {
      const line = headers.map((h) => `"${String(row[h] ?? '').replace(/"/g, '""')}"`);
      csvLines.push(line.join(','));
    });
    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `leadops_${leadId}_data_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('CSV downloaded successfully!', 'success');
  };

  const handleDirectDownloadJson = async () => {
    try {
      const data = await exportJsonData(leadId, token);
      const records = data.records || dashState?.sample_records || [];
      const jsonStr = JSON.stringify(records, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `leadops_${leadId}_data_export.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast('JSON export downloaded successfully!', 'success');
    } catch (err) {
      showToast(`Download failed: ${err.message}`, 'error');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Primary Integration Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: '0 0 6px 0' }}>
              🚀 Live Data Export &amp; Automated Delivery Channels
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
              Route verified daily records directly into your workflow tools every morning at 06:00 AM UTC.
            </p>
          </div>
          <span className="badge-tag badge-green" style={{ fontSize: '11px', padding: '4px 10px' }}>
            ● Zero Mock Data • Real-Time Pipeline
          </span>
        </div>

        {/* Multi-Channel Navigation Tabs */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '24px', borderBottom: '1px solid var(--border-light)', paddingBottom: '16px' }}>
          <button
            className={`btn ${activeTab === 'google_sheets' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('google_sheets'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            📊 Google Sheets
          </button>
          <button
            className={`btn ${activeTab === 'webhook' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('webhook'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            ⚡ Webhook (HTTP POST)
          </button>
          <button
            className={`btn ${activeTab === 'email_csv' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('email_csv'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            📧 Email CSV Delivery
          </button>
          <button
            className={`btn ${activeTab === 'direct_download' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('direct_download'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            💾 Instant File Download
          </button>
        </div>

        {/* TAB 1: GOOGLE SHEETS */}
        {activeTab === 'google_sheets' && (
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
                  <li>Copy your Web App URL and paste it in the <b>Webhook (HTTP POST)</b> tab!</li>
                </ol>
                <pre style={{ background: '#0b1329', padding: '12px', borderRadius: '6px', fontSize: '11px', color: 'var(--cyan)', overflowX: 'auto', maxHeight: '200px' }}>
                  {sheetsInfo.apps_script_template}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: WEBHOOK */}
        {activeTab === 'webhook' && (
          <div>
            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                Webhook Endpoint URL (HTTP POST)
              </label>
              <input
                type="url"
                className="form-input"
                placeholder="https://api.yourdomain.com/v1/leadops/webhook or https://script.google.com/macros/s/.../exec"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                style={{ width: '100%', fontSize: '13px' }}
              />
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                We'll transmit batched JSON payloads containing record objects immediately after each extraction run.
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                HMAC-SHA256 Secret Key (Optional Security Signature)
              </label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. whsec_9a87bf91c2..."
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                style={{ width: '100%', fontSize: '13px', fontFamily: 'var(--mono)' }}
              />
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                If specified, every POST request includes <code>X-LeadOps-Signature</code> and <code>X-LeadOps-Timestamp</code> headers for payload verification.
              </div>
            </div>

            {/* Webhook Actions */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '20px' }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                {isSaving ? 'Saving Settings...' : '💾 Save Webhook Destination'}
              </button>
              <button className="btn btn-cyan" onClick={handleTestWebhook} disabled={isTesting}>
                {isTesting ? '⚡ Sending Live Ping...' : '⚡ Send Test Webhook Payload'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 3: EMAIL CSV DELIVERY */}
        {activeTab === 'email_csv' && (
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
        )}

        {/* TAB 4: DIRECT FILE DOWNLOAD */}
        {activeTab === 'direct_download' && (
          <div>
            <div style={{ background: 'var(--card-alt)', borderRadius: '10px', padding: '20px', border: '1px solid var(--border-light)', marginBottom: '20px' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#fff', margin: '0 0 8px 0' }}>
                📥 Instant One-Click Data Download
              </h4>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, margin: '0 0 16px 0' }}>
                Download your full verified dataset directly to your device in your format of choice.
              </p>
              <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
                <button className="btn btn-primary" onClick={handleDirectDownloadCsv}>
                  📊 Download CSV Spreadsheet
                </button>
                <button className="btn btn-outline" onClick={handleDirectDownloadJson}>
                  📦 Download JSON Dataset
                </button>
              </div>
            </div>
          </div>
        )}

        {/* DIAGNOSTIC TEST RESULT BOX */}
        {testResult && (
          <div
            style={{
              marginTop: '24px',
              padding: '16px',
              borderRadius: '8px',
              border: `1px solid ${testResult.ok ? 'var(--green)' : 'var(--red)'}`,
              background: testResult.ok ? 'rgba(34, 197, 94, 0.08)' : 'rgba(239, 68, 68, 0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontWeight: 700, fontSize: '13px', color: testResult.ok ? 'var(--green)' : 'var(--red)' }}>
                {testResult.ok ? '✓ Verification Handshake Succeeded' : '✕ Connection Diagnostic Notice'}
              </span>
              {testResult.details?.latency_ms !== undefined && (
                <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--cyan)' }}>
                  Latency: {testResult.details.latency_ms}ms
                </span>
              )}
            </div>
            <div style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: 1.5 }}>
              {testResult.message}
            </div>
            {testResult.details?.response_preview && (
              <div style={{ marginTop: '10px', padding: '8px', background: '#0b1329', borderRadius: '4px', fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--text-dim)' }}>
                Response Body Preview: {testResult.details.response_preview}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Cadence Info Card */}
      <div className="card">
        <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
          ⏰ Automated SLA Delivery Cadence
        </h4>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.6, margin: 0 }}>
          Autonomous crawlers execute daily starting at <b>06:00 AM UTC</b>. Records are schema-verified, deduplicated, and dispatched to your active destinations before the <b>08:00 AM UTC SLA deadline</b>.
        </p>
      </div>
    </div>
  );
}
