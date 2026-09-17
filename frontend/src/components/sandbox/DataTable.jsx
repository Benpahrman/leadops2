import React, { useState, useMemo, useEffect, useRef } from 'react';
import { unlockBacklog } from '../../services/api';
import { useToast } from '../../context/ToastContext';

import {
  TableToolbar,
  TablePagination,
  RecordDetailModal,
  BacklogUnlockModal,
} from './table';

export default function DataTable({
  slug = '',
  rows: initialRows = [],
  sourceUrl = '',
  companyName = '',
  jurisdiction = '',
  defaultEmail = '',
}) {
  const { showToast } = useToast();
  const [rows, setRows] = useState(initialRows);
  const [searchTerm, setSearchTerm] = useState('');
  const [isBacklogModalOpen, setIsBacklogModalOpen] = useState(false);
  const [email, setEmail] = useState(defaultEmail || '');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [backlogPaypalReady, setBacklogPaypalReady] = useState(false);
  const [backlogPaypalError, setBacklogPaypalError] = useState(null);
  const emailRef = useRef(email);

  const [sortField, setSortField] = useState('date');
  const [sortAsc, setSortAsc] = useState(false);
  const [filterCategory, setFilterCategory] = useState('all');
  const [density, setDensity] = useState('comfortable');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [copiedJson, setCopiedJson] = useState(false);

  // Sync rows if initialRows changes
  useEffect(() => {
    if (initialRows && initialRows.length > 0 && (!rows || rows.length === 0)) {
      setRows(initialRows);
    }
  }, [initialRows]);

  useEffect(() => {
    if (defaultEmail && !email) {
      setEmail(defaultEmail);
    }
  }, [defaultEmail]);

  useEffect(() => {
    emailRef.current = email;
  }, [email]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
    setCurrentPage(1);
  };

  const parseAmt = (val) => parseFloat(String(val || '').replace(/[^0-9.-]/g, '')) || 0;

  const processedRows = useMemo(() => {
    const activeRows = rows && rows.length > 0 ? rows : initialRows;
    let result = [...activeRows];

    if (searchTerm) {
      const q = searchTerm.toLowerCase().trim();
      result = result.filter((r) => JSON.stringify(r).toLowerCase().includes(q));
    }

    if (filterCategory === 'high_value') {
      result = result.filter((r) => {
        const amt = parseAmt(r.amount || r.est_value || r.valuation || r.opening_bid);
        return amt >= 50000;
      });
    } else if (filterCategory === 'commercial') {
      result = result.filter((r) => {
        const str = JSON.stringify(r).toLowerCase();
        return str.includes('llc') || str.includes('inc') || str.includes('corp') || str.includes('contractor') || str.includes('commercial') || str.includes('building');
      });
    } else if (filterCategory === 'permits') {
      result = result.filter((r) => {
        const str = JSON.stringify(r).toLowerCase();
        return str.includes('permit') || str.includes('lien') || str.includes('docket') || str.includes('case');
      });
    }

    result.sort((a, b) => {
      let valA = '';
      let valB = '';

      if (sortField === 'id') {
        valA = a.record_id || a.permit_number || a.taxpayer_number || a.job_number || a.case_number || a.filing_number || a.id || '';
        valB = b.record_id || b.permit_number || b.taxpayer_number || b.job_number || b.case_number || b.filing_number || b.id || '';
      } else if (sortField === 'entity') {
        valA = a.primary_entity || a.contractor || a.contractor_name || a.business_name || a.taxpayer_name || a.legal_name || a.primary_party || '';
        valB = b.primary_entity || b.contractor || b.contractor_name || b.business_name || b.taxpayer_name || b.legal_name || b.primary_party || '';
      } else if (sortField === 'date') {
        valA = a.filing_date || a.issue_date || a.date_issued || a.valid_from_date || a.file_date || '';
        valB = b.filing_date || b.issue_date || b.date_issued || b.valid_from_date || b.file_date || '';
      } else if (sortField === 'details') {
        valA = a.description_or_type || a.work_description || a.permit_type || a.category || a.business_activity || '';
        valB = b.description_or_type || b.work_description || b.permit_type || b.category || b.business_activity || '';
      } else if (sortField === 'address') {
        valA = a.property_address || a.location_address || a.address || '';
        valB = b.property_address || b.location_address || b.address || '';
      }

      valA = String(valA).toLowerCase();
      valB = String(valB).toLowerCase();
      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });

    return result;
  }, [rows, initialRows, searchTerm, filterCategory, sortField, sortAsc]);

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

  // Real PayPal Buttons for $49 backlog unlock
  useEffect(() => {
    if (!isBacklogModalOpen) {
      setBacklogPaypalReady(false);
      setBacklogPaypalError(null);
      return;
    }

    let isMounted = true;
    let buttonsInstance = null;
    let retryCount = 0;

    const renderBacklogPayPal = () => {
      if (!isMounted) return;
      const clientId = window.__PAYPAL_CLIENT_ID__ || 'BAAa18mhTonKniN6UJij6PasfiTBu0_sQgMKP9XwyMeXtBurHvoUD4YkDD09KTmC8RHwVTpOW_qbqalGkY';

      if (!window.paypal || !window.paypal.Buttons) {
        if (retryCount < 20) {
          retryCount++;
          setTimeout(renderBacklogPayPal, 250);
          return;
        }
        if (isMounted) setBacklogPaypalError('PayPal SDK timed out. Please check your internet connection and reload.');
        return;
      }

      const container = document.getElementById('paypal-backlog-button-container');
      if (!container) return;
      container.innerHTML = '';

      try {
        buttonsInstance = window.paypal.Buttons({
          style: { shape: 'rect', color: 'gold', layout: 'vertical', label: 'paypal', height: 42 },
          createOrder: async () => {
            const currentMail = emailRef.current ? emailRef.current.trim() : '';
            if (!currentMail || !currentMail.includes('@')) {
              showToast('Please enter your work email address above before paying.', 'error');
              throw new Error('Email is required');
            }
            setIsProcessing(true);
            try {
              const res = await fetch(`/api/sandbox/${slug}/backlog-order`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: currentMail }),
              });
              if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Could not generate PayPal order');
              }
              const orderData = await res.json();
              return orderData.order_id;
            } catch (err) {
              setIsProcessing(false);
              showToast(err.message || 'Payment setup failed', 'error');
              throw err;
            }
          },
          onApprove: async (data) => {
            setIsProcessing(true);
            try {
              const captureRes = await fetch(`/api/sandbox/${slug}/backlog-capture`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: data.orderID, email: emailRef.current }),
              });
              if (!captureRes.ok) {
                const errData = await captureRes.json().catch(() => ({}));
                throw new Error(errData.detail || 'Payment capture failed');
              }
              const captureData = await captureRes.json();
              setIsUnlocked(true);
              setIsBacklogModalOpen(false);

              if (captureData.records && captureData.records.length > 0) {
                setRows(captureData.records);
                triggerDownload(captureData.records, 'full_30d_backlog');
              } else {
                const unlocked = await unlockBacklog(slug);
                if (unlocked.records) {
                  setRows(unlocked.records);
                  triggerDownload(unlocked.records, 'full_30d_backlog');
                }
              }
              showToast('🎉 $49 Backlog Unlocked! 100% credited toward your setup sprint.', 'success', 8000);
            } catch (err) {
              showToast(`Capture failed: ${err.message}`, 'error');
            } finally {
              setIsProcessing(false);
            }
          },
          onError: (err) => {
            console.error('Backlog PayPal error:', err);
            showToast('PayPal could not complete the transaction. Please try again.', 'error');
          },
          onCancel: () => {
            showToast('Payment cancelled. Your backlog unlock is waiting whenever you\'re ready.', 'info');
          },
        });

        if (isMounted && container) {
          buttonsInstance.render('#paypal-backlog-button-container');
          setBacklogPaypalReady(true);
        }
      } catch (err) {
        console.error('Failed to render backlog PayPal Buttons:', err);
        setBacklogPaypalError('Failed to initialize PayPal. Please reload the page.');
      }
    };

    renderBacklogPayPal();

    return () => {
      isMounted = false;
      if (buttonsInstance && typeof buttonsInstance.close === 'function') {
        try { 
          buttonsInstance.close(); 
        } catch (closeErr) {
          console.debug('PayPal backlog instance cleanup:', closeErr);
        }
      }
    };
  }, [isBacklogModalOpen, slug, companyName, sourceUrl, showToast]);

  return (
    <div style={{ marginTop: '24px' }}>
      {/* Table Toolbar */}
      <TableToolbar
        sourceUrl={sourceUrl}
        rowsCount={rows.length > 0 ? rows.length : initialRows.length}
        filterCategory={filterCategory}
        setFilterCategory={setFilterCategory}
        density={density}
        setDensity={setDensity}
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        setCurrentPage={setCurrentPage}
        handleExportCsv={handleExportCsv}
        setIsBacklogModalOpen={setIsBacklogModalOpen}
      />

      {/* Live Table with Row Click Inspection */}
      <div className="data-table-container" style={{ boxShadow: '0 8px 30px rgba(0,0,0,0.4)' }}>
        <table className={`data-table table-interactive ${density === 'comfortable' ? 'table-comfortable' : 'table-compact'}`}>
          <thead>
            <tr>
              <th className="sortable-th" onClick={() => handleSort('id')} style={{ width: '18%' }}>
                Record / Filing ID {sortField === 'id' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="sortable-th" onClick={() => handleSort('entity')} style={{ width: '26%' }}>
                Primary Entity / Contractor {sortField === 'entity' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="sortable-th" onClick={() => handleSort('date')} style={{ width: '13%' }}>
                Date Filed / Issued {sortField === 'date' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="sortable-th" onClick={() => handleSort('details')} style={{ width: '18%' }}>
                Filing Type / Scope {sortField === 'details' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="sortable-th" onClick={() => handleSort('address')} style={{ width: '16%' }}>
                Address / Location {sortField === 'address' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th style={{ width: '9%', textAlign: 'right' }}>Official Proof</th>
            </tr>
          </thead>
          <tbody>
            {paginatedRows.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-muted)' }}>
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto 8px', display: 'block' }}>
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                  </svg>
                  <b>No records match your filter criteria.</b>
                  <div style={{ fontSize: '12px', marginTop: '4px' }}>Try switching filter tabs or clearing your search.</div>
                </td>
              </tr>
            ) : (
              paginatedRows.map((row, idx) => {
                const idVal = row.record_id || row.permit_number || row.taxpayer_number || row.job_number || row.case_number || row.filing_number || row.license_number || row.request_id || row.id || Object.values(row)[0] || `REC-${1000 + idx}`;
                const entityVal = row.primary_entity || row.contractor || row.contractor_name || row.business_name || row.taxpayer_name || row.legal_name || row.primary_party || row.debtor_name || row.owner_name || row.applicant_name || Object.values(row)[1] || 'Public Entity';
                const rawDate = row.filing_date || row.issue_date || row.date_issued || row.valid_from_date || row.file_date || row.created_date || row.posted_date || '';
                const dateVal = rawDate ? String(rawDate).split('T')[0] : 'Recent';
                const descVal = row.description_or_type || row.work_description || row.permit_type || row.category || row.business_activity || row.details || (row.valuation_amount || row.amount || row.est_value ? (String(row.valuation_amount || row.amount || row.est_value).startsWith('$') ? String(row.valuation_amount || row.amount || row.est_value) : `$${row.valuation_amount || row.amount || row.est_value}`) : (row.status || 'Active'));
                const addrVal = row.property_address || row.location_address || row.address || (row.city && row.state ? `${row.city}, ${row.state}` : '') || row.jurisdiction || jurisdiction || 'Public Records';
                const proofUrl = row.source_url || sourceUrl || 'https://data.gov';
                const isCorp = /inc|llc|corp|co\.|ltd|company|contractor|roofing|plumbing|electric/i.test(String(entityVal));

                return (
                  <tr
                    key={idx}
                    onClick={() => setSelectedRecord(row)}
                    title="Click row to inspect full record attributes in slide-out drawer"
                  >
                    <td>
                      <div className="docket-id-badge">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                          <polyline points="14 2 14 8 20 8"/>
                        </svg>
                        <span>{idVal}</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                        {isCorp ? (
                          <svg style={{ flexShrink: 0, marginTop: '3px', color: 'var(--cyan)' }} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="4" y="2" width="16" height="20" rx="2" ry="2"/>
                            <line x1="9" y1="6" x2="9" y2="6.01"/>
                            <line x1="15" y1="6" x2="15" y2="6.01"/>
                            <line x1="9" y1="10" x2="9" y2="10.01"/>
                            <line x1="15" y1="10" x2="15" y2="10.01"/>
                            <line x1="9" y1="14" x2="9" y2="14.01"/>
                            <line x1="15" y1="14" x2="15" y2="14.01"/>
                            <line x1="9" y1="18" x2="15" y2="18"/>
                          </svg>
                        ) : (
                          <svg style={{ flexShrink: 0, marginTop: '3px', color: 'var(--purple)' }} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                            <circle cx="12" cy="7" r="4"/>
                          </svg>
                        )}
                        <div>
                          <b style={{ color: '#fff', fontSize: '13px' }}>{entityVal}</b>
                          {row.debtor_address && (
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                                <circle cx="12" cy="10" r="3"/>
                              </svg>
                              <span>{row.debtor_address}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--mono)', color: 'var(--text-muted)', fontSize: '12px' }}>{dateVal}</span>
                    </td>
                    <td>
                      <span className="valuation-pill" style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={descVal}>
                        {descVal}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--text-muted)', fontSize: '11px', display: 'inline-block', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={addrVal}>
                        {addrVal}
                      </span>
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
                          👁️ Inspect
                        </button>
                        <a
                          href={proofUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="btn btn-outline"
                          style={{ padding: '4px 8px', fontSize: '11px', color: 'var(--cyan)', borderColor: 'rgba(56, 189, 248, 0.4)' }}
                          title="Verify filing at official source website"
                        >
                          🔗 Sourced
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
        <TablePagination
          currentPage={currentPage}
          pageSize={pageSize}
          totalRows={totalRows}
          totalPages={totalPages}
          setCurrentPage={setCurrentPage}
        />
      </div>

      {/* Record Inspector Drawer */}
      <RecordDetailModal
        selectedRecord={selectedRecord}
        setSelectedRecord={setSelectedRecord}
        sourceUrl={sourceUrl}
        companyName={companyName}
        handleCopyJson={handleCopyJson}
        copiedJson={copiedJson}
      />

      {/* 30-Day Historical Backlog Unlock Modal */}
      <BacklogUnlockModal
        isOpen={isBacklogModalOpen}
        onClose={() => setIsBacklogModalOpen(false)}
        companyName={companyName}
        email={email}
        setEmail={setEmail}
        backlogPaypalReady={backlogPaypalReady}
        backlogPaypalError={backlogPaypalError}
        isProcessing={isProcessing}
      />
    </div>
  );
}
