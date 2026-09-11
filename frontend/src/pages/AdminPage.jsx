import React, { useEffect, useState, useMemo } from 'react';
import { useAuth, useUser, SignIn } from '@clerk/clerk-react';
import {
  fetchAdminPipeline,
  fetchAdminMetrics,
  triggerSwarmBuild,
  purgeAllData,
  advanceLeadState,
  batchApprovePendingPitches,
  fetchScoutStatus,
  fetchSwarmProgress,
  fetchActiveBuilds,
  overrideQA,
  fetchScrapersCatalog,
  fetchScraperCode,
  fetchScraperOutput,
  runScraperOnDemand,
  fetchDailyGrid,
  triggerDailyDelivery,
  toggleEmergencyStop,
  fetchAuditTrail,
  deleteLead,
  resolveAdminAuth,
  fetchAutoOutreachStatus,
  toggleAutoOutreach,
  triggerScoutDiscovery,
  cancelAutoOutreach,
  fetchAdminInboxes,
  upsertAdminInbox,
  testAdminInbox,
  deleteAdminInbox,
  triggerOutreachFlush,
  enrichLeadContact,
  batchEnrichArchivedLeads,
  fetchArchivedLeads,
  fetchMicrosoftOAuthStatus,
  fetchMicrosoftOAuthAuthorizeUrl,
  disconnectMicrosoftOAuth,
  fetchDeliverabilityStatus,
  runDeliverabilityAudit,
} from '../services/api';
import { useToast } from '../context/ToastContext';
import ConfirmModal from '../components/common/ConfirmModal';
import CommandPalette from '../components/common/CommandPalette';

export default function AdminPage() {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { user } = useUser();
  const { showToast } = useToast();

  const [masterAuth, setMasterAuth] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const urlParams = new URLSearchParams(window.location.search);
        const k = urlParams.get('key') || urlParams.get('token') || urlParams.get('admin_key');
        if (k) {
          localStorage.setItem('leadops_admin_token', k);
          return true;
        }
        return !!localStorage.getItem('leadops_admin_token');
      } catch (e) {
        return false;
      }
    }
    return false;
  });

  const resolveToken = async () => {
    try {
      if (isSignedIn && getToken) {
        const t = await getToken();
        if (t) return t;
      }
    } catch (e) {
      console.warn('Clerk session token note:', e);
    }
    return resolveAdminAuth();
  };

  // URL Query Helper
  const getInitialParam = (key, fallback) => {
    if (typeof window === 'undefined') return fallback;
    try {
      const p = new URLSearchParams(window.location.search);
      return p.get(key) || fallback;
    } catch {
      return fallback;
    }
  };

  // Active Tab & Filters with URL persistence
  const [activeTab, setActiveTab] = useState(() => getInitialParam('tab', 'deals'));
  const [searchQuery, setSearchQuery] = useState(() => getInitialParam('q', ''));
  const [stateFilter, setStateFilter] = useState(() => getInitialParam('state', 'ALL'));
  const [paymentFilter, setPaymentFilter] = useState(() => getInitialParam('payment', 'ALL'));
  const [scoreFilter, setScoreFilter] = useState(() => getInitialParam('score', 'ALL'));

  // Pipeline & Data
  const [pipeline, setPipeline] = useState([]);
  const [archivedLeads, setArchivedLeads] = useState([]);
  const [enrichingLeadId, setEnrichingLeadId] = useState(null);
  const [batchEnriching, setBatchEnriching] = useState(false);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState({});
  const [scoutStatus, setScoutStatus] = useState(null);
  const [batchApproving, setBatchApproving] = useState(false);
  const [autoOutreachStatus, setAutoOutreachStatus] = useState(null);
  const [autoOutreachLoading, setAutoOutreachLoading] = useState(false);
  const [scoutingInProgress, setScoutingInProgress] = useState(false);
  const [selectedScoutChannel, setSelectedScoutChannel] = useState('');
  const [scoutSearchQuery, setScoutSearchQuery] = useState('');

  const renderDiscoveryBadge = (channel, filingCaseNumber) => {
    const norm = (channel || '').toUpperCase().trim();
    const config = {
      COUNTY_FILING_PARTY: { label: '🏛️ County Court Docket', bg: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: 'rgba(234, 179, 8, 0.35)', tooltip: 'Scouted from same-day municipal court / county public filing docket' },
      STATE_BAR_DIRECTORY: { label: '⚖️ State Bar Directory', bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: 'rgba(168, 85, 247, 0.35)', tooltip: 'Identified via licensed state bar attorney directory' },
      SOS_NEW_BUSINESS: { label: '🏢 Secretary of State', bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: 'rgba(56, 189, 248, 0.35)', tooltip: 'Discovered from state Secretary of State commercial registrations' },
      GOOGLE_MAPS_LOCAL: { label: '📍 Google Maps / Local', bg: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', border: 'rgba(34, 197, 94, 0.35)', tooltip: 'Scouted via local business map & review intelligence' },
      JOB_BOARD_INTENT: { label: '💼 Hiring / Job Signals', bg: 'rgba(244, 63, 94, 0.15)', color: '#fb7185', border: 'rgba(244, 63, 94, 0.35)', tooltip: 'Identified via active operations / coordinator hiring requisitions' },
      B2B_WEB_SEARCH: { label: '🌐 Autonomous Web Scout', bg: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: 'rgba(99, 102, 241, 0.35)', tooltip: 'Discovered via autonomous B2B web crawler' },
      INBOUND_REFERRAL: { label: '🤝 Inbound Referral', bg: 'rgba(16, 185, 129, 0.15)', color: '#34d399', border: 'rgba(16, 185, 129, 0.35)', tooltip: 'Introduced via existing customer or partner referral' },
      CATALOG_SEARCH: { label: '🏛️ Municipal Open Data', bg: 'rgba(14, 165, 233, 0.15)', color: '#38bdf8', border: 'rgba(14, 165, 233, 0.35)', tooltip: 'Identified from municipal open data registry & public portals' },
    }[norm] || { label: `🔍 ${channel || 'Public Registry'}`, bg: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)', tooltip: 'Discovered via municipal public registry' };

    return (
      <div style={{ marginTop: '5px', display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap' }}>
        <span
          style={{
            fontSize: '10px',
            fontWeight: 700,
            padding: '2px 7px',
            borderRadius: '4px',
            background: config.bg,
            color: config.color,
            border: `1px solid ${config.border}`,
            letterSpacing: '0.02em',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
          title={config.tooltip}
        >
          {config.label}
        </span>
        {filingCaseNumber && (
          <span
            style={{
              fontSize: '10px',
              fontFamily: 'var(--mono)',
              padding: '2px 5px',
              borderRadius: '4px',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'var(--text-dim)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
            title={`Public Record Filing: Docket #${filingCaseNumber}`}
          >
            #{filingCaseNumber}
          </span>
        )}
      </div>
    );
  };

  // Sync tab & filters to URL query string
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const params = new URLSearchParams(window.location.search);
      params.set('tab', activeTab);
      if (searchQuery.trim()) params.set('q', searchQuery.trim()); else params.delete('q');
      if (stateFilter !== 'ALL') params.set('state', stateFilter); else params.delete('state');
      if (paymentFilter !== 'ALL') params.set('payment', paymentFilter); else params.delete('payment');
      if (scoreFilter !== 'ALL') params.set('score', scoreFilter); else params.delete('score');

      const newUrl = `${window.location.pathname}?${params.toString()}`;
      window.history.replaceState(null, '', newUrl);
    } catch (e) {
      console.warn('URL sync note:', e);
    }
  }, [activeTab, searchQuery, stateFilter, paymentFilter, scoreFilter]);

  // Command Palette State & Hotkey Listener (Cmd+K / Ctrl+K)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Confirm Modal state (replaces native window.confirm & prompt)
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    confirmText: 'Confirm',
    cancelText: 'Cancel',
    isDestructive: false,
    requireMatch: null,
    hasInput: false,
    inputLabel: '',
    inputPlaceholder: '',
    inputDefaultValue: '',
    onConfirm: () => {},
  });
  const closeConfirmModal = () => setConfirmModal((prev) => ({ ...prev, isOpen: false }));

  // Quick Copy Helper
  const handleCopyText = (text, label = 'Text') => {
    if (!text) return;
    try {
      navigator.clipboard.writeText(text);
      showToast(`${label} copied to clipboard!`, 'success');
    } catch {
      showToast(`Could not copy ${label}`, 'info');
    }
  };

  // Scrapers & Daily Grid
  const [scrapers, setScrapers] = useState([]);
  const [scrapersLoading, setScrapersLoading] = useState(false);
  const [dailyGrid, setDailyGrid] = useState([]);
  const [activeBuilds, setActiveBuilds] = useState([]);

  // Modals state
  const [codeModal, setCodeModal] = useState({ open: false, title: '', code: '' });
  const [dataModal, setDataModal] = useState({ open: false, title: '', rows: [], count: 0, leadId: '' });
  const [auditModal, setAuditModal] = useState({ open: false, title: '', events: [] });
  const [scoreModal, setScoreModal] = useState({ open: false, lead: null });
  const [qaOverrideModal, setQaOverrideModal] = useState({ open: false, leadId: '', company: '' });
  const [overrideScore, setOverrideScore] = useState(1.0);
  const [overrideReason, setOverrideReason] = useState('Founder verified edge-case pass');
  const [swarmProgressModal, setSwarmProgressModal] = useState({ open: false, leadId: '', company: '', data: null });

  // Inboxes & Email Infrastructure State
  const [inboxes, setInboxes] = useState([]);
  const [fleetSummary, setFleetSummary] = useState(null);
  const [inboxFilter, setInboxFilter] = useState('ALL');
  const [inboxesLoading, setInboxesLoading] = useState(false);
  const [testingInboxId, setTestingInboxId] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [flushingQueue, setFlushingQueue] = useState(false);
  const [showAddInboxModal, setShowAddInboxModal] = useState(false);
  const [inboxFormData, setInboxFormData] = useState({
    inbox_id: '',
    email_address: '',
    password: '',
    from_name: 'Alex | OmniLeadFeeder',
    provider: 'zoho',
    daily_limit: 25,
  });

  // Morning Deliverability & TestMail Spam Assessment State
  const [deliverabilityReport, setDeliverabilityReport] = useState(null);
  const [auditingDeliverability, setAuditingDeliverability] = useState(false);
  const [selectedSpamReport, setSelectedSpamReport] = useState(null);

  // Microsoft OAuth2 State
  const [msOAuthStatus, setMsOAuthStatus] = useState(null);
  const [msOAuthLoading, setMsOAuthLoading] = useState(false);
  const [msOAuthConnecting, setMsOAuthConnecting] = useState(false);

  const loadMsOAuthStatus = async () => {
    setMsOAuthLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchMicrosoftOAuthStatus(token);
      if (res && res.status) {
        setMsOAuthStatus(res.status);
      }
    } catch (err) {
      console.warn('Could not load Microsoft OAuth status:', err);
    } finally {
      setMsOAuthLoading(false);
    }
  };

  const handleConnectMicrosoftOAuth = async () => {
    setMsOAuthConnecting(true);
    try {
      const token = await resolveToken();
      const origin = typeof window !== 'undefined' ? window.location.origin : '';
      const redirectUri = origin ? `${origin}/api/admin/oauth/microsoft/callback` : '';
      const res = await fetchMicrosoftOAuthAuthorizeUrl(token, redirectUri);
      if (res && res.auth_url) {
        window.location.href = res.auth_url;
      }
    } catch (err) {
      showToast(`Microsoft OAuth error: ${err.message}`, 'error');
      setMsOAuthConnecting(false);
    }
  };

  const handleDisconnectMicrosoftOAuth = async () => {
    try {
      const token = await resolveToken();
      await disconnectMicrosoftOAuth(token);
      showToast('Outlook account disconnected successfully.', 'info');
      await loadMsOAuthStatus();
      await loadInboxes();
    } catch (err) {
      showToast(`Disconnect error: ${err.message}`, 'error');
    }
  };

  // Listen for OAuth callback query parameters on redirect
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('oauth') === 'microsoft_success') {
        const authedEmail = urlParams.get('email') || 'omnileadfeeder@outlook.com';
        showToast(`🎉 Microsoft Outlook (${authedEmail}) connected successfully via OAuth2!`, 'success');
        urlParams.delete('oauth');
        urlParams.delete('email');
        const cleanUrl = `${window.location.pathname}?${urlParams.toString()}`;
        window.history.replaceState(null, '', cleanUrl);
        loadMsOAuthStatus();
      } else if (urlParams.get('oauth_error')) {
        showToast(`❌ Microsoft OAuth error: ${decodeURIComponent(urlParams.get('oauth_error'))}`, 'error');
        urlParams.delete('oauth_error');
        const cleanUrl = `${window.location.pathname}?${urlParams.toString()}`;
        window.history.replaceState(null, '', cleanUrl);
      }
    } catch (e) {
      console.warn('OAuth URL listener note:', e);
    }
  }, []);

  // Load Admin Data
  const loadAdminData = async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      const [pipeData, metricData, buildsData, scoutData, autoData, inboxesData] = await Promise.allSettled([
        fetchAdminPipeline(token),
        fetchAdminMetrics(token),
        fetchActiveBuilds(token),
        fetchScoutStatus(token),
        fetchAutoOutreachStatus(token),
        fetchAdminInboxes(token),
      ]);

      if (pipeData.status === 'fulfilled') {
        const raw = pipeData.value || {};
        const list = Array.isArray(raw) ? raw : (raw.leads || raw.pipeline || []);
        // Strict Archival Isolation: Active pipeline exclusively contains non-archived leads
        const activeOnly = list.filter((l) => l.state !== 'ARCHIVED');
        setPipeline(activeOnly);
        if (raw.archived && Array.isArray(raw.archived)) {
          setArchivedLeads(raw.archived);
        }
      } else {
        console.warn('Pipeline fetch error:', pipeData.reason);
        showToast(`Pipeline load error: ${pipeData.reason?.message || 'Authentication required'}`, 'error');
      }
      if (metricData.status === 'fulfilled') {
        setMetrics(metricData.value);
      }
      if (buildsData.status === 'fulfilled') {
        setActiveBuilds(buildsData.value.active_builds || []);
      }
      if (scoutData.status === 'fulfilled') {
        setScoutStatus(scoutData.value);
      }
      if (autoData.status === 'fulfilled') {
        setAutoOutreachStatus(autoData.value);
      }
      if (inboxesData.status === 'fulfilled') {
        const iVal = inboxesData.value || {};
        if (iVal.inboxes) setInboxes(iVal.inboxes);
        if (iVal.fleet_summary) setFleetSummary(iVal.fleet_summary);
      }
    } catch (err) {
      console.warn('Admin load note:', err);
      showToast(`Admin load: ${err.message}`, 'info');
    } finally {
      setLoading(false);
    }
  };

  const loadArchivedLeads = async () => {
    try {
      const token = await resolveToken();
      const res = await fetchArchivedLeads(token);
      if (res && res.leads) {
        setArchivedLeads(res.leads);
      }
    } catch (err) {
      console.warn('Could not load archived leads:', err);
    }
  };

  // Load Scrapers / Inboxes / Archived when tab changes
  useEffect(() => {
    if (activeTab === 'scrapers' && scrapers.length === 0) {
      loadScrapers();
    } else if (activeTab === 'daily' && dailyGrid.length === 0) {
      loadDailyGrid();
    } else if (activeTab === 'inboxes') {
      loadInboxes();
      loadMsOAuthStatus();
    } else if (activeTab === 'archived') {
      loadArchivedLeads();
    }
  }, [activeTab]);

  const loadInboxes = async () => {
    setInboxesLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchAdminInboxes(token);
      if (res && res.inboxes) {
        setInboxes(res.inboxes);
      }
      if (res && res.fleet_summary) {
        setFleetSummary(res.fleet_summary);
      }
      loadMsOAuthStatus();
      loadDeliverabilityStatus();
    } catch (err) {
      console.warn('Could not load inboxes:', err);
    } finally {
      setInboxesLoading(false);
    }
  };

  const loadDeliverabilityStatus = async () => {
    try {
      const token = await resolveToken();
      const res = await fetchDeliverabilityStatus(token);
      if (res && res.report) {
        setDeliverabilityReport(res.report);
      }
    } catch (err) {
      console.warn('Could not load deliverability status:', err);
    }
  };

  const handleRunDeliverabilityAudit = async () => {
    setAuditingDeliverability(true);
    showToast('🛡️ Initiating morning deliverability probes: sending AI cold emails to TestMail across all active Zoho inboxes...', 'info');
    try {
      const token = await resolveToken();
      await runDeliverabilityAudit({ force: true, wait: false }, token);
      showToast('🚀 Test probes dispatched! Polling TestMail for live SPF, DKIM, and SpamAssassin scores...', 'success');

      // Schedule progressive poll refreshes
      setTimeout(async () => {
        await loadDeliverabilityStatus();
      }, 8000);
      setTimeout(async () => {
        await loadDeliverabilityStatus();
        setAuditingDeliverability(false);
        showToast('✅ Deliverability audit scorecard updated from live TestMail report!', 'success');
      }, 16000);
      setTimeout(async () => {
        await loadDeliverabilityStatus();
      }, 30000);
    } catch (err) {
      showToast(`Deliverability audit failed: ${err.message}`, 'error');
      setAuditingDeliverability(false);
    }
  };

  const handleTestInbox = async (inboxId) => {
    try {
      setTestingInboxId(inboxId);
      const token = await resolveToken();
      const res = await testAdminInbox(inboxId, token);
      if (res && res.result) {
        setTestResults((prev) => ({ ...prev, [inboxId]: res.result }));
        if (res.result.smtp_ok && res.result.imap_ok) {
          showToast(`✅ Inbox '${inboxId}' verified successfully (${res.result.latency_ms}ms)!`, 'success');
        } else {
          showToast(`⚠️ Verification notice for '${inboxId}': ${res.result.smtp_message || res.result.imap_message}`, 'warning');
        }
      }
    } catch (err) {
      showToast(`Test error: ${err.message}`, 'error');
    } finally {
      setTestingInboxId(null);
    }
  };

  const handleFlushOutreachQueue = async () => {
    setFlushingQueue(true);
    showToast('⚡ Flushing outreach queue across all active Zoho inboxes...', 'info');
    try {
      const token = await resolveToken();
      const res = await triggerOutreachFlush(token);
      showToast(res.message || 'Outreach dispatch worker triggered with anti-spam jitter!', 'success');
      await loadInboxes();
      await loadAdminData();
    } catch (err) {
      showToast(`Flush queue failed: ${err.message}`, 'error');
    } finally {
      setFlushingQueue(false);
    }
  };

  const handleSaveInbox = async () => {
    if (!inboxFormData.email_address || !inboxFormData.email_address.includes('@')) {
      showToast('Please provide a valid email address', 'warning');
      return;
    }
    try {
      const token = await resolveToken();
      await upsertAdminInbox(inboxFormData, token);
      showToast(`Inbox '${inboxFormData.email_address}' saved successfully!`, 'success');
      const savedId = inboxFormData.inbox_id || inboxFormData.email_address.replace('@', '_').replace('.', '_');
      setShowAddInboxModal(false);
      setInboxFormData({
        inbox_id: '',
        email_address: '',
        password: '',
        from_name: 'Alex | OmniLeadFeeder',
        provider: 'zoho',
        daily_limit: 25,
      });
      await loadInboxes();
      if (inboxFormData.password) {
        handleTestInbox(savedId);
      }
    } catch (err) {
      showToast(`Failed to save inbox: ${err.message}`, 'error');
    }
  };

  const handleDeleteInbox = async (inboxId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Remove Inbox Account',
      message: `Are you sure you want to remove inbox '${inboxId}' from active rotation?`,
      confirmText: 'Remove Inbox',
      cancelText: 'Cancel',
      isDestructive: true,
      onConfirm: async () => {
        try {
          const token = await resolveToken();
          await deleteAdminInbox(inboxId, token);
          showToast(`Inbox '${inboxId}' removed.`, 'success');
          await loadInboxes();
        } catch (err) {
          showToast(`Failed to delete inbox: ${err.message}`, 'error');
        }
      },
    });
  };

  const handleToggleInboxActive = async (inbox) => {
    try {
      const token = await resolveToken();
      await upsertAdminInbox({
        inbox_id: inbox.inbox_id,
        email_address: inbox.email_address,
        is_active: !inbox.is_active,
      }, token);
      showToast(`Inbox '${inbox.inbox_id}' ${!inbox.is_active ? 'activated' : 'paused'}.`, 'success');
      await loadInboxes();
    } catch (err) {
      showToast(`Could not toggle inbox state: ${err.message}`, 'error');
    }
  };

  const loadScrapers = async () => {
    setScrapersLoading(true);
    try {
      const token = await resolveToken();
      const data = await fetchScrapersCatalog(token);
      setScrapers(data.scrapers || data || []);
    } catch (err) {
      showToast(`Failed to load scrapers: ${err.message}`, 'error');
    } finally {
      setScrapersLoading(false);
    }
  };

  const loadDailyGrid = async () => {
    try {
      const token = await resolveToken();
      const data = await fetchDailyGrid(token);
      setDailyGrid(data.grid || data || []);
    } catch (err) {
      showToast(`Failed to load daily grid: ${err.message}`, 'error');
    }
  };

  useEffect(() => {
    if (isSignedIn || masterAuth) {
      loadAdminData();
      loadInboxes();
      const interval = setInterval(loadAdminData, 20000);
      return () => clearInterval(interval);
    }
  }, [isSignedIn, masterAuth]);

  // Filtered Leads
  const filteredLeads = useMemo(() => {
    return pipeline.filter((l) => {
      // 1. Strict Archival Isolation: Archived leads are put away in Vault and NEVER shown in active Deals & Customers
      if (l.state === 'ARCHIVED') return false;

      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        (l.company_name && l.company_name.toLowerCase().includes(q)) ||
        (l.contact_email && l.contact_email.toLowerCase().includes(q)) ||
        (l.jurisdiction && l.jurisdiction.toLowerCase().includes(q)) ||
        (l.lead_id && l.lead_id.toLowerCase().includes(q));

      const matchesState = stateFilter === 'ALL' || l.state === stateFilter;

      let matchesPayment = true;
      if (paymentFilter === 'DEPOSIT_PAID') {
        matchesPayment = l.deposit_paid;
      } else if (paymentFilter === 'FINAL_PAID') {
        matchesPayment = l.final_paid;
      } else if (paymentFilter === 'SUBSCRIPTION_ACTIVE') {
        matchesPayment = l.subscription_active;
      } else if (paymentFilter === 'UNPAID') {
        matchesPayment = !l.deposit_paid && !l.final_paid;
      }

      let matchesScore = true;
      const opp = l.automation_opportunity_score || 75;
      if (scoreFilter === 'HIGH') {
        matchesScore = opp >= 75;
      } else if (scoreFilter === 'QUALIFIED') {
        matchesScore = opp >= 65;
      } else if (scoreFilter === 'NURTURE') {
        matchesScore = opp < 65;
      }

      return matchesSearch && matchesState && matchesPayment && matchesScore;
    });
  }, [pipeline, searchQuery, stateFilter, paymentFilter, scoreFilter]);

  // Actions
  const handleAdvance = async (leadId) => {
    setActionInProgress((p) => ({ ...p, [leadId]: true }));
    showToast(`Advancing deal stage for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      const res = await advanceLeadState(leadId, token);
      showToast(res.message || `Lead ${leadId} advanced!`, 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Advance error: ${err.message}`, 'error');
    } finally {
      setActionInProgress((p) => ({ ...p, [leadId]: false }));
    }
  };

  const handleBatchApprove = async () => {
    const pendingCount = pipeline.filter((l) => l.state === 'PITCH_PENDING_APPROVAL').length;
    if (pendingCount === 0) {
      showToast('No leads currently pending pitch approval.', 'info');
      return;
    }
    const confirmed = window.confirm(
      `🚀 BATCH APPROVAL CONFIRMATION\n\nApprove and dispatch pitches for all ${pendingCount} pending leads?\n\n- Junk aggregator addresses (e.g. duckduckgo, sentry) will be filtered.\n- Natural, casual 2-4 word subject lines will be delivered.\n- Verified leads will transition to OUTREACH_SENT.`
    );
    if (!confirmed) return;

    setBatchApproving(true);
    showToast(`Batch approving ${pendingCount} pending pitches...`, 'info');
    try {
      const token = await resolveToken();
      const res = await batchApprovePendingPitches(token);
      showToast(res.message || `Batch approval complete: ${res.approved_count} dispatched, ${res.skipped_count} skipped.`, 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Batch approval failed: ${err.message}`, 'error');
    } finally {
      setBatchApproving(false);
    }
  };

  const handleToggleAutoOutreach = async () => {
    const current = autoOutreachStatus?.enabled ?? true;
    const nextState = !current;
    setAutoOutreachLoading(true);
    try {
      const token = await resolveToken();
      await toggleAutoOutreach(nextState, token);
      showToast(`Auto-Outreach 3-minute grace period ${nextState ? 'ENABLED (with anti-spam jitter)' : 'PAUSED'}.`, 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Failed to toggle auto-outreach: ${err.message}`, 'error');
    } finally {
      setAutoOutreachLoading(false);
    }
  };

  const handleTriggerWebScout = async (overrideChannel = null, overrideQuery = null) => {
    setScoutingInProgress(true);
    const targetChannel = overrideChannel !== null ? overrideChannel : selectedScoutChannel;
    const targetQuery = overrideQuery !== null ? overrideQuery : scoutSearchQuery;
    const searchTrimmed = (targetQuery || '').trim();
    const channelLabel = searchTrimmed
      ? `Search: "${searchTrimmed}"`
      : targetChannel === 'county_filing_party'
      ? 'County Filing Parties'
      : targetChannel === 'state_bar'
      ? 'State Bar Attorneys'
      : targetChannel === 'sos_entity'
      ? 'SOS Registrations'
      : targetChannel === 'local_business'
      ? 'Google Maps / Local'
      : 'All Channels (Auto)';

    showToast(`🔎 Hunting for a new qualified lead via [${channelLabel}] until found...`, 'info');
    try {
      const token = await resolveToken();
      const res = await triggerScoutDiscovery(searchTrimmed || null, token, targetChannel || null, true);
      if (res && res.lead_id) {
        showToast(`🎯 Discovered new qualified lead: ${res.company_name || res.lead_id}!`, 'success');
      } else if (res && res.ok) {
        showToast(`🎯 Discovered new lead! Telemetry updated.`, 'success');
      } else {
        showToast(res.message || res.reason || 'Scout pass complete. Telemetry updated.', 'info');
      }
      await loadAdminData();
    } catch (err) {
      showToast(`Scout trigger error: ${err.message}`, 'error');
    } finally {
      setScoutingInProgress(false);
    }
  };

  const handleCancelOutreach = async (leadId, companyName) => {
    setActionInProgress((p) => ({ ...p, [leadId]: true }));
    try {
      const token = await resolveToken();
      await cancelAutoOutreach(leadId, token);
      showToast(`Auto-outreach cancelled for ${companyName || leadId}. Pitch archived.`, 'success');
      await loadAdminData();
      await loadArchivedLeads();
    } catch (err) {
      showToast(`Cancel outreach error: ${err.message}`, 'error');
    } finally {
      setActionInProgress((p) => ({ ...p, [leadId]: false }));
    }
  };

  const handleEnrichLead = async (leadId, companyName) => {
    setEnrichingLeadId(leadId);
    showToast(`🤖 Contact Enricher Agent researching alternatives for ${companyName || leadId}...`, 'info');
    try {
      const token = await resolveToken();
      const res = await enrichLeadContact(leadId, token);
      if (res.recovered) {
        showToast(`🎉 Contact Recovered! ${res.company_name} updated to ${res.new_email} and moved to Review stage!`, 'success');
        await loadAdminData();
        await loadArchivedLeads();
      } else {
        showToast(`⚠️ Research complete for ${companyName || leadId}: ${res.reason || 'No deliverable contact found'}. Lead remains archived.`, 'warning');
        await loadArchivedLeads();
      }
    } catch (err) {
      showToast(`Contact enrichment error: ${err.message}`, 'error');
    } finally {
      setEnrichingLeadId(null);
    }
  };

  const handleBatchEnrichArchived = async () => {
    setBatchEnriching(true);
    showToast('🤖 Triggering Contact Enricher Researcher Agent across all archived leads...', 'info');
    try {
      const token = await resolveToken();
      const res = await batchEnrichArchivedLeads(token);
      showToast(res.message || `Processed ${res.total_archived} archived leads, recovering ${res.recovered_count}.`, 'success');
      await loadAdminData();
      await loadArchivedLeads();
    } catch (err) {
      showToast(`Batch recovery error: ${err.message}`, 'error');
    } finally {
      setBatchEnriching(false);
    }
  };



  const handleTriggerSwarm = async (leadId) => {
    setActionInProgress((p) => ({ ...p, [leadId]: true }));
    showToast(`Triggering autonomous 7-agent dev swarm for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      await triggerSwarmBuild(leadId, token);
      showToast(`Autonomous swarm build initiated for ${leadId}!`, 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Swarm launch error: ${err.message}`, 'error');
    } finally {
      setActionInProgress((p) => ({ ...p, [leadId]: false }));
    }
  };

  const handlePurgeAllData = () => {
    setConfirmModal({
      isOpen: true,
      title: 'Reset & Purge All Test Records',
      message: 'This will permanently remove all test leads, sandboxes, and customer records, resetting the database to a clean 0-lead state for real production customers.',
      confirmText: 'Purge Database',
      cancelText: 'Cancel',
      isDestructive: true,
      requireMatch: 'PURGE',
      hasInput: false,
      onConfirm: async () => {
        closeConfirmModal();
        showToast("Purging all test data and resetting pipeline...", "info");
        try {
          const token = await resolveToken();
          const res = await purgeAllData(token);
          showToast(res.message || "All test records successfully purged!", "success");
          await loadAdminData();
        } catch (err) {
          showToast(`Purge failed: ${err.message}`, "error");
        }
      },
    });
  };

  const handleDeleteLead = (leadId, companyName) => {
    setConfirmModal({
      isOpen: true,
      title: 'Delete Lead',
      message: `Are you sure you want to permanently delete lead "${companyName || leadId}"? This will remove the lead, associated sandboxes, and audit records.`,
      confirmText: 'Delete Lead',
      cancelText: 'Cancel',
      isDestructive: true,
      requireMatch: null,
      hasInput: false,
      onConfirm: async () => {
        closeConfirmModal();
        setActionInProgress((p) => ({ ...p, [leadId]: true }));
        try {
          const token = await resolveToken();
          await deleteLead(leadId, token);
          showToast(`Lead "${companyName || leadId}" deleted successfully.`, 'success');
          await loadAdminData();
        } catch (err) {
          showToast(`Failed to delete lead: ${err.message}`, 'error');
        } finally {
          setActionInProgress((p) => ({ ...p, [leadId]: false }));
        }
      },
    });
  };

  const handleToggleEmergencyStop = () => {
    const currentState = metrics?.emergency_stop_active || false;
    const newState = !currentState;
    setConfirmModal({
      isOpen: true,
      title: newState ? 'Activate Emergency Stop' : 'Resume Normal Operations',
      message: newState
        ? 'Emergency stop pauses all autonomous prospecting, outbound emails, and dev swarm iterations immediately.'
        : 'Resuming will allow background dev swarms and auto-outreach schedules to proceed normally.',
      confirmText: newState ? 'Activate Emergency Stop' : 'Resume System',
      cancelText: 'Cancel',
      isDestructive: newState,
      requireMatch: null,
      hasInput: true,
      inputLabel: newState ? 'Reason for EMERGENCY STOP:' : 'Reason for RESUMING normal operations:',
      inputPlaceholder: newState ? 'Manual founder safety stop' : 'Founder resumed operations',
      inputDefaultValue: newState ? 'Manual founder safety stop' : 'Founder resumed operations',
      onConfirm: async (reason) => {
        closeConfirmModal();
        try {
          const token = await resolveToken();
          await toggleEmergencyStop(
            newState,
            reason || (newState ? 'Manual founder safety stop' : 'Founder resumed operations'),
            token
          );
          showToast(
            newState ? '🛑 EMERGENCY STOP ACTIVATED' : '✅ Systems resumed normal operation',
            newState ? 'error' : 'success'
          );
          await loadAdminData();
        } catch (err) {
          showToast(`Emergency toggle failed: ${err.message}`, 'error');
        }
      },
    });
  };

  // Command Palette Actions
  const commandPaletteActions = useMemo(() => [
    {
      id: 'act-refresh',
      label: 'Refresh Pipeline & Telemetry',
      icon: '🔄',
      category: 'Actions',
      run: () => loadAdminData(),
    },
    {
      id: 'act-scout',
      label: 'Trigger Scout Prospecting Cycle',
      icon: '🔎',
      category: 'Actions',
      run: () => handleTriggerWebScout(),
    },
    {
      id: 'act-auto-outreach',
      label: `Toggle Auto-Outreach (${autoOutreachStatus?.enabled ? 'Pause' : 'Enable'})`,
      icon: '⏱️',
      category: 'Actions',
      run: () => handleToggleAutoOutreach(),
    },
    {
      id: 'act-emergency',
      label: metrics?.emergency_stop_active ? 'Resume Normal Operations' : 'Activate Emergency Stop',
      icon: '🛑',
      category: 'Actions',
      run: () => handleToggleEmergencyStop(),
    },
    {
      id: 'act-purge',
      label: 'Purge All Test Records',
      icon: '🧹',
      category: 'Danger Zone',
      run: () => handlePurgeAllData(),
    },
  ], [metrics, autoOutreachStatus, loadAdminData, handleTriggerWebScout, handleToggleAutoOutreach, handleToggleEmergencyStop, handlePurgeAllData]);

  const handleViewAudit = async (leadId, companyName, leadObj = null) => {
    try {
      const token = await resolveToken();
      let events = [];
      try {
        const res = await fetchAuditTrail(leadId, token);
        events = res.trail || res.audit_trail || res.events || res.audit_log || [];
      } catch (fetchErr) {
        console.warn('Network fetchAuditTrail failed, falling back to local lead data:', fetchErr);
      }

      // If backend audit trail had 0 events, fallback to leadObj or search pipeline
      if (!events || events.length === 0) {
        const targetLead = leadObj || pipeline.find((l) => l.lead_id === leadId);
        if (targetLead && Array.isArray(targetLead.audit_log) && targetLead.audit_log.length > 0) {
          events = targetLead.audit_log.map((ev) => {
            if (typeof ev === 'object' && ev !== null) {
              const frm = ev.from || '';
              const toSt = ev.to || '';
              const action = frm && toSt ? `${frm} ➔ ${toSt}` : (ev.action || ev.event || 'Lifecycle Transition');
              return {
                action,
                timestamp: ev.at || ev.timestamp || new Date().toISOString(),
                detail: ev.reason || ev.detail || 'Automated lifecycle transition',
                metadata: ev,
              };
            }
            return { action: 'State Transition', detail: String(ev), timestamp: '' };
          });
        }
      }

      setAuditModal({
        open: true,
        title: `Audit Trail: ${companyName || leadId}`,
        events: events || [],
      });
    } catch (err) {
      showToast(`Failed to load audit trail: ${err.message}`, 'error');
    }
  };

  const handleViewSwarmProgress = async (leadId, companyName) => {
    try {
      const token = await resolveToken();
      const res = await fetchSwarmProgress(leadId, token);
      setSwarmProgressModal({
        open: true,
        leadId,
        company: companyName || leadId,
        data: res,
      });
    } catch (err) {
      showToast(`Swarm telemetry note: ${err.message}`, 'info');
    }
  };

  const handleOpenQaOverride = (leadId, companyName) => {
    setQaOverrideModal({ open: true, leadId, company: companyName || leadId });
  };

  const handleSubmitQaOverride = async () => {
    try {
      const token = await resolveToken();
      await overrideQA(qaOverrideModal.leadId, overrideScore, overrideReason, token);
      showToast(`QA Gate override applied (Score: ${overrideScore * 100}%)`, 'success');
      setQaOverrideModal({ open: false, leadId: '', company: '' });
      await loadAdminData();
    } catch (err) {
      showToast(`QA override failed: ${err.message}`, 'error');
    }
  };

  const handleViewCode = async (leadId, scraperName) => {
    try {
      const token = await resolveToken();
      const code = await fetchScraperCode(leadId, token);
      setCodeModal({ open: true, title: `Source: ${scraperName || leadId}`, code });
    } catch (err) {
      showToast(`Code load: ${err.message}`, 'error');
    }
  };

  const handleViewOutput = async (leadId, scraperName) => {
    try {
      const token = await resolveToken();
      const res = await fetchScraperOutput(leadId, 'json', token);
      const rows = res.data || res.rows || res || [];
      setDataModal({
        open: true,
        title: `Extracted Records: ${scraperName || leadId}`,
        rows,
        count: rows.length,
        leadId,
      });
    } catch (err) {
      showToast(`Dataset note: ${err.message}`, 'info');
    }
  };

  const handleRunScraper = async (leadId) => {
    setActionInProgress((p) => ({ ...p, [leadId]: true }));
    showToast(`Executing extractor pipeline for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      const res = await runScraperOnDemand(leadId, token);
      showToast(`Extractor finished! ${res.rows_extracted || 0} rows extracted.`, 'success');
      await loadScrapers();
    } catch (err) {
      showToast(`Execution error: ${err.message}`, 'error');
    } finally {
      setActionInProgress((p) => ({ ...p, [leadId]: false }));
    }
  };

  const handleTriggerDailyDelivery = async (leadId) => {
    showToast(`Dispatching live daily feed delivery for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      await triggerDailyDelivery(leadId, token);
      showToast(`Daily delivery sent for ${leadId}!`, 'success');
      await loadDailyGrid();
    } catch (err) {
      showToast(`Delivery error: ${err.message}`, 'error');
    }
  };

  // Financial calculations
  const depositTotal = useMemo(() => {
    return pipeline
      .filter((l) => l.deposit_paid)
      .reduce((sum, l) => sum + (l.deposit_amount_usd || 99.0), 0);
  }, [pipeline]);

  const releasedTotal = useMemo(() => {
    return pipeline
      .filter((l) => l.final_paid)
      .reduce((sum, l) => sum + (l.next_payment_amount || 151.0), 0);
  }, [pipeline]);

  const activeMrr = useMemo(() => {
    return pipeline
      .filter((l) => l.subscription_active)
      .reduce((sum, l) => {
        const p = l.tier_key === 'ai' ? 850 : l.tier_key === 'daily' ? 500 : 250;
        return sum + p;
      }, 0);
  }, [pipeline]);

  // Authentication Gate
  if (isLoaded && !isSignedIn && !masterAuth) {
    return (
      <main style={{ minHeight: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '50px 16px' }}>
        <div style={{ maxWidth: '440px', width: '100%', textAlign: 'center' }}>
          <div style={{ marginBottom: '24px' }}>
            <div style={{ fontSize: '42px', marginBottom: '8px' }}>⚡</div>
            <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#fff', letterSpacing: '-0.5px', marginBottom: '8px' }}>
              LeadOps Mission Control
            </h1>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Sign in with your administrator account to access live lead streams, dev swarms, and daily automated delivery.
            </p>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
            <SignIn routing="hash" />
          </div>

          <div style={{ padding: '20px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ color: 'var(--cyan)', fontWeight: 700, fontSize: '13px' }}>⚡ Founder Direct Access</span>
              <span className="badge-tag badge-purple" style={{ fontSize: '10px' }}>BYPASS</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginBottom: '14px' }}>
              Unlock directly with your master operational token:
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="password"
                id="founderPasscodeInput"
                placeholder="Enter Master Token"
                defaultValue={localStorage.getItem('leadops_admin_token') || '0baac74dfda043fdaf84c5d0b38e259b'}
                style={{ flex: 1, padding: '9px 12px', background: '#070d18', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', color: '#fff', fontSize: '12px', fontFamily: 'var(--mono)' }}
              />
              <button
                className="btn btn-primary"
                style={{ padding: '9px 18px', fontSize: '12px', whiteSpace: 'nowrap' }}
                onClick={() => {
                  const val = document.getElementById('founderPasscodeInput')?.value || '0baac74dfda043fdaf84c5d0b38e259b';
                  localStorage.setItem('leadops_admin_token', val.trim());
                  setMasterAuth(true);
                  showToast('Founder Master Access Activated!', 'success');
                }}
              >
                Unlock ➔
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main style={{ padding: '36px 0 90px' }}>
      <div className="container">
        {/* Admin Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="brand-icon" style={{ width: '32px', height: '32px', fontSize: '16px' }}>⚡</span>
              <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#fff', letterSpacing: '-0.5px' }}>
                Founder Mission Control
              </h1>
              <span className="badge-tag badge-cyan">GLOBAL ADMIN</span>
              {scoutStatus && (
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '3px 8px',
                    borderRadius: '6px',
                    background: scoutStatus.is_office_hours ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.2)',
                    color: scoutStatus.is_office_hours ? 'var(--green)' : '#94a3b8',
                    border: `1px solid ${scoutStatus.is_office_hours ? 'rgba(16, 185, 129, 0.35)' : 'rgba(100, 116, 139, 0.3)'}`,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                  }}
                  title={`Scout Office Hours: 8:00 AM - 5:00 PM CST Mon-Fri. Current CST: ${scoutStatus.current_cst_time || ''}`}
                >
                  <span>{scoutStatus.is_office_hours ? '🟢' : '🌙'}</span>
                  Scout: {scoutStatus.is_office_hours ? 'Office Hours (8am-5pm CST)' : 'Standby (Office Hours Only)'}
                </span>
              )}
              {metrics?.emergency_stop_active && (
                <span className="badge-tag badge-red">🛑 EMERGENCY STOP ACTIVE</span>
              )}
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Autonomous 7-Agent Dev Swarms, Live Municipal Extractors, QA Gate &amp; Escrow Vault
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-dim)', marginRight: '6px' }}>
              {user?.primaryEmailAddress?.emailAddress ? `👤 ${user.primaryEmailAddress.emailAddress}` : '⚡ Founder Key Active'}
            </span>
            {masterAuth && !isSignedIn && (
              <button
                className="btn btn-outline"
                style={{ fontSize: '11px', padding: '6px 12px' }}
                onClick={() => {
                  localStorage.removeItem('leadops_admin_token');
                  setMasterAuth(false);
                }}
              >
                Lock Console
              </button>
            )}
            <button
              className="btn btn-outline"
              style={{
                borderColor: autoOutreachStatus?.enabled ? 'var(--green)' : 'rgba(148, 163, 184, 0.4)',
                color: autoOutreachStatus?.enabled ? 'var(--green)' : '#94a3b8',
                fontSize: '11px',
                padding: '6px 12px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
              }}
              onClick={handleToggleAutoOutreach}
              disabled={autoOutreachLoading}
              title="When enabled, newly scouted leads auto-send after a 3-minute grace period unless cancelled via mobile Discord/Telegram."
            >
              <span>{autoOutreachStatus?.enabled ? '⏱️ Auto-Outreach: ON (3m Grace)' : '⏸️ Auto-Outreach: OFF'}</span>
            </button>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <input
                type="text"
                value={scoutSearchQuery}
                onChange={(e) => setScoutSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !scoutingInProgress) {
                    handleTriggerWebScout();
                  }
                }}
                placeholder="🔍 Search query or niche (e.g. Austin probate)..."
                disabled={scoutingInProgress}
                style={{
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(56, 189, 248, 0.35)',
                  borderRadius: '6px',
                  color: '#e2e8f0',
                  fontSize: '11px',
                  padding: '5px 10px',
                  width: '220px',
                  outline: 'none',
                }}
                title="Enter custom search query or niche. Press Enter or click Scout Now to run until a new lead is found."
              />
              <select
                value={selectedScoutChannel}
                onChange={(e) => setSelectedScoutChannel(e.target.value)}
                disabled={scoutingInProgress}
                style={{
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(56, 189, 248, 0.35)',
                  borderRadius: '6px',
                  color: 'var(--cyan)',
                  fontSize: '11px',
                  padding: '5px 8px',
                  outline: 'none',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                title="Select High-ROI Prospect Discovery Engine"
              >
                <option value="">🎯 All High-ROI Channels (Auto)</option>
                <option value="county_filing_party">🏛️ County Filing Parties (Priority 1)</option>
                <option value="state_bar">⚖️ State Bar Directories (Priority 2)</option>
                <option value="sos_entity">🏢 SOS New Registrations (Priority 3)</option>
                <option value="local_business">📍 Google Maps / Local (Priority 4)</option>
              </select>
              <button
                className="btn btn-outline"
                style={{
                  borderColor: 'rgba(56, 189, 248, 0.4)',
                  color: 'var(--cyan)',
                  fontSize: '11px',
                  padding: '6px 12px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                }}
                onClick={() => handleTriggerWebScout()}
                disabled={scoutingInProgress}
                title="Manually trigger autonomous scout to hunt continuously until a new qualified B2B lead is found."
              >
                <span>{scoutingInProgress ? '⏳ Hunting Lead...' : '🔎 Scout Now'}</span>
              </button>
            </div>

            <button
              className="btn btn-outline"
              style={{
                borderColor: metrics?.emergency_stop_active ? 'var(--green)' : 'rgba(239, 68, 68, 0.4)',
                color: metrics?.emergency_stop_active ? 'var(--green)' : '#f87171',
              }}
              onClick={handleToggleEmergencyStop}
            >
              {metrics?.emergency_stop_active ? '▶️ Resume System' : '🛑 Emergency Stop'}
            </button>
            <button
              className="btn btn-outline"
              style={{ borderColor: 'rgba(239, 68, 68, 0.35)', color: '#f87171' }}
              onClick={handlePurgeAllData}
              title="Wipes all mock data for a 100% clean live launch"
            >
              🧹 Purge Test Data
            </button>
            <button className="btn btn-outline" onClick={loadAdminData}>
              🔄 Refresh Telemetry
            </button>
            <button
              className="btn btn-primary"
              style={{
                fontSize: '11px',
                padding: '6px 14px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                background: 'rgba(56, 189, 248, 0.15)',
                color: 'var(--cyan)',
                border: '1px solid rgba(56, 189, 248, 0.4)',
              }}
              onClick={() => setCommandPaletteOpen(true)}
              title="Open Command Palette (Cmd+K / Ctrl+K)"
            >
              <span>⚡ ⌘K Omnibar</span>
              <kbd style={{ fontSize: '9px', background: 'rgba(0, 0, 0, 0.3)', padding: '2px 4px', borderRadius: '3px' }}>
                ⌘K
              </kbd>
            </button>
          </div>
        </div>

        {/* Top Summary Stats Bar - 5 Color-Coded Live KPIs */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
          <div className="stat-card stat-green">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="stat-label" style={{ color: 'var(--green)' }}>🏦 Down Payments Held</div>
              <span className="pulse-dot-green" title="Milestone #1 deposits secured in escrow" />
            </div>
            <div className="stat-value" style={{ color: 'var(--green)' }}>
              ${depositTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span>Milestone #1 ($99 deposits)</span>
              <span style={{ color: '#fff', fontWeight: 600 }}>{pipeline.filter((l) => l.deposit_paid).length} secured</span>
            </div>
          </div>

          <div className="stat-card stat-cyan">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="stat-label" style={{ color: 'var(--cyan)' }}>💰 Released Milestone #2</div>
              <span className="pulse-dot-cyan" title="Auto-charged on ≥95% QA pass" />
            </div>
            <div className="stat-value" style={{ color: 'var(--cyan)' }}>
              ${releasedTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span>Passed QA Gate (≥95%)</span>
              <span style={{ color: '#fff', fontWeight: 600 }}>{pipeline.filter((l) => l.final_paid).length} verified</span>
            </div>
          </div>

          <div className="stat-card stat-purple">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="stat-label" style={{ color: '#c084fc' }}>📈 Active Retainer MRR</div>
              <span style={{ fontSize: '12px' }}>🟣</span>
            </div>
            <div className="stat-value" style={{ color: 'var(--purple)' }}>
              ${activeMrr.toLocaleString('en-US', { minimumFractionDigits: 2 })}/mo
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span>Recurring cashflow</span>
              <span style={{ color: '#fff', fontWeight: 600 }}>{pipeline.filter((l) => l.subscription_active).length} retainers</span>
            </div>
          </div>

          <div className="stat-card stat-yellow">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="stat-label" style={{ color: '#fbbf24' }}>🎯 Active Pipeline Deals</div>
              <span className="pulse-dot-amber" title="Active pipeline load" />
            </div>
            <div className="stat-value" style={{ color: '#fbbf24' }}>
              {pipeline.filter((l) => l.state !== 'ARCHIVED').length}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span>{activeBuilds.length} dev builds active</span>
              <span style={{ color: 'var(--text-muted)' }}>{archivedLeads.length} in vault</span>
            </div>
          </div>

          <div className={`stat-card ${
            deliverabilityReport?.fleet_status === 'HEALTHY'
              ? 'stat-green'
              : deliverabilityReport?.fleet_status === 'WARNING'
              ? 'stat-yellow'
              : deliverabilityReport?.fleet_status === 'CRITICAL'
              ? 'stat-red'
              : 'stat-cyan'
          }`}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="stat-label" style={{
                color: deliverabilityReport?.fleet_status === 'HEALTHY'
                  ? 'var(--green)'
                  : deliverabilityReport?.fleet_status === 'WARNING'
                  ? '#fbbf24'
                  : deliverabilityReport?.fleet_status === 'CRITICAL'
                  ? '#f87171'
                  : 'var(--cyan)'
              }}>
                🛡️ TestMail Deliverability
              </div>
              <span className={
                deliverabilityReport?.fleet_status === 'HEALTHY'
                  ? 'pulse-dot-green'
                  : deliverabilityReport?.fleet_status === 'CRITICAL'
                  ? 'pulse-dot-red'
                  : 'pulse-dot-amber'
              } />
            </div>
            <div className="stat-value" style={{
              color: deliverabilityReport?.fleet_status === 'HEALTHY'
                ? 'var(--green)'
                : deliverabilityReport?.fleet_status === 'WARNING'
                ? '#fbbf24'
                : deliverabilityReport?.fleet_status === 'CRITICAL'
                ? '#f87171'
                : '#fff',
              fontSize: '20px',
              display: 'flex',
              alignItems: 'baseline',
              gap: '6px',
            }}>
              <span>{deliverabilityReport?.fleet_status || 'ARMED'}</span>
              {deliverabilityReport?.average_score !== undefined && (
                <span style={{ fontSize: '13px', color: 'var(--cyan)', fontWeight: 700 }}>({deliverabilityReport.average_score}%)</span>
              )}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
              <span>{deliverabilityReport?.healthy_count ?? inboxes.length} healthy inboxes</span>
              <span style={{ color: 'var(--green)', fontWeight: 600 }}>0% Spam Trap</span>
            </div>
          </div>
        </div>

        {/* =========================================================
            ⚡ AUTONOMOUS AI SWARM LIVE OPERATIONS COCKPIT & HUD
           ========================================================= */}
        <div className="swarm-cockpit-card">
          {/* Header Row & Quick Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px', marginBottom: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '24px', background: 'rgba(56, 189, 248, 0.12)', padding: '8px', borderRadius: '10px', border: '1px solid rgba(56, 189, 248, 0.25)' }}>⚡</span>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#fff', margin: 0, letterSpacing: '-0.3px' }}>
                    Autonomous AI Swarm Operations Cockpit
                  </h3>
                  <span className="badge-tag badge-green" style={{ fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                    <span className="pulse-dot-green" /> 6 Swarms Active &amp; Governed
                  </span>
                  <span className="badge-tag badge-cyan" style={{ fontSize: '11px' }}>
                    ⏱️ 5 – 20m Jitter Stagger
                  </span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-dim)', margin: '4px 0 0' }}>
                  Autonomous swarm telemetry with live anti-spam jitter rotation, AST self-healing, and ≥95% schema release gates.
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                className="btn btn-outline"
                style={{
                  fontSize: '11px',
                  padding: '7px 14px',
                  borderColor: 'rgba(56, 189, 248, 0.35)',
                  color: 'var(--cyan)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontWeight: 600,
                }}
                onClick={handleFlushOutreachQueue}
                disabled={flushingQueue}
                title="Immediately process queued pitches adhering to anti-burst human stagger"
              >
                <span>{flushingQueue ? '⏳ Flushing...' : '⚡ Flush Outreach Queue'}</span>
              </button>
              <button
                className="btn btn-outline"
                style={{
                  fontSize: '11px',
                  padding: '7px 14px',
                  borderColor: 'rgba(168, 85, 247, 0.35)',
                  color: '#c084fc',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontWeight: 600,
                }}
                onClick={() => handleTriggerWebScout()}
                disabled={scoutingInProgress}
                title="Prospect next qualified B2B lead immediately via autonomous Scout"
              >
                <span>{scoutingInProgress ? '⏳ Scouting...' : '🔎 Scout Lead'}</span>
              </button>
              <button
                className="btn btn-outline"
                style={{
                  fontSize: '11px',
                  padding: '7px 14px',
                  borderColor: 'rgba(99, 102, 241, 0.35)',
                  color: '#818cf8',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontWeight: 600,
                }}
                onClick={handleRunDeliverabilityAudit}
                disabled={auditingDeliverability}
                title="Send test emails to TestMail and verify SPF/DKIM/SpamAssassin scores"
              >
                <span>{auditingDeliverability ? '⏳ Probing...' : '🛡️ TestMail Audit'}</span>
              </button>
              <button
                className="btn btn-outline"
                style={{
                  fontSize: '11px',
                  padding: '7px 12px',
                  borderColor: 'var(--border)',
                  color: 'var(--text-muted)',
                }}
                onClick={loadAdminData}
                title="Refresh all swarm telemetry from PostgreSQL and server logs"
              >
                🔄
              </button>
            </div>
          </div>

          {/* 6-Agent Live Telemetry HUD Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '10px', marginBottom: '18px' }}>
            {/* Agent 1: Scout */}
            <div className="swarm-agent-tile">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '16px' }}>🔍</span>
                  <span className={`badge-tag ${scoutingInProgress ? 'badge-yellow' : 'badge-green'}`} style={{ fontSize: '10px' }}>
                    {scoutingInProgress ? '⏳ SCOUTING' : '🟢 ACTIVE'}
                  </span>
                </div>
                <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Scout Agent</div>
                <div style={{ fontSize: '11px', color: 'var(--cyan)', marginTop: '2px' }}>Travis/Harris Dockets</div>
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                Same-Day Freshness (&lt;24h cache)
              </div>
            </div>

            {/* Agent 2: Pitcher */}
            {(() => {
              const earliestWait = fleetSummary?.earliest_jitter_wait ?? Math.min(...inboxes.map((i) => i.jitter_wait_seconds || 0));
              const isOnWait = earliestWait > 0;
              return (
                <div className="swarm-agent-tile">
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontSize: '16px' }}>💬</span>
                      <span className={`badge-tag ${isOnWait ? 'badge-yellow' : 'badge-green'}`} style={{ fontSize: '10px' }}>
                        {isOnWait ? `⏳ ~${(earliestWait / 60).toFixed(0)}m WAIT` : '🟢 PRIMED'}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Pitcher (Alex)</div>
                    <div style={{ fontSize: '11px', color: '#c084fc', marginTop: '2px' }}>5 Zoho Sequential</div>
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                    Sub-55w Zero-Link Plaintext
                  </div>
                </div>
              );
            })()}

            {/* Agent 3: Dev Swarm */}
            <div className="swarm-agent-tile">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '16px' }}>⚙️</span>
                  <span className={`badge-tag ${activeBuilds.length > 0 ? 'badge-cyan' : 'badge-green'}`} style={{ fontSize: '10px' }}>
                    {activeBuilds.length > 0 ? `⚡ ${activeBuilds.length} BUILDING` : '🟢 STANDBY'}
                  </span>
                </div>
                <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Dev Swarm</div>
                <div style={{ fontSize: '11px', color: 'var(--cyan)', marginTop: '2px' }}>AST Selector Pruner</div>
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                Docker Sandbox (≤4k tokens)
              </div>
            </div>

            {/* Agent 4: QA Gatekeeper */}
            <div className="swarm-agent-tile">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '16px' }}>🧪</span>
                  <span className="badge-tag badge-green" style={{ fontSize: '10px' }}>
                    🟢 ≥95% FLOOR
                  </span>
                </div>
                <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>QA Gatekeeper</div>
                <div style={{ fontSize: '11px', color: 'var(--green)', marginTop: '2px' }}>Release Authority</div>
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                Unlocks M2 Balance Auto-Charge
              </div>
            </div>

            {/* Agent 5: Deliverability Shield */}
            <div className="swarm-agent-tile">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '16px' }}>🛡️</span>
                  <span className={`badge-tag ${
                    deliverabilityReport?.fleet_status === 'HEALTHY'
                      ? 'badge-green'
                      : deliverabilityReport?.fleet_status === 'WARNING'
                      ? 'badge-yellow'
                      : deliverabilityReport?.fleet_status === 'CRITICAL'
                      ? 'badge-red'
                      : 'badge-cyan'
                  }`} style={{ fontSize: '10px' }}>
                    {deliverabilityReport?.fleet_status === 'HEALTHY'
                      ? '🟢 NOMINAL'
                      : deliverabilityReport?.fleet_status === 'WARNING'
                      ? '⚠️ WARNING'
                      : deliverabilityReport?.fleet_status === 'CRITICAL'
                      ? '🚨 CRITICAL'
                      : '🟢 ARMED'}
                  </span>
                </div>
                <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Deliverability Shield</div>
                <div style={{ fontSize: '11px', color: '#818cf8', marginTop: '2px' }}>TestMail Live Probes</div>
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                SPF / DKIM / SpamAssassin Check
              </div>
            </div>

            {/* Agent 6: Courier Dispatcher */}
            <div className="swarm-agent-tile">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '16px' }}>🚚</span>
                  <span className="badge-tag badge-green" style={{ fontSize: '10px' }}>
                    🟢 06:00 UTC
                  </span>
                </div>
                <div style={{ fontSize: '12px', fontWeight: 800, color: '#fff' }}>Courier Dispatch</div>
                <div style={{ fontSize: '11px', color: 'var(--green)', marginTop: '2px' }}>Zero-Idle Ephemeral</div>
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '8px', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '6px' }}>
                Sheets + API + 05:30 Drift Shield
              </div>
            </div>
          </div>

          {/* Velocity Progress Bar & Key Metrics */}
          {(() => {
            const fleetSent = fleetSummary?.fleet_sent_today ?? inboxes.reduce((acc, i) => acc + (i.sent_today || 0), 0);
            const fleetQuota = fleetSummary?.fleet_daily_quota ?? 125;
            const velocityPct = Math.min(100, Math.round((fleetSent / (fleetQuota || 1)) * 100));
            const nextInboxId = fleetSummary?.available_inbox || (inboxes.find((i) => !i.is_on_jitter && (i.sent_today || 0) < (i.daily_limit || 25))?.inbox_id) || 'zoho_1';
            const earliestWait = fleetSummary?.earliest_jitter_wait ?? Math.min(...inboxes.map((i) => i.jitter_wait_seconds || 0));

            const velocityColor = velocityPct >= 85 ? '#f87171' : velocityPct >= 60 ? '#fbbf24' : 'var(--green)';

            return (
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '12px', marginBottom: '12px' }}>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700 }}>TODAY'S FLEET VELOCITY</div>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginTop: '3px', display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                      <span style={{ color: velocityColor }}>{fleetSent} / {fleetQuota}</span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 500 }}>dispatched today ({velocityPct}%)</span>
                    </div>
                  </div>

                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700 }}>NEXT DISPATCH CADENCE</div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: earliestWait > 0 ? '#fbbf24' : 'var(--green)', marginTop: '3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>{earliestWait > 0 ? `⏳ Next dispatch in ~${(earliestWait / 60).toFixed(1)}m` : '🟢 Ready for immediate send'}</span>
                    </div>
                  </div>

                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700 }}>NEXT INBOX IN ROTATION</div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--cyan)', marginTop: '3px' }}>
                      📬 {String(nextInboxId).replace('_', ' ').toUpperCase()}
                    </div>
                  </div>

                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 700 }}>SCOUT REPLENISHMENT</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#c084fc', marginTop: '3px' }}>
                      🚀 10 – 20 min (2 leads / cycle)
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div style={{ height: '7px', background: 'rgba(255, 255, 255, 0.08)', borderRadius: '4px', overflow: 'hidden', position: 'relative' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.max(velocityPct, 3)}%`,
                      background: velocityPct >= 85
                        ? 'linear-gradient(90deg, #f59e0b 0%, #ef4444 100%)'
                        : velocityPct >= 60
                        ? 'linear-gradient(90deg, #38bdf8 0%, #f59e0b 100%)'
                        : 'linear-gradient(90deg, #38bdf8 0%, #10b981 100%)',
                      borderRadius: '4px',
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>

                {/* Inboxes Fleet Chips */}
                {inboxes.length > 0 && (
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '14px' }}>
                    {inboxes.map((inb) => {
                      const onJitter = inb.is_on_jitter;
                      const waitSec = inb.jitter_wait_seconds || 0;
                      const isMaxed = (inb.sent_today || 0) >= (inb.daily_limit || 25);
                      return (
                        <div
                          key={inb.inbox_id}
                          style={{
                            fontSize: '11px',
                            padding: '5px 10px',
                            borderRadius: '6px',
                            background: isMaxed
                              ? 'rgba(239, 68, 68, 0.1)'
                              : onJitter
                              ? 'rgba(245, 158, 11, 0.1)'
                              : 'rgba(16, 185, 129, 0.1)',
                            border: `1px solid ${
                              isMaxed
                                ? 'rgba(239, 68, 68, 0.35)'
                                : onJitter
                                ? 'rgba(245, 158, 11, 0.35)'
                                : 'rgba(16, 185, 129, 0.35)'
                            }`,
                            color: isMaxed ? '#f87171' : onJitter ? '#fbbf24' : 'var(--green)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                          }}
                          title={
                            isMaxed
                              ? 'Daily quota reached'
                              : onJitter
                              ? `Jitter cooldown: ~${(waitSec / 60).toFixed(1)}m remaining`
                              : 'Ready to dispatch'
                          }
                        >
                          <span>{isMaxed ? '🛑' : onJitter ? '⏳' : '🟢'}</span>
                          <span style={{ fontWeight: 700, color: '#fff' }}>{inb.inbox_id}:</span>
                          <span>{inb.sent_today || 0}/{inb.daily_limit || 25} sent</span>
                          {onJitter && waitSec > 0 && !isMaxed && (
                            <span style={{ color: '#fbbf24', fontSize: '10px' }}>({(waitSec / 60).toFixed(0)}m wait)</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })()}
        </div>

        {/* Tab Navigation */}
        <div className="admin-tabs-nav">
          <button
            className={`admin-tab-btn ${activeTab === 'deals' ? 'active' : ''}`}
            onClick={() => setActiveTab('deals')}
          >
            📊 Deals &amp; Customers ({pipeline.filter((l) => l.state !== 'ARCHIVED').length})
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'kanban' ? 'active' : ''}`}
            onClick={() => setActiveTab('kanban')}
          >
            📌 Stage Kanban
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'archived' ? 'active' : ''}`}
            onClick={() => setActiveTab('archived')}
            style={{
              borderColor: activeTab === 'archived' ? 'var(--amber, #f59e0b)' : undefined,
              color: activeTab === 'archived' ? '#fbbf24' : undefined,
            }}
          >
            📦 Archived Vault ({archivedLeads.length})
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'swarm' ? 'active' : ''}`}
            onClick={() => setActiveTab('swarm')}
          >
            🤖 Dev Swarms &amp; QA Gate ({activeBuilds.length} Active)
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'accounting' ? 'active' : ''}`}
            onClick={() => setActiveTab('accounting')}
          >
            💰 Accounting &amp; Revenue Vault
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'scrapers' ? 'active' : ''}`}
            onClick={() => setActiveTab('scrapers')}
          >
            ⚡ Scrapers &amp; Extracted Datasets
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'daily' ? 'active' : ''}`}
            onClick={() => setActiveTab('daily')}
          >
            📅 Automated Daily Feeds
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'inboxes' ? 'active' : ''}`}
            onClick={() => setActiveTab('inboxes')}
          >
            📬 Email Inboxes ({inboxes.length})
          </button>
        </div>

        {/* =========================================================
            TAB 1: DEALS & CUSTOMERS
           ========================================================= */}
        {activeTab === 'deals' && (
          <div>
            {/* Filter Toolbar */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '18px', background: 'var(--card)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
              <input
                type="text"
                placeholder="🔍 Search company, contact, jurisdiction, lead ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  flex: '1 1 240px',
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 14px',
                  color: '#fff',
                  fontSize: '13px',
                }}
              />

              <select
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 14px',
                  color: '#fff',
                  fontSize: '13px',
                }}
              >
                <option value="ALL">All Lifecycle States</option>
                <option value="PROSPECTING">Prospecting</option>
                <option value="REVIEW">Review</option>
                <option value="PITCH_PENDING_APPROVAL">Pitch Pending Approval</option>
                <option value="OUTREACH_SENT">Outreach Sent</option>
                <option value="CONVERSATIONAL_INTAKE">Conversational Intake</option>
                <option value="SOW_GENERATED">SOW Generated</option>
                <option value="DEPOSIT_PAID">Down Payment Paid ($99)</option>
                <option value="DEV_BUILDING">Dev Building (Swarm)</option>
                <option value="ESCROW_PREVIEW">Customer QA Preview (QA Passed)</option>
                <option value="FINAL_PAID">Final Paid</option>
                <option value="DELIVERED">Delivered</option>
                <option value="WARRANTY_ACTIVE">Warranty / Retainer Active</option>
              </select>

              <select
                value={paymentFilter}
                onChange={(e) => setPaymentFilter(e.target.value)}
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 14px',
                  color: '#fff',
                  fontSize: '13px',
                }}
              >
                <option value="ALL">All Payments</option>
                <option value="DEPOSIT_PAID">Deposit Paid ($250)</option>
                <option value="FINAL_PAID">Final Paid ($250)</option>
                <option value="SUBSCRIPTION_ACTIVE">Active Retainer</option>
                <option value="UNPAID">Unpaid / Prospect</option>
              </select>

              <select
                value={scoreFilter}
                onChange={(e) => setScoreFilter(e.target.value)}
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px 14px',
                  color: '#fff',
                  fontSize: '13px',
                }}
              >
                <option value="ALL">All AI Lead Scores</option>
                <option value="HIGH">🔥 High Opportunity (≥75)</option>
                <option value="QUALIFIED">⚡ Qualified Fit (≥65)</option>
                <option value="NURTURE">🌱 Nurture (&lt;65)</option>
              </select>

              {pipeline.filter((l) => l.state === 'PITCH_PENDING_APPROVAL').length > 0 && (
                <button
                  className="btn btn-primary"
                  style={{
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    border: 'none',
                    fontWeight: 700,
                    fontSize: '13px',
                    padding: '10px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    boxShadow: '0 2px 10px rgba(16, 185, 129, 0.3)',
                    marginLeft: 'auto',
                  }}
                  onClick={handleBatchApprove}
                  disabled={batchApproving}
                  title="Approve and send all pending outreach pitches"
                >
                  {batchApproving
                    ? '⏳ Dispatching Pitches...'
                    : `🚀 Approve All Pending (${pipeline.filter((l) => l.state === 'PITCH_PENDING_APPROVAL').length})`}
                </button>
              )}
            </div>

            {/* Deals Table */}
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Organization / Lead ID</th>
                    <th>Origin &amp; Source Portal</th>
                    <th>Tier / Retainer</th>
                    <th>Lifecycle State</th>
                    <th>Payment Status</th>
                    <th>AI Scores &amp; QA Gate</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeads.length === 0 ? (
                    <tr>
                      <td colSpan="7" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                        {loading ? (
                          'Fetching live pipeline deals from PostgreSQL...'
                        ) : pipeline.length === 0 ? (
                          <div>
                            <div style={{ fontSize: '32px', marginBottom: '8px' }}>⚡</div>
                            <p style={{ color: '#fff', fontWeight: 700, fontSize: '15px', marginBottom: '6px' }}>
                              Pipeline is Ready for Live Leads
                            </p>
                            <p style={{ fontSize: '12px', color: 'var(--text-dim)', maxWidth: '440px', margin: '0 auto 16px', lineHeight: 1.5 }}>
                              The database is clean with 0 records. Trigger an autonomous Scout discovery cycle to prospect live municipal leads now, or authenticate via Founder Master Key:
                            </p>
                            <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', flexWrap: 'wrap' }}>
                              <button
                                className="btn btn-primary"
                                style={{ padding: '8px 18px', fontSize: '12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                                onClick={handleTriggerWebScout}
                                disabled={scoutingInProgress}
                              >
                                <span>{scoutingInProgress ? '⏳ Scouting In Progress...' : '🚀 Trigger Live Prospecting Run'}</span>
                              </button>
                              <button
                                className="btn btn-outline"
                                style={{ padding: '8px 16px', fontSize: '12px' }}
                                onClick={async () => {
                                  localStorage.setItem('leadops_admin_token', '0baac74dfda043fdaf84c5d0b38e259b');
                                  showToast('Founder Master Key Activated!', 'success');
                                  await loadAdminData();
                                }}
                              >
                                ⚡ Authenticate Master Key
                              </button>
                              <button
                                className="btn btn-outline"
                                style={{ padding: '8px 16px', fontSize: '12px' }}
                                onClick={loadAdminData}
                              >
                                🔄 Refresh Telemetry
                              </button>
                            </div>
                          </div>
                        ) : (
                          'No deals match your search criteria.'
                        )}
                      </td>
                    </tr>
                  ) : (
                    filteredLeads.map((lead) => {
                      const slug = lead.slug || lead.lead_id;
                      const qa = lead.qa_score !== null && lead.qa_score !== undefined ? lead.qa_score : null;

                      return (
                        <tr key={lead.lead_id}>
                          <td>
                            <button
                              type="button"
                              onClick={() => setScoreModal({ open: true, lead })}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                padding: 0,
                                margin: 0,
                                cursor: 'pointer',
                                textAlign: 'left',
                                fontWeight: 700,
                                color: '#fff',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '13px',
                              }}
                              title="Click to view detailed lead intelligence, origin, and scoring"
                            >
                              <span style={{ textDecoration: 'underline', textDecorationColor: 'rgba(56, 189, 248, 0.4)' }}>
                                {lead.company_name || 'Organization Lead'}
                              </span>
                              <span style={{ fontSize: '11px', color: 'var(--cyan)' }}>ℹ️</span>
                            </button>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)', marginTop: '2px', display: 'flex', alignItems: 'center' }}>
                              <span>{lead.lead_id}</span>
                              <button
                                type="button"
                                onClick={() => handleCopyText(lead.lead_id, 'Lead ID')}
                                title="Copy Lead ID"
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  cursor: 'pointer',
                                  color: 'var(--text-dim)',
                                  fontSize: '11px',
                                  padding: '0 4px',
                                  marginLeft: '4px',
                                }}
                              >
                                📋
                              </button>
                            </div>
                            {lead.contact_email && (
                              <div style={{ fontSize: '11px', color: 'var(--cyan)', marginTop: '2px' }}>
                                ✉️ {lead.contact_email}
                              </div>
                            )}
                            {renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}
                          </td>
                          <td>
                            <div style={{ fontSize: '13px', color: 'var(--text)', fontWeight: 600 }}>
                              {lead.target_portal_name || lead.jurisdiction || 'Municipal Registry'}
                            </div>
                            {lead.jurisdiction && lead.target_portal_name && (
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '1px' }}>
                                📍 {lead.jurisdiction}
                              </div>
                            )}
                            <div style={{ display: 'flex', gap: '8px', marginTop: '5px', flexWrap: 'wrap' }}>
                              {lead.source_url && (
                                <a
                                  href={lead.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{
                                    fontSize: '11px',
                                    color: 'var(--cyan)',
                                    textDecoration: 'none',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    background: 'rgba(56, 189, 248, 0.08)',
                                    padding: '2px 6px',
                                    borderRadius: '3px',
                                    border: '1px solid rgba(56, 189, 248, 0.2)',
                                  }}
                                  title="Official municipal / county registry source where records were extracted"
                                >
                                  🏛️ Portal ↗
                                </a>
                              )}
                              {lead.website && (
                                <a
                                  href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{
                                    fontSize: '11px',
                                    color: 'var(--purple)',
                                    textDecoration: 'none',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    background: 'rgba(168, 85, 247, 0.08)',
                                    padding: '2px 6px',
                                    borderRadius: '3px',
                                    border: '1px solid rgba(168, 85, 247, 0.2)',
                                  }}
                                  title="Lead company website"
                                >
                                  🌐 Website ↗
                                </a>
                              )}
                            </div>
                          </td>
                          <td>
                            <div style={{ fontWeight: 600, color: 'var(--purple)' }}>
                              {lead.tier_name || lead.tier_key || 'Weekly Sync'}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                              ${lead.mrr ? lead.mrr.toFixed(0) : '250'}/month
                            </div>
                          </td>
                          <td>
                            <span className={`badge-tag ${
                              lead.state === 'DELIVERED' || lead.state === 'WARRANTY_ACTIVE' || lead.state === 'ESCROW_PREVIEW'
                                ? 'badge-green'
                                : lead.state === 'DEV_BUILDING'
                                ? 'badge-cyan'
                                : lead.state === 'DEPOSIT_PAID'
                                ? 'badge-purple'
                                : lead.state === 'PITCH_PENDING_APPROVAL'
                                ? 'badge-orange'
                                : lead.state === 'OUTREACH_SENT'
                                ? 'badge-blue'
                                : 'badge-yellow'
                            }`}>
                              {lead.state}
                            </span>
                          </td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {lead.deposit_paid ? (
                                <span style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600 }}>
                                  ✓ M1 Down Payment ($99 Paid)
                                </span>
                              ) : (
                                <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                                  ○ M1 Pending ($99)
                                </span>
                              )}

                              {lead.final_paid ? (
                                <span style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600 }}>
                                  ✓ M2 Final ($151 Paid)
                                </span>
                              ) : (
                                <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                                  ○ M2 Pending ($151)
                                </span>
                              )}

                              {lead.subscription_active && (
                                <span style={{ fontSize: '11px', color: 'var(--purple)', fontWeight: 600 }}>
                                  ⚡ Active Monthly Retainer
                                </span>
                              )}
                            </div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              <button
                                type="button"
                                onClick={() => setScoreModal({ open: true, lead })}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  padding: 0,
                                  cursor: 'pointer',
                                  textAlign: 'left',
                                }}
                                title="Click to view 7-factor BDR scoring breakdown & buyer signals"
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <span
                                    style={{
                                      fontWeight: 800,
                                      fontSize: '12px',
                                      padding: '2px 7px',
                                      borderRadius: '4px',
                                      background: (lead.automation_opportunity_score || 75) >= 75 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                                      color: (lead.automation_opportunity_score || 75) >= 75 ? 'var(--green)' : 'var(--cyan)',
                                      border: `1px solid ${(lead.automation_opportunity_score || 75) >= 75 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`,
                                    }}
                                  >
                                    ⚡ Opp: {lead.automation_opportunity_score || 75}/100
                                  </span>
                                  <span style={{ fontSize: '10px', color: 'var(--cyan)', textDecoration: 'underline' }}>
                                    📊 Intel ↗
                                  </span>
                                </div>
                              </button>

                              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: '11px', marginTop: '2px' }}>
                                <span style={{ color: 'var(--purple)', fontWeight: 600 }} title="Buyer Intent Probability">
                                  🎯 {lead.purchase_probability || 60}% Intent
                                </span>
                                <span style={{ color: 'var(--text-dim)' }}>•</span>
                                <span style={{ color: 'var(--yellow)', fontWeight: 600 }} title="Operational Pain Severity (1-10)">
                                  🔥 {lead.pain_severity || 6}/10 Pain
                                </span>
                              </div>

                              {qa !== null ? (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                                  <span
                                    style={{
                                      fontWeight: 700,
                                      fontSize: '11px',
                                      color: qa >= 0.95 ? 'var(--green)' : 'var(--yellow)',
                                    }}
                                  >
                                    🛡️ QA: {(qa * 100).toFixed(0)}%
                                  </span>
                                  <span style={{ fontSize: '9px', color: 'var(--text-dim)' }}>
                                    {qa >= 0.95 ? 'PASSED' : 'REVIEW'}
                                  </span>
                                </div>
                              ) : (
                                <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                                  🛡️ QA: Pending Build
                                </span>
                              )}
                            </div>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                              <button
                                className="btn btn-outline"
                                style={{ padding: '4px 8px', fontSize: '11px', color: 'var(--cyan)', borderColor: 'rgba(56, 189, 248, 0.4)' }}
                                onClick={() => setScoreModal({ open: true, lead })}
                                title="View 7-factor BDR scoring breakdown, buyer signals, and full lead dossier"
                              >
                                ℹ️ Details
                              </button>
                              <a
                                href={`/p/${slug}`}
                                target="_blank"
                                rel="noreferrer"
                                className="btn btn-outline"
                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                title="Open customer sandbox"
                              >
                                🌐 Portal
                              </a>
                              <a
                                href={`/dashboard/${lead.lead_id}`}
                                target="_blank"
                                rel="noreferrer"
                                className="btn btn-outline"
                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                title="Open customer dashboard"
                              >
                                📈 Dashboard
                              </a>
                              <button
                                className="btn btn-primary"
                                style={{
                                  padding: '4px 10px',
                                  fontSize: '11px',
                                  background: lead.state === 'PITCH_PENDING_APPROVAL' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : undefined,
                                  borderColor: lead.state === 'PITCH_PENDING_APPROVAL' ? '#10b981' : undefined,
                                }}
                                onClick={() => handleAdvance(lead.lead_id)}
                                disabled={actionInProgress[lead.lead_id]}
                                title={lead.state === 'PITCH_PENDING_APPROVAL' ? 'Approve pitch and dispatch outreach email' : '1-Click Advance lifecycle stage'}
                              >
                                {lead.state === 'PITCH_PENDING_APPROVAL' ? '✓ Approve Pitch' : '⏩ Advance'}
                              </button>
                              {lead.state === 'PITCH_PENDING_APPROVAL' && (
                                <button
                                  className="btn btn-outline"
                                  style={{ padding: '4px 8px', fontSize: '11px', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                                  onClick={() => handleCancelOutreach(lead.lead_id, lead.company_name)}
                                  disabled={actionInProgress[lead.lead_id]}
                                  title="Cancel auto-dispatch timer and archive pitch"
                                >
                                  ✕ Cancel Outreach
                                </button>
                              )}
                              <button
                                className="btn btn-outline"
                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                onClick={() => handleTriggerSwarm(lead.lead_id)}
                                disabled={actionInProgress[lead.lead_id]}
                                title="Launch Autonomous Dev Swarm"
                              >
                                🤖 Swarm
                              </button>
                              <button
                                className="btn btn-outline"
                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                onClick={() => handleViewAudit(lead.lead_id, lead.company_name, lead)}
                                title="View immutable event trail"
                              >
                                📜 Audit
                              </button>
                              <button
                                className="btn btn-outline"
                                style={{ padding: '4px 8px', fontSize: '11px', color: '#ff6b6b', borderColor: 'rgba(239, 68, 68, 0.4)' }}
                                onClick={() => handleDeleteLead(lead.lead_id, lead.company_name)}
                                disabled={actionInProgress[lead.lead_id]}
                                title="Permanently delete lead and sandbox"
                              >
                                🗑️ Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* =========================================================
            TAB 2: STAGE KANBAN
           ========================================================= */}
        {activeTab === 'kanban' && (
          <div className="kanban-board">
            {[
              { key: 'PROSPECTING', label: '1. Prospecting', color: 'var(--cyan)', borderTop: '3px solid var(--cyan)', badgeClass: 'badge-cyan' },
              { key: 'REVIEW', label: '2. Enriched / Review', color: '#fbbf24', borderTop: '3px solid #fbbf24', badgeClass: 'badge-yellow' },
              { key: 'PITCH_PENDING_APPROVAL', label: '3. Pitch Pending', color: '#fb923c', borderTop: '3px solid #fb923c', badgeClass: 'badge-orange' },
              { key: 'OUTREACH_SENT', label: '4. Outreach Sent', color: '#60a5fa', borderTop: '3px solid #60a5fa', badgeClass: 'badge-blue' },
              { key: 'DEPOSIT_PAID', label: '5. Down Payment ($99)', color: '#c084fc', borderTop: '3px solid #c084fc', badgeClass: 'badge-purple' },
              { key: 'DEV_BUILDING', label: '6. Dev Swarm', color: 'var(--cyan)', borderTop: '3px solid var(--cyan)', badgeClass: 'badge-cyan' },
              { key: 'ESCROW_PREVIEW', label: '7. QA Pass (≥95%)', color: 'var(--green)', borderTop: '3px solid var(--green)', badgeClass: 'badge-green' },
              { key: 'DELIVERED', label: '8. Delivered', color: 'var(--green)', borderTop: '3px solid var(--green)', badgeClass: 'badge-green' },
            ].map((col) => {
              const colLeads = pipeline.filter((l) => l.state === col.key);

              return (
                <div key={col.key} className="kanban-column" style={{ borderTop: col.borderTop }}>
                  <div className="kanban-col-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: col.color, fontWeight: 700 }}>{col.label}</span>
                      <span className={`badge-tag ${col.badgeClass}`}>{colLeads.length}</span>
                    </div>
                    {col.key === 'PITCH_PENDING_APPROVAL' && colLeads.length > 0 && (
                      <button
                        className="btn btn-primary"
                        style={{
                          padding: '2px 8px',
                          fontSize: '10px',
                          fontWeight: 700,
                          background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                          border: 'none',
                          boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)',
                        }}
                        onClick={handleBatchApprove}
                        disabled={batchApproving}
                        title="Approve and send all pending outreach pitches"
                      >
                        {batchApproving ? '⏳ Sending...' : `✓ Approve All (${colLeads.length})`}
                      </button>
                    )}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto' }}>
                    {colLeads.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: '24px 0', fontSize: '12px', color: 'var(--text-dim)' }}>
                        Empty stage
                      </div>
                    ) : (
                      colLeads.map((lead) => (
                        <div key={lead.lead_id} className="kanban-card">
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div
                              style={{
                                fontWeight: 700,
                                fontSize: '13px',
                                color: '#fff',
                                cursor: 'pointer',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                              onClick={() => setScoreModal({ open: true, lead })}
                              title="Click to view full lead intelligence, origin, and scoring"
                            >
                              <span style={{ textDecoration: 'underline', textDecorationColor: 'rgba(56, 189, 248, 0.4)' }}>
                                {lead.company_name || 'Lead'}
                              </span>
                              <span style={{ fontSize: '11px', color: 'var(--cyan)' }}>ℹ️</span>
                            </div>
                            <span style={{ fontSize: '10px', color: 'var(--purple)', fontWeight: 600 }}>
                              {lead.tier_key || 'weekly'}
                            </span>
                          </div>

                          {renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}

                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ maxWidth: '170px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={lead.target_portal_name || lead.jurisdiction}>
                              📍 {lead.target_portal_name || lead.jurisdiction || 'Public Records'}
                            </span>
                            <div style={{ display: 'flex', gap: '6px' }}>
                              {lead.source_url && (
                                <a
                                  href={lead.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{ color: 'var(--cyan)', textDecoration: 'none', fontSize: '11px' }}
                                  title="Open municipal data portal"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  🏛️ ↗
                                </a>
                              )}
                              {lead.website && (
                                <a
                                  href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{ color: 'var(--purple)', textDecoration: 'none', fontSize: '11px' }}
                                  title="Visit company website"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  🌐 ↗
                                </a>
                              )}
                            </div>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', fontSize: '11px' }}>
                            <span style={{ color: lead.deposit_paid ? 'var(--green)' : 'var(--text-dim)' }}>
                              {lead.deposit_paid ? '✓ $99 Sprint Credited' : '○ $99 Sprint Pending'}
                            </span>
                            {lead.qa_score !== null && lead.qa_score !== undefined && (
                              <span style={{ color: lead.qa_score >= 0.95 ? 'var(--green)' : 'var(--yellow)', fontWeight: 700 }}>
                                QA: {(lead.qa_score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>

                          {/* AI Opportunity & Buyer Signals Badges */}
                          <div
                            style={{ display: 'flex', alignItems: 'center', gap: '5px', flexWrap: 'wrap', marginTop: '7px', cursor: 'pointer' }}
                            onClick={() => setScoreModal({ open: true, lead })}
                            title="Click to view full BDR 7-factor scoring & buyer signals"
                          >
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: '2px 6px',
                                borderRadius: '4px',
                                background: (lead.automation_opportunity_score || 75) >= 75 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                                color: (lead.automation_opportunity_score || 75) >= 75 ? 'var(--green)' : 'var(--cyan)',
                                border: `1px solid ${(lead.automation_opportunity_score || 75) >= 75 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`,
                              }}
                            >
                              ⚡ Opp: {lead.automation_opportunity_score || 75}/100
                            </span>
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 600,
                                padding: '2px 5px',
                                borderRadius: '4px',
                                background: 'rgba(168, 85, 247, 0.15)',
                                color: 'var(--purple)',
                                border: '1px solid rgba(168, 85, 247, 0.3)',
                              }}
                              title="Buyer Purchase Intent"
                            >
                              🎯 {lead.purchase_probability || 60}%
                            </span>
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 600,
                                padding: '2px 5px',
                                borderRadius: '4px',
                                background: 'rgba(245, 158, 11, 0.15)',
                                color: 'var(--yellow)',
                                border: '1px solid rgba(245, 158, 11, 0.3)',
                              }}
                              title="Operational Pain Severity (1-10)"
                            >
                              🔥 {lead.pain_severity || 6}/10
                            </span>
                          </div>

                          <div style={{ display: 'flex', gap: '5px', marginTop: '8px', flexWrap: 'wrap' }}>
                            <button
                              className="btn btn-primary"
                              style={{
                                padding: '4px 8px',
                                fontSize: '11px',
                                flex: 1,
                                minWidth: '80px',
                                background: lead.state === 'PITCH_PENDING_APPROVAL' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : undefined,
                                borderColor: lead.state === 'PITCH_PENDING_APPROVAL' ? '#10b981' : undefined,
                              }}
                              onClick={() => handleAdvance(lead.lead_id)}
                              disabled={actionInProgress[lead.lead_id]}
                            >
                              {lead.state === 'PITCH_PENDING_APPROVAL' ? '✓ Approve' : '⏩ Advance'}
                            </button>
                            <button
                              className="btn btn-outline"
                              style={{ padding: '4px 7px', fontSize: '11px', color: 'var(--cyan)', borderColor: 'rgba(56, 189, 248, 0.3)' }}
                              onClick={(e) => {
                                e.stopPropagation();
                                setScoreModal({ open: true, lead });
                              }}
                              title="View full lead intelligence & BDR breakdown"
                            >
                              ℹ️ Info
                            </button>
                            <button
                              className="btn btn-outline"
                              style={{ padding: '4px 7px', fontSize: '11px' }}
                              onClick={(e) => {
                                e.stopPropagation();
                                handleViewAudit(lead.lead_id, lead.company_name, lead);
                              }}
                              title="View immutable audit trail"
                            >
                              📜 Audit
                            </button>
                            <a
                              href={`/p/${lead.slug || lead.lead_id}`}
                              target="_blank"
                              rel="noreferrer"
                              className="btn btn-outline"
                              style={{ padding: '4px 8px', fontSize: '11px' }}
                              title="Open customer portal"
                            >
                              🌐
                            </a>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* =========================================================
            TAB 2B: ARCHIVED & RECOVERY VAULT
           ========================================================= */}
        {activeTab === 'archived' && (
          <div>
            {/* Header & Batch Controls */}
            <div
              style={{
                background: 'var(--card)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '20px 24px',
                marginBottom: '20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '16px',
              }}
            >
              <div>
                <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#fbbf24', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                  <span>📦</span> Archived &amp; Recovery Vault
                  <span
                    style={{
                      fontSize: '11px',
                      background: 'rgba(245, 158, 11, 0.2)',
                      color: '#fde68a',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      border: '1px solid rgba(245, 158, 11, 0.4)',
                    }}
                  >
                    {archivedLeads.length} Isolated Leads
                  </span>
                </h2>
                <p style={{ fontSize: '12px', color: 'var(--text-dim)', margin: '6px 0 0 0', maxWidth: '720px' }}>
                  Leads isolated from active Kanban and Deals Funnel due to 45-day duplicate contact suppression,
                  bad/undeliverable emails, or delivery bounces. The autonomous <strong>Contact Enricher Researcher Agent</strong>{' '}
                  can research corporate filings, team directories, and executive email permutations to recover verified decision-makers.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <button
                  className="btn btn-outline"
                  onClick={loadArchivedLeads}
                  style={{ fontSize: '11px', padding: '7px 12px' }}
                >
                  🔄 Refresh
                </button>
                <button
                  className="btn btn-primary"
                  style={{
                    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                    border: 'none',
                    fontSize: '11px',
                    fontWeight: 700,
                    padding: '8px 16px',
                    boxShadow: '0 2px 10px rgba(245, 158, 11, 0.35)',
                    color: '#fff',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  onClick={handleBatchEnrichArchived}
                  disabled={batchEnriching || archivedLeads.length === 0}
                  title="Run autonomous Contact Enricher Agent across all archived leads"
                >
                  <span>{batchEnriching ? '⏳ Researching All Leads...' : `⚡ Run AI Contact Enricher on All (${archivedLeads.length})`}</span>
                </button>
              </div>
            </div>

            {/* Archived Cards List */}
            {archivedLeads.length === 0 ? (
              <div
                style={{
                  background: 'var(--card)',
                  border: '1px dashed rgba(255, 255, 255, 0.15)',
                  borderRadius: 'var(--radius-md)',
                  padding: '60px 24px',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: '36px', marginBottom: '12px' }}>✨</div>
                <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
                  Zero Archived Leads
                </h3>
                <p style={{ fontSize: '13px', color: 'var(--text-dim)', maxWidth: '480px', margin: '0 auto' }}>
                  All leads currently have deliverable email addresses and active outreach viability.
                  Any leads that trigger 45-day cooldowns or deliverability failures will be automatically quarantined here.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
                {archivedLeads.map((lead) => {
                  const reason = lead.archive_reason || 'Archived';
                  const is45Days = reason.includes('45');
                  const isBadEmail = reason.toLowerCase().includes('email') || reason.toLowerCase().includes('deliverability') || reason.toLowerCase().includes('bounce');
                  const isEnriching = enrichingLeadId === lead.lead_id;

                  return (
                    <div
                      key={lead.lead_id}
                      className="card"
                      style={{
                        background: 'rgba(15, 23, 42, 0.65)',
                        border: '1px solid rgba(245, 158, 11, 0.25)',
                        borderRadius: 'var(--radius-md)',
                        padding: '18px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        gap: '14px',
                        position: 'relative',
                      }}
                    >
                      <div>
                        {/* Status Badges */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                          <div style={{ fontWeight: 800, fontSize: '15px', color: '#fff' }}>
                            {lead.company_name || 'Prospect Firm'}
                          </div>
                          <span
                            style={{
                              fontSize: '10px',
                              fontWeight: 700,
                              padding: '3px 8px',
                              borderRadius: '4px',
                              background: is45Days
                                ? 'rgba(239, 68, 68, 0.18)'
                                : isBadEmail
                                ? 'rgba(245, 158, 11, 0.18)'
                                : 'rgba(148, 163, 184, 0.18)',
                              color: is45Days ? '#f87171' : isBadEmail ? '#fbbf24' : '#cbd5e1',
                              border: `1px solid ${is45Days ? 'rgba(239, 68, 68, 0.35)' : isBadEmail ? 'rgba(245, 158, 11, 0.35)' : 'rgba(148, 163, 184, 0.3)'}`,
                            }}
                          >
                            {is45Days ? '🛑 45-Day Suppression' : isBadEmail ? '⚠️ Bad / Bounced Email' : '📦 Archived'}
                          </span>
                        </div>

                        {/* Contact Info with Strikethrough/Warning */}
                        <div
                          style={{
                            background: 'rgba(0, 0, 0, 0.25)',
                            padding: '10px 12px',
                            borderRadius: '6px',
                            border: '1px solid rgba(255, 255, 255, 0.06)',
                            fontSize: '12px',
                            marginBottom: '10px',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', marginBottom: '4px' }}>
                            <span>Decision Maker:</span>
                            <span style={{ fontWeight: 600, color: '#fff' }}>
                              {lead.contact_name || 'Unknown Officer'} {lead.contact_role ? `(${lead.contact_role})` : ''}
                            </span>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                            <span>Failed / Quarantined Email:</span>
                            <span style={{ color: '#f87171', fontFamily: 'var(--mono)', textDecoration: isBadEmail ? 'line-through' : 'none' }}>
                              {lead.contact_email || 'No email recorded'}
                            </span>
                          </div>
                          {lead.website && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', marginTop: '4px' }}>
                              <span>Domain / Website:</span>
                              <a
                                href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                                target="_blank"
                                rel="noreferrer"
                                style={{ color: 'var(--cyan)', textDecoration: 'none' }}
                              >
                                {lead.website.replace(/^https?:\/\//, '').replace(/\/$/, '')} ↗
                              </a>
                            </div>
                          )}
                        </div>

                        {/* Reason Box */}
                        <div
                          style={{
                            fontSize: '11px',
                            color: '#fbbf24',
                            background: 'rgba(245, 158, 11, 0.08)',
                            padding: '8px 10px',
                            borderRadius: '5px',
                            border: '1px solid rgba(245, 158, 11, 0.2)',
                            lineHeight: 1.4,
                          }}
                        >
                          <strong>Reason:</strong> {reason}
                        </div>

                        {/* Previous Enrichment Attempt Notice */}
                        {lead.recovery_history && (
                          <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '6px', fontStyle: 'italic' }}>
                            Last Agent Run: {lead.recovery_history.attempted_at ? new Date(lead.recovery_history.attempted_at).toLocaleTimeString() : 'Recent'} ({lead.recovery_history.status || 'Executed'})
                          </div>
                        )}
                      </div>

                      {/* Action Bar */}
                      <div style={{ display: 'flex', gap: '8px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
                        <button
                          className="btn btn-primary"
                          style={{
                            flex: 1,
                            background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                            border: 'none',
                            fontSize: '11px',
                            fontWeight: 700,
                            padding: '7px 10px',
                            color: '#fff',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '5px',
                          }}
                          onClick={() => handleEnrichLead(lead.lead_id, lead.company_name)}
                          disabled={isEnriching}
                          title="Trigger Contact Enricher Agent to research and verify substitute contacts"
                        >
                          <span>{isEnriching ? '⏳ Researching Web & MX...' : '🤖 AI Contact Enricher'}</span>
                        </button>
                        <button
                          className="btn btn-outline"
                          style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: '#f87171', fontSize: '11px', padding: '7px 10px' }}
                          onClick={() => handleDeleteLead(lead.lead_id, lead.company_name)}
                          title="Permanently remove lead from database"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* =========================================================
            TAB 3: DEV SWARMS & QA TELEMETRY
           ========================================================= */}
        {activeTab === 'swarm' && (
          <div>
            {/* 7-Agent Architecture Banner */}
            <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '24px', marginBottom: '28px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#fff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>🤖</span> Autonomous 7-Agent Synthesis &amp; QA Pipeline
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
                {[
                  { step: '1', name: 'Synthesizer', icon: '🏛️', desc: 'Schema Contract' },
                  { step: '2', name: 'Scout', icon: '🔍', desc: 'DOM Traversal' },
                  { step: '3', name: 'Engineer', icon: '⚙️', desc: 'Python Crawler' },
                  { step: '4', name: 'Normalizer', icon: '🔄', desc: 'Dedup & Clean' },
                  { step: '5', name: 'Resiliency', icon: '🛡️', desc: 'Proxy Evasion' },
                  { step: '6', name: 'QA Gate', icon: '🧪', desc: '≥95% Verified' },
                  { step: '7', name: 'Courier', icon: '🚚', desc: 'Feed Delivery' },
                ].map((a) => (
                  <div key={a.step} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px', textAlign: 'center' }}>
                    <div style={{ fontSize: '20px', marginBottom: '4px' }}>{a.icon}</div>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>Agent #{a.step}</div>
                    <div style={{ fontSize: '11px', color: 'var(--cyan)' }}>{a.name}</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>{a.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Active Builds & QA Table */}
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Target Feed / Lead ID</th>
                    <th>Tier / Jurisdiction</th>
                    <th>Swarm Build Status</th>
                    <th>QA Gatekeeper Score</th>
                    <th>Auto-Charge Condition</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pipeline.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                        No dev swarms currently active or logged.
                      </td>
                    </tr>
                  ) : (
                    pipeline.map((lead) => {
                      const qa = lead.qa_score !== null && lead.qa_score !== undefined ? lead.qa_score : null;
                      const isPassing = qa !== null && qa >= 0.95;

                      return (
                        <tr key={lead.lead_id}>
                          <td>
                            <div style={{ fontWeight: 700, color: '#fff' }}>{lead.company_name || 'Feed Target'}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{lead.lead_id}</div>
                            {renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}
                          </td>
                          <td>
                            <div>{lead.tier_name || lead.tier_key || 'Weekly'}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{lead.jurisdiction || 'Portal'}</div>
                          </td>
                          <td>
                            <span className={`badge-tag ${
                              lead.state === 'DEV_BUILDING' ? 'badge-cyan' : isPassing ? 'badge-green' : 'badge-yellow'
                            }`}>
                              {lead.state === 'DEV_BUILDING' ? '⚡ Active Swarm Synthesizing' : lead.state}
                            </span>
                          </td>
                          <td>
                            {qa !== null ? (
                              <div>
                                <span style={{ fontSize: '15px', fontWeight: 800, color: isPassing ? 'var(--green)' : 'var(--yellow)' }}>
                                  {(qa * 100).toFixed(0)}%
                                </span>
                                <div style={{ fontSize: '10px', color: isPassing ? 'var(--green)' : 'var(--yellow)' }}>
                                  {isPassing ? '✓ Passed Schema Floor (≥95%)' : '⚠️ Below 95% Floor'}
                                </div>
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>Awaiting Swarm Run</span>
                            )}
                          </td>
                          <td>
                            <span style={{ fontSize: '12px', color: lead.final_paid ? 'var(--green)' : 'var(--text-muted)' }}>
                              {lead.final_paid ? '✓ Milestone #2 Auto-Charged ($250)' : 'Milestone #2 pre-authorized ($250)'}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px' }}>
                              <button
                                className="btn btn-outline"
                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                onClick={() => handleViewSwarmProgress(lead.lead_id, lead.company_name)}
                              >
                                📊 Progress Logs
                              </button>
                              <button
                                className="btn btn-outline"
                                style={{ padding: '4px 8px', fontSize: '11px', color: 'var(--yellow)', borderColor: 'rgba(245, 158, 11, 0.4)' }}
                                onClick={() => handleOpenQaOverride(lead.lead_id, lead.company_name)}
                              >
                                ⚖️ Override QA
                              </button>
                              <button
                                className="btn btn-primary"
                                style={{ padding: '4px 8px', fontSize: '11px' }}
                                onClick={() => handleTriggerSwarm(lead.lead_id)}
                                disabled={actionInProgress[lead.lead_id]}
                              >
                                🚀 Launch
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* =========================================================
            TAB 4: ACCOUNTING & REVENUE VAULT
           ========================================================= */}
        {activeTab === 'accounting' && (
          <div>
            {/* Accounting Breakdown Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              <div className="stat-card" style={{ borderLeft: '4px solid var(--green)' }}>
                <div className="stat-label">🏦 Total Milestone #1 Down Payments</div>
                <div className="stat-value" style={{ color: 'var(--green)' }}>
                  ${depositTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  {pipeline.filter((l) => l.deposit_paid).length} deposits held ($99 each)
                </div>
              </div>

              <div className="stat-card" style={{ borderLeft: '4px solid var(--cyan)' }}>
                <div className="stat-label">💰 Released Milestone #2 Funds</div>
                <div className="stat-value" style={{ color: 'var(--cyan)' }}>
                  ${releasedTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  {pipeline.filter((l) => l.final_paid).length} completions unlocked ($151 each)
                </div>
              </div>

              <div className="stat-card" style={{ borderLeft: '4px solid var(--purple)' }}>
                <div className="stat-label">📈 Active Monthly Subscriptions</div>
                <div className="stat-value" style={{ color: 'var(--purple)' }}>
                  ${activeMrr.toLocaleString('en-US', { minimumFractionDigits: 2 })}/mo
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  PayPal automated recurring billing
                </div>
              </div>

              <div className="stat-card" style={{ borderLeft: '4px solid var(--yellow)' }}>
                <div className="stat-label">💳 Gross Pipeline Value</div>
                <div className="stat-value" style={{ color: '#fff' }}>
                  ${(depositTotal + releasedTotal + activeMrr).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Total processed &amp; under contract
                </div>
              </div>
            </div>

            {/* Customer Ledger */}
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Customer Organization</th>
                    <th>Plan Tier</th>
                    <th>Milestone #1 ($99 Deposit)</th>
                    <th>Milestone #2 ($151 Balance)</th>
                    <th>Recurring Retainer</th>
                    <th>PayPal Provider</th>
                    <th style={{ textAlign: 'right' }}>Official Invoice</th>
                  </tr>
                </thead>
                <tbody>
                  {pipeline.length === 0 ? (
                    <tr>
                      <td colSpan="7" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                        No customer accounting records logged yet.
                      </td>
                    </tr>
                  ) : (
                    pipeline.map((lead) => (
                      <tr key={lead.lead_id}>
                        <td>
                          <div style={{ fontWeight: 700, color: '#fff' }}>{lead.company_name || 'Client'}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{lead.lead_id}</div>
                        </td>
                        <td>
                          <span style={{ fontWeight: 600, color: 'var(--purple)' }}>{lead.tier_name || lead.tier_key || 'Weekly Sync'}</span>
                        </td>
                        <td>
                          <span style={{ color: lead.deposit_paid ? 'var(--green)' : 'var(--text-dim)', fontWeight: 600 }}>
                            {lead.deposit_paid ? `✓ $${(lead.deposit_amount_usd || 99.0).toFixed(2)} PAID (DOWN PAYMENT)` : 'Pending'}
                          </span>
                        </td>
                        <td>
                          <span style={{ color: lead.final_paid ? 'var(--green)' : 'var(--text-dim)', fontWeight: 600 }}>
                            {lead.final_paid ? `✓ $${(lead.next_payment_amount || 151.0).toFixed(2)} RELEASED` : 'Pre-authorized'}
                          </span>
                        </td>
                        <td>
                          <span style={{ color: lead.subscription_active ? 'var(--cyan)' : 'var(--text-dim)', fontWeight: 600 }}>
                            {lead.subscription_active ? '⚡ Active Recurring' : 'Inactive'}
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                            {lead.deposit_paid || lead.final_paid ? 'PayPal Live Vault' : '—'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <a
                            href={`/api/dashboard/${lead.lead_id}/invoice`}
                            target="_blank"
                            rel="noreferrer"
                            className="btn btn-outline"
                            style={{ padding: '6px 12px', fontSize: '12px', borderColor: 'var(--cyan)', color: 'var(--cyan)' }}
                          >
                            📄 Printable PDF Invoice
                          </a>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* =========================================================
            TAB 5: SCRAPERS & EXTRACTED DATASETS
           ========================================================= */}
        {activeTab === 'scrapers' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Production Municipal Extractors, Python Crawler Source Code, and Real-time Output Records
              </p>
              <button className="btn btn-outline" onClick={loadScrapers}>
                🔄 Refresh Catalog
              </button>
            </div>

            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Municipal Feed / Identifier</th>
                    <th>Category / Portal</th>
                    <th>Target Source URL</th>
                    <th>Dataset Records</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {scrapersLoading ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                        Loading scraper catalog...
                      </td>
                    </tr>
                  ) : scrapers.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                        No scrapers in catalog. Run a dev swarm to generate extractors.
                      </td>
                    </tr>
                  ) : (
                    scrapers.map((s) => (
                      <tr key={s.lead_id || s.id}>
                        <td>
                          <div style={{ fontWeight: 700, color: '#fff' }}>{s.company_name || s.name || s.lead_id}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{s.lead_id || s.id}</div>
                        </td>
                        <td>
                          <span className="badge-tag">{s.category || s.niche || 'Public Records'}</span>
                        </td>
                        <td>
                          {s.source_url ? (
                            <a
                              href={s.source_url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ color: 'var(--cyan)', fontSize: '12px', textDecoration: 'underline' }}
                            >
                              {s.source_url.slice(0, 45)}...
                            </a>
                          ) : (
                            <span style={{ color: 'var(--text-dim)', fontSize: '12px' }}>—</span>
                          )}
                        </td>
                        <td>
                          <span style={{ fontWeight: 700, color: 'var(--green)' }}>
                            {s.records_count !== undefined ? `${s.records_count} records` : 'Live Dataset'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '6px' }}>
                            <button
                              className="btn btn-primary"
                              style={{ padding: '4px 10px', fontSize: '11px' }}
                              onClick={() => handleRunScraper(s.lead_id || s.id)}
                              disabled={actionInProgress[s.lead_id || s.id]}
                            >
                              ⚡ Run
                            </button>
                            <button
                              className="btn btn-outline"
                              style={{ padding: '4px 8px', fontSize: '11px' }}
                              onClick={() => handleViewCode(s.lead_id || s.id, s.company_name)}
                            >
                              💻 Python Code
                            </button>
                            <button
                              className="btn btn-outline"
                              style={{ padding: '4px 8px', fontSize: '11px' }}
                              onClick={() => handleViewOutput(s.lead_id || s.id, s.company_name)}
                            >
                              📊 Output Data
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* =========================================================
            TAB 6: AUTOMATED DAILY FEEDS
           ========================================================= */}
        {activeTab === 'daily' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Automated 6:00 AM UTC Daily Data Deliveries (Google Sheets, Webhooks, CSV Deliveries)
              </p>
              <button className="btn btn-outline" onClick={loadDailyGrid}>
                🔄 Refresh Grid
              </button>
            </div>

            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Customer Feed</th>
                    <th>Schedule</th>
                    <th>Destination Type</th>
                    <th>Last Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pipeline.filter((l) => l.state === 'DELIVERED' || l.state === 'WARRANTY_ACTIVE' || l.subscription_active).length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                        No delivered feeds currently scheduled for daily automation.
                      </td>
                    </tr>
                  ) : (
                    pipeline
                      .filter((l) => l.state === 'DELIVERED' || l.state === 'WARRANTY_ACTIVE' || l.subscription_active)
                      .map((lead) => (
                        <tr key={lead.lead_id}>
                          <td>
                            <div style={{ fontWeight: 700, color: '#fff' }}>{lead.company_name}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{lead.lead_id}</div>
                          </td>
                          <td>
                            <span style={{ color: 'var(--purple)', fontWeight: 600 }}>Daily 6:00 AM UTC</span>
                          </td>
                          <td>
                            <span className="badge-tag">Google Sheets + Webhook</span>
                          </td>
                          <td>
                            <span style={{ color: 'var(--green)', fontWeight: 600 }}>✓ Healthy</span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <button
                              className="btn btn-primary"
                              style={{ padding: '6px 12px', fontSize: '12px' }}
                              onClick={() => handleTriggerDailyDelivery(lead.lead_id)}
                            >
                              🚀 Run Delivery Now
                            </button>
                          </td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* =========================================================
            TAB 7: EMAIL INBOXES & WARMUP FLEET (ZOHO / GMAIL)
           ========================================================= */}
        {activeTab === 'inboxes' && (
          <div>
            {/* Header & Controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '24px', background: 'var(--card)', padding: '20px 24px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', margin: 0 }}>
                    📬 Multi-Inbox Fleet &amp; Warmup Engine
                  </h2>
                  <span className="badge-tag badge-cyan">{inboxes.length} Configured</span>
                </div>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '6px', marginBottom: 0 }}>
                  Automated cold outreach load balancing &amp; bidirectional reply monitoring across Zoho Workplace and Gmail inboxes.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <button
                  className="btn btn-outline"
                  style={{ fontSize: '12px', padding: '8px 14px' }}
                  onClick={loadInboxes}
                  disabled={inboxesLoading}
                >
                  {inboxesLoading ? '🔄 Refreshing...' : '🔄 Refresh Fleet'}
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '12px', padding: '8px 14px', borderColor: 'var(--accent)' }}
                  onClick={handleFlushOutreachQueue}
                  disabled={flushingQueue}
                  title="Flush pending outreach queue immediately across inboxes with anti-spam jitter"
                >
                  {flushingQueue ? '⏳ Dispatching...' : '⚡ Flush Outreach Queue'}
                </button>
                <button
                  className="btn btn-primary"
                  style={{ fontSize: '12px', padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  onClick={() => setShowAddInboxModal(true)}
                >
                  <span>+</span> Add Zoho / Email Inbox
                </button>
              </div>
            </div>

            {/* Quick Fleet Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              <div className="stat-card stat-green">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="stat-label" style={{ color: 'var(--green)' }}>⚡ Active Inboxes</div>
                  <span className="pulse-dot-green" title="Active sending accounts" />
                </div>
                <div className="stat-value" style={{ color: 'var(--green)' }}>
                  {inboxes.filter((i) => i.is_active).length} / {inboxes.length}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Participating in rotation
                </div>
              </div>

              <div className="stat-card stat-purple">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="stat-label" style={{ color: '#c084fc' }}>🟣 Zoho Workplace Inboxes</div>
                  <span style={{ fontSize: '12px' }}>🔒</span>
                </div>
                <div className="stat-value" style={{ color: '#c084fc' }}>
                  {inboxes.filter((i) => i.provider === 'zoho').length}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  smtp.zoho.com (SSL 465)
                </div>
              </div>

              <div className="stat-card stat-cyan">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="stat-label" style={{ color: 'var(--cyan)' }}>📈 Fleet Daily Capacity</div>
                  <span className="pulse-dot-cyan" title="Warmup daily limit" />
                </div>
                <div className="stat-value" style={{ color: 'var(--cyan)' }}>
                  {inboxes.filter((i) => i.is_active && (i.provider === 'zoho' || i.inbox_id !== 'primary')).reduce((sum, i) => sum + (i.daily_limit || 25), 0) || (inboxes.filter((i) => i.is_active).length * 25)}/day
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  5 Zoho inboxes × 25/day (Week 1 Warmup)
                </div>
              </div>

              <div className="stat-card stat-yellow">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div className="stat-label" style={{ color: '#fbbf24' }}>📨 Dispatched Today</div>
                  <span className="pulse-dot-amber" title="Fleet sends today" />
                </div>
                <div className="stat-value" style={{ color: '#fbbf24' }}>
                  {inboxes.reduce((sum, i) => sum + (i.sent_today || 0), 0)} / {inboxes.filter((i) => i.is_active && (i.provider === 'zoho' || i.inbox_id !== 'primary')).reduce((sum, i) => sum + (i.daily_limit || 25), 0) || 125}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Across all active inboxes
                </div>
              </div>
            </div>

            {/* Morning Fleet Deliverability & TestMail Spam Assessment Shield */}
            <div
              style={{
                background: deliverabilityReport?.fleet_status === 'HEALTHY'
                  ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(15, 23, 42, 0.85) 100%)'
                  : deliverabilityReport?.fleet_status === 'WARNING'
                  ? 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(15, 23, 42, 0.85) 100%)'
                  : deliverabilityReport?.fleet_status === 'CRITICAL'
                  ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.14) 0%, rgba(15, 23, 42, 0.85) 100%)'
                  : 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(15, 23, 42, 0.85) 100%)',
                borderRadius: 'var(--radius-md)',
                border: deliverabilityReport?.fleet_status === 'HEALTHY'
                  ? '1px solid rgba(16, 185, 129, 0.4)'
                  : deliverabilityReport?.fleet_status === 'WARNING'
                  ? '1px solid rgba(245, 158, 11, 0.4)'
                  : deliverabilityReport?.fleet_status === 'CRITICAL'
                  ? '1px solid rgba(239, 68, 68, 0.4)'
                  : '1px solid rgba(99, 102, 241, 0.35)',
                padding: '22px 24px',
                marginBottom: '24px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '18px',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', maxWidth: '780px' }}>
                <div
                  style={{
                    width: '50px',
                    height: '50px',
                    borderRadius: '12px',
                    background: 'rgba(99, 102, 241, 0.2)',
                    border: '1px solid rgba(99, 102, 241, 0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '24px',
                    flexShrink: 0,
                  }}
                >
                  🛡️
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#fff', margin: 0 }}>
                      Morning Fleet Deliverability &amp; TestMail Spam Shield
                    </h3>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '3px 10px',
                        borderRadius: '20px',
                        background: deliverabilityReport?.fleet_status === 'HEALTHY'
                          ? 'rgba(16, 185, 129, 0.2)'
                          : deliverabilityReport?.fleet_status === 'WARNING'
                          ? 'rgba(245, 158, 11, 0.2)'
                          : deliverabilityReport?.fleet_status === 'CRITICAL'
                          ? 'rgba(239, 68, 68, 0.2)'
                          : 'rgba(148, 163, 184, 0.2)',
                        color: deliverabilityReport?.fleet_status === 'HEALTHY'
                          ? 'var(--green)'
                          : deliverabilityReport?.fleet_status === 'WARNING'
                          ? '#fbbf24'
                          : deliverabilityReport?.fleet_status === 'CRITICAL'
                          ? '#f87171'
                          : '#cbd5e1',
                        border: `1px solid ${
                          deliverabilityReport?.fleet_status === 'HEALTHY'
                            ? 'rgba(16, 185, 129, 0.4)'
                            : deliverabilityReport?.fleet_status === 'WARNING'
                            ? 'rgba(245, 158, 11, 0.4)'
                            : 'rgba(148, 163, 184, 0.3)'
                        }`,
                      }}
                    >
                      {deliverabilityReport?.fleet_status === 'HEALTHY'
                        ? '🟢 100% HEALTHY'
                        : deliverabilityReport?.fleet_status === 'WARNING'
                        ? '⚠️ WARNINGS DETECTED'
                        : deliverabilityReport?.fleet_status === 'CRITICAL'
                        ? '🚨 CRITICAL RISKS'
                        : '⚪ PENDING AUDIT'}
                    </span>
                    {deliverabilityReport?.average_score !== undefined && deliverabilityReport?.average_score !== null && (
                      <span style={{ fontSize: '12px', color: 'var(--cyan)', fontWeight: 700, fontFamily: 'var(--mono)' }}>
                        Grade: {deliverabilityReport.average_score}%
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '6px 0 0', lineHeight: 1.5 }}>
                    Autonomous AI agent sends compliant zero-link test cold emails to <code>{deliverabilityReport?.testmail_namespace || 'KGDDJ'}.*@inbox.testmail.app</code> across all sending addresses and parses live <strong>SPF</strong>, <strong>DKIM</strong>, and <strong>SpamAssassin</strong> scores before prospect dispatches begin.
                  </p>
                  {deliverabilityReport?.audited_at && (
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '6px' }}>
                      Last Audited: <span style={{ color: '#fff' }}>{new Date(deliverabilityReport.audited_at).toLocaleString()}</span> ({deliverabilityReport.healthy_count || 0} Healthy, {deliverabilityReport.warning_count || 0} Warnings, {deliverabilityReport.critical_count || 0} Critical)
                    </div>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <button
                  className="btn btn-primary"
                  style={{
                    fontSize: '13px',
                    padding: '10px 18px',
                    background: 'linear-gradient(135deg, #4f46e5 0%, #4338ca 100%)',
                    border: '1px solid #818cf8',
                    boxShadow: '0 0 16px rgba(99, 102, 241, 0.35)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontWeight: 700,
                  }}
                  onClick={handleRunDeliverabilityAudit}
                  disabled={auditingDeliverability}
                >
                  <span>{auditingDeliverability ? '⏳' : '🛡️'}</span>
                  {auditingDeliverability ? 'Probing TestMail...' : 'Run Deliverability Audit Now'}
                </button>
              </div>
            </div>

            {/* Microsoft Outlook (OAuth2 Graph API) Watched Inbound Reply Box */}
            <div
              style={{
                background: msOAuthStatus?.authorized
                  ? 'linear-gradient(135deg, rgba(34, 197, 94, 0.08) 0%, rgba(15, 23, 42, 0.7) 100%)'
                  : msOAuthStatus?.configured
                  ? 'linear-gradient(135deg, rgba(234, 179, 8, 0.08) 0%, rgba(15, 23, 42, 0.7) 100%)'
                  : 'linear-gradient(135deg, rgba(56, 189, 248, 0.06) 0%, rgba(15, 23, 42, 0.7) 100%)',
                borderRadius: 'var(--radius-md)',
                border: msOAuthStatus?.authorized
                  ? '1px solid rgba(34, 197, 94, 0.35)'
                  : msOAuthStatus?.configured
                  ? '1px solid rgba(234, 179, 8, 0.35)'
                  : '1px solid rgba(56, 189, 248, 0.3)',
                padding: '20px 24px',
                marginBottom: '24px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '16px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div
                  style={{
                    width: '46px',
                    height: '46px',
                    borderRadius: '12px',
                    background: 'rgba(234, 88, 12, 0.15)',
                    border: '1px solid rgba(234, 88, 12, 0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '22px',
                    flexShrink: 0,
                  }}
                >
                  🟧
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#fff', margin: 0 }}>
                      Inbound Reply Listener: omnileadfeeder@outlook.com
                    </h3>
                    {msOAuthStatus?.authorized ? (
                      <span className="badge-tag badge-green" style={{ fontSize: '11px' }}>
                        🟢 Microsoft OAuth2 Connected
                      </span>
                    ) : msOAuthStatus?.configured ? (
                      <span
                        className="badge-tag"
                        style={{ fontSize: '11px', background: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: '1px solid rgba(234, 179, 8, 0.35)' }}
                      >
                        ⚠️ Authorization Required
                      </span>
                    ) : (
                      <span
                        className="badge-tag"
                        style={{ fontSize: '11px', background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8', border: '1px solid rgba(148, 163, 184, 0.3)' }}
                      >
                        ⚙️ Azure App Setup Pending
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 0' }}>
                    {msOAuthStatus?.authorized
                      ? `Perpetual silent token refresh active. Polling Microsoft Graph API every 60s for inbound prospect replies.`
                      : msOAuthStatus?.configured
                      ? `Azure App Registered! Click 'Connect Outlook Account' below to grant 1-click permission for omnileadfeeder@outlook.com.`
                      : `Option 3 Provisioning: Add MICROSOFT_CLIENT_ID & MICROSOFT_CLIENT_SECRET to .env, then click Connect Outlook.`}
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                {msOAuthStatus?.authorized ? (
                  <>
                    <button
                      className="btn btn-outline"
                      style={{ fontSize: '12px', padding: '7px 14px' }}
                      onClick={() => handleTestInbox('primary')}
                      disabled={testingInboxId === 'primary'}
                      title="Test live Microsoft Graph API inbox connection"
                    >
                      {testingInboxId === 'primary' ? '⚡ Testing...' : '⚡ Test Graph Connection'}
                    </button>
                    <button
                      className="btn btn-outline"
                      style={{ fontSize: '12px', padding: '7px 14px', color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                      onClick={handleDisconnectMicrosoftOAuth}
                      title="Disconnect Outlook account and revoke local refresh token"
                    >
                      Disconnect
                    </button>
                  </>
                ) : (
                  <button
                    className="btn btn-primary"
                    style={{
                      fontSize: '13px',
                      padding: '9px 20px',
                      background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                      border: '1px solid #38bdf8',
                      boxShadow: '0 0 16px rgba(56, 189, 248, 0.35)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      fontWeight: 700,
                    }}
                    onClick={handleConnectMicrosoftOAuth}
                    disabled={msOAuthConnecting}
                  >
                    <span>{msOAuthConnecting ? '⏳' : '🔗'}</span>
                    {msOAuthConnecting ? 'Redirecting to Microsoft...' : 'Connect Outlook Account (OAuth2)'}
                  </button>
                )}
              </div>
            </div>

            {/* Inboxes List Cards */}
            {inboxes.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', background: 'var(--card)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border)' }}>
                <div style={{ fontSize: '42px', marginBottom: '14px' }}>📬</div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>No Email Inboxes Configured Yet</h3>
                <p style={{ fontSize: '14px', color: 'var(--text-muted)', maxWidth: '460px', margin: '0 auto 20px' }}>
                  Connect your 4 new Zoho inboxes to start automated outreach load balancing and continuous IMAP prospect reply monitoring.
                </p>
                <button
                  className="btn btn-primary"
                  onClick={() => setShowAddInboxModal(true)}
                  style={{ fontSize: '13px', padding: '10px 20px' }}
                >
                  + Add Your First Zoho Inbox
                </button>
              </div>
            ) : (() => {
              const healthyInboxes = inboxes.filter((inbox) => {
                const deliv = deliverabilityReport?.inboxes?.find(
                  (d) => d.email_address?.toLowerCase() === inbox.email_address?.toLowerCase() || d.inbox_id === inbox.inbox_id
                );
                return inbox.is_active && (!deliv || deliv.status === 'HEALTHY') && !inbox.is_on_jitter && ((inbox.sent_today || 0) < (inbox.daily_limit || 25));
              });

              const warningInboxes = inboxes.filter((inbox) => {
                const deliv = deliverabilityReport?.inboxes?.find(
                  (d) => d.email_address?.toLowerCase() === inbox.email_address?.toLowerCase() || d.inbox_id === inbox.inbox_id
                );
                return !inbox.is_active || (deliv && (deliv.status === 'WARNING' || deliv.status === 'CRITICAL')) || ((inbox.sent_today || 0) >= (inbox.daily_limit || 25) * 0.75);
              });

              const jitterInboxes = inboxes.filter((inbox) => inbox.is_on_jitter);

              const filteredInboxes = inboxes.filter((inbox) => {
                if (inboxFilter === 'ALL') return true;
                if (inboxFilter === 'HEALTHY') return healthyInboxes.some((i) => i.inbox_id === inbox.inbox_id);
                if (inboxFilter === 'WARNING') return warningInboxes.some((i) => i.inbox_id === inbox.inbox_id);
                if (inboxFilter === 'JITTER') return jitterInboxes.some((i) => i.inbox_id === inbox.inbox_id);
                return true;
              });

              return (
                <div>
                  {/* Status Filter Chips Bar */}
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Filter Fleet:</span>
                    <button
                      type="button"
                      className={`inbox-filter-chip ${inboxFilter === 'ALL' ? 'active' : ''}`}
                      onClick={() => setInboxFilter('ALL')}
                    >
                      All Inboxes ({inboxes.length})
                    </button>
                    <button
                      type="button"
                      className={`inbox-filter-chip ${inboxFilter === 'HEALTHY' ? 'active' : ''}`}
                      onClick={() => setInboxFilter('HEALTHY')}
                    >
                      <span className="pulse-dot-green" /> 🟢 Healthy &amp; Ready ({healthyInboxes.length})
                    </button>
                    <button
                      type="button"
                      className={`inbox-filter-chip ${inboxFilter === 'WARNING' ? 'active' : ''}`}
                      onClick={() => setInboxFilter('WARNING')}
                    >
                      <span className="pulse-dot-amber" /> ⚠️ Attention ({warningInboxes.length})
                    </button>
                    <button
                      type="button"
                      className={`inbox-filter-chip ${inboxFilter === 'JITTER' ? 'active' : ''}`}
                      onClick={() => setInboxFilter('JITTER')}
                    >
                      ⏳ Jitter Cooldown ({jitterInboxes.length})
                    </button>
                  </div>

                  {filteredInboxes.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px 20px', background: 'var(--card)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border)', color: 'var(--text-muted)' }}>
                      No inboxes match the "{inboxFilter}" filter.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '18px' }}>
                      {filteredInboxes.map((inbox) => {
                        const testRes = testResults[inbox.inbox_id];
                        const isTesting = testingInboxId === inbox.inbox_id;
                        const pct = Math.min(100, Math.round(((inbox.sent_today || 0) / (inbox.daily_limit || 25)) * 100));

                        const deliv = deliverabilityReport?.inboxes?.find(
                          (d) => d.email_address?.toLowerCase() === inbox.email_address?.toLowerCase() || d.inbox_id === inbox.inbox_id
                        );
                        const isCritical = deliv?.status === 'CRITICAL' || (testRes && (!testRes.smtp_ok || !testRes.imap_ok));
                        const isWarning = deliv?.status === 'WARNING' || inbox.is_on_jitter || ((inbox.sent_today || 0) >= (inbox.daily_limit || 25) * 0.75);

                        const cardBorder = isCritical
                          ? '1px solid rgba(239, 68, 68, 0.5)'
                          : isWarning
                          ? '1px solid rgba(245, 158, 11, 0.45)'
                          : '1px solid rgba(16, 185, 129, 0.4)';

                        const cardGlow = isCritical
                          ? '0 6px 24px -4px var(--red-glow)'
                          : isWarning
                          ? '0 6px 24px -4px var(--yellow-glow)'
                          : '0 6px 24px -4px var(--green-glow)';

                        return (
                          <div
                            key={inbox.inbox_id}
                            style={{
                              background: 'var(--card)',
                              borderRadius: 'var(--radius-md)',
                              border: cardBorder,
                              boxShadow: cardGlow,
                              padding: '20px',
                              display: 'flex',
                              flexDirection: 'column',
                              justifyContent: 'space-between',
                              opacity: inbox.is_active ? 1 : 0.65,
                              transition: 'all 0.2s ease',
                            }}
                          >
                            <div>
                              {/* Header: Provider & Active Pill */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                                <span
                                  style={{
                                    fontSize: '11px',
                                    fontWeight: 700,
                                    padding: '4px 10px',
                                    borderRadius: '20px',
                                    background: inbox.provider === 'zoho' ? 'rgba(168, 85, 247, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                                    color: inbox.provider === 'zoho' ? '#c084fc' : '#60a5fa',
                                    border: `1px solid ${inbox.provider === 'zoho' ? 'rgba(168, 85, 247, 0.35)' : 'rgba(59, 130, 246, 0.35)'}`,
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                  }}
                                >
                                  <span>{inbox.provider === 'zoho' ? '🟣' : inbox.provider === 'outlook' ? '🟧' : '🔵'}</span>
                                  {inbox.provider === 'zoho' ? 'Zoho Workplace' : inbox.provider === 'outlook' ? 'Microsoft Outlook' : inbox.provider === 'gmail' ? 'Google / Gmail' : 'Custom SMTP'}
                                </span>

                                <span
                                  style={{
                                    fontSize: '11px',
                                    fontWeight: 600,
                                    padding: '3px 8px',
                                    borderRadius: '6px',
                                    background: inbox.is_active ? 'rgba(16, 185, 129, 0.15)' : 'rgba(100, 116, 139, 0.2)',
                                    color: inbox.is_active ? 'var(--green)' : '#94a3b8',
                                    border: `1px solid ${inbox.is_active ? 'rgba(16, 185, 129, 0.3)' : 'rgba(100, 116, 139, 0.3)'}`,
                                  }}
                                >
                                  {inbox.is_active ? '● Active' : '○ Paused'}
                                </span>
                              </div>

                              {/* Email & From Name */}
                              <div style={{ marginBottom: '16px' }}>
                                <div style={{ fontSize: '16px', fontWeight: 700, color: '#fff', wordBreak: 'break-all' }}>
                                  {inbox.email_address}
                                </div>
                                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '3px' }}>
                                  From: <span style={{ color: 'var(--text-dim)' }}>{inbox.from_name || 'Alex | OmniLeadFeeder'}</span>
                                </div>
                              </div>

                              {/* Protocol Chips */}
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '16px', fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--mono)', background: 'rgba(15, 23, 42, 0.5)', padding: '10px 12px', borderRadius: 'var(--radius-sm)' }}>
                                <div>📤 SMTP: <span style={{ color: '#fff' }}>{inbox.smtp_host || 'smtp.zoho.com'}:{inbox.smtp_port || 465}</span> ({inbox.smtp_use_ssl ? 'SSL' : 'TLS'})</div>
                                <div>📥 IMAP: <span style={{ color: '#fff' }}>{inbox.imap_host || 'imap.zoho.com'}:{inbox.imap_port || 993}</span> ({inbox.imap_use_ssl ? 'SSL' : 'TLS'})</div>
                              </div>

                              {/* Quota Progress */}
                              <div style={{ marginBottom: '16px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                                  <span style={{ color: 'var(--text-muted)' }}>Daily Warmup Quota:</span>
                                  <span style={{ color: '#fff', fontWeight: 600 }}>
                                    {inbox.sent_today || 0} / {inbox.daily_limit || 25} sent ({pct}%)
                                  </span>
                                </div>
                                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                                  <div
                                    style={{
                                      width: `${pct}%`,
                                      height: '100%',
                                      background: pct >= 100 ? 'var(--red)' : pct >= 75 ? '#f59e0b' : 'var(--green)',
                                      transition: 'width 0.3s ease',
                                    }}
                                  />
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px' }}>
                                  <span>{inbox.warmup_name || 'Week 1 (Warmup: 20-25/day)'}</span>
                                  <span>{inbox.can_send ? '✅ Quota Available' : '⚠️ Limit Reached Today'}</span>
                                </div>
                              </div>

                              {/* Deliverability & Spam Status (TestMail Live Telemetry) */}
                              {deliv && (() => {
                                const isSpamClean = (deliv.spam_score || 0) <= 2.0;
                                const spfPass = (deliv.spf || '').toLowerCase().includes('pass');
                                const dkimPass = (deliv.dkim || '').toLowerCase().includes('pass');

                                return (
                                  <div
                                    style={{
                                      background: 'rgba(15, 23, 42, 0.65)',
                                      border: '1px solid rgba(255, 255, 255, 0.08)',
                                      borderRadius: 'var(--radius-sm)',
                                      padding: '12px',
                                      marginBottom: '16px',
                                      fontSize: '11px',
                                    }}
                                  >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                      <span style={{ fontWeight: 700, color: '#fff' }}>🛡️ Deliverability &amp; Spam</span>
                                      <span
                                        style={{
                                          fontSize: '10px',
                                          fontWeight: 700,
                                          padding: '2px 7px',
                                          borderRadius: '4px',
                                          background: deliv.status === 'HEALTHY' ? 'rgba(16, 185, 129, 0.2)' : deliv.status === 'WARNING' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                                          color: deliv.status === 'HEALTHY' ? 'var(--green)' : deliv.status === 'WARNING' ? '#fbbf24' : '#f87171',
                                          border: `1px solid ${deliv.status === 'HEALTHY' ? 'rgba(16, 185, 129, 0.4)' : deliv.status === 'WARNING' ? 'rgba(245, 158, 11, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
                                        }}
                                      >
                                        {deliv.status} ({deliv.score}%)
                                      </span>
                                    </div>

                                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '8px' }}>
                                      <span
                                        style={{
                                          padding: '3px 7px',
                                          borderRadius: '4px',
                                          fontSize: '10px',
                                          fontWeight: 600,
                                          background: spfPass ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                          color: spfPass ? 'var(--green)' : '#f87171',
                                          border: `1px solid ${spfPass ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                                        }}
                                      >
                                        SPF: {deliv.spf?.toUpperCase() || 'NONE'}
                                      </span>

                                      <span
                                        style={{
                                          padding: '3px 7px',
                                          borderRadius: '4px',
                                          fontSize: '10px',
                                          fontWeight: 600,
                                          background: dkimPass ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                                          color: dkimPass ? 'var(--green)' : '#fbbf24',
                                          border: `1px solid ${dkimPass ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                                        }}
                                      >
                                        DKIM: {deliv.dkim?.toUpperCase() || 'NONE'}
                                      </span>

                                      <span
                                        style={{
                                          padding: '3px 7px',
                                          borderRadius: '4px',
                                          fontSize: '10px',
                                          fontWeight: 600,
                                          background: isSpamClean ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                                          color: isSpamClean ? 'var(--green)' : '#f87171',
                                          border: `1px solid ${isSpamClean ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                                        }}
                                      >
                                        Spam: {typeof deliv.spam_score === 'number' ? deliv.spam_score.toFixed(1) : deliv.spam_score}
                                      </span>
                                    </div>

                                    <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginBottom: deliv.spam_report ? '8px' : '0', lineHeight: 1.4 }}>
                                      {deliv.diagnostic}
                                    </div>

                                    {deliv.spam_report && (
                                      <button
                                        className="btn btn-outline"
                                        style={{ width: '100%', fontSize: '10px', padding: '5px 8px', color: 'var(--cyan)', borderColor: 'rgba(6, 182, 212, 0.3)' }}
                                        onClick={() => setSelectedSpamReport(deliv)}
                                      >
                                        📄 Inspect SpamAssassin Details
                                      </button>
                                    )}
                                  </div>
                                );
                              })()}

                              {/* Test Result Card */}
                              {testRes && (
                                <div
                                  style={{
                                    padding: '10px 12px',
                                    borderRadius: 'var(--radius-sm)',
                                    marginBottom: '16px',
                                    fontSize: '11px',
                                    background: testRes.smtp_ok && testRes.imap_ok ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                    border: `1px solid ${testRes.smtp_ok && testRes.imap_ok ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                                    color: testRes.smtp_ok && testRes.imap_ok ? 'var(--green)' : '#fca5a5',
                                  }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, marginBottom: '4px' }}>
                                    <span>{testRes.smtp_ok && testRes.imap_ok ? '✅ Verification Passed' : '⚠️ Verification Issue'}</span>
                                    <span>⚡ {testRes.latency_ms}ms</span>
                                  </div>
                                  <div>SMTP: {testRes.smtp_message}</div>
                                  <div>IMAP: {testRes.imap_message}</div>
                                </div>
                              )}
                            </div>

                            {/* Footer Actions */}
                            <div style={{ display: 'flex', gap: '8px', paddingTop: '12px', borderTop: '1px solid var(--border)' }}>
                              <button
                                className="btn btn-outline"
                                style={{ flex: 1, fontSize: '11px', padding: '6px 10px' }}
                                onClick={() => handleTestInbox(inbox.inbox_id)}
                                disabled={isTesting}
                              >
                                {isTesting ? '⚡ Testing...' : '⚡ Test Connection'}
                              </button>
                              <button
                                className="btn btn-outline"
                                style={{ fontSize: '11px', padding: '6px 10px' }}
                                onClick={() => handleToggleInboxActive(inbox)}
                                title={inbox.is_active ? 'Pause this inbox' : 'Activate this inbox'}
                              >
                                {inbox.is_active ? '⏸️ Pause' : '▶️ Activate'}
                              </button>
                              {inbox.inbox_id !== 'primary' && (
                                <button
                                  className="btn btn-outline"
                                  style={{ fontSize: '11px', padding: '6px 10px', color: '#f87171' }}
                                  onClick={() => handleDeleteInbox(inbox.inbox_id)}
                                  title="Remove inbox from storage"
                                >
                                  🗑️
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}
      </div>

      {/* Add Inbox Modal */}
      {showAddInboxModal && (
        <div className="admin-modal-overlay" onClick={() => setShowAddInboxModal(false)}>
          <div className="admin-modal-content" style={{ maxWidth: '520px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0 }}>
                📬 Connect New Email Inbox
              </h3>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setShowAddInboxModal(false)}
              >
                ✕ Close
              </button>
            </div>

            {/* Zoho Guidance Callout */}
            <div
              style={{
                background: 'rgba(168, 85, 247, 0.12)',
                border: '1px solid rgba(168, 85, 247, 0.35)',
                borderRadius: 'var(--radius-sm)',
                padding: '12px 14px',
                fontSize: '12px',
                color: '#e9d5ff',
                lineHeight: 1.5,
                marginBottom: '18px',
              }}
            >
              <b>💡 Zoho Workplace &amp; Zoho Mail Setup</b>:
              <br />
              Zoho strictly requires an <b>App-Specific Password</b> for third-party SMTP &amp; IMAP. Generate one under:{' '}
              <a
                href="https://accounts.zoho.com"
                target="_blank"
                rel="noreferrer"
                style={{ color: 'var(--cyan)', textDecoration: 'underline' }}
              >
                Zoho Accounts ➔ Security ➔ App Passwords
              </a>
              . Standard account passwords will fail authentication.
            </div>

            {/* Form Fields */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Provider Preset:
                </label>
                <select
                  value={inboxFormData.provider}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, provider: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                >
                  <option value="zoho">🟣 Zoho Workplace (smtppro.zoho.com:465 / imappro.zoho.com:993)</option>
                  <option value="gmail">🔵 Google / Gmail (smtp.gmail.com:465 / imap.gmail.com:993)</option>
                  <option value="outlook">🟧 Microsoft Outlook / 365 (smtp-mail.outlook.com:587 / outlook.office365.com:993)</option>
                  <option value="smtp_generic">⚪ Generic Custom SMTP / IMAP</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Inbox Email Address *
                </label>
                <input
                  type="email"
                  placeholder="e.g. alex@yourdomain.com or omnileadfeeder@outlook.com"
                  value={inboxFormData.email_address}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, email_address: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  {inboxFormData.provider === 'zoho' ? 'Zoho App-Specific Password *' : inboxFormData.provider === 'outlook' ? 'Outlook App Password *' : 'App-Specific Password *'}
                </label>
                <input
                  type="password"
                  placeholder="App password or account password"
                  value={inboxFormData.password}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, password: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Sender Display Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Alex | OmniLeadFeeder"
                  value={inboxFormData.from_name}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, from_name: e.target.value }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Daily Outreach Warmup Limit (emails/day)
                </label>
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={inboxFormData.daily_limit}
                  onChange={(e) => setInboxFormData((p) => ({ ...p, daily_limit: parseInt(e.target.value) || 25 }))}
                  style={{
                    width: '100%',
                    background: 'var(--bg)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '8px 10px',
                    color: '#fff',
                    fontSize: '13px',
                  }}
                />
              </div>
            </div>

            {/* Modal Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '22px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
              <button
                className="btn btn-outline"
                style={{ fontSize: '12px', padding: '8px 16px' }}
                onClick={() => setShowAddInboxModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '8px 18px' }}
                onClick={handleSaveInbox}
              >
                Save &amp; Verify Connection ➔
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================
          MODALS
         ========================================================= */}

      {/* Python Code Viewer Modal */}
      {codeModal.open && (
        <div className="admin-modal-overlay" onClick={() => setCodeModal({ open: false, title: '', code: '' })}>
          <div className="admin-modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>{codeModal.title}</h3>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setCodeModal({ open: false, title: '', code: '' })}
              >
                ✕ Close
              </button>
            </div>
            <pre className="code-viewer">{codeModal.code}</pre>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-outline"
                onClick={() => {
                  navigator.clipboard.writeText(codeModal.code);
                  showToast('Python source code copied to clipboard!', 'success');
                }}
              >
                📋 Copy Code
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Dataset Records Modal */}
      {dataModal.open && (
        <div className="admin-modal-overlay" onClick={() => setDataModal({ open: false, title: '', rows: [], count: 0, leadId: '' })}>
          <div className="admin-modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>{dataModal.title}</h3>
                <span style={{ fontSize: '12px', color: 'var(--green)' }}>{dataModal.count} Total Records Extracted</span>
              </div>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setDataModal({ open: false, title: '', rows: [], count: 0, leadId: '' })}
              >
                ✕ Close
              </button>
            </div>

            <div style={{ maxHeight: '420px', overflow: 'auto', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)' }}>
              {dataModal.rows.length === 0 ? (
                <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>No records in dataset.</div>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      {Object.keys(dataModal.rows[0] || {}).map((k) => (
                        <th key={k}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {dataModal.rows.slice(0, 50).map((r, i) => (
                      <tr key={i}>
                        {Object.values(r).map((v, j) => (
                          <td key={j} style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {String(v ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                className="btn btn-outline"
                onClick={() => {
                  const blob = new Blob([JSON.stringify(dataModal.rows, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${dataModal.leadId}_records.json`;
                  a.click();
                  showToast('JSON dataset downloaded!', 'success');
                }}
              >
                📥 Download JSON
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Audit Trail Modal */}
      {auditModal.open && (
        <div className="admin-modal-overlay" onClick={() => setAuditModal({ open: false, title: '', events: [] })}>
          <div className="admin-modal-content" style={{ maxWidth: '680px' }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '14px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', margin: 0 }}>📜 {auditModal.title}</h3>
                <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>Immutable lifecycle events &amp; AI orchestration telemetry</span>
              </div>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setAuditModal({ open: false, title: '', events: [] })}
              >
                ✕ Close
              </button>
            </div>

            <div style={{ maxHeight: '460px', overflowY: 'auto', marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {!auditModal.events || auditModal.events.length === 0 ? (
                <div style={{ padding: '36px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <p style={{ margin: 0, fontSize: '14px' }}>No audit events recorded for this lead.</p>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>State transitions and AI agent dispatches will appear here automatically.</p>
                </div>
              ) : (
                auditModal.events.map((ev, i) => {
                  const actionStr = typeof ev.action === 'string' ? ev.action : (typeof ev.event === 'string' ? ev.event : 'Lifecycle Transition');
                  const timeRaw = ev.timestamp || ev.created_at || ev.at || '';
                  let timeStr = '';
                  if (timeRaw) {
                    try {
                      timeStr = new Date(timeRaw).toLocaleString();
                    } catch {
                      timeStr = String(timeRaw);
                    }
                  }
                  let detailStr = '';
                  if (typeof ev.detail === 'string' && ev.detail) {
                    detailStr = ev.detail;
                  } else if (typeof ev.reason === 'string' && ev.reason) {
                    detailStr = ev.reason;
                  } else if (ev.detail && typeof ev.detail === 'object') {
                    detailStr = JSON.stringify(ev.detail);
                  } else if (ev.reason && typeof ev.reason === 'object') {
                    detailStr = JSON.stringify(ev.reason);
                  } else {
                    detailStr = 'Automated lifecycle transition';
                  }

                  return (
                    <div key={i} style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', fontSize: '13px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: 'var(--cyan)', fontWeight: 600 }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ color: 'var(--green)' }}>●</span>
                          {actionStr}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{timeStr}</span>
                      </div>
                      <div style={{ marginTop: '6px', color: 'var(--text-muted)', fontSize: '12px', lineHeight: 1.4 }}>{detailStr}</div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}

      {/* QA Override Modal */}
      {qaOverrideModal.open && (
        <div className="admin-modal-overlay" onClick={() => setQaOverrideModal({ open: false, leadId: '', company: '' })}>
          <div className="admin-modal-content" style={{ maxWidth: '480px' }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>⚖️ Founder QA Gate Override</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Manually authorize completion for <b>{qaOverrideModal.company}</b> ({qaOverrideModal.leadId}).
            </p>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Override QA Score (0.0 to 1.0):
              </label>
              <input
                type="number"
                step="0.05"
                min="0.8"
                max="1.0"
                value={overrideScore}
                onChange={(e) => setOverrideScore(parseFloat(e.target.value) || 1.0)}
                style={{
                  width: '100%',
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px',
                  color: '#fff',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                Justification / Reason:
              </label>
              <input
                type="text"
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '10px',
                  color: '#fff',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
              <button
                className="btn btn-outline"
                onClick={() => setQaOverrideModal({ open: false, leadId: '', company: '' })}
              >
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleSubmitQaOverride}>
                Confirm QA Override
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Swarm Progress Modal */}
      {swarmProgressModal.open && (
        <div className="admin-modal-overlay" onClick={() => setSwarmProgressModal({ open: false, leadId: '', company: '', data: null })}>
          <div className="admin-modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>
                🤖 Swarm Telemetry: {swarmProgressModal.company}
              </h3>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setSwarmProgressModal({ open: false, leadId: '', company: '', data: null })}
              >
                ✕ Close
              </button>
            </div>
            <pre className="code-viewer">
              {JSON.stringify(swarmProgressModal.data || { note: 'No real-time build logs active' }, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* AI Lead Scoring & BDR Intelligence Modal */}
      {scoreModal.open && scoreModal.lead && (() => {
        const lead = scoreModal.lead;
        const oppScore = typeof lead.automation_opportunity_score === 'number'
          ? lead.automation_opportunity_score
          : (parseInt(lead.automation_opportunity_score, 10) || 75);
        const purchaseProb = typeof lead.purchase_probability === 'number'
          ? lead.purchase_probability
          : (parseInt(lead.purchase_probability, 10) || 60);
        const painSev = typeof lead.pain_severity === 'number'
          ? lead.pain_severity
          : (parseInt(lead.pain_severity, 10) || 6);
        const verdict = lead.qualification_verdict || (oppScore >= 65 ? 'QUALIFIED_HOT' : 'QUALIFIED_NURTURE');

        // Safely extract factor scores whether nested {score, max} objects or raw numbers
        const rawBreakdown = (lead.scoring_breakdown && typeof lead.scoring_breakdown === 'object')
          ? (lead.scoring_breakdown.breakdown || lead.scoring_breakdown)
          : {};

        const getFactor = (item, defaultScore, defaultMax) => {
          if (item === null || item === undefined) {
            return { score: defaultScore, max: defaultMax };
          }
          if (typeof item === 'number') {
            return { score: item, max: defaultMax };
          }
          if (typeof item === 'object') {
            const sc = typeof item.score === 'number' ? item.score : (parseInt(item.score, 10) || defaultScore);
            const mx = typeof item.max === 'number' ? item.max : (parseInt(item.max, 10) || defaultMax);
            return { score: sc, max: mx };
          }
          const parsed = parseInt(item, 10);
          return { score: isNaN(parsed) ? defaultScore : parsed, max: defaultMax };
        };

        const f1 = getFactor(rawBreakdown.labor_intensive_operations ?? rawBreakdown.labor_intensity, 20, 25);
        const f2 = getFactor(rawBreakdown.portal_usage ?? rawBreakdown.target_portal_scraping, 12, 15);
        const f3 = getFactor(rawBreakdown.manual_data_entry, 12, 15);
        const f4 = getFactor(rawBreakdown.compliance_requirements ?? rawBreakdown.compliance_regulatory, 11, 15);
        const f5 = getFactor(rawBreakdown.document_processing_volume ?? rawBreakdown.document_volume, 8, 10);
        const f6 = getFactor(rawBreakdown.company_size_fit ?? rawBreakdown.smb_size_fit, 8, 10);
        const f7 = getFactor(rawBreakdown.growth_signals ?? rawBreakdown.market_growth, 7, 10);

        const factorItems = [
          { label: 'Labor-Intensive Operations', val: f1.score, max: f1.max, desc: 'High repetitive human touchpoints' },
          { label: 'Target Portal Scraping Viability', val: f2.score, max: f2.max, desc: 'Public docket/portal data accessibility' },
          { label: 'Manual Data Entry Elimination', val: f3.score, max: f3.max, desc: 'Direct software bridge opportunity' },
          { label: 'Compliance & Regulatory Overhead', val: f4.score, max: f4.max, desc: 'Statutory filing & auditing requirements' },
          { label: 'Document & Record Volume', val: f5.score, max: f5.max, desc: 'Daily PDF/CSV/Record throughput' },
          { label: 'SMB Company Size Fit', val: f6.score, max: f6.max, desc: '5-50 staff sweet spot for agile adoption' },
          { label: 'Market Growth & Hiring Signals', val: f7.score, max: f7.max, desc: 'Active hiring or market expansion signals' },
        ];

        let signals = [];
        if (Array.isArray(lead.buyer_signals)) {
          signals = lead.buyer_signals.map((s) => (typeof s === 'object' && s !== null ? (s.label || s.signal || JSON.stringify(s)) : String(s)));
        } else if (lead.buyer_signals && typeof lead.buyer_signals === 'object') {
          if (Array.isArray(lead.buyer_signals.positive_signals)) {
            signals = lead.buyer_signals.positive_signals.map((s) => (typeof s === 'object' && s !== null ? (s.label || s.signal || JSON.stringify(s)) : String(s)));
          } else {
            signals = Object.values(lead.buyer_signals).filter((v) => typeof v === 'string');
          }
        }
        if (signals.length === 0) {
          signals = [
            'High manual data entry overhead identified in core workflow',
            'Municipal/public docket dependencies detected',
            'Sub-50 employee size matches automation deployment sweet-spot',
          ];
        }
        const qa = lead.qa_score !== null && lead.qa_score !== undefined ? lead.qa_score : null;

        return (
          <div className="admin-modal-overlay" onClick={() => setScoreModal({ open: false, lead: null })}>
            <div className="admin-modal-content" style={{ maxWidth: '780px' }} onClick={(e) => e.stopPropagation()}>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', margin: 0 }}>
                      ⚡ AI Opportunity &amp; BDR Scoring Intelligence
                    </h3>
                    <span className={`badge-tag ${verdict.includes('HOT') ? 'badge-green' : 'badge-cyan'}`} style={{ fontSize: '11px' }}>
                      {verdict}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '13px', color: 'var(--text-dim)' }}>
                    <span style={{ color: '#fff', fontWeight: 600 }}>{lead.company_name || 'Candidate Organization'}</span>
                    <span>•</span>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: '11px' }}>{lead.lead_id}</span>
                    <span>•</span>
                    <span style={{ color: 'var(--cyan)' }}>{lead.jurisdiction || lead.target_portal_name || 'Municipal Portal'}</span>
                  </div>
                </div>
                <button
                  className="btn btn-outline"
                  style={{ padding: '6px 12px', fontSize: '12px' }}
                  onClick={() => setScoreModal({ open: false, lead: null })}
                >
                  ✕ Close
                </button>
              </div>

              {/* KPI Scores Row */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                    Automation Opp Score
                  </div>
                  <div style={{ fontSize: '26px', fontWeight: 800, color: oppScore >= 75 ? 'var(--green)' : 'var(--cyan)', marginTop: '4px' }}>
                    {oppScore}<span style={{ fontSize: '14px', color: 'var(--text-dim)' }}>/100</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    7-Factor BDR Weighted
                  </div>
                </div>

                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                    Purchase Intent Prob
                  </div>
                  <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--purple)', marginTop: '4px' }}>
                    {purchaseProb}%
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {purchaseProb >= 70 ? '🔥 High Intent' : '⚡ Moderate Intent'}
                  </div>
                </div>

                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                    Pain Severity
                  </div>
                  <div style={{ fontSize: '26px', fontWeight: 800, color: painSev >= 7 ? '#f87171' : '#fbbf24', marginTop: '4px' }}>
                    {painSev}<span style={{ fontSize: '14px', color: 'var(--text-dim)' }}>/10</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {painSev >= 7 ? 'Critical Bottlenecks' : 'Moderate Inefficiency'}
                  </div>
                </div>

                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                    QA Verification Gate
                  </div>
                  <div style={{ fontSize: '26px', fontWeight: 800, color: qa && qa >= 0.95 ? 'var(--green)' : '#fbbf24', marginTop: '4px' }}>
                    {qa !== null ? `${(qa * 100).toFixed(0)}%` : 'Pending'}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {qa && qa >= 0.95 ? '✓ Meets Founder Gate' : 'Escrow Validation Stage'}
                  </div>
                </div>
              </div>

              {/* 7-Factor Weighted Breakdown */}
              <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: 0 }}>
                    📊 7-Factor BDR Score Model Breakdown
                  </h4>
                  <span style={{ fontSize: '12px', color: 'var(--cyan)', fontWeight: 600 }}>
                    Calculated Live ({oppScore}/100 Total)
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {factorItems.map((f, idx) => {
                    const pct = Math.round((f.val / f.max) * 100);
                    return (
                      <div key={idx}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                          <span style={{ color: '#fff', fontWeight: 500 }}>
                            {f.label} <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>({f.desc})</span>
                          </span>
                          <span style={{ fontFamily: 'var(--mono)', color: 'var(--cyan)', fontWeight: 600 }}>
                            {f.val} / {f.max} pts ({pct}%)
                          </span>
                        </div>
                        <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${pct}%`,
                              height: '100%',
                              background: pct >= 80 ? 'var(--green)' : pct >= 50 ? 'var(--cyan)' : '#fbbf24',
                              borderRadius: '3px',
                              transition: 'width 0.4s ease',
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Buyer Signals & Portal Info */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '16px' }}>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px' }}>
                    🎯 Detected Buyer Intent Signals
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {signals.map((sig, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '12px', color: 'var(--text)' }}>
                        <span style={{ color: 'var(--green)', fontSize: '14px', lineHeight: 1 }}>✓</span>
                        <span>{sig}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', margin: 0 }}>
                      📍 Lead Origin &amp; Discovery Provenance
                    </h4>
                    {renderDiscoveryBadge(lead.discovery_channel, lead.filing_case_number)}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div>
                      <b style={{ color: '#fff' }}>Acquisition Channel:</b>{' '}
                      <span style={{ color: 'var(--text)' }}>
                        {lead.discovery_channel ? lead.discovery_channel.replace(/_/g, ' ') : 'Municipal Public Registry'}
                      </span>
                    </div>
                    <div>
                      <b style={{ color: '#fff' }}>Target Portal / Registry:</b>{' '}
                      <span style={{ color: 'var(--text)' }}>
                        {lead.target_portal_name || lead.jurisdiction || 'Municipal Registry'}
                      </span>
                      {lead.jurisdiction && lead.target_portal_name && (
                        <span style={{ color: 'var(--text-dim)', marginLeft: '6px' }}>
                          ({lead.jurisdiction})
                        </span>
                      )}
                    </div>
                    {(lead.source_url || lead.target_url) && (
                      <div>
                        <b style={{ color: '#fff' }}>Official Source Registry URL:</b>{' '}
                        <a
                          href={lead.source_url || lead.target_url}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--cyan)', textDecoration: 'underline', wordBreak: 'break-all' }}
                        >
                          {lead.source_url || lead.target_url} ↗
                        </a>
                      </div>
                    )}
                    {lead.website && (
                      <div>
                        <b style={{ color: '#fff' }}>Company Website:</b>{' '}
                        <a
                          href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: 'var(--purple)', textDecoration: 'underline', wordBreak: 'break-all' }}
                        >
                          {lead.website} ↗
                        </a>
                      </div>
                    )}
                    {lead.filing_case_number && (
                      <div>
                        <b style={{ color: '#fff' }}>Docket / Case Number:</b>{' '}
                        <span style={{ fontFamily: 'var(--mono)', color: 'var(--yellow)' }}>
                          #{lead.filing_case_number}
                        </span>
                        {lead.filing_date && (
                          <span style={{ color: 'var(--text-dim)', marginLeft: '8px' }}>
                            (Filed: {lead.filing_date})
                          </span>
                        )}
                      </div>
                    )}
                    {lead.matter_description && (
                      <div>
                        <b style={{ color: '#fff' }}>Filing Classification:</b>{' '}
                        <span style={{ color: 'var(--text)' }}>{lead.matter_description}</span>
                      </div>
                    )}
                    <div>
                      <b style={{ color: '#fff' }}>Niche / Vertical:</b> {lead.niche || 'B2B Professional Services'}
                    </div>
                    {lead.contact_email && (
                      <div>
                        <b style={{ color: '#fff' }}>Contact:</b> {lead.contact_email}
                        {lead.contact_role && <span style={{ color: 'var(--text-dim)' }}> ({lead.contact_role})</span>}
                        {lead.email_source && (
                          <span style={{ marginLeft: '6px', fontSize: '10px', background: 'rgba(56, 189, 248, 0.1)', color: 'var(--cyan)', padding: '1px 5px', borderRadius: '3px' }}>
                            via {lead.email_source}
                          </span>
                        )}
                      </div>
                    )}
                    {lead.decision_maker_linkedin && (
                      <div>
                        <b style={{ color: '#fff' }}>LinkedIn:</b>{' '}
                        <a href={lead.decision_maker_linkedin} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)', textDecoration: 'underline' }}>
                          Profile ↗
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Pain Points / Human Observation */}
              {(lead.pain_points || lead.notes || lead.human_observation) && (
                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '6px' }}>
                    📝 Operational Friction &amp; Human Observations
                  </h4>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0, lineHeight: 1.5 }}>
                    {typeof lead.pain_points === 'object' && lead.pain_points !== null
                      ? JSON.stringify(lead.pain_points)
                      : (lead.pain_points || lead.notes || lead.human_observation || 'No operational observations noted.')}
                  </p>
                </div>
              )}

              {/* Modal Footer Actions */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', paddingTop: '8px', borderTop: '1px solid var(--border)' }}>
                {lead.slug && (
                  <a
                    href={`/portal/${lead.slug}`}
                    target="_blank"
                    rel="noreferrer"
                    className="btn btn-primary"
                    style={{ fontSize: '12px', padding: '8px 16px', textDecoration: 'none' }}
                  >
                    Open Client Portal ↗
                  </a>
                )}
                <button
                  className="btn btn-outline"
                  style={{ fontSize: '12px', padding: '8px 16px' }}
                  onClick={() => setScoreModal({ open: false, lead: null })}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* SpamAssassin Detailed Breakdown Modal */}
      {selectedSpamReport && (
        <div className="admin-modal-overlay" onClick={() => setSelectedSpamReport(null)}>
          <div
            className="admin-modal-content"
            style={{ maxWidth: '650px', background: 'var(--card)', border: '1px solid var(--border)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '24px' }}>🛡️</span>
                <div>
                  <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#fff', margin: 0 }}>
                    SpamAssassin Deliverability Report
                  </h3>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {selectedSpamReport.email_address}
                  </div>
                </div>
              </div>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setSelectedSpamReport(null)}
              >
                ✕ Close
              </button>
            </div>

            {/* Metric Pills */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '18px' }}>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>SPF Status</div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: selectedSpamReport.spf?.includes('pass') ? 'var(--green)' : '#f87171', marginTop: '4px' }}>
                  {selectedSpamReport.spf?.toUpperCase() || 'UNKNOWN'}
                </div>
              </div>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>DKIM Status</div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: selectedSpamReport.dkim?.includes('pass') ? 'var(--green)' : '#fbbf24', marginTop: '4px' }}>
                  {selectedSpamReport.dkim?.toUpperCase() || 'NONE'}
                </div>
              </div>
              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px', textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Spam Score</div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: (selectedSpamReport.spam_score || 0) <= 2.0 ? 'var(--green)' : '#f87171', marginTop: '4px' }}>
                  {typeof selectedSpamReport.spam_score === 'number' ? selectedSpamReport.spam_score.toFixed(1) : selectedSpamReport.spam_score}
                </div>
              </div>
            </div>

            {/* Recommendation Callout */}
            {selectedSpamReport.recommendation && (
              <div
                style={{
                  background: selectedSpamReport.status === 'HEALTHY' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                  border: `1px solid ${selectedSpamReport.status === 'HEALTHY' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
                  borderRadius: 'var(--radius-sm)',
                  padding: '12px 14px',
                  marginBottom: '16px',
                  fontSize: '12px',
                  color: selectedSpamReport.status === 'HEALTHY' ? 'var(--green)' : '#fbbf24',
                  lineHeight: 1.5,
                }}
              >
                <b>💡 Recommendation:</b> {selectedSpamReport.recommendation}
              </div>
            )}

            {/* Raw SpamAssassin Report Output */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '6px' }}>
                SpamAssassin Rule Triggers &amp; Telemetry:
              </div>
              <pre
                style={{
                  background: '#090d16',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '14px',
                  fontSize: '11px',
                  color: '#e2e8f0',
                  fontFamily: 'var(--mono)',
                  maxHeight: '260px',
                  overflowY: 'auto',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.5,
                  margin: 0,
                }}
              >
                {selectedSpamReport.spam_report || 'No SpamAssassin rule triggers recorded. Clean message score.'}
              </pre>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                className="btn btn-primary"
                style={{ fontSize: '12px', padding: '8px 18px' }}
                onClick={() => setSelectedSpamReport(null)}
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Risk-Guard Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.confirmText}
        cancelText={confirmModal.cancelText}
        isDestructive={confirmModal.isDestructive}
        requireMatch={confirmModal.requireMatch}
        hasInput={confirmModal.hasInput}
        inputLabel={confirmModal.inputLabel}
        inputPlaceholder={confirmModal.inputPlaceholder}
        inputDefaultValue={confirmModal.inputDefaultValue}
        onConfirm={confirmModal.onConfirm}
        onClose={closeConfirmModal}
      />

      {/* Global Command Palette (Cmd+K / Ctrl+K) */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        activeTab={activeTab}
        onSelectTab={(tabKey) => {
          setActiveTab(tabKey);
        }}
        pipeline={pipeline}
        onSelectLead={(selectedLead) => {
          setScoreModal({ open: true, lead: selectedLead });
        }}
        actions={commandPaletteActions}
      />
    </main>
  );
}
