import React from 'react';

export default function LiveFeedSection({
  importDataFormula,
  liveCsvFeedUrl,
  liveJsonFeedUrl,
  currentFeedToken,
  isRotatingToken,
  handleCopy,
  handleRotateFeedToken,
}) {
  return (
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
      <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>
            🔒 Feed Security Key: <code style={{ color: 'var(--cyan)' }}>{currentFeedToken.slice(0, 14)}...</code>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
            Rotates automatically if compromised.
          </div>
        </div>
        <button
          className="btn btn-outline"
          onClick={handleRotateFeedToken}
          disabled={isRotatingToken}
          style={{ fontSize: '12px' }}
        >
          {isRotatingToken ? '⏳ Rotating...' : '🔄 Rotate Feed Token'}
        </button>
      </div>
    </div>
  );
}
