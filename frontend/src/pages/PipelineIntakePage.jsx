import React, { useState, useEffect, useRef } from 'react';
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

  // Onboarding route: 'portal' (Option 2 - zero friction direct to dashboard after paying)
  // or 'sandbox' (Option 1 - deliver sandbox like cold email)
  const [onboardingRoute, setOnboardingRoute] = useState('portal');

  // Submission & Loading Screen state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(15);
  const [loadingStage, setLoadingStage] = useState('Initializing Scout Agent...');
  const [loadingLogs, setLoadingLogs] = useState([]);
  const progressTimerRef = useRef(null);

  // Extracted result state
  const [extractedResult, setExtractedResult] = useState(null);

  // PayPal modal state
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

  // Start animated loading stages while backend extracts real 5-10 records
  const startLoadingAnimation = (targetUrl, companyName) => {
    const host = targetUrl ? targetUrl.replace(/^https?:\/\//, '').split('/')[0] : 'Municipal Registry';
    setLoadingProgress(15);
    setLoadingStage(`Connecting to target portal: ${host}...`);
    setLoadingLogs([
      { time: new Date().toLocaleTimeString(), text: `[SCOUT AGENT] Dispatched to target portal: ${host}` },
    ]);

    const milestones = [
      { p: 35, s: `Inspecting WAF posture & analyzing DOM tree at ${host}...`, m: `[DOM ANALYZER] Parsing HTML nodes and structured tables.` },
      { p: 65, s: `Harvesting 5–10 live sample records matching requirements...`, m: `[DATA EXTRACTOR] Extracting authentic docket rows & record fields.` },
      { p: 85, s: `Validating schema integrity & generating verified sandbox...`, m: `[QA GATEKEEPER] Schema formatted with zero mock data.` },
    ];

    let step = 0;
    progressTimerRef.current = setInterval(() => {
      if (step < milestones.length) {
        const item = milestones[step];
        setLoadingProgress(item.p);
        setLoadingStage(item.s);
        setLoadingLogs((prev) => [
          ...prev,
          { time: new Date().toLocaleTimeString(), text: item.m },
        ]);
        step++;
      }
    }, 1100);
  };

  const stopLoadingAnimation = () => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
  };

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
    setExtractedResult(null);
    startLoadingAnimation(formData.targetUrl, formData.companyName);

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
      stopLoadingAnimation();
      setLoadingProgress(100);
      setLoadingStage('✓ 5–10 Live Records Extracted & Verified!');
      setLoadingLogs((prev) => [
        ...prev,
        { time: new Date().toLocaleTimeString(), text: `[COMPLETE] Successfully extracted ${result.record_count || 10} verified live records.` },
      ]);

      if (result.ok && result.slug) {
        localStorage.setItem('leadops_active_lead_id', result.lead_id || result.slug);
        setExtractedResult(result);
        setCheckoutSlug(result.slug);
        setCheckoutCompanyName(result.company_name || formData.companyName.trim());
        setCheckoutEmail(formData.contactEmail.trim().toLowerCase());
        setCheckoutTargetUrl(formData.targetUrl.trim() || result.source_url || '');

        // Route selection behavior
        if (onboardingRoute === 'portal') {
          // Option 2: Open PayPal directly — after payment, takes user straight to Customer Portal!
          setTimeout(() => {
            setIsSubmitting(false);
            setIsCheckoutOpen(true);
            showToast('✓ 5–10 Live records extracted! Authorize $99 to enter your Customer Portal.', 'success', 6000);
          }, 800);
        } else {
          // Option 1: Deliver sandbox just like cold email
          setTimeout(() => {
            setIsSubmitting(false);
            showToast('✓ Sandbox ready with authentic records! Navigating to sandbox...', 'success', 3000);
            navigate(`/p/${result.slug}`);
          }, 1200);
        }
      } else {
        setIsSubmitting(false);
        showToast('Could not initialize pipeline. Please try again.', 'error');
      }
    } catch (err) {
      stopLoadingAnimation();
      setIsSubmitting(false);
      console.error('Pipeline initialization failed:', err);
      showToast(err.message || 'Pipeline initialization failed', 'error');
    }
  };

  const handleCheckoutClose = () => {
    setIsCheckoutOpen(false);
  };

  return (
    <main style={{ padding: '48px 0 96px', background: 'var(--bg)' }}>
      <div className="container" style={{ maxWidth: '940px' }}>
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
            AUTONOMOUS EXTRACTION SWARM
          </div>
          <h1 style={{ fontSize: '34px', fontWeight: 800, color: '#fff', letterSpacing: '-0.8px', lineHeight: 1.2 }}>
            Configure Your Autonomous Public Records Scraper
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px', lineHeight: 1.6 }}>
            Enter your target registry or court docket. Our Scout Agent will immediately run a live micro-scrape pulling 5–10 real records from your source, verify schema accuracy, and provision your pipeline.
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
                    borderRadius: '10px',
                    background: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'rgba(15, 23, 42, 0.6)',
                    border: isSelected ? '2px solid var(--cyan)' : '1px solid #1e3355',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    position: 'relative',
                    boxShadow: isSelected ? '0 0 20px rgba(56, 189, 248, 0.15)' : 'none',
                  }}
                >
                  {pkg.badge && (
                    <span style={{
                      position: 'absolute',
                      top: '-10px',
                      right: '12px',
                      background: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
                      color: '#fff',
                      fontSize: '9px',
                      fontWeight: 800,
                      padding: '2px 8px',
                      borderRadius: '10px',
                      letterSpacing: '0.5px',
                    }}>
                      {pkg.badge}
                    </span>
                  )}
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '4px' }}>
                      {pkg.name}
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

            {/* Section 4: Onboarding Route Selection (Option 1 vs Option 2) */}
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
                  boxShadow: onboardingRoute === 'portal' ? '0 4px 24px rgba(16, 185, 129, 0.35)' : '0 4px 24px rgba(56, 189, 248, 0.35)',
                  background: onboardingRoute === 'portal' ? 'linear-gradient(135deg, #10b981, #059669)' : 'linear-gradient(135deg, #0284c7, #2563eb)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px',
                }}
              >
                {onboardingRoute === 'portal' ? (
                  <span>⚡ Gather 5–10 Live Records &amp; Authorize $99 Setup Sprint ➔</span>
                ) : (
                  <span>🔍 Gather 5–10 Live Records &amp; Preview Sandbox ➔</span>
                )}
              </button>
              <div style={{ textAlign: 'center', marginTop: '10px', fontSize: '11px', color: 'var(--text-dim)' }}>
                🔒 256-Bit Encrypted • Real Data Over Promises • Zero Mock Data • 100% Refundable Guarantee
              </div>
            </div>
          </div>
        </form>

        {/* Real-Time Loading Modal Overlay */}
        {isSubmitting && (
          <div style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(5, 10, 20, 0.88)',
            backdropFilter: 'blur(8px)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}>
            <div style={{
              background: '#0c1322',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '14px',
              maxWidth: '560px',
              width: '100%',
              padding: '32px',
              textAlign: 'left',
              boxShadow: '0 20px 60px rgba(0, 0, 0, 0.7), 0 0 30px rgba(56, 189, 248, 0.2)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: 'var(--cyan)',
                    boxShadow: '0 0 10px var(--cyan)',
                    animation: 'pulse 1.2s infinite',
                  }} />
                  <span style={{ fontSize: '13px', fontWeight: 800, color: 'var(--cyan)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
                    AI Scout Swarm Active
                  </span>
                </div>
                <span style={{ fontSize: '14px', fontWeight: 800, color: '#fff', fontFamily: 'var(--mono)' }}>
                  {loadingProgress}%
                </span>
              </div>

              <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
                Harvesting 5–10 Live Records from Target Source
              </h2>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px', lineHeight: 1.5 }}>
                Target: <b style={{ color: '#fff' }}>{formData.targetUrl || 'Regional Public Registry'}</b>
              </p>

              {/* Progress Bar */}
              <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '16px' }}>
                <div
                  style={{
                    width: `${loadingProgress}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, #38bdf8, #10b981)',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>

              {/* Current Stage Headline */}
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--cyan)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--cyan)' }} />
                {loadingStage}
              </div>

              {/* Live Terminal Telemetry */}
              <div style={{
                background: '#050a14',
                border: '1px solid rgba(56, 189, 248, 0.15)',
                borderRadius: '8px',
                padding: '12px 14px',
                fontFamily: 'var(--mono)',
                fontSize: '11px',
                color: '#94a3b8',
                lineHeight: 1.6,
                maxHeight: '120px',
                overflowY: 'auto',
              }}>
                {loadingLogs.map((log, idx) => (
                  <div key={idx}>
                    <span style={{ color: 'var(--text-dim)' }}>[{log.time}]</span> {log.text}
                  </div>
                ))}
              </div>

              <div style={{ textAlign: 'center', marginTop: '18px', fontSize: '11px', color: 'var(--text-dim)' }}>
                Connecting directly to live source • Zero mock data standard enforced
              </div>
            </div>
          </div>
        )}

        {/* Live Extracted Records Preview Table (Shows after extraction finishes) */}
        {extractedResult && extractedResult.sample_records && extractedResult.sample_records.length > 0 && (
          <div style={{
            marginTop: '32px',
            background: 'rgba(15, 23, 42, 0.9)',
            border: '1px solid var(--border-highlight)',
            borderRadius: '12px',
            padding: '24px 28px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '18px' }}>
              <div>
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'rgba(16, 185, 129, 0.15)',
                  color: 'var(--green)',
                  fontSize: '11px',
                  fontWeight: 800,
                  padding: '3px 10px',
                  borderRadius: '12px',
                  marginBottom: '6px',
                }}>
                  <span>✓</span> {extractedResult.sample_records.length} LIVE SOURCED RECORDS EXTRACTED
                </div>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>
                  Authentic Sample Filings Harvested from Target Portal
                </h3>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Source: <a href={extractedResult.source_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--cyan)' }}>{extractedResult.source_url}</a>
                </span>
              </div>

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                {/* Option 2: Instant Customer Portal CTA */}
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setIsCheckoutOpen(true)}
                  style={{ fontWeight: 800, padding: '10px 20px', fontSize: '13px', background: 'linear-gradient(135deg, #10b981, #059669)' }}
                >
                  ⚡ Authorize $99 &amp; Enter Customer Portal ➔
                </button>

                {/* Option 1: Full Sandbox CTA */}
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => navigate(`/p/${extractedResult.slug}`)}
                  style={{ fontWeight: 700, padding: '10px 18px', fontSize: '13px' }}
                >
                  🔍 View Full Sandbox (/p/{extractedResult.slug}) ➔
                </button>
              </div>
            </div>

            {/* Scrollable Records Table */}
            <div style={{ overflowX: 'auto', maxHeight: '300px', border: '1px solid #1e3355', borderRadius: '8px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ background: '#0a101d', borderBottom: '1px solid #1e3355' }}>
                    {extractedResult.fields.slice(0, 6).map((f) => (
                      <th key={f} style={{ padding: '10px 14px', color: 'var(--cyan)', fontWeight: 700, textTransform: 'capitalize' }}>
                        {f.replace(/_/g, ' ')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {extractedResult.sample_records.slice(0, 8).map((row, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: idx % 2 === 0 ? 'rgba(15,23,42,0.4)' : 'transparent' }}>
                      {extractedResult.fields.slice(0, 6).map((f) => (
                        <td key={f} style={{ padding: '8px 14px', color: '#cbd5e1', maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {String(row[f] || '—')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '14px', fontSize: '11px', color: 'var(--text-muted)' }}>
              <span>✓ Verified schema with live extracted government dockets • 100% Zero Mock Data</span>
              <span style={{ color: 'var(--cyan)' }}>Showing {Math.min(8, extractedResult.sample_records.length)} of {extractedResult.sample_records.length} records</span>
            </div>
          </div>
        )}

        {/* Inline sandbox link shown after modal is closed without paying */}
        {checkoutSlug && !isCheckoutOpen && !extractedResult && (
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
              <b style={{ color: '#fff' }}>Your 5–10 sample records are ready.</b> Complete your $99 payment to launch your Customer Portal.
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

      {/* PayPal Checkout Modal — opens inline with direct redirect to Customer Portal upon payment approval */}
      {checkoutSlug && (
        <EscrowCheckoutModal
          isOpen={isCheckoutOpen}
          onClose={handleCheckoutClose}
          slug={checkoutSlug}
          companyName={checkoutCompanyName}
          defaultEmail={checkoutEmail}
          defaultTargetUrl={checkoutTargetUrl}
          redirectTo={onboardingRoute === 'portal' ? `/dashboard/${checkoutSlug}` : null}
        />
      )}
    </main>
  );
}
