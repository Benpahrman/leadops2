import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const playbooks = [
  {
    id: 'roofing-contractors',
    badge: 'Roofing & Construction',
    title: 'Building & Roofing Permits',
    headline: 'Beat Competitors to Every New Construction & Re-Roofing Project in Your County',
    painPoint: 'Contractors waste hours every week manually checking municipal building portals or buy stale permit lists that are already 14 days old.',
    solution: 'OmniLeadFeeder extracts every new building, mechanical, and roofing permit filed in your county within 24 hours of docketing, delivering clean rows into your Google Sheet every morning at 06:00 AM.',
    roiMetric: '1 closed re-roofing job ($12k–$25k) covers 4+ years of data feeds.',
    fields: [
      'permit_number',
      'issue_date',
      'property_address',
      'owner_name',
      'contractor_assigned',
      'valuation_amount',
      'work_description',
      'verification_url',
    ],
    destinations: ['Google Sheets (Auto-Sorted)', 'Zapier / Make Webhook', 'CSV Download'],
    turnaround: 'Daily morning drop (06:00 UTC)',
    ctaText: 'Deploy Roofing Permit Feed ($99 Sprint)',
  },
  {
    id: 'real-estate-investors',
    badge: 'Real Estate & Wholesaling',
    title: 'Probate & Pre-Foreclosure Filings',
    headline: 'Access Motivated Sellers 2 to 3 Weeks Before Stale List Brokers',
    painPoint: 'Real estate investors rely on third-party data brokers who resell 30-to-60 day old probate and foreclosure lists that have already been spammed by hundreds of competitors.',
    solution: 'We extract same-day estate administrations, letters of probate, and notice of defaults directly from the county clerk docket. Fresh off-market leads hit your CRM before anyone else has dialed.',
    roiMetric: 'Direct-from-the-clerk filings arrive weeks before broker syndication.',
    fields: [
      'case_number',
      'filing_date',
      'decedent_name',
      'petitioner_name',
      'attorney_of_record',
      'real_estate_parcel_id',
      'assessed_value',
      'verification_url',
    ],
    destinations: ['Podio / REISift Webhook', 'Google Sheets', 'REST API Endpoint'],
    turnaround: 'Daily morning drop (06:00 UTC)',
    ctaText: 'Deploy Probate & Lien Feed ($99 Sprint)',
  },
  {
    id: 'legal-debt',
    badge: 'Legal Intelligence & Debt Buyers',
    title: "Mechanic's Liens & Civil Dockets",
    headline: 'Automate Legal Research & Eliminate 15 Hours of Paralegal Scraper Time',
    painPoint: 'Paralegals and legal analysts spend 2–3 hours every morning logging into clunky municipal circuit court databases searching for new mechanic’s liens, judgments, and lis pendens filings.',
    solution: 'Fully automated extraction with resilient AST self-healing. When courts update their website layout, our autonomous Dev Swarm prunes selectors and redeploys without breaking your downstream pipeline.',
    roiMetric: 'Saves 15+ hours/wk in manual staff lookups ($1,200/mo net labor savings).',
    fields: [
      'instrument_number',
      'recording_date',
      'claimant_business',
      'respondent_party',
      'lien_principal_amount',
      'legal_description',
      'court_division',
      'verification_url',
    ],
    destinations: ['PostgreSQL Direct Sync', 'REST API Dispatch', 'Google Sheets'],
    turnaround: 'Continuous or Daily Ingestion',
    ctaText: "Deploy Mechanic's Lien Feed ($99 Sprint)",
  },
];

export default function VerticalPlaybooks() {
  const [selectedPlaybook, setSelectedPlaybook] = useState(playbooks[0]);
  const navigate = useNavigate();

  return (
    <section id="playbooks" style={{ padding: '80px 0', borderTop: '1px solid var(--border)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ textAlign: 'center', maxWidth: '820px', margin: '0 auto 48px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(168, 85, 247, 0.1)',
            border: '1px solid rgba(168, 85, 247, 0.25)',
            padding: '5px 14px',
            borderRadius: '20px',
            fontSize: '11px',
            fontWeight: 700,
            color: 'var(--purple)',
            letterSpacing: '1px',
            textTransform: 'uppercase',
            marginBottom: '16px',
          }}>
            Vertical Playbooks &amp; Case Studies
          </div>
          <h2 style={{ fontSize: '34px', fontWeight: 800, color: '#fff', letterSpacing: '-0.6px', lineHeight: 1.25 }}>
            Production Blueprints for High-Intent Lead Feeds
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '12px', lineHeight: 1.6 }}>
            Explore exactly how contractors, real estate operators, and legal teams replace hours of manual portal searches with automated daily public record pipelines.
          </p>
        </div>

        {/* Playbook Selection Tabs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', marginBottom: '36px' }}>
          {playbooks.map((pb) => {
            const isSelected = selectedPlaybook.id === pb.id;
            return (
              <div
                key={pb.id}
                onClick={() => setSelectedPlaybook(pb)}
                style={{
                  background: isSelected ? 'rgba(30, 46, 74, 0.6)' : 'rgba(15, 23, 42, 0.6)',
                  border: `1px solid ${isSelected ? 'var(--cyan)' : 'var(--border)'}`,
                  borderRadius: 'var(--radius-md)',
                  padding: '20px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: isSelected ? '0 0 20px rgba(56, 189, 248, 0.15)' : 'none',
                }}
              >
                <div style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: isSelected ? 'var(--cyan)' : 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
                  {pb.badge}
                </div>
                <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#fff', marginTop: '4px', marginBottom: '8px' }}>
                  {pb.title}
                </h3>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  {pb.headline}
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Playbook Blueprint Container */}
        <div style={{
          background: 'rgba(10, 19, 36, 0.9)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-lg)',
          padding: '36px',
          boxShadow: '0 16px 48px rgba(0, 0, 0, 0.4)',
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '36px' }}>
            {/* Left: Problem & Solution Architecture */}
            <div>
              <div style={{ display: 'inline-block', background: 'rgba(56, 189, 248, 0.1)', color: 'var(--cyan)', padding: '4px 10px', borderRadius: '4px', fontSize: '11px', fontFamily: 'var(--mono)', fontWeight: 700, marginBottom: '12px' }}>
                ARCHITECTURE SPECIFICATION
              </div>
              <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#fff', lineHeight: 1.3, marginBottom: '16px' }}>
                {selectedPlaybook.headline}
              </h3>

              <div style={{ marginBottom: '18px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: '#ef4444', textTransform: 'uppercase', fontFamily: 'var(--mono)', marginBottom: '4px' }}>
                  ✕ The Manual Friction:
                </div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  {selectedPlaybook.painPoint}
                </p>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--green)', textTransform: 'uppercase', fontFamily: 'var(--mono)', marginBottom: '4px' }}>
                  ✓ The Automated Feed Solution:
                </div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  {selectedPlaybook.solution}
                </p>
              </div>

              <div style={{
                background: 'rgba(16, 185, 129, 0.08)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                marginBottom: '24px',
              }}>
                <span style={{ fontSize: '20px' }}>💰</span>
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--green)', fontFamily: 'var(--mono)', fontWeight: 700, textTransform: 'uppercase' }}>
                    Economic ROI Benchmark
                  </div>
                  <div style={{ fontSize: '13px', color: '#fff', fontWeight: 600, marginTop: '2px' }}>
                    {selectedPlaybook.roiMetric}
                  </div>
                </div>
              </div>

              <button
                className="btn btn-primary btn-lg"
                onClick={() => navigate(`/get-started?plan=production&vertical=${encodeURIComponent(selectedPlaybook.title)}`)}
                style={{ fontWeight: 800 }}
              >
                {selectedPlaybook.ctaText} ➔
              </button>
            </div>

            {/* Right: Schema Spec & Integration Destinations */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>Delivered Schema Specification</span>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--mono)', color: 'var(--green)' }}>≥ 95% QA Pass</span>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '24px' }}>
                  {selectedPlaybook.fields.map((field, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontFamily: 'var(--mono)',
                        fontSize: '11px',
                        padding: '4px 10px',
                        background: field === 'verification_url' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(30, 46, 74, 0.6)',
                        border: `1px solid ${field === 'verification_url' ? 'var(--green)' : 'var(--border)'}`,
                        color: field === 'verification_url' ? 'var(--green)' : 'var(--cyan)',
                        borderRadius: '4px',
                      }}
                    >
                      {field === 'verification_url' ? '✓ verification_url' : field}
                    </span>
                  ))}
                </div>

                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', marginBottom: '16px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
                    Supported Sync Destinations
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {selectedPlaybook.destinations.map((dest, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
                        <span style={{ color: 'var(--cyan)' }}>➔</span>
                        <span>{dest}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div style={{
                background: 'rgba(10, 19, 36, 0.8)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: '12px 16px',
                fontSize: '11px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                color: 'var(--text-dim)',
              }}>
                <span>Cadence: <b>{selectedPlaybook.turnaround}</b></span>
                <span style={{ color: 'var(--green)' }}>● Zero Mock Guarantee</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
