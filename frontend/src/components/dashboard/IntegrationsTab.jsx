import React, { useState, useEffect } from 'react';
import {
  saveDestinations,
  testDestinationPing,
  fetchGoogleSheetsInfo,
  sendEmailExport,
  rotateFeedToken,
} from '../../services/api';
import { useToast } from '../../context/ToastContext';

import {
  LiveFeedSection,
  GoogleSheetsSection,
  WebhookSection,
  AirtableNotionSection,
  EmailCsvSection,
  DirectDownloadSection,
  TestResultBanner,
} from './integrations';

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
      .catch((err) => {
        console.debug('Google Sheets info fetch fallback:', err);
      });
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
        showToast('Webhook endpoint verified!', 'success');
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
      showToast('Please enter Airtable Base ID, Table Name, and Personal Access Token', 'warning');
      return;
    }
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testDestinationPing(
        leadId,
        'airtable',
        { airtable_base_id: airtableBaseId, airtable_table_name: airtableTableName, airtable_api_key: airtableApiKey },
        token
      );
      setTestResult({
        type: 'airtable',
        ok: res.ok,
        message: res.message,
        details: res,
      });
      if (res.ok) {
        showToast('Airtable table verified and connected!', 'success');
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
          {[
            { id: 'live_feed', label: '🌐 Live Feed URL' },
            { id: 'google_sheets', label: '📊 Google Sheets' },
            { id: 'webhook', label: '⚡ Webhooks & Zapier' },
            { id: 'airtable', label: '📑 Airtable' },
            { id: 'notion', label: '📓 Notion' },
            { id: 'email_csv', label: '📧 Email CSV' },
            { id: 'direct_download', label: '💾 File Downloads' },
          ].map((tab) => (
            <button
              key={tab.id}
              className={`btn ${activeTab === tab.id ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => { setActiveTab(tab.id); setTestResult(null); }}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px' }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Dynamic Section Rendering */}
        {activeTab === 'live_feed' && (
          <LiveFeedSection
            importDataFormula={importDataFormula}
            liveCsvFeedUrl={liveCsvFeedUrl}
            liveJsonFeedUrl={liveJsonFeedUrl}
            currentFeedToken={currentFeedToken}
            isRotatingToken={isRotatingToken}
            handleCopy={handleCopy}
            handleRotateFeedToken={handleRotateFeedToken}
          />
        )}

        {activeTab === 'google_sheets' && (
          <GoogleSheetsSection
            sheetUrl={sheetUrl}
            setSheetUrl={setSheetUrl}
            sheetsInfo={sheetsInfo}
            showAppsScript={showAppsScript}
            setShowAppsScript={setShowAppsScript}
            isSaving={isSaving}
            isTesting={isTesting}
            handleCopy={handleCopy}
            handleSave={handleSave}
            handleTestGoogleSheets={handleTestGoogleSheets}
          />
        )}

        {activeTab === 'webhook' && (
          <WebhookSection
            webhookUrl={webhookUrl}
            setWebhookUrl={setWebhookUrl}
            webhookPreset={webhookPreset}
            setWebhookPreset={setWebhookPreset}
            webhookSecret={webhookSecret}
            setWebhookSecret={setWebhookSecret}
            isSaving={isSaving}
            isTesting={isTesting}
            handleSave={handleSave}
            handleTestWebhook={handleTestWebhook}
          />
        )}

        {(activeTab === 'airtable' || activeTab === 'notion') && (
          <AirtableNotionSection
            activeTab={activeTab}
            airtableBaseId={airtableBaseId}
            setAirtableBaseId={setAirtableBaseId}
            airtableTableName={airtableTableName}
            setAirtableTableName={setAirtableTableName}
            airtableApiKey={airtableApiKey}
            setAirtableApiKey={setAirtableApiKey}
            notionDbId={notionDbId}
            setNotionDbId={setNotionDbId}
            notionToken={notionToken}
            setNotionToken={setNotionToken}
            isSaving={isSaving}
            isTesting={isTesting}
            handleSave={handleSave}
            handleTestAirtable={handleTestAirtable}
            handleTestNotion={handleTestNotion}
          />
        )}

        {activeTab === 'email_csv' && (
          <EmailCsvSection
            emailRecipient={emailRecipient}
            setEmailRecipient={setEmailRecipient}
            emailEnabled={emailEnabled}
            setEmailEnabled={setEmailEnabled}
            isSaving={isSaving}
            isTesting={isTesting}
            handleSave={handleSave}
            handleSendTestEmail={handleSendTestEmail}
          />
        )}

        {activeTab === 'direct_download' && (
          <DirectDownloadSection leadId={leadId} />
        )}

        {/* Diagnostic Test Result Banner */}
        <TestResultBanner testResult={testResult} />
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
