import React, { useState } from 'react';
import { saveDestinations, testDestinationPing } from '../../services/api';
import { useToast } from '../../context/ToastContext';

export default function IntegrationsTab({ leadId, dashState, onRefresh, token = '' }) {
  const { showToast } = useToast();

  const [destType, setDestType] = useState(
    dashState?.destination?.webhook_url ? 'webhook' : 'google_sheets'
  );
  const [sheetUrl, setSheetUrl] = useState(dashState?.destination?.google_sheet_url || '');
  const [webhookUrl, setWebhookUrl] = useState(dashState?.destination?.webhook_url || '');
  const [isSaving, setIsSaving] = useState(false);
  const [pingResult, setPingResult] = useState('');

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveDestinations(
        leadId,
        {
          destination_type: destType,
          google_sheet_url: sheetUrl,
          webhook_url: webhookUrl,
        },
        token
      );
      showToast('Destination settings saved successfully!', 'success');
      if (onRefresh) onRefresh();
    } catch (err) {
      showToast(`Error saving destinations: ${err.message}`, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestPing = async (type) => {
    setPingResult('⚡ Testing connection handshake...');
    try {
      const data = await testDestinationPing(leadId, type, token);
      setPingResult(`✓ ${data.message || 'Connection test successful! Destination reachable.'}`);
      showToast('Destination ping handshake succeeded!', 'success');
    } catch (err) {
      setPingResult(`✕ Connection failed: ${err.message}`);
      showToast(`Test failed: ${err.message}`, 'error');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="card">
        <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
          🚀 Delivery Destinations &amp; Webhooks
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px' }}>
          Choose where your daily extracted records should be routed every morning at 06:00 AM UTC.
        </p>

        {/* Destination Type Toggle */}
        <div style={{ display: 'flex', gap: '12px', marginBottom: '24px' }}>
          <button
            className={`btn ${destType === 'google_sheets' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setDestType('google_sheets')}
          >
            📊 Google Sheets
          </button>
          <button
            className={`btn ${destType === 'webhook' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setDestType('webhook')}
          >
            ⚡ Webhook (HTTP POST)
          </button>
        </div>

        {destType === 'google_sheets' ? (
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
              Target Google Sheet URL
            </label>
            <input
              type="url"
              className="form-input"
              placeholder="https://docs.google.com/spreadsheets/d/your-sheet-id/edit"
              value={sheetUrl}
              onChange={(e) => setSheetUrl(e.target.value)}
            />
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
              Ensure your Google Sheet is shared with edit access to <b>service@omnileadfeeder.tech</b>.
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                {isSaving ? 'Saving...' : 'Save Google Sheet Destination'}
              </button>
              <button className="btn btn-outline" onClick={() => handleTestPing('google_sheets')}>
                ⚡ Test Google Sheet Handshake
              </button>
            </div>
          </div>
        ) : (
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '8px', color: '#fff' }}>
              Webhook Endpoint URL (JSON Payload)
            </label>
            <input
              type="url"
              className="form-input"
              placeholder="https://api.yourcompany.com/webhooks/records"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
              We'll send an array of JSON record objects signed with an HMAC-SHA256 signature header.
            </div>

            <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
              <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                {isSaving ? 'Saving...' : 'Save Webhook Destination'}
              </button>
              <button className="btn btn-outline" onClick={() => handleTestPing('webhook')}>
                ⚡ Test Webhook Ping
              </button>
            </div>
          </div>
        )}

        {pingResult && (
          <div style={{ marginTop: '20px', padding: '12px', background: 'var(--card-alt)', borderRadius: '8px', border: '1px solid var(--border-light)', fontSize: '12px', color: pingResult.startsWith('✓') ? 'var(--green)' : 'var(--red)', fontFamily: 'var(--mono)' }}>
            {pingResult}
          </div>
        )}
      </div>

      {/* Schedule Info */}
      <div className="card">
        <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
          ⏰ Automated Delivery Cadence
        </h4>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Automated extraction runs daily at <b>06:00 AM UTC</b>. New records are deduplicated against existing dockets and pushed directly to your configured destination.
        </p>
      </div>
    </div>
  );
}
