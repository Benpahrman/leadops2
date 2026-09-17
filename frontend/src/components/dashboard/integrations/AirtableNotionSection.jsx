import React from 'react';

export default function AirtableNotionSection({
  activeTab,
  airtableBaseId,
  setAirtableBaseId,
  airtableTableName,
  setAirtableTableName,
  airtableApiKey,
  setAirtableApiKey,
  notionDbId,
  setNotionDbId,
  notionToken,
  setNotionToken,
  isSaving,
  isTesting,
  handleSave,
  handleTestAirtable,
  handleTestNotion,
}) {
  if (activeTab === 'airtable') {
    return (
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
    );
  }

  if (activeTab === 'notion') {
    return (
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
    );
  }

  return null;
}
