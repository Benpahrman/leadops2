import React, { useState } from 'react';

const compliancePillars = [
  {
    iconSvg: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        <polyline points="9 12 11 14 15 10"/>
      </svg>
    ),
    title: 'Statutory Public Domain Mandate',
    subtitle: 'State Open Records & FOIA Compliance',
    description: 'All docket and filing data synthesized by OmniLeadFeeder originates strictly from public-access municipal court dockets, building permit offices, and county recorder repositories governed by state Open Records Acts and the Freedom of Information Act (FOIA).',
    stat: '100% Public Record',
  },
  {
    iconSvg: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
    ),
    title: 'Judicial Precedent Alignment',
    subtitle: 'hiQ Labs v. LinkedIn & Sandvig v. Barr',
    description: 'Our automated pipelines operate strictly within U.S. Federal appellate precedent establishing that automated collection of publicly available, non-authenticated web data does not violate the Computer Fraud and Abuse Act (CFAA) or First Amendment protections.',
    stat: '9th Cir. Precedent',
  },
  {
    iconSvg: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--purple)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
    ),
    title: 'Courteous Zero-Load Ingestion',
    subtitle: 'Off-Peak 06:00 UTC Schedules & Rate Limits',
    description: 'We prioritize municipal infrastructure stability. Headless crawlers execute single-pass ephemeral syncs during off-peak morning windows (06:00 UTC) with conservative request delays, zero brute-force retries, and automated polite backoff.',
    stat: 'Zero Server Strain',
  },
  {
    iconSvg: (
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>
    ),
    title: 'Immutable Provenance & Verification',
    subtitle: 'Direct Clerk Docket URLs on Every Row',
    description: 'Every record streamed into your Google Sheets, webhook, or PostgreSQL database contains an unmodified, clickable direct URL to the official municipal docket or case summary for compliance auditing and legal verification.',
    stat: '1-Click Proof',
  },
];

const faqs = [
  {
    q: 'Is ingesting and monitoring county public records legally compliant?',
    a: 'Yes. State public inspection laws and the federal Freedom of Information Act mandate that court dockets, building permits, tax liens, and deed recordings are public domain information intended for civic transparency. In landmark rulings including hiQ Labs v. LinkedIn (9th Cir. 2022) and Sandvig v. Barr (D.D.C. 2020), courts affirmed that automated access to publicly viewable information without authentication does not violate federal anti-hacking laws (CFAA).',
  },
  {
    q: 'Does OmniLeadFeeder bypass authenticated paywalls or access private data?',
    a: 'No. OmniLeadFeeder strictly limits operations to publicly accessible portals and open municipal registries. We never attempt credential stuffing, password cracking, private account bypassing, or unauthorized access to restricted government intranets. If a municipal court requires user registration or PACER tokens, client-delegated credentials are securely stored in client-isolated Azure Key Vaults.',
  },
  {
    q: 'How does OmniLeadFeeder ensure municipal portal servers are not overloaded?',
    a: 'Our Dev Swarm engineers all Playwright extractors with rate-limiting constraints, polite concurrency caps (max 2 parallel requests per target portal), and intelligent DOM diffing that halts crawling as soon as previously synced docket IDs are encountered. Crawlers execute during off-peak municipal windows (06:00 UTC / night cycles) to ensure zero impact on municipal daytime operations.',
  },
  {
    q: 'Do you collect or resell private consumer PII (SSNs, medical records)?',
    a: 'Never. Municipal dockets naturally redact SSNs and financial account numbers at the court level. OmniLeadFeeder extracts only statutory commercial and legal docket attributes (e.g. Case Number, Filing Date, Party Names, Contractor, Property Parcel, Lien Valuation). We never enrich, append, or syndicate unauthorized consumer PII.',
  },
];

export default function ComplianceTrustSection() {
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <section id="compliance" style={{ padding: '80px 0', borderTop: '1px solid var(--border)', background: 'linear-gradient(180deg, rgba(10, 19, 36, 0.4) 0%, rgba(7, 13, 24, 0.8) 100%)' }}>
      <div className="container">
        {/* Section Header */}
        <div style={{ textAlign: 'center', maxWidth: '820px', margin: '0 auto 52px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            padding: '5px 14px',
            borderRadius: '20px',
            fontSize: '11px',
            fontWeight: 700,
            color: 'var(--green)',
            letterSpacing: '1px',
            textTransform: 'uppercase',
            marginBottom: '16px',
          }}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <polyline points="9 12 11 14 15 10"/>
            </svg>
            Legal &amp; Regulatory Standard
          </div>
          <h2 style={{ fontSize: '34px', fontWeight: 800, color: '#fff', letterSpacing: '-0.6px', lineHeight: 1.25 }}>
            Built for Enterprise Legal, FOIA &amp; Regulatory Compliance
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '12px', lineHeight: 1.6 }}>
            OmniLeadFeeder is engineered from the ground up for strict alignment with statutory open-records laws, judicial precedents, and respectful municipal data ingestion standards.
          </p>
        </div>

        {/* 4 Pillars Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '20px', marginBottom: '56px' }}>
          {compliancePillars.map((pillar, idx) => (
            <div
              key={idx}
              className="card"
              style={{
                background: 'rgba(15, 23, 42, 0.7)',
                backdropFilter: 'blur(12px)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '24px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'transform 0.2s ease, border-color 0.2s ease',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                  <div style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '10px',
                    background: 'rgba(10, 19, 36, 0.8)',
                    border: '1px solid var(--border)',
                    display: 'grid',
                    placeItems: 'center',
                  }}>
                    {pillar.iconSvg}
                  </div>
                  <span style={{
                    fontSize: '11px',
                    fontFamily: 'var(--mono)',
                    color: 'var(--cyan)',
                    background: 'rgba(56, 189, 248, 0.1)',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    border: '1px solid rgba(56, 189, 248, 0.2)',
                  }}>
                    {pillar.stat}
                  </span>
                </div>
                <h3 style={{ fontSize: '17px', fontWeight: 700, color: '#fff', marginBottom: '4px' }}>
                  {pillar.title}
                </h3>
                <div style={{ fontSize: '12px', color: 'var(--cyan)', fontWeight: 600, marginBottom: '10px' }}>
                  {pillar.subtitle}
                </div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  {pillar.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Legal Authority & FAQ Container */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid var(--border-light)',
          borderRadius: 'var(--radius-lg)',
          padding: '36px',
          maxWidth: '920px',
          margin: '0 auto',
          boxShadow: '0 10px 40px rgba(0, 0, 0, 0.4)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(56, 189, 248, 0.15)',
              display: 'grid',
              placeItems: 'center',
              color: 'var(--cyan)',
            }}>
              ⚖️
            </div>
            <div>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>
                Legal &amp; Compliance Frequently Answered Questions
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Clarifying legal frameworks, data provenance, and server etiquette for enterprise buyers.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {faqs.map((faq, index) => {
              const isOpen = openFaq === index;
              return (
                <div
                  key={index}
                  style={{
                    background: isOpen ? 'rgba(30, 46, 74, 0.45)' : 'rgba(10, 19, 36, 0.6)',
                    border: `1px solid ${isOpen ? 'var(--cyan)' : 'var(--border)'}`,
                    borderRadius: 'var(--radius-md)',
                    overflow: 'hidden',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setOpenFaq(isOpen ? null : index)}
                    style={{
                      width: '100%',
                      padding: '16px 20px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: 'none',
                      border: 'none',
                      color: '#fff',
                      fontSize: '14px',
                      fontWeight: 700,
                      textAlign: 'left',
                      cursor: 'pointer',
                    }}
                  >
                    <span>{faq.q}</span>
                    <span style={{
                      color: isOpen ? 'var(--cyan)' : 'var(--text-dim)',
                      transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.2s ease',
                      fontSize: '12px',
                      marginLeft: '12px',
                    }}>
                      ▼
                    </span>
                  </button>
                  {isOpen && (
                    <div style={{ padding: '0 20px 18px', color: 'var(--text-muted)', fontSize: '13px', lineHeight: 1.6, borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '12px' }}>
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Compliance Guarantee Footer Strip */}
          <div style={{
            marginTop: '28px',
            paddingTop: '20px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '14px',
            fontSize: '12px',
            color: 'var(--text-dim)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: 'var(--green)' }}>✓</span>
              <span>Every row includes unmodified municipal proof link</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: 'var(--green)' }}>✓</span>
              <span>Off-peak 06:00 UTC respectful ingestion</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: 'var(--green)' }}>✓</span>
              <span>Zero consumer private PII collection</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
