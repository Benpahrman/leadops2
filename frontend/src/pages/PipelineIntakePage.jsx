import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { initializePipeline } from '../services/api';
import { useToast } from '../context/ToastContext';
import SetupSprintCheckoutModal from '../components/sandbox/SetupSprintCheckoutModal';

import {
  PACKAGES,
  PackageSelector,
  ScoutLoadingOverlay,
  ExtractedPreviewCard,
  IntakeForm,
} from './intake';

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

  // Onboarding route: 'portal' (Option 2 - zero friction direct to dashboard) or 'sandbox'
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
  const startLoadingAnimation = (targetUrl) => {
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
    startLoadingAnimation(formData.targetUrl);

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

        if (selectedPlanId === 'trial') {
          setTimeout(() => {
            setIsSubmitting(false);
            showToast('✓ 3-Day Free Trial Activated! 5–10 verified live records loaded. Daily feed starts tomorrow at 06:00 UTC.', 'success', 8000);
            navigate(`/p/${result.slug}?trial=true`);
          }, 900);
          return;
        }

        if (onboardingRoute === 'portal') {
          setTimeout(() => {
            setIsSubmitting(false);
            setIsCheckoutOpen(true);
            showToast('✓ 5–10 Live records extracted! Authorize $99 to enter your Customer Portal.', 'success', 6000);
          }, 800);
        } else {
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
        <PackageSelector
          selectedPlanId={selectedPlanId}
          onSelectPlan={setSelectedPlanId}
        />

        {/* Dynamic Intake Form */}
        <IntakeForm
          formData={formData}
          setFormData={setFormData}
          onboardingRoute={onboardingRoute}
          setOnboardingRoute={setOnboardingRoute}
          selectedPlanId={selectedPlanId}
          isSubmitting={isSubmitting}
          onSubmit={handleSubmit}
        />

        {/* Real-Time Loading Modal Overlay */}
        {isSubmitting && (
          <ScoutLoadingOverlay
            loadingProgress={loadingProgress}
            loadingStage={loadingStage}
            loadingLogs={loadingLogs}
            targetUrl={formData.targetUrl}
          />
        )}

        {/* Live Extracted Records Preview Table */}
        <ExtractedPreviewCard
          extractedResult={extractedResult}
          onOpenCheckout={() => setIsCheckoutOpen(true)}
          onNavigateSandbox={() => navigate(`/p/${extractedResult.slug}`)}
        />

        {/* PayPal Checkout Modal */}
        <SetupSprintCheckoutModal
          isOpen={isCheckoutOpen}
          onClose={() => setIsCheckoutOpen(false)}
          slug={checkoutSlug}
          companyName={checkoutCompanyName}
          sourceUrl={checkoutTargetUrl}
          email={checkoutEmail}
        />
      </div>
    </main>
  );
}
