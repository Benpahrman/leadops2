import React from 'react';

export default function ScrapersTab({
  loadScrapers,
  scrapersLoading = false,
  scrapers = [],
  handleRunScraper,
  handleViewCode,
  handleViewOutput,
  actionInProgress = {},
}) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Production Municipal Extractors, Python Crawler Source Code, and Real-time Output Records
        </p>
        <button className="btn btn-outline" onClick={loadScrapers}>
          🔄 Refresh Catalog
        </button>
      </div>

      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Municipal Feed / Identifier</th>
              <th>Category / Portal</th>
              <th>Target Source URL</th>
              <th>Dataset Records</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {scrapersLoading ? (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                  Loading scraper catalog...
                </td>
              </tr>
            ) : scrapers.length === 0 ? (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                  No scrapers in catalog. Run a dev swarm to generate extractors.
                </td>
              </tr>
            ) : (
              scrapers.map((s) => (
                <tr key={s.lead_id || s.id}>
                  <td>
                    <div style={{ fontWeight: 700, color: '#fff' }}>{s.company_name || s.name || s.lead_id}</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{s.lead_id || s.id}</div>
                  </td>
                  <td>
                    <span className="badge-tag">{s.category || s.niche || 'Public Records'}</span>
                  </td>
                  <td>
                    {s.source_url ? (
                      <a
                        href={s.source_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: 'var(--cyan)', fontSize: '12px', textDecoration: 'underline' }}
                      >
                        {s.source_url.slice(0, 45)}...
                      </a>
                    ) : (
                      <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>—</span>
                    )}
                  </td>
                  <td>
                    <span style={{ fontWeight: 700, color: 'var(--green)' }}>
                      {s.records_count !== undefined ? `${s.records_count} records` : 'Live Dataset'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: '6px' }}>
                      <button
                        className="btn btn-primary"
                        style={{ padding: '4px 10px', fontSize: '11px' }}
                        onClick={() => handleRunScraper(s.lead_id || s.id)}
                        disabled={actionInProgress[s.lead_id || s.id]}
                      >
                        ⚡ Run
                      </button>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '4px 8px', fontSize: '11px' }}
                        onClick={() => handleViewCode(s.lead_id || s.id, s.company_name)}
                      >
                        💻 Python Code
                      </button>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '4px 8px', fontSize: '11px' }}
                        onClick={() => handleViewOutput(s.lead_id || s.id, s.company_name)}
                      >
                        📊 Output Data
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
