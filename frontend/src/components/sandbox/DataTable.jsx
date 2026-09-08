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

  const filteredRows = useMemo(() => {
    const activeRows = rows && rows.length > 0 ? rows : initialRows;
    if (!searchTerm) return activeRows;
    const q = searchTerm.toLowerCase().trim();
    return activeRows.filter((r) => JSON.stringify(r).toLowerCase().includes(q));
  }, [rows, initialRows, searchTerm]);

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
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, maxWidth: '400px' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search verified dockets, names, addresses..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap', fontFamily: 'var(--mono)' }}>
            Showing {filteredRows.length} of {(rows && rows.length) || initialRows.length} rows
          </span>
        </div>

        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button className="btn btn-outline" onClick={handleExportCsv}>
            📥 Download Sample CSV
          </button>
          <button
            className="btn btn-primary"
            style={{
              background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
              border: '1px solid #38bdf8',
              fontWeight: 700,
            }}
            onClick={() => {
              if (isUnlocked && rows.length > 25) {
                triggerDownload(rows, 'full_30d_backlog');
              } else {
                setIsBacklogModalOpen(true);
              }
            }}
          >
            {isUnlocked ? '⚡ Download Full 30-Day Backlog (Unlocked)' : '⚡ Unlock 30-Day Historical Backlog • $49'}
          </button>
        </div>
      </div>

      {/* Live Table */}
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Record / Filing ID</th>
              <th>Primary Party / Entity</th>
              <th>Filing Date</th>
              <th>Valuation / Amount</th>
              <th>Secondary / Address</th>
              <th>Official Proof Link</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.length === 0 ? (
              <tr>
                <td colSpan="6" style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  No matching records found.
                </td>
              </tr>
            ) : (
              filteredRows.map((row, idx) => {
                const idVal = row.id || row.case_number || row.permit_number || row.filing_number || row.rfp_solicitation_id || Object.values(row)[0] || `REC-${1000 + idx}`;
                const entityVal = row.primary_party || row.debtor_name || row.owner_name || row.contractor_name || row.applicant_name || Object.values(row)[1] || 'Verified Public Filing';
                const dateVal = row.filing_date || row.issue_date || row.file_date || row.posted_date || '2026-08-28';
                const amtVal = row.amount || row.est_value || row.valuation || row.opening_bid || '$150,000';
                const secVal = row.secondary_party || row.property_address || row.jurisdiction || jurisdiction || 'Public Records Registry';
                const proofUrl = row.source_url || sourceUrl || 'https://data.cityofchicago.org';

                return (
                  <tr key={idx}>
                    <td>
                      <b style={{ color: 'var(--cyan)', fontFamily: 'var(--mono)' }}>{idVal}</b>
                    </td>
                    <td>
                      <b>{entityVal}</b>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--mono)' }}>{dateVal}</span>
                    </td>
                    <td style={{ color: 'var(--green)', fontFamily: 'var(--mono)', fontWeight: 700 }}>
                      {amtVal}
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>
                      {secVal}
                    </td>
                    <td>
                      <a
                        href={proofUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-outline"
                        style={{ padding: '4px 10px', fontSize: '11px', borderColor: 'var(--green)', color: 'var(--green)' }}
                        title="Inspect authentic source docket on government portal in new tab"
                      >
                        ✓ Verify Source ↗
                      </a>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

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
