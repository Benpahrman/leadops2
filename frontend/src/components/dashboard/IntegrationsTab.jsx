import React, { useState, useEffect } from 'react';
import {
  saveDestinations,
  testDestinationPing,
  fetchGoogleSheetsInfo,
  sendEmailExport,
  exportJsonData,
  rotateFeedToken,
} from '../../services/api';
import { useToast } from '../../context/ToastContext';

export default function IntegrationsTab({ leadId, dashState, onRefresh, token = '' }) {
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState(
    dashState?.destination?.airtable_base_id
      ? 'airtable'
      : dashState?.destination?.notion_database_id
      ? 'notion'
      : dashState?.destination?.webhook_url
      ? 'webhook'
      : dashState?.destination?.type === 'email_csv'
      ? 'email_csv'
      : 'live_feed'
  );

  // Destination Form State
  const [sheetUrl, setSheetUrl] = useState(dashState?.destination?.google_sheet_url || '');
  const [webhookUrl, setWebhookUrl] = useState(dashState?.destination?.webhook_url || '');
  const [webhookSecret, setWebhookSecret] = useState(dashState?.destination?.webhook_secret || '');
  const [webhookPreset, setWebhookPreset] = useState(dashState?.destination?.webhook_preset || 'standard');
  const [emailRecipient, setEmailRecipient] = useState(
    dashState?.destination?.email_csv_recipient || dashState?.contact_email || ''
  );
  const [emailEnabled, setEmailEnabled] = useState(dashState?.destination?.email_csv_enabled ?? true);
  const [airtableBaseId, setAirtableBaseId] = useState(dashState?.destination?.airtable_base_id || '');
  const [airtableTableName, setAirtableTableName] = useState(dashState?.destination?.airtable_table_name || '');
  const [airtableApiKey, setAirtableApiKey] = useState(dashState?.destination?.airtable_api_key || '');
  const [notionDbId, setNotionDbId] = useState(dashState?.destination?.notion_database_id || '');
  const [notionToken, setNotionToken] = useState(dashState?.destination?.notion_integration_token || '');

  // Feed Token State
  const [feedToken, setFeedToken] = useState(dashState?.destination?.feed_token || '');
  const [isRotatingToken, setIsRotatingToken] = useState(false);

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

  const handleRotateFeedToken = async () => {
    if (!window.confirm('Are you sure you want to rotate your Live Feed Token? Any previous Google Sheets formulas or PowerBI queries using the old token will stop updating until replaced.')) {
      return;
    }
    setIsRotatingToken(true);
    try {
      const res = await rotateFeedToken(leadId, token);
      setFeedToken(res.feed_token);
      showToast('Live Feed Token rotated successfully!', 'success');
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast(`Failed rotating feed token: ${err.message}`, 'error');
    } finally {
      setIsRotatingToken(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveDestinations(
        leadId,
        {
          destination_type: activeTab === 'direct_download' || activeTab === 'live_feed' ? 'google_sheets' : activeTab,
          google_sheet_url: sheetUrl,
          webhook_url: webhookUrl,
          webhook_secret: webhookSecret,
          webhook_preset: webhookPreset,
          email_csv_enabled: emailEnabled,
          email_csv_recipient: emailRecipient,
          airtable_base_id: airtableBaseId,
          airtable_table_name: airtableTableName,
          airtable_api_key: airtableApiKey,
          notion_database_id: notionDbId,
          notion_integration_token: notionToken,
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
      const res = await testDestinationPing(leadId, 'google_sheets', { google_sheet_url: sheetUrl }, token);
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
        { webhook_url: webhookUrl, webhook_secret: webhookSecret, webhook_preset: webhookPreset },
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

  const handleTestAirtable = async () => {
    if (!airtableApiKey || !airtableBaseId || !airtableTableName) {
      showToast('Please enter Airtable Token, Base ID, and Table Name', 'warning');
      return;
    }
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testDestinationPing(
        leadId,
        'airtable',
        { airtable_api_key: airtableApiKey, airtable_base_id: airtableBaseId, airtable_table_name: airtableTableName },
        token
      );
      setTestResult({
        type: 'airtable',
        ok: res.ok,
        message: res.message,
        details: res,
      });
      if (res.ok) {
        showToast('Airtable table verified and accessible!', 'success');
      } else {
        showToast(`Airtable issue: ${res.message}`, 'warning');
      }
    } catch (err) {
      setTestResult({
        type: 'airtable',
        ok: false,
        message: err.message,
      });
      showToast(`Test failed: ${err.message}`, 'error');
    } finally {
      setIsTesting(false);
    }
  };

  const handleTestNotion = async () => {
    if (!notionToken || !notionDbId) {
      showToast('Please enter Notion Integration Secret and Database ID', 'warning');
      return;
    }
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testDestinationPing(
        leadId,
        'notion',
        { notion_integration_token: notionToken, notion_database_id: notionDbId },
        token
      );
      setTestResult({
        type: 'notion',
        ok: res.ok,
        message: res.message,
        details: res,
      });
      if (res.ok) {
        showToast('Notion database verified and connected!', 'success');
      } else {
        showToast(`Notion issue: ${res.message}`, 'warning');
      }
    } catch (err) {
      setTestResult({
        type: 'notion',
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

  const appBaseUrl = typeof window !== 'undefined' ? window.location.origin : 'https://omnileadfeeder.tech';
  const currentFeedToken = feedToken || dashState?.destination?.feed_token || 'tok_live_feed';
  const liveCsvFeedUrl = `${appBaseUrl}/api/feed/${currentFeedToken}/records.csv`;
  const liveJsonFeedUrl = `${appBaseUrl}/api/feed/${currentFeedToken}/records.json`;
  const importDataFormula = `=IMPORTDATA("${liveCsvFeedUrl}")`;

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
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '24px', borderBottom: '1px solid var(--border-light)', paddingBottom: '16px' }}>
          <button
            className={`btn ${activeTab === 'live_feed' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('live_feed'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          >
            🌐 Live Feed URL
          </button>
          <button
            className={`btn ${activeTab === 'google_sheets' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('google_sheets'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          >
            📊 Google Sheets
          </button>
          <button
            className={`btn ${activeTab === 'webhook' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('webhook'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          >
            ⚡ Webhooks &amp; Zapier
          </button>
          <button
            className={`btn ${activeTab === 'airtable' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('airtable'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          >
            📑 Airtable
          </button>
          <button
            className={`btn ${activeTab === 'notion' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('notion'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          >
            📓 Notion
          </button>
          <button
            className={`btn ${activeTab === 'email_csv' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('email_csv'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          >
            📧 Email CSV
          </button>
          <button
            className={`btn ${activeTab === 'direct_download' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => { setActiveTab('direct_download'); setTestResult(null); }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
          >
            💾 File Downloads
          </button>
        </div>

        {/* TAB 0: LIVE FEED URL (=IMPORTDATA & BI) */}
        {activeTab === 'live_feed' && (
          <div>
            <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.25)', borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#38bdf8', marginBottom: '4px' }}>
                🌐 Zero-Config Live Feed Ingestion (Google Sheets, PowerBI, Tableau, Retool)
              </div>
              <p style={{ fontSize: '13px', color: '#cbd5e1', margin: 0, lineHeight: 1.6 }}>
                Paste the formula below into cell <b>A1</b> of any Google Sheet. It will automatically load and refresh your latest scraped records with <b>0 Google Cloud setup</b> required.
              </p>
            </div>

            {/* Google Sheets Formula */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                1. Google Sheets =IMPORTDATA() Formula (Instant Auto-Sync)
              </label>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <input
                  type="text"
                  readOnly
                  className="form-input"
                  value={importDataFormula}
                  style={{ width: '100%', fontFamily: 'var(--mono)', fontSize: '12px', background: '#0b1329', color: 'var(--cyan)' }}
                />
                <button
                  className="btn btn-primary"
                  onClick={() => handleCopy(importDataFormula, 'Google Sheets Formula')}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  📋 Copy Formula
                </button>
              </div>
            </div>

            {/* Live CSV URL */}
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                2. Live CSV Feed Endpoint (PowerBI Web Source, Tableau, Excel Web Query)
              </label>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <input
                  type="text"
                  readOnly
                  className="form-input"
                  value={liveCsvFeedUrl}
                  style={{ width: '100%', fontFamily: 'var(--mono)', fontSize: '12px', background: '#0b1329', color: '#94a3b8' }}
                />
                <button
                  className="btn btn-outline"
                  onClick={() => handleCopy(liveCsvFeedUrl, 'Live CSV URL')}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  📋 Copy CSV URL
                </button>
              </div>
            </div>

            {/* Live JSON URL */}
            <div style={{ marginBottom: '24px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                3. Live REST JSON Feed Endpoint (Custom Apps, CRMs &amp; Scripts)
              </label>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <input
                  type="text"
                  readOnly
                  className="form-input"
                  value={liveJsonFeedUrl}
                  style={{ width: '100%', fontFamily: 'var(--mono)', fontSize: '12px', background: '#0b1329', color: '#94a3b8' }}
                />
                <button
                  className="btn btn-outline"
                  onClick={() => handleCopy(liveJsonFeedUrl, 'Live JSON URL')}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  📋 Copy JSON URL
                </button>
              </div>
            </div>

            {/* Feed Token Security & Rotation */}
            <div style={{ background: 'var(--card-alt)', border: '1px solid var(--border-light)', borderRadius: '10px', padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>
                  🔒 Live Feed Token Security
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  Active Token: <code style={{ color: 'var(--cyan)' }}>{currentFeedToken}</code>
                </div>
              </div>
              <button
                className="btn btn-outline btn-sm"
                onClick={handleRotateFeedToken}
                disabled={isRotatingToken}
                style={{ color: '#f59e0b', borderColor: '#f59e0b' }}
              >
                {isRotatingToken ? 'Rotating Token...' : '🔄 Rotate / Revoke Secret Token'}
              </button>
            </div>
          </div>
        )}

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
                  <li>Copy your Web App URL and paste it in the <b>Webhook</b> tab!</li>
                </ol>
                <pre style={{ background: '#0b1329', padding: '12px', borderRadius: '6px', fontSize: '11px', color: 'var(--cyan)', overflowX: 'auto', maxHeight: '200px' }}>
                  {sheetsInfo.apps_script_template}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: WEBHOOK & AUTOMATION PRESETS */}
        {activeTab === 'webhook' && (
          <div>
            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                Webhook Endpoint URL (HTTP POST)
              </label>
              <input
                type="url"
                className="form-input"
                placeholder="https://hooks.zapier.com/hooks/catch/... or https://hook.us1.make.com/..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                style={{ width: '100%', fontSize: '13px' }}
              />
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                We'll transmit JSON payloads containing new records immediately after each morning scrape.
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '20px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                  Payload Formatting Preset
                </label>
                <select
                  className="form-input"
                  value={webhookPreset}
                  onChange={(e) => setWebhookPreset(e.target.value)}
                  style={{ width: '100%', fontSize: '13px', background: '#0f172a' }}
                >
                  <option value="standard">Standard LeadOps Schema (Full Metadata)</option>
                  <option value="zapier">Zapier Webhook Catch (Flattened Records)</option>
                  <option value="make">Make.com / Integromat Webhook</option>
                  <option value="n8n">n8n Workflow Trigger</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                  HMAC-SHA256 Secret (Optional)
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. whsec_9a87bf91c2..."
                  value={webhookSecret}
                  onChange={(e) => setWebhookSecret(e.target.value)}
                  style={{ width: '100%', fontSize: '13px', fontFamily: 'var(--mono)' }}
                />
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

        {/* TAB 3: AIRTABLE SYNC */}
        {activeTab === 'airtable' && (
          <div>
            <div style={{ background: 'rgba(234, 88, 12, 0.08)', border: '1px solid rgba(234, 88, 12, 0.25)', borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
              <div style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: 1.6 }}>
                📑 <b>Airtable Direct Sync</b> creates new records in your target Airtable Base table automatically. Generate a Personal Access Token at <a href="https://airtable.com/create/tokens" target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)' }}>airtable.com/create/tokens</a> with scopes <code>data.records:write</code> and <code>schema.bases:read</code>.
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '18px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                  Airtable Base ID (starts with 'app')
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="appXXXXXXXXXXXXXX"
                  value={airtableBaseId}
                  onChange={(e) => setAirtableBaseId(e.target.value)}
                  style={{ width: '100%', fontSize: '13px', fontFamily: 'var(--mono)' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                  Table Name or Table ID
                </label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. LeadOps Feed or tblXXXXXXXXXXXXXX"
                  value={airtableTableName}
                  onChange={(e) => setAirtableTableName(e.target.value)}
                  style={{ width: '100%', fontSize: '13px' }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                Airtable Personal Access Token (PAT)
              </label>
              <input
                type="password"
                className="form-input"
                placeholder="patXXXXXXXXXXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                value={airtableApiKey}
                onChange={(e) => setAirtableApiKey(e.target.value)}
                style={{ width: '100%', fontSize: '13px', fontFamily: 'var(--mono)' }}
              />
            </div>

            {/* Airtable Actions */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                {isSaving ? 'Saving Settings...' : '💾 Save Airtable Destination'}
              </button>
              <button className="btn btn-cyan" onClick={handleTestAirtable} disabled={isTesting}>
                {isTesting ? '⚡ Verifying Airtable...' : '⚡ Test Airtable Connection'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 4: NOTION DATABASE SYNC */}
        {activeTab === 'notion' && (
          <div>
            <div style={{ background: 'rgba(168, 85, 247, 0.08)', border: '1px solid rgba(168, 85, 247, 0.25)', borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
              <div style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: 1.6 }}>
                📓 <b>Notion Database Sync</b> appends daily records as page entries into your Notion Database. Create an internal integration at <a href="https://www.notion.so/my-integrations" target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)' }}>notion.so/my-integrations</a>, then share your Database with that integration.
              </div>
            </div>

            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                Notion Database ID (32-Character Hex)
              </label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. 2b9e119d8544458597f7481b0a82410a"
                value={notionDbId}
                onChange={(e) => setNotionDbId(e.target.value)}
                style={{ width: '100%', fontSize: '13px', fontFamily: 'var(--mono)' }}
              />
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                Found in the share URL of your Notion database (between the workspace name and the <code>?v=</code> query).
              </div>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
                Notion Integration Secret Token
              </label>
              <input
                type="password"
                className="form-input"
                placeholder="secret_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                value={notionToken}
                onChange={(e) => setNotionToken(e.target.value)}
                style={{ width: '100%', fontSize: '13px', fontFamily: 'var(--mono)' }}
              />
            </div>

            {/* Notion Actions */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                {isSaving ? 'Saving Settings...' : '💾 Save Notion Destination'}
              </button>
              <button className="btn btn-cyan" onClick={handleTestNotion} disabled={isTesting}>
                {isTesting ? '⚡ Verifying Notion...' : '⚡ Test Notion Connection'}
              </button>
            </div>
          </div>
        )}

        {/* TAB 5: EMAIL CSV DELIVERY */}
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

        {/* TAB 6: DIRECT FILE DOWNLOAD */}
        {activeTab === 'direct_download' && (
          <div>
            <div style={{ background: 'var(--card-alt)', borderRadius: '10px', padding: '20px', border: '1px solid var(--border-light)', marginBottom: '20px' }}>
              <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#fff', margin: '0 0 8px 0' }}>
                📥 Instant Multi-Format Data Downloads
              </h4>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, margin: '0 0 16px 0' }}>
                Export your full dataset directly in Excel (.xlsx), CSV, JSON, or streaming JSONL formats.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
                <a
                  href={`/api/dashboard/${leadId}/export/xlsx`}
                  download={`leadops_feed_${leadId}.xlsx`}
                  className="btn btn-primary"
                  style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
                >
                  📗 Download Excel (.xlsx)
                </a>
                <a
                  href={`/api/dashboard/${leadId}/export/csv`}
                  download={`leadops_feed_${leadId}.csv`}
                  className="btn btn-cyan"
                  style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
                >
                  📊 Download CSV (.csv)
                </a>
                <a
                  href={`/api/dashboard/${leadId}/export/json`}
                  download={`leadops_feed_${leadId}.json`}
                  className="btn btn-outline"
                  style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
                >
                  📦 Download JSON (.json)
                </a>
                <a
                  href={`/api/dashboard/${leadId}/export/jsonl`}
                  download={`leadops_feed_${leadId}.jsonl`}
                  className="btn btn-outline"
                  style={{ textAlign: 'center', textDecoration: 'none', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}
                >
                  📜 Download JSONL (.jsonl)
                </a>
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
