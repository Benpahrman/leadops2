import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchSandbox } from '../services/api';
import { useToast } from '../context/ToastContext';
import DataTable from '../components/sandbox/DataTable';
import SchemaSelector from '../components/sandbox/SchemaSelector';
import EscrowCheckoutModal from '../components/sandbox/EscrowCheckoutModal';

export default function SandboxPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [sandboxData, setSandboxData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [activeFields, setActiveFields] = useState([
    'case_number',
    'filing_date',
    'primary_party',
    'secondary_party',
    'amount',
    'property_address',
  ]);

  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);

  // Load live sandbox data from backend
  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const data = await fetchSandbox(slug || 'lead-apex-roofing');
        if (isMounted) {
          setSandboxData(data);
          if (data.lead?.selected_fields && data.lead.selected_fields.length > 0) {
            setActiveFields(data.lead.selected_fields);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message);
          showToast(`Error loading sandbox: ${err.message}`, 'error');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    load();
    return () => { isMounted = false; };
  }, [slug, showToast]);

  const companyName = sandboxData?.lead?.company_name || slug?.replace('lead-', '').replace(/-/g, ' ').toUpperCase() || 'YOUR COMPANY';
  const jurisdiction = sandboxData?.lead?.jurisdiction || 'Public Records Registry';
  const sourceUrl = sandboxData?.source_url || 'https://data.cityofchicago.org';
  const rows = sandboxData?.rows || [];

  const handleToggleField = (field) => {
    setActiveFields((prev) =>
      prev.includes(field) ? prev.filter((f) => f !== field) : [...prev, field]
    );
  };

  const handleAddField = (field) => {
    setActiveFields((prev) => (prev.includes(field) ? prev : [...prev, field]));
  };

  if (loading) {
    return (
      <div className="container" style={{ padding: '80px 24px', textAlign: 'center' }}>
        <div style={{ fontSize: '36px', animation: 'spin 1.5s linear infinite', display: 'inline-block' }}>⚡</div>
        <h2 style={{ fontSize: '20px', color: '#fff', marginTop: '16px' }}>Connecting to Live Government Open Data Endpoints...</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '6px' }}>
          Extracting authentic filings and building your preview sandbox. Zero mock data.
        </p>
      </div>
    );
  }

  return (
    <main style={{ padding: '40px 0 80px' }}>
      <div className="container">
        {/* Sandbox Hero Header */}
        <div className="card" style={{ background: 'linear-gradient(180deg, #162238 0%, #0f172a 100%)', borderColor: 'var(--border-highlight)', marginBottom: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '20px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                <span className="badge-tag badge-green">LIVE PREVIEW SANDBOX</span>
                <span style={{ color: 'var(--text-dim)' }}>•</span>
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="badge-tag badge-cyan"
                  style={{ textDecoration: 'none' }}
                  title="Official Open Data Registry Endpoint"
                >
                  🏛️ Official Registry: {new URL(sourceUrl).hostname} ↗
                </a>
                <button
                  type="button"
                  onClick={() => setIsCheckoutOpen(true)}
                  className="badge-tag"
                  style={{
                    background: 'rgba(56, 189, 248, 0.12)',
                    color: 'var(--cyan)',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    cursor: 'pointer',
                    fontSize: '11px',
                    fontWeight: 600,
                  }}
                  title="Confirm or change the target docket URL for your pipeline"
                >
                  🎯 Confirm / Edit Target Portal
                </button>
              </div>

              <h1 style={{ fontSize: '28px', fontWeight: 800, color: '#fff', letterSpacing: '-0.5px' }}>
                {companyName} Data Extraction Stream
              </h1>
              <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '4px', maxWidth: '680px' }}>
                Jurisdiction: <b style={{ color: '#fff' }}>{jurisdiction}</b>. 25 live-scraped records pulled from official government open data registries. Click any row's verification link to cross-check the official docket.
              </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
              <button
                className="btn btn-primary btn-lg"
                onClick={() => setIsCheckoutOpen(true)}
              >
                💳 Start $99 Setup Sprint (100% Credited to Month 1) ➔
              </button>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
                100% Refundable if QA Fails • Balance of $151 Due Upon Delivery
              </span>
            </div>
          </div>
        </div>

        {/* Live Data Table with 1-Click Verification Links & $49 Backlog Unlock */}
        <DataTable
          slug={slug}
          rows={rows}
          sourceUrl={sourceUrl}
          companyName={companyName}
          jurisdiction={jurisdiction}
          defaultEmail={sandboxData?.lead?.contact_email || ''}
        />

        {/* Active Schema & AI Suggestions */}
        <SchemaSelector
          slug={slug}
          activeFields={activeFields}
          onToggleField={handleToggleField}
          onAddField={handleAddField}
        />

        {/* Bottom Checkout Callout */}
        <div className="card" style={{ marginTop: '32px', textAlign: 'center', padding: '36px', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(56, 189, 248, 0.08))', border: '1px solid var(--green)' }}>
          <h3 style={{ fontSize: '22px', fontWeight: 800, color: '#fff' }}>
            Ready to Automate Daily Delivery to Google Sheets?
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: '8px auto 20px', maxWidth: '620px' }}>
            Authorize your $99 setup sprint deposit. 100% credited toward your first month ($151 balance due only when live QA passes with &gt;=95% accuracy). Held safely in third-party escrow.
          </p>
          <button
            className="btn btn-primary btn-lg"
            onClick={() => setIsCheckoutOpen(true)}
          >
            Start $99 Setup Sprint (Credited to Month 1) ➔
          </button>
        </div>
      </div>

      {/* Escrow Checkout Modal */}
      <EscrowCheckoutModal
        isOpen={isCheckoutOpen}
        onClose={() => setIsCheckoutOpen(false)}
        slug={slug}
        companyName={companyName}
        defaultEmail={sandboxData?.lead?.contact_email || ''}
        defaultTargetUrl={sourceUrl}
      />
    </main>
  );
}
