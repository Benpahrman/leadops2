import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { initializePipeline } from '../services/api';
import { useToast } from '../context/ToastContext';
import EscrowCheckoutModal from '../components/sandbox/EscrowCheckoutModal';

const PACKAGES = [
  {
    id: 'starter',
    name: 'Starter Docket Feed',
    tierKey: 'weekly',
    price: '$150/mo',
    cadence: 'Weekly Batch (4x / mo)',
    records: 'Up to 2,000 filings/mo',
    desc: 'Single-county municipal registries, boutique legal teams, or weekly recap pipelines.',
  },
  {
    id: 'production',
    name: 'Production Feed',
    tierKey: 'daily',
    price: '$250/mo',
    badge: 'RECOMMENDED',
    cadence: 'Daily Morning (06:00 UTC)',
    records: 'Up to 15,000 filings/mo',
    desc: 'Our flagship daily feed. Autonomous Cloudflare/WAF bypass, custom schema mapping, and self-healing AST repair.',
  },
  {
    id: 'enterprise',
    name: 'Enterprise Swarm',
    tierKey: 'enterprise',
    price: '$590/mo',
    cadence: 'Hourly / Continuous Sync',
    records: 'Unlimited filings/mo',
    desc: 'Continuous multi-county monitoring, automated PDF OCR extraction, and private proxy pools.',
  },
  {
    id: 'buyout',
    name: 'Perpetual Code Buyout',
    tierKey: 'buyout',
    price: '$1,500 One-Time',
    cadence: 'Self-Hosted Runtime',
    records: 'Unlimited & Autonomous',
    desc: 'Standalone Playwright & Python AST pipeline repository (.zip) for 100% self-hosted perpetual operation.',
  },
];

export default function PipelineIntakePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const initialPlanParam = searchParams.get('plan') || 'production';
  const [selectedPlanId, setSelectedPlanId] = useState(initialPlanParam);

  const [formData, setFormData] = useState({
    companyName: '',
    contactEmail: '',
    targetUrl: '',
    jurisdiction: '',
    dataGoal: '',
    preferredDestination: 'Google Sheets',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  // PayPal modal state — populated after successful pipeline init
  const [checkoutSlug, setCheckoutSlug] = useState(null);
  const [checkoutCompanyName, setCheckoutCompanyName] = useState('');
  const [checkoutEmail, setCheckoutEmail] = useState('');
  const [checkoutTargetUrl, setCheckoutTargetUrl] = useState('');
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);

  useEffect(() => {
    const planParam = searchParams.get('plan');
    if (planParam && PACKAGES.some((p) => p.id === planParam)) {
      setSelectedPlanId(planParam);
    }
  }, [searchParams]);

  const selectedPackage = PACKAGES.find((p) => p.id === selectedPlanId) || PACKAGES[1];

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.companyName.trim()) {
      showToast('Please provide your company or business name.', 'error');
      return;
    }
    if (!formData.contactEmail || !formData.contactEmail.includes('@')) {
      showToast('Please provide a valid work email address.', 'error');
      return;
    }

    setIsSubmitting(true);
    showToast('Provisioning your verified live sandbox...', 'info');

    try {
      const payload = {
        company_name: formData.companyName.trim(),
        contact_email: formData.contactEmail.trim().toLowerCase(),
        target_url: formData.targetUrl.trim(),
        jurisdiction: formData.jurisdiction.trim(),
        data_goal: formData.dataGoal.trim(),
        tier_key: selectedPackage.tierKey,
        preferred_destination: formData.preferredDestination,
      };

      const result = await initializePipeline(payload);

      if (result.ok && result.slug) {
        localStorage.setItem('leadops_active_lead_id', result.lead_id || result.slug);

        // Populate checkout modal with returned lead data and open PayPal RIGHT HERE
        setCheckoutSlug(result.slug);
        setCheckoutCompanyName(result.company_name || formData.companyName.trim());
        setCheckoutEmail(formData.contactEmail.trim().toLowerCase());
        setCheckoutTargetUrl(formData.targetUrl.trim() || result.source_url || '');
        setIsCheckoutOpen(true);

        showToast('✓ Sandbox ready! Complete your $99 Setup Sprint payment below.', 'success', 5000);
      } else {
        showToast('Could not initialize pipeline. Please try again.', 'error');
      }
    } catch (err) {
      console.error('Pipeline initialization failed:', err);
      showToast(err.message || 'Pipeline initialization failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCheckoutClose = () => {
    setIsCheckoutOpen(false);
  };

  // After successful PayPal payment the modal navigates to /checkout/success
  // but if the user just closes the modal, offer them the sandbox link
  const handlePaymentSuccess = () => {
    // EscrowCheckoutModal handles navigation to /checkout/success internally
    setIsCheckoutOpen(false);
  };

  return (
    <main style={{ padding: '48px 0 96px', background: 'var(--bg)' }}>
      <div className="container" style={{ maxWidth: '920px' }}>
        {/* Navigation Breadcrumb */}
        <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
          <button
            type="button"
            onClick={() => navigate('/#pricing')}
            style={{ background: 'none', border: 'none', color: 'var(--cyan)', cursor: 'pointer', padding: 0, fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
          >
            ← Back to Pricing
          </button>
          <span>/</span>
          <span style={{ color: '#fff' }}>Configure Custom Extraction Pipeline</span>
        </div>

        {/* Header Title */}
        <div style={{ marginBottom: '36px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(56, 189, 248, 0.1)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            padding: '4px 12px',
            borderRadius: '20px',
            fontSize: '11px',
            fontWeight: 700,
            color: 'var(--cyan)',
            textTransform: 'uppercase',
            letterSpacing: '0.8px',
            marginBottom: '12px',
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--cyan)' }}></span>
            ENTERPRISE PIPELINE CONFIGURATOR
          </div>
          <h1 style={{ fontSize: '34px', fontWeight: 800, color: '#fff', letterSpacing: '-0.8px', lineHeight: 1.2 }}>
            Configure Your Autonomous Public Records Scraper
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px', lineHeight: 1.6 }}>
            Fill in your target government registry or municipal court docket below. After submitting, you'll authorize your $99 refundable deposit via PayPal — no navigation required.
          </p>
        </div>

        {/* Selected Package Selector Grid */}
        <div style={{ marginBottom: '32px' }}>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--cyan)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '12px' }}>
            Selected Ingestion Package
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            {PACKAGES.map((pkg) => {
              const isSelected = pkg.id === selectedPlanId;
              return (
                <div
                  key={pkg.id}
                  onClick={() => setSelectedPlanId(pkg.id)}
                  style={{
                    padding: '16px 18px',
                    borderRadius: 'var(--radius-md)',
                    background: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'rgba(15, 23, 42, 0.7)',
                    border: isSelected ? '1px solid var(--cyan)' : '1px solid #1e3355',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    boxShadow: isSelected ? '0 0 16px rgba(56, 189, 248, 0.2)' : 'none',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                      <span style={{ fontSize: '13px', fontWeight: 800, color: '#fff' }}>{pkg.name}</span>
                      {pkg.badge && (
                        <span style={{ fontSize: '9px', fontWeight: 800, background: 'var(--green)', color: '#041410', padding: '2px 5px', borderRadius: '4px' }}>
                          {pkg.badge}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '18px', fontWeight: 800, color: isSelected ? 'var(--cyan)' : '#fff', fontFamily: 'var(--mono)' }}>
                      {pkg.price}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                      {pkg.cadence}
                    </div>
                  </div>
                  <div style={{ marginTop: '12px', fontSize: '11px', color: isSelected ? 'var(--cyan)' : 'var(--text-dim)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>{isSelected ? '✓ Selected' : 'Select'}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Configuration Form */}
        <form onSubmit={handleSubmit}>
          <div className="card" style={{ padding: '36px 32px', background: 'rgba(15, 23, 42, 0.85)', border: '1px solid #1e3355', display: 'flex', flexDirection: 'column', gap: '28px' }}>
            {/* Section 1: Organization & Contact */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(56, 189, 248, 0.15)', border: '1px solid var(--cyan)', display: 'grid', placeItems: 'center', color: 'var(--cyan)', fontSize: '11px', fontWeight: 800 }}>
                  1
                </div>
                <h2 style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>
                  Organization &amp; Primary Contact
                </h2>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '18px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
                    Company / Organization Name <span style={{ color: 'var(--cyan)' }}>*</span>
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
                    Municipal Portal or Court Docket URL
                  </label>
                  <input
                    type="url"
                    className="form-input"
                    placeholder="e.g. https://data.cityofchicago.org or county court URL"
                    value={formData.targetUrl}
                    onChange={(e) => setFormData({ ...formData, targetUrl: e.target.value })}
                  />
                  <span style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'block' }}>
                    Leave blank to use our pre-verified standard municipal portal in your jurisdiction.
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
                  Our AI DOM Architect uses this description to configure schema columns and filter logic.
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

            {/* Refundable Deposit Callout */}
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
                  boxShadow: '0 4px 24px rgba(16, 185, 129, 0.35)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                }}
              >
                {isSubmitting ? (
                  <>
                    <span style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.8s linear infinite', display: 'inline-block' }}></span>
                    <span>Preparing Sandbox &amp; Opening PayPal...</span>
                  </>
                ) : (
                  <span>Authorize $99 Setup Sprint via PayPal ➔</span>
                )}
              </button>
              <div style={{ textAlign: 'center', marginTop: '10px', fontSize: '11px', color: 'var(--text-dim)' }}>
                🔒 256-Bit Encrypted • PayPal, Visa, Mastercard, AMEX &amp; Discover • 100% Refundable if Unfulfilled
              </div>
            </div>
          </div>
        </form>

        {/* Inline sandbox link shown after modal is closed without paying */}
        {checkoutSlug && !isCheckoutOpen && (
          <div style={{
            marginTop: '24px',
            padding: '16px 20px',
            background: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap',
          }}>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              <b style={{ color: '#fff' }}>Your sandbox is ready.</b> Complete your $99 payment to activate your pipeline.
            </div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => setIsCheckoutOpen(true)}
                style={{ fontWeight: 800, padding: '8px 18px', fontSize: '13px' }}
              >
                🔒 Pay $99 via PayPal
              </button>
              <button
                type="button"
                onClick={() => navigate(`/p/${checkoutSlug}`)}
                style={{ background: 'none', border: '1px solid #1e3355', color: 'var(--cyan)', borderRadius: '8px', padding: '8px 14px', cursor: 'pointer', fontSize: '12px' }}
              >
                View Sandbox First
              </button>
            </div>
          </div>
        )}
      </div>

      {/* PayPal Checkout Modal — opens inline after form submit */}
      {checkoutSlug && (
        <EscrowCheckoutModal
          isOpen={isCheckoutOpen}
          onClose={handleCheckoutClose}
          slug={checkoutSlug}
          companyName={checkoutCompanyName}
          defaultEmail={checkoutEmail}
          defaultTargetUrl={checkoutTargetUrl}
        />
      )}
    </main>
  );
}
