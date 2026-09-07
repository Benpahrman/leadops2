import React from 'react';
import { Link } from 'react-router-dom';

export default function PrivacyPage() {
  return (
    <main style={{ padding: '50px 0 90px' }}>
      <div className="container" style={{ maxWidth: '860px' }}>
        <div style={{ marginBottom: '32px', borderBottom: '1px solid var(--border)', paddingBottom: '20px' }}>
          <span className="badge-tag badge-green">PRIVACY &amp; DATA GOVERNANCE</span>
          <h1 style={{ fontSize: '32px', fontWeight: 800, color: '#fff', marginTop: '10px' }}>
            Privacy &amp; Data Protection Policy
          </h1>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px' }}>
            Effective: September 7, 2026 • OmniLeadFeeder Data Intelligence
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '28px', lineHeight: 1.7, fontSize: '14px', color: '#cbd5e1' }}>
          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              1. Information We Collect
            </h2>
            <p>
              OmniLeadFeeder collects only information necessary to deliver enterprise data pipeline services:
            </p>
            <ul style={{ paddingLeft: '20px', marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <li><b>Account Information:</b> Company name, contact email, and delivery destination URLs (Google Sheets or Webhooks).</li>
              <li><b>Payment Telemetry:</b> Transaction IDs and escrow verification tokens managed securely via PayPal or Stripe. We never store raw credit card numbers.</li>
              <li><b>Audit Telemetry:</b> Client IP address, browser signature, and timestamp recorded during digital Statement of Work (SOW) clickwrap acceptance for mutual legal verification.</li>
            </ul>
          </section>

          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              2. Public Records Ingestion &amp; FOIA Compliance
            </h2>
            <p>
              Data extracted by our autonomous crawlers originates exclusively from open government records, judicial dockets, building departments, and statutory filings made available under the Freedom of Information Act (FOIA) and municipal sunshine laws. We do not aggregate non-public consumer credit data or confidential personal records.
            </p>
          </section>

          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              3. Data Security &amp; Encryption
            </h2>
            <p>
              All customer delivery endpoints, webhook signatures, and extraction credentials are encrypted at rest using <b>AES-256</b> and transmitted over authenticated <b>TLS 1.3</b> connections. Our cloud infrastructure runs on Microsoft Azure with role-based access control and strict network boundaries.
            </p>
          </section>

          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              4. Data Retention &amp; Right to Deletion
            </h2>
            <p>
              Upon request or subscription termination, clients may request the immediate purging of all cached extraction batches and historical records from our systems within 48 business hours by contacting <b>support@omnileadfeeder.tech</b>.
            </p>
          </section>
        </div>

        <div style={{ marginTop: '24px', textAlign: 'center' }}>
          <Link to="/" className="btn btn-outline">
            ← Return to Homepage
          </Link>
        </div>
      </div>
    </main>
  );
}
