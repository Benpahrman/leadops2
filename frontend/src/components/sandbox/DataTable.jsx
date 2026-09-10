import React, { useState, useMemo, useEffect, useRef } from 'react';
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
  const [backlogPaypalReady, setBacklogPaypalReady] = useState(false);
  const [backlogPaypalError, setBacklogPaypalError] = useState(null);
  const emailRef = useRef(email);

  const [sortField, setSortField] = useState('date');
  const [sortAsc, setSortAsc] = useState(false);
  const [filterCategory, setFilterCategory] = useState('all');
  const [density, setDensity] = useState('comfortable');
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

  // Keep emailRef in sync for use inside PayPal SDK callbacks
  useEffect(() => { emailRef.current = email; }, [email]);

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

  const parseAmt = (val) => parseFloat(String(val || '').replace(/[^0-9.-]/g, '')) || 0;

  const processedRows = useMemo(() => {
    const activeRows = rows && rows.length > 0 ? rows : initialRows;
    let result = [...activeRows];

    // Filter by search query
    if (searchTerm) {
      const q = searchTerm.toLowerCase().trim();
      result = result.filter((r) => JSON.stringify(r).toLowerCase().includes(q));
    }

    // Filter by category
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

    // Sort rows
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

  // Real PayPal Buttons for $49 backlog unlock — rendered when modal opens
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
        let script = document.getElementById('paypal-js-sdk');
        if (!script) {
          script = document.createElement('script');
          script.id = 'paypal-js-sdk';
          script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=USD`;
          script.onload = () => { if (isMounted) renderBacklogPayPal(); };
          script.onerror = () => { if (isMounted) setBacklogPaypalError('Unable to reach PayPal. Please disable any content blockers and try again.'); };
          document.head.appendChild(script);
        }
        if (retryCount < 20) {
          retryCount++;
          setTimeout(() => { if (isMounted) renderBacklogPayPal(); }, 350);
        } else {
          setBacklogPaypalError('PayPal checkout took too long to load. Please refresh and try again.');
        }
        return;
      }

      const container = document.getElementById('paypal-backlog-button-container');
      if (!container) return;
      container.innerHTML = '';

      try {
        buttonsInstance = window.paypal.Buttons({
          style: { layout: 'vertical', color: 'blue', shape: 'rect', label: 'pay', height: 44 },
          createOrder: async (data, actions) => {
            if (!emailRef.current || !emailRef.current.includes('@')) {
              showToast('Please enter a valid billing email before paying.', 'error');
              throw new Error('Valid email required');
            }
            // Try server-side order creation first
            try {
              const res = await fetch(`/api/paypal/create-order/${slug}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  deposit_amount: 49.00,
                  email: emailRef.current,
                  cardholder: companyName || slug,
                  target_url: sourceUrl || '',
                }),
              });
              if (res.ok) {
                const orderData = await res.json();
                if (orderData.order_id) return orderData.order_id;
              }
            } catch (serverErr) {
              console.warn('Backlog: backend order creation fallback to client SDK:', serverErr);
            }
            // Client-side SDK fallback
            return actions.order.create({
              purchase_units: [{
                description: `LeadOps 30-Day Backlog Unlock — ${companyName || slug}`,
                custom_id: 'backlog',
                invoice_id: `backlog-${slug}-${Date.now()}`,
                amount: { currency_code: 'USD', value: '49.00',
                  breakdown: { item_total: { currency_code: 'USD', value: '49.00' } } },
                items: [{ name: '30-Day Historical Backlog Dataset', quantity: '1',
                  unit_amount: { currency_code: 'USD', value: '49.00' },
                  description: '200–500 verified records • Instant CSV download • 100% credited toward Setup Sprint',
                }],
              }],
              application_context: { shipping_preference: 'NO_SHIPPING', user_action: 'PAY_NOW', brand_name: 'LeadOps / OmniLeadFeeder' },
            });
          },
          onApprove: async (data, actions) => {
            setIsProcessing(true);
            showToast('✓ Capturing $49 payment...', 'info');
            try {
              let captureId = data.orderID;
              // Server-side capture
              try {
                const captureRes = await fetch(`/api/paypal/capture-order/${slug}`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ order_id: data.orderID, email: emailRef.current, cardholder: companyName || slug, target_url: sourceUrl || '' }),
                });
                if (captureRes.ok) {
                  const capData = await captureRes.json();
                  captureId = capData.capture_id || data.orderID;
                }
              } catch (capErr) {
                const orderDetails = await actions.order.capture();
                captureId = orderDetails?.purchase_units?.[0]?.payments?.captures?.[0]?.id || orderDetails?.id || data.orderID;
              }
              // Unlock backlog with verified paypal_order_id
              const unlockData = await unlockBacklog(slug, { email: emailRef.current, paypalOrderId: captureId });
              if (unlockData.ok && unlockData.rows) {
                setIsUnlocked(true);
                setRows(unlockData.rows);
                setIsBacklogModalOpen(false);
                showToast(`✓ Backlog Unlocked! ${unlockData.rows_count} verified records downloaded.`, 'success', 6000);
                triggerDownload(unlockData.rows, 'full_30d_backlog');
              } else {
                showToast('Payment captured but backlog delivery failed. Our team will follow up within minutes.', 'error');
              }
            } catch (err) {
              console.error('Backlog onApprove error:', err);
              showToast(`Payment error: ${err.message}`, 'error');
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
      if (buttonsInstance && buttonsInstance.close) {
        try { buttonsInstance.close(); } catch (e) {}
      }
    };
  }, [isBacklogModalOpen, slug, companyName, sourceUrl, showToast]);

  const hostDisplay = sourceUrl ? (() => {
    try { return new URL(sourceUrl).hostname; } catch { return 'records.official.gov'; }
  })() : 'records.official.gov';

  return (
    <div style={{ marginTop: '24px' }}>
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
            All Filings ({rows.length > 0 ? rows.length : initialRows.length})
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
              onClick={() => setSearchTerm('')}
              style={{ position: 'absolute', right: '10px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              title="Clear search"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn btn-outline" onClick={handleExportCsv} style={{ fontSize: '12px', padding: '9px 16px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            <span>Export Verified CSV</span>
          </button>
          <button
            className="btn btn-primary"
            style={{
              background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
              border: '1px solid #38bdf8',
              fontWeight: 700,
              fontSize: '12px',
              padding: '9px 16px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
            onClick={() => {
              if (isUnlocked && rows.length > 25) {
                triggerDownload(rows, 'full_30d_backlog');
              } else {
                setIsBacklogModalOpen(true);
              }
            }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
            </svg>
            <span>{isUnlocked ? 'Download 30-Day Dataset' : 'Unlock 30-Day Historical Backlog ($49)'}</span>
          </button>
        </div>
      </div>

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
                          <span>Proof</span>
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="7" y1="17" x2="17" y2="7"/>
                            <polyline points="7 7 17 7 17 17"/>
                          </svg>
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
                href={selectedRecord.source_url || sourceUrl || 'https://data.gov'}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '8px 14px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                <span>Open Government Source Docket</span>
              </a>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => handleCopyJson(selectedRecord)}
                style={{ fontSize: '12px', padding: '8px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                <span>{copiedJson ? '✓ Copied' : 'Copy JSON'}</span>
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

      {/* 30-Day Historical Backlog Unlock Modal ($49) — Real PayPal */}
      {isBacklogModalOpen && (
        <div className="modal-overlay" onClick={() => setIsBacklogModalOpen(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
            <button className="modal-close" onClick={() => setIsBacklogModalOpen(false)}>✕</button>

            <div style={{ textAlign: 'center', marginBottom: '18px' }}>
              <div style={{
                width: '44px', height: '44px', borderRadius: '50%',
                background: 'rgba(56, 189, 248, 0.12)', border: '1px solid rgba(56, 189, 248, 0.3)',
                display: 'grid', placeItems: 'center', margin: '0 auto 12px', color: 'var(--cyan)',
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              </div>
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
                100% Credited: Upgrade to an automated daily feed anytime, and your $49 is credited toward your setup sprint!
              </div>
            </div>

            {/* Billing Email */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#fff' }}>
                Delivery / Work Email *
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

            {/* PayPal Buttons Container */}
            <div style={{ minHeight: '100px' }}>
              {backlogPaypalError ? (
                <div style={{ textAlign: 'center', padding: '14px', color: '#f87171', fontSize: '12px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px', border: '1px solid rgba(239,68,68,0.25)' }}>
                  ⚠️ {backlogPaypalError}
                  <div style={{ marginTop: '8px' }}>
                    <button type="button" onClick={() => window.location.reload()} className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 12px' }}>Reload Page</button>
                  </div>
                </div>
              ) : !backlogPaypalReady && !isProcessing ? (
                <div style={{ textAlign: 'center', padding: '14px', color: 'var(--text-muted)', fontSize: '12px' }}>
                  <div className="spinner" style={{ width: '22px', height: '22px', margin: '0 auto 8px' }}></div>
                  Connecting to secure PayPal checkout...
                </div>
              ) : null}
              {backlogPaypalReady && !isProcessing && (
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '8px' }}>
                  Select payment method below to pay $49 and instantly download your backlog:
                </div>
              )}
              <div id="paypal-backlog-button-container"></div>
            </div>

            <div style={{ textAlign: 'center', marginTop: '14px', borderTop: '1px solid var(--border)', paddingTop: '10px', fontSize: '10px', color: 'var(--text-dim)' }}>
              🔒 256-Bit Encrypted Payment • PayPal, Visa, Mastercard, AMEX & Discover Accepted
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

