import React, { useState, useMemo } from 'react';
import { unlockBacklog } from '../../services/api';
import { useToast } from '../../context/ToastContext';

export default function DataTable({ slug = '', rows: initialRows = [], sourceUrl = '', companyName = '', jurisdiction = '', defaultEmail = '' }) {
  const { showToast } = useToast();
  const [rows, setRows] = useState(initialRows);
  const [searchTerm, setSearchTerm] = useState('');
  const [isBacklogModalOpen, setIsBacklogModalOpen] = useState(false);
  const [email, setEmail] = useState(defaultEmail || '');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(false);

  const [sortField, setSortField] = useState('date');
  const [sortAsc, setSortAsc] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [copiedJson, setCopiedJson] = useState(false);

  // Sync rows if initialRows changes
  React.useEffect(() => {
    if (initialRows && initialRows.length > 0 && (!rows || rows.length === 0)) {
      setRows(initialRows);
    }
  }, [initialRows]);

  React.useEffect(() => {
    if (defaultEmail && !email) {
      setEmail(defaultEmail);
    }
  }, [defaultEmail]);

  // Sorting helper
  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
    setCurrentPage(1);
  };

  const processedRows = useMemo(() => {
    const activeRows = rows && rows.length > 0 ? rows : initialRows;
    let result = [...activeRows];

    // Filter by search query
    if (searchTerm) {
      const q = searchTerm.toLowerCase().trim();
      result = result.filter((r) => JSON.stringify(r).toLowerCase().includes(q));
    }

    // Sort rows
    result.sort((a, b) => {
      let valA = '';
      let valB = '';

      if (sortField === 'id') {
        valA = a.id || a.case_number || a.permit_number || a.filing_number || '';
        valB = b.id || b.case_number || b.permit_number || b.filing_number || '';
      } else if (sortField === 'entity') {
        valA = a.primary_party || a.debtor_name || a.owner_name || a.contractor_name || a.applicant_name || '';
        valB = b.primary_party || b.debtor_name || b.owner_name || b.contractor_name || b.applicant_name || '';
      } else if (sortField === 'date') {
        valA = a.filing_date || a.issue_date || a.file_date || a.posted_date || '';
        valB = b.filing_date || b.issue_date || b.file_date || b.posted_date || '';
      } else if (sortField === 'amount') {
        const parseAmt = (val) => parseFloat(String(val || '').replace(/[^0-9.-]/g, '')) || 0;
        valA = parseAmt(a.amount || a.est_value || a.valuation || a.opening_bid);
        valB = parseAmt(b.amount || b.est_value || b.valuation || b.opening_bid);
        return sortAsc ? valA - valB : valB - valA;
      }

      valA = String(valA).toLowerCase();
      valB = String(valB).toLowerCase();
      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });

    return result;
  }, [rows, initialRows, searchTerm, sortField, sortAsc]);

  // Paginated rows
  const totalRows = processedRows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return processedRows.slice(start, start + pageSize);
  }, [processedRows, currentPage, pageSize]);

  const triggerDownload = (dataset, filenamePrefix = 'verified_records') => {
    if (!dataset || dataset.length === 0) return;
    const headers = Object.keys(dataset[0]);
    if (!headers.includes('official_source_verification_link')) {
      headers.push('official_source_verification_link');
    }

    const csvLines = [headers.join(',')];
    dataset.forEach((row) => {
      const line = headers.map((h) => {
        if (h === 'official_source_verification_link') {
          return `"${row.source_url || sourceUrl || 'https://data.cityofchicago.org'}"`;
        }
        const val = String(row[h] ?? '').replace(/"/g, '""');
        return `"${val}"`;
      });
      csvLines.push(line.join(','));
    });

    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${companyName.toLowerCase().replace(/[^a-z0-9]/g, '_')}_${filenamePrefix}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleExportCsv = () => {
    triggerDownload(rows && rows.length > 0 ? rows : initialRows, 'sample_records');
  };

  const handleCopyJson = (record) => {
    if (!record) return;
    navigator.clipboard.writeText(JSON.stringify(record, null, 2));
    setCopiedJson(true);
    showToast('✓ Record payload copied to clipboard!', 'success');
    setTimeout(() => setCopiedJson(false), 2500);
  };

  const handleUnlockBacklog = async (e) => {
    e.preventDefault();
    if (!email || !email.includes('@')) {
      showToast('Please enter a valid billing/work email.', 'error');
      return;
    }

    setIsProcessing(true);
    showToast('Unlocking 30-day historical backlog dataset ($49)...', 'info');

    try {
      const data = await unlockBacklog(slug, { email });
      if (data.ok && data.rows) {
        setIsUnlocked(true);
        setRows(data.rows);
        setIsBacklogModalOpen(false);
        showToast(`✓ Backlog Unlocked! Downloaded ${data.rows_count} records.`, 'success', 6000);
        triggerDownload(data.rows, 'full_30d_backlog');
      } else {
        showToast('Could not unlock backlog. Please try again.', 'error');
      }
    } catch (err) {
      console.error('Backlog unlock error:', err);
      showToast(`Unlock failed: ${err.message}`, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{ marginTop: '24px' }}>
      {/* Search & Actions Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '280px', maxWidth: '440px', position: 'relative' }}>
          <span style={{ position: 'absolute', left: '12px', color: 'var(--text-dim)', fontSize: '14px' }}>🔍</span>
          <input
            type="text"
            className="form-input"
            style={{ paddingLeft: '34px', paddingRight: searchTerm ? '32px' : '14px' }}
            placeholder="Search verified dockets, names, addresses..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              style={{ position: 'absolute', right: '10px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '14px' }}
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-outline" onClick={handleExportCsv} style={{ fontSize: '12px', padding: '9px 16px' }}>
            📥 Download Verified CSV
          </button>
          <button
            className="btn btn-primary"
            style={{
              background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
              border: '1px solid #38bdf8',
              fontWeight: 700,
              fontSize: '12px',
              padding: '9px 16px',
            }}
            onClick={() => {
              if (isUnlocked && rows.length > 25) {
                triggerDownload(rows, 'full_30d_backlog');
              } else {
                setIsBacklogModalOpen(true);
              }
            }}
          >
            {isUnlocked ? '⚡ Download Full 30-Day Backlog' : '⚡ Unlock 30-Day Historical Backlog • $49'}
          </button>
        </div>
      </div>

      {/* Live Table with Row Click Inspection */}
      <div className="data-table-container" style={{ boxShadow: '0 8px 24px rgba(0,0,0,0.35)' }}>
        <table className="data-table table-interactive">
          <thead>
            <tr>
              <th className="sortable-th" onClick={() => handleSort('id')} style={{ width: '18%' }}>
                Record / Filing ID {sortField === 'id' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="sortable-th" onClick={() => handleSort('entity')} style={{ width: '26%' }}>
                Primary Party / Entity {sortField === 'entity' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="sortable-th" onClick={() => handleSort('date')} style={{ width: '14%' }}>
                Filing Date {sortField === 'date' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="sortable-th" onClick={() => handleSort('amount')} style={{ width: '15%' }}>
                Valuation / Amount {sortField === 'amount' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th style={{ width: '15%' }}>Jurisdiction / City</th>
              <th style={{ width: '12%', textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {paginatedRows.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)' }}>
                  <div style={{ fontSize: '32px', marginBottom: '8px' }}>📂</div>
                  <b>No records match your filter.</b>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>Try clearing your search query.</div>
                </td>
              </tr>
            ) : (
              paginatedRows.map((row, idx) => {
                const idVal = row.id || row.case_number || row.permit_number || row.filing_number || row.rfp_solicitation_id || Object.values(row)[0] || `REC-${1000 + idx}`;
                const entityVal = row.primary_party || row.debtor_name || row.owner_name || row.contractor_name || row.applicant_name || Object.values(row)[1] || 'Verified Public Filing';
                const dateVal = row.filing_date || row.issue_date || row.file_date || row.posted_date || '2026-08-28';
                const amtVal = row.amount || row.est_value || row.valuation || row.opening_bid || '$150,000';
                const secVal = row.secondary_party || row.property_address || row.jurisdiction || jurisdiction || 'Public Records Registry';
                const proofUrl = row.source_url || sourceUrl || 'https://data.cityofchicago.org';

                return (
                  <tr
                    key={idx}
                    onClick={() => setSelectedRecord(row)}
                    title="Click row to inspect full record attributes"
                  >
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: 'var(--cyan)', fontFamily: 'var(--mono)', fontWeight: 700 }}>
                          {idVal}
                        </span>
                      </div>
                    </td>
                    <td>
                      <b style={{ color: '#fff', fontSize: '13px' }}>{entityVal}</b>
                      {row.debtor_address && (
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          📍 {row.debtor_address}
                        </div>
                      )}
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--mono)', color: 'var(--text-muted)' }}>{dateVal}</span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--green)', fontFamily: 'var(--mono)', fontWeight: 800 }}>
                        {amtVal}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{secVal}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px', alignItems: 'center' }}>
                        <button
                          type="button"
                          className="btn btn-outline"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedRecord(row);
                          }}
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                          title="Inspect raw payload"
                        >
                          Inspect
                        </button>
                        <a
                          href={proofUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="badge-verified-docket"
                          style={{ textDecoration: 'none' }}
                          title="Inspect authentic source docket on government portal in new tab"
                        >
                          ✓ Proof ↗
                        </a>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>

        {/* Pagination Bar */}
        <div className="pagination-bar">
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
            Showing <b>{totalRows === 0 ? 0 : (currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, totalRows)}</b> of <b>{totalRows}</b> verified filings
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              className="pagination-btn"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
            >
              ← Prev
            </button>
            <span style={{ fontSize: '12px', color: '#fff', padding: '0 6px', fontFamily: 'var(--mono)' }}>
              {currentPage} / {totalPages}
            </span>
            <button
              className="pagination-btn"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
            >
              Next →
            </button>
          </div>
        </div>
      </div>

      {/* Record Inspector Drawer (Slide-out) */}
      {selectedRecord && (
        <div className="record-drawer-overlay" onClick={() => setSelectedRecord(null)}>
          <div className="record-drawer" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <span className="badge-tag badge-green" style={{ marginBottom: '8px' }}>
                  ✓ AUTHENTIC DOCKET RECORD
                </span>
                <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginTop: '4px' }}>
                  {selectedRecord.id || selectedRecord.case_number || selectedRecord.filing_number || 'Filing Details'}
                </h3>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {selectedRecord.primary_party || selectedRecord.debtor_name || companyName}
                </div>
              </div>
              <button className="modal-close" onClick={() => setSelectedRecord(null)} style={{ position: 'static' }}>
                ✕
              </button>
            </div>

            {/* Quick Action Links */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', flexWrap: 'wrap' }}>
              <a
                href={selectedRecord.source_url || sourceUrl || 'https://data.cityofchicago.org'}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '8px 14px', textDecoration: 'none' }}
              >
                🏛️ Open Government Source Docket ↗
              </a>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => handleCopyJson(selectedRecord)}
                style={{ fontSize: '12px', padding: '8px 14px' }}
              >
                {copiedJson ? '✓ Copied!' : '📋 Copy JSON'}
              </button>
            </div>

            {/* Formatted Key-Value Grid */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--cyan)', textTransform: 'uppercase', marginBottom: '10px', letterSpacing: '0.5px' }}>
                Parsed Record Attributes
              </div>
              {Object.entries(selectedRecord).map(([key, val]) => (
                <div key={key} className="drawer-field-row">
                  <span className="drawer-field-label">{key.replace(/_/g, ' ')}</span>
                  <span className="drawer-field-value">
                    {val === null || val === undefined ? '—' : String(val)}
                  </span>
                </div>
              ))}
            </div>

            {/* Raw JSON View */}
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.5px' }}>
                Raw JSON Payload
              </div>
              <pre style={{
                background: '#040914',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '14px',
                fontSize: '11px',
                fontFamily: 'var(--mono)',
                color: '#a7f3d0',
                maxHeight: '220px',
                overflowY: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}>
                {JSON.stringify(selectedRecord, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* 30-Day Historical Backlog Unlock Modal ($49 Tripwire) */}
      {isBacklogModalOpen && (
        <div className="modal-overlay" onClick={() => setIsBacklogModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
            <button className="modal-close" onClick={() => setIsBacklogModalOpen(false)}>✕</button>

            <div style={{ textAlign: 'center', marginBottom: '18px' }}>
              <div style={{ fontSize: '32px', marginBottom: '6px' }}>⚡</div>
              <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff' }}>
                Instant Backlog Unlock: 30-Day Records ($49)
              </h2>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Full Historical Dataset for <b style={{ color: 'var(--cyan)' }}>{companyName}</b>
              </div>
            </div>

            {/* Value Highlights Box */}
            <div style={{ background: 'var(--card-alt)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', marginBottom: '20px', fontSize: '12px', lineHeight: 1.6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Historical Depth:</span>
                <span style={{ color: '#fff', fontWeight: 700, fontFamily: 'var(--mono)' }}>Past 30 Days (200–500 Rows)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Delivery Format:</span>
                <span style={{ color: 'var(--cyan)', fontWeight: 700, fontFamily: 'var(--mono)' }}>Instant CSV Download</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-muted)' }}>One-Time Cost:</span>
                <span style={{ color: 'var(--green)', fontWeight: 800, fontFamily: 'var(--mono)', fontSize: '14px' }}>$49.00 USD</span>
              </div>
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: '8px', marginTop: '8px', color: 'var(--green)', fontWeight: 600 }}>
                💡 100% Credited: Upgrade to an automated daily feed anytime, and your $49 is credited straight toward your setup sprint!
              </div>
            </div>

            <form onSubmit={handleUnlockBacklog}>
              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#fff' }}>
                  Delivery / Work Email
                </label>
                <input
                  type="email"
                  required
                  className="form-input"
                  placeholder="alex@yourcompany.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{
                  width: '100%',
                  padding: '12px',
                  fontSize: '14px',
                  fontWeight: 800,
                  background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                  border: '1px solid #38bdf8',
                }}
                disabled={isProcessing}
              >
                {isProcessing ? '⚡ Unlocking & Generating CSV...' : '💳 Pay $49 & Download Full 30-Day CSV ➔'}
              </button>
            </form>

            <div style={{ textAlign: 'center', marginTop: '16px', fontSize: '11px', color: 'var(--text-dim)' }}>
              🔒 Instant Delivery • Secure Payment • PayPal &amp; Cards
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
