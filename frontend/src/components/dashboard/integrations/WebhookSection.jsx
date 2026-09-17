import React from 'react';

export default function WebhookSection({
  webhookUrl,
  setWebhookUrl,
  webhookPreset,
  setWebhookPreset,
  webhookSecret,
  setWebhookSecret,
  isSaving,
  isTesting,
  handleSave,
  handleTestWebhook,
}) {
  return (
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
  );
}
