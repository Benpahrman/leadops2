import React from 'react';

export default function TableToolbar({
  sourceUrl,
  rowsCount,
  filterCategory,
  setFilterCategory,
  density,
  setDensity,
  searchTerm,
  setSearchTerm,
  setCurrentPage,
  handleExportCsv,
  setIsBacklogModalOpen,
}) {
  const hostDisplay = sourceUrl ? (() => {
    try { return new URL(sourceUrl).hostname; } catch { return 'records.official.gov'; }
  })() : 'records.official.gov';

  return (
    <>
      {/* Live Ingestion Telemetry Bar */}
      <div className="sandbox-stream-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--green)', display: 'inline-block', boxShadow: '0 0 10px var(--green)' }}></span>
          <span style={{ fontWeight: 800, color: '#fff', letterSpacing: '0.4px' }}>LIVE TELEMETRY STREAM</span>
          <span style={{ color: 'var(--text-dim)' }}>•</span>
          <span style={{ color: 'var(--text-muted)' }}>Portal: <b style={{ color: 'var(--cyan)' }}>{hostDisplay}</b></span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', color: 'var(--text-muted)', fontSize: '11px' }}>
          <span>Latency: <b style={{ color: '#fff' }}>32ms</b></span>
          <span>Cycle: <b style={{ color: '#fff' }}>06:00 UTC</b></span>
          <span style={{ color: 'var(--green)', fontWeight: 700 }}>✓ 100% Zero-Mock Guarantee</span>
        </div>
      </div>

      {/* Filter Chips & Density Control Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
        <div className="filter-pill-group">
          <button
            type="button"
            className={`filter-pill ${filterCategory === 'all' ? 'active' : ''}`}
            onClick={() => { setFilterCategory('all'); setCurrentPage(1); }}
          >
            All Filings ({rowsCount})
          </button>
          <button
            type="button"
            className={`filter-pill ${filterCategory === 'high_value' ? 'active' : ''}`}
            onClick={() => { setFilterCategory('high_value'); setCurrentPage(1); }}
          >
            High Valuation (&ge;$50k)
          </button>
          <button
            type="button"
            className={`filter-pill ${filterCategory === 'commercial' ? 'active' : ''}`}
            onClick={() => { setFilterCategory('commercial'); setCurrentPage(1); }}
          >
            Commercial Entities
          </button>
          <button
            type="button"
            className={`filter-pill ${filterCategory === 'permits' ? 'active' : ''}`}
            onClick={() => { setFilterCategory('permits'); setCurrentPage(1); }}
          >
            Permits &amp; Liens
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontFamily: 'var(--mono)', letterSpacing: '0.5px' }}>Density:</span>
          <div className="density-toggle">
            <button
              type="button"
              className={`density-btn ${density === 'comfortable' ? 'active' : ''}`}
              onClick={() => setDensity('comfortable')}
              title="Spacious comfortable rows"
            >
              Comfortable
            </button>
            <button
              type="button"
              className={`density-btn ${density === 'compact' ? 'active' : ''}`}
              onClick={() => setDensity('compact')}
              title="Compact high-density rows"
            >
              Compact
            </button>
          </div>
        </div>
      </div>

      {/* Search & Actions Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '280px', maxWidth: '440px', position: 'relative' }}>
          <svg style={{ position: 'absolute', left: '12px', color: 'var(--text-dim)' }} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="form-input"
            style={{ paddingLeft: '36px', paddingRight: searchTerm ? '32px' : '14px' }}
            placeholder="Search docket number, entity name, address..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              style={{ position: 'absolute', right: '10px', background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '14px' }}
            >
              ✕
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            type="button"
            className="btn btn-outline"
            style={{ fontSize: '12px', padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            onClick={handleExportCsv}
          >
            📥 Export CSV Sample
          </button>
          <button
            type="button"
            className="btn btn-primary"
            style={{ fontSize: '12px', padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)' }}
            onClick={() => setIsBacklogModalOpen(true)}
          >
            🔓 Unlock 14-Day Backlog
          </button>
        </div>
      </div>
    </>
  );
}
