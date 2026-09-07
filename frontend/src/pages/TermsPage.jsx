import React from 'react';
import { Link } from 'react-router-dom';

export default function TermsPage() {
  return (
    <main style={{ padding: '50px 0 90px' }}>
      <div className="container" style={{ maxWidth: '860px' }}>
        <div style={{ marginBottom: '32px', borderBottom: '1px solid var(--border)', paddingBottom: '20px' }}>
          <span className="badge-tag badge-cyan">LEGAL &amp; COMPLIANCE SPECIFICATION</span>
          <h1 style={{ fontSize: '32px', fontWeight: 800, color: '#fff', marginTop: '10px' }}>
            Statement of Work (SOW) &amp; Terms of Service
          </h1>
          <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px' }}>
            Last Updated: September 7, 2026 • Governing Agreement for OmniLeadFeeder Autonomous Feeds
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '28px', lineHeight: 1.7, fontSize: '14px', color: '#cbd5e1' }}>
          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              1. Engineering Scope of Work (SOW)
            </h2>
            <p>
              OmniLeadFeeder ("Provider") deploys a proprietary 7-agent autonomous engineering swarm (Planner, DOM Architect, Stealth Engineer, Systems Architect, Junior Dev, QA Gatekeeper) to synthesize, test, and maintain custom Python/Playwright extraction crawlers targeting public government registries, court dockets, and municipal portals specified by the Client.
            </p>
          </section>

          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              2. 50% Milestone Escrow Guarantee
            </h2>
            <p>
              All custom extractor builds adhere to an escrow-protected two-milestone schedule:
            </p>
            <ul style={{ paddingLeft: '20px', marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <li>
                <b>Milestone #1 ($250.00 USD):</b> Setup deposit locked in escrow upon order initiation. Authorizes initial DOM AST analysis, residential proxy provisioning, and extractor code compilation.
              </li>
              <li>
                <b>Milestone #2 ($250.00 USD):</b> Final balance payable <i>only after</i> the Independent QA Gatekeeper and Client verify 25 live, accurate sample records against the authentic public registry (&gt;=95.0% QA Score).
              </li>
              <li>
                <b>100% Refund Guarantee:</b> If the autonomous swarm fails to produce a verified 25-row extraction feed within 24 hours of order placement, Milestone #1 is automatically refunded in full.
              </li>
            </ul>
          </section>

          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              3. Delivery Service Level Agreement (SLA)
            </h2>
            <p>
              Automated data streams are scheduled for daily delivery every morning at <b>08:00 AM (Client Local Time)</b> or <b>06:00 AM UTC</b> directly into the Client's authenticated Google Sheets destination or webhook endpoint. Batches include deduplicated primary keys, normalized schema fields, and 1-click source verification links.
            </p>
          </section>

          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              4. Anti-Bot Defense &amp; 4-Hour Repair SLA
            </h2>
            <p>
              Provider maintains residential proxy pools and browser fingerprint spoofing (WebGL, navigator.webdriver concealment, Client Hints) to navigate Cloudflare Turnstile, reCAPTCHA, and WAF defenses passively. If a target jurisdiction alters its DOM layout or bot shields, Provider commits to an autonomous re-engineering turnaround of <b>under 4 hours</b>.
            </p>
          </section>

          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              5. Zero-Mock Data Policy
            </h2>
            <p>
              Provider contractually warrants that <b>zero synthetic or fabricated rows</b> are ever delivered as live data. Every row delivered is scraped in real-time from official public sources and includes a verifiable government docket URL.
            </p>
          </section>

          <section>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
              6. Cancellation, Pausing &amp; Codebase Buyout
            </h2>
            <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <li>
                <b>30-Day Flexible Pause:</b> Clients may pause automated deliveries for 30 days via their dashboard at zero penalty, preserving all custom selector maps.
              </li>
              <li>
                <b>Self-Service Cancellation:</b> Subscriptions may be cancelled anytime via the dashboard prior to the next billing cycle.
              </li>
              <li>
                <b>Perpetual Code Buyout ($1,500):</b> Clients may exercise a permanent buyout option to acquire the standalone, self-hosted Python Playwright codebase (.zip) with full commercial ownership rights.
              </li>
            </ul>
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
