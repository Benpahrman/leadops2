import React from 'react';

export default function IntakeForm({
  formData,
  setFormData,
  onboardingRoute,
  setOnboardingRoute,
  selectedPlanId,
  isSubmitting,
  onSubmit,
}) {
  return (
    <form onSubmit={onSubmit}>
      <div style={{
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid #1e3355',
        borderRadius: '14px',
        padding: '32px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.36)',
        display: 'flex',
        flexDirection: 'column',
        gap: '28px',
      }}>
        {/* Section 1: Business Identity */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(56, 189, 248, 0.15)', border: '1px solid var(--cyan)', display: 'grid', placeItems: 'center', color: 'var(--cyan)', fontSize: '11px', fontWeight: 800 }}>
              1
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>
              Your Business &amp; Delivery Identity
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '18px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
                Company / Team Name <span style={{ color: 'var(--cyan)' }}>*</span>
              </label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="e.g. Apex Industrial Roofing, BluePeak Capital"
                value={formData.companyName}
                onChange={(e) => setFormData({ ...formData, companyName: e.target.value })}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
                Used to label your pipeline and generate your secure preview sandbox.
              </span>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
                Work / Delivery Email <span style={{ color: 'var(--cyan)' }}>*</span>
              </label>
              <input
                type="email"
                required
                className="form-input"
                placeholder="e.g. alex@yourcompany.com"
                value={formData.contactEmail}
                onChange={(e) => setFormData({ ...formData, contactEmail: e.target.value })}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
                Where automated delivery reports and pipeline status alerts are dispatched.
              </span>
            </div>
          </div>
        </div>

        {/* Section 2: Target Registry & Docket Source */}
        <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(168, 85, 247, 0.15)', border: '1px solid var(--purple)', display: 'grid', placeItems: 'center', color: 'var(--purple)', fontSize: '11px', fontWeight: 800 }}>
              2
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>
              Target Public Registry &amp; Jurisdiction
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '18px', marginBottom: '18px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
                Target Municipal Portal or Registry URL
              </label>
              <input
                type="url"
                className="form-input"
                placeholder="e.g. https://data.cityofchicago.org or county court URL"
                value={formData.targetUrl}
                onChange={(e) => setFormData({ ...formData, targetUrl: e.target.value })}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
                Our Scout Agent will live-scrape 5–10 sample records from this website during setup.
              </span>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
                Target County / Jurisdiction
              </label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Cook County, IL • Travis County, TX • Maricopa, AZ"
                value={formData.jurisdiction}
                onChange={(e) => setFormData({ ...formData, jurisdiction: e.target.value })}
              />
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
                The geographical or legal jurisdiction our swarm should target.
              </span>
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
              What specific filings or records do you need extracted?
            </label>
            <textarea
              className="form-input"
              rows="3"
              placeholder="e.g. Commercial building permits with valuation >$50,000, mechanics liens against corporate debtors, probate and estate filings with executor addresses..."
              value={formData.dataGoal}
              onChange={(e) => setFormData({ ...formData, dataGoal: e.target.value })}
              style={{ resize: 'vertical' }}
            />
            <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
              Our AI DOM Architect uses this description to harvest matching records and configure schema columns.
            </span>
          </div>
        </div>

        {/* Section 3: Delivery Preferences */}
        <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--green)', display: 'grid', placeItems: 'center', color: 'var(--green)', fontSize: '11px', fontWeight: 800 }}>
              3
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>
              Preferred Output Delivery Format
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            {[
              { id: 'Google Sheets', label: 'Google Sheets (Auto-Sync)', desc: 'Real-time tab append' },
              { id: 'Webhook', label: 'Custom Webhook (JSON)', desc: 'Direct CRM / DB ingestion' },
              { id: 'CSV Email', label: 'Daily CSV Email Digest', desc: 'Delivered at 06:00 UTC' },
            ].map((dest) => (
              <label
                key={dest.id}
                onClick={() => setFormData({ ...formData, preferredDestination: dest.id })}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  background: formData.preferredDestination === dest.id ? 'rgba(16, 185, 129, 0.12)' : 'rgba(15, 23, 42, 0.6)',
                  border: formData.preferredDestination === dest.id ? '1px solid var(--green)' : '1px solid #1e3355',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <input
                    type="radio"
                    name="preferredDestination"
                    checked={formData.preferredDestination === dest.id}
                    onChange={() => setFormData({ ...formData, preferredDestination: dest.id })}
                  />
                  <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>{dest.label}</span>
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', marginLeft: '22px' }}>
                  {dest.desc}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Section 4: Onboarding Route Selection */}
        <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
            <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(245, 158, 11, 0.15)', border: '1px solid #f59e0b', display: 'grid', placeItems: 'center', color: '#f59e0b', fontSize: '11px', fontWeight: 800 }}>
              4
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>
              Onboarding Speed &amp; Delivery Preference
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
            {/* Option 2 Card */}
            <div
              onClick={() => setOnboardingRoute('portal')}
              style={{
                padding: '16px 18px',
                borderRadius: '10px',
                background: onboardingRoute === 'portal' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(15, 23, 42, 0.6)',
                border: onboardingRoute === 'portal' ? '2px solid var(--green)' : '1px solid #1e3355',
                cursor: 'pointer',
                transition: 'all 0.2s',
                position: 'relative',
              }}
            >
              <span style={{
                position: 'absolute',
                top: '-9px',
                right: '12px',
                background: 'var(--green)',
                color: '#000',
                fontSize: '9px',
                fontWeight: 800,
                padding: '2px 8px',
                borderRadius: '10px',
                letterSpacing: '0.4px',
              }}>
                FAST-TRACK • ZERO FRICTION
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <input
                  type="radio"
                  name="onboardingRoute"
                  checked={onboardingRoute === 'portal'}
                  onChange={() => setOnboardingRoute('portal')}
                />
                <div style={{ fontSize: '14px', fontWeight: 800, color: '#fff' }}>
                  ⚡ Option 2: Direct to Customer Portal
                </div>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0, paddingLeft: '24px' }}>
                Gather 5–10 sample records, authorize $99 setup sprint via PayPal, and land <b>directly in your Feed Console &amp; Customer Portal</b>. No back-and-forth friction.
              </p>
            </div>

            {/* Option 1 Card */}
            <div
              onClick={() => setOnboardingRoute('sandbox')}
              style={{
                padding: '16px 18px',
                borderRadius: '10px',
                background: onboardingRoute === 'sandbox' ? 'rgba(56, 189, 248, 0.12)' : 'rgba(15, 23, 42, 0.6)',
                border: onboardingRoute === 'sandbox' ? '2px solid var(--cyan)' : '1px solid #1e3355',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <input
                  type="radio"
                  name="onboardingRoute"
                  checked={onboardingRoute === 'sandbox'}
                  onChange={() => setOnboardingRoute('sandbox')}
                />
                <div style={{ fontSize: '14px', fontWeight: 800, color: '#fff' }}>
                  🔍 Option 1: Deliver Interactive Sandbox
                </div>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0, paddingLeft: '24px' }}>
                Gather 5–10 sample records and deliver your bespoke sandbox URL (<code>/p/{'{slug}'}</code>) just like a cold email. Inspect rows &amp; chat with Alex AI before paying.
              </p>
            </div>
          </div>
        </div>

        {/* Refundable Deposit Callout or 3-Day Free Trial Banner */}
        {selectedPlanId === 'trial' ? (
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(56, 189, 248, 0.12))',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            borderRadius: 'var(--radius-md)',
            padding: '18px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
          }}>
            <div style={{ fontSize: '26px', flexShrink: 0 }}>🎁</div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              <b style={{ color: '#fff' }}>3-Day Free Trial Active ($0 Due Today):</b> No credit card required. You'll receive real, verified daily feeds for 3 days directly into your preferred destination ({formData.preferredDestination || 'Google Sheets'}). Experience our 06:00 UTC morning delivery risk-free before making any financial commitment.
            </div>
          </div>
        ) : (
          <div style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(56, 189, 248, 0.08))',
            border: '1px solid #1e3a5f',
            borderRadius: 'var(--radius-md)',
            padding: '18px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
          }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              <b style={{ color: '#fff' }}>100% Refundable Deposit Guarantee:</b> Your setup sprint requires only a <b>$99 down payment</b>, 100% credited toward your first month. The net balance ($151 on Production) activates only after you inspect 25 live government filings passing &ge;95% schema accuracy.
            </div>
          </div>
        )}

        {/* Submit CTA */}
        <div>
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={isSubmitting}
            style={{
              width: '100%',
              fontWeight: 800,
              fontSize: '15px',
              padding: '16px',
              boxShadow: selectedPlanId === 'trial'
                ? '0 4px 24px rgba(16, 185, 129, 0.45)'
                : onboardingRoute === 'portal'
                ? '0 4px 24px rgba(16, 185, 129, 0.35)'
                : '0 4px 24px rgba(56, 189, 248, 0.35)',
              background: selectedPlanId === 'trial'
                ? 'linear-gradient(135deg, #10b981, #047857)'
                : onboardingRoute === 'portal'
                ? 'linear-gradient(135deg, #10b981, #059669)'
                : 'linear-gradient(135deg, #0284c7, #2563eb)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
            }}
          >
            {selectedPlanId === 'trial' ? (
              <span>🎁 Harvest 5–10 Live Records &amp; Start 3-Day Free Trial ($0 Due) ➔</span>
            ) : onboardingRoute === 'portal' ? (
              <span>⚡ Gather 5–10 Live Records &amp; Authorize $99 Setup Sprint ➔</span>
            ) : (
              <span>🔍 Gather 5–10 Live Records &amp; Preview Sandbox ➔</span>
            )}
          </button>
          <div style={{ textAlign: 'center', marginTop: '10px', fontSize: '11px', color: 'var(--text-dim)' }}>
            {selectedPlanId === 'trial'
              ? '🎁 Zero Credit Card Required • Authentic Government Filings • 1-Click Verification'
              : '🔒 256-Bit Encrypted • Real Data Over Promises • Zero Mock Data • 100% Refundable Guarantee'}
          </div>
        </div>
      </div>
    </form>
  );
}
