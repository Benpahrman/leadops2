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
  triggerBatchScout,
  deepEnrichLead,
  cancelAutoOutreach,
  fetchAdminInboxes,
  fetchInboundStream,
  fetchWarmupTargets,
  addWarmupTarget,
  deleteWarmupTarget,
  fetchWarmupActivity,
  startWarmupCycle,
  dispatchWarmupBatch,
  runWarmupMonitoring,
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
  fetchComprehensiveDeliverabilityReport,
  runComprehensiveDeliverabilityAudit,
  checkRBLBlacklists,
  checkContentSpamScore,
  fetchProspectorStatus,
  startProspectorCampaign,
  pauseProspectorCampaign,
  resumeProspectorCampaign,
  triggerProspectorBurst,
  refreshLeadFreshness,
  batchRefreshStaleBacklog,
  fetchCountyOrchestratorStatus,
  advanceCountyOrchestratorCursor,
  setCountyOrchestratorStateFocus,
} from '../services/api';
import { useToast } from '../context/ToastContext';
import ConfirmModal from '../components/common/ConfirmModal';
import CommandPalette from '../components/common/CommandPalette';
import ProspectorTab from './admin/tabs/ProspectorTab';
import DealsTab from './admin/tabs/DealsTab';
import KanbanTab from './admin/tabs/KanbanTab';
import ArchivedLeadsTab from './admin/tabs/ArchivedLeadsTab';
import SwarmTab from './admin/tabs/SwarmTab';
import AccountingTab from './admin/tabs/AccountingTab';
import ScrapersTab from './admin/tabs/ScrapersTab';
import DailyDeliveryTab from './admin/tabs/DailyDeliveryTab';
import InboxesAndWarmupTab from './admin/tabs/InboxesAndWarmupTab';

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
  const [channelFilter, setChannelFilter] = useState(() => getInitialParam('channel', 'ALL'));

  // 14-Day High-Volume Prospector & Freshness State
  const [prospectorStatus, setProspectorStatus] = useState(null);
  const [prospectorLoading, setProspectorLoading] = useState(false);
  const [freshnessRefreshingLeadId, setFreshnessRefreshingLeadId] = useState(null);
  const [sweepingStaleRecords, setSweepingStaleRecords] = useState(false);
  const [burstLeadCount, setBurstLeadCount] = useState(3);
  const [selectedProspectorChannel, setSelectedProspectorChannel] = useState('ALL');

  // 50-State & County-by-County Swarm Prospecting State
  const [countyOrchestrator, setCountyOrchestrator] = useState(null);
  const [orchestratorLoading, setOrchestratorLoading] = useState(false);

  // Pagination for Deals & Backlog
  const [dealsPage, setDealsPage] = useState(1);
  const [dealsPageSize, setDealsPageSize] = useState(20);
  const [backlogPage, setBacklogPage] = useState(1);
  const [backlogPageSize, setBacklogPageSize] = useState(15);

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
  const [scoutBatchCount, setScoutBatchCount] = useState(1);
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
  const [inboxSubTab, setInboxSubTab] = useState('fleet'); // 'fleet' | 'inbound' | 'receivers' | 'activity'
  const [fleetSummary, setFleetSummary] = useState(null);
  const [warmupCycle, setWarmupCycle] = useState(null);
  const [startingWarmup, setStartingWarmup] = useState(false);
  const [dispatchingWarmup, setDispatchingWarmup] = useState(false);
  const [monitoringWarmup, setMonitoringWarmup] = useState(false);
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
    provider: 'olfmailer',
    daily_limit: 5,
  });

  // Inbound Prospect Stream & Watched Mailbox Telemetry
  const [inboundStream, setInboundStream] = useState(null);
  const [inboundLoading, setInboundLoading] = useState(false);

  // Peer Warmup Network & Warm Receivers State
  const [warmupTargets, setWarmupTargets] = useState([]);
  const [warmupTargetsLoading, setWarmupTargetsLoading] = useState(false);
  const [warmupActivity, setWarmupActivity] = useState(null);
  const [warmupActivityLoading, setWarmupActivityLoading] = useState(false);
  const [showAddReceiverModal, setShowAddReceiverModal] = useState(false);
  const [receiverFormData, setReceiverFormData] = useState({
    email: '',
    name: '',
    password: '',
    provider: 'gmail',
    is_monitored: true,
  });

  // Enterprise 4-Vector Deliverability Suite State
  const [deliverabilityReport, setDeliverabilityReport] = useState(null);
  const [auditingDeliverability, setAuditingDeliverability] = useState(false);
  const [selectedSpamReport, setSelectedSpamReport] = useState(null);
  const [deliverabilityTab, setDeliverabilityTab] = useState('dns'); // 'dns' | 'rbl' | 'content' | 'placement'
  const [testCopySubject, setTestCopySubject] = useState('morning docket records for your jurisdiction');
  const [testCopyBody, setTestCopyBody] = useState(
    "Hi there,\n\nOur automated scraper indexed today's morning public records and filings for your target jurisdiction into a clean spreadsheet.\n\nWould it be helpful if I passed over the sample dataset so your team can review it?\n\nBest,\nAlex\nOmniLeadFeeder Automated Swarm"
  );
  const [contentAuditResult, setContentAuditResult] = useState(null);
  const [auditingContent, setAuditingContent] = useState(false);

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

  const handleStartWarmup = async () => {
    setStartingWarmup(true);
    try {
      const token = await resolveToken();
      const res = await startWarmupCycle(token);
      if (res && res.warmup_cycle) {
        setWarmupCycle(res.warmup_cycle);
      }
      showToast(res.message || 'Domain warming cycle initialized!', 'success');
      await loadInboxes();
    } catch (err) {
      showToast(`Failed to initialize warmup: ${err.message}`, 'error');
    } finally {
      setStartingWarmup(false);
    }
  };

  const handleDispatchWarmupBatch = async (count = 3) => {
    setDispatchingWarmup(true);
    try {
      const token = await resolveToken();
      showToast(`🔥 Dispatching ${count} peer warmup emails across available inboxes...`, 'info');
      const res = await dispatchWarmupBatch(count, token);
      showToast(`🎉 ${res.message || `Dispatched ${res.dispatched_count || count} warmup emails!`}`, 'success');
      await loadInboxes();
      if (inboxSubTab === 'activity') {
        loadWarmupActivity();
      }
    } catch (err) {
      showToast(`Failed to dispatch warmup batch: ${err.message}`, 'error');
    } finally {
      setDispatchingWarmup(false);
    }
  };

  const handleRunWarmupMonitoring = async () => {
    setMonitoringWarmup(true);
    try {
      const token = await resolveToken();
      showToast('🛡️ Scanning peer warm receiver inboxes for unspam and reply signals...', 'info');
      const res = await runWarmupMonitoring(token);
      showToast(res.message || 'Peer inbox monitoring completed!', 'success');
      if (inboxSubTab === 'receivers') {
        loadWarmupTargets();
      }
    } catch (err) {
      showToast(`Monitoring failed: ${err.message}`, 'error');
    } finally {
      setMonitoringWarmup(false);
    }
  };


  // Listen for OAuth callback query parameters on redirect
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('oauth') === 'microsoft_success') {
        const authedEmail = urlParams.get('email') || user?.primaryEmailAddress?.emailAddress || 'Connected Account';
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
      const [pipeData, metricData, buildsData, scoutData, autoData, inboxesData, prospectorData, countyData] = await Promise.allSettled([
        fetchAdminPipeline(token),
        fetchAdminMetrics(token),
        fetchActiveBuilds(token),
        fetchScoutStatus(token),
        fetchAutoOutreachStatus(token),
        fetchAdminInboxes(token),
        fetchProspectorStatus(token),
        fetchCountyOrchestratorStatus(token),
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
        if (iVal.warmup_cycle) setWarmupCycle(iVal.warmup_cycle);
      }
      if (prospectorData.status === 'fulfilled' && prospectorData.value) {
        setProspectorStatus(prospectorData.value);
      }
      if (countyData.status === 'fulfilled' && countyData.value && countyData.value.ok) {
        setCountyOrchestrator(countyData.value);
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
      if (res && res.warmup_cycle) {
        setWarmupCycle(res.warmup_cycle);
      }
      loadMsOAuthStatus();
      loadDeliverabilityStatus();
      loadInboundStream();
      loadWarmupTargets();
      loadWarmupActivity();
    } catch (err) {
      console.warn('Could not load inboxes:', err);
    } finally {
      setInboxesLoading(false);
    }
  };

  const loadInboundStream = async () => {
    setInboundLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchInboundStream(token);
      if (res && res.ok) {
        setInboundStream(res);
      }
    } catch (err) {
      console.warn('Could not load inbound stream:', err);
    } finally {
      setInboundLoading(false);
    }
  };

  const loadWarmupTargets = async () => {
    setWarmupTargetsLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchWarmupTargets(token);
      if (res && res.targets) {
        setWarmupTargets(res.targets);
      }
    } catch (err) {
      console.warn('Could not load warmup targets:', err);
    } finally {
      setWarmupTargetsLoading(false);
    }
  };

  const loadWarmupActivity = async () => {
    setWarmupActivityLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchWarmupActivity(50, token);
      if (res && res.ok) {
        setWarmupActivity(res);
      }
    } catch (err) {
      console.warn('Could not load warmup activity:', err);
    } finally {
      setWarmupActivityLoading(false);
    }
  };

  const handleSaveReceiver = async () => {
    if (!receiverFormData.email || !receiverFormData.email.includes('@')) {
      showToast('Please provide a valid email address for warm receiver', 'warning');
      return;
    }
    try {
      const token = await resolveToken();
      await addWarmupTarget(receiverFormData, token);
      showToast(`Warm receiver '${receiverFormData.email}' registered into peer warmup loop!`, 'success');
      setShowAddReceiverModal(false);
      setReceiverFormData({
        email: '',
        name: '',
        password: '',
        provider: 'gmail',
        is_monitored: true,
      });
      await loadWarmupTargets();
    } catch (err) {
      showToast(`Failed to add warm receiver: ${err.message}`, 'error');
    }
  };

  const handleDeleteReceiver = async (targetId, email) => {
    setConfirmModal({
      isOpen: true,
      title: 'Remove Warm Receiver',
      message: `Remove '${email}' from the peer warmup network?`,
      confirmText: 'Remove Receiver',
      cancelText: 'Cancel',
      isDestructive: true,
      onConfirm: async () => {
        try {
          const token = await resolveToken();
          await deleteWarmupTarget(targetId, token);
          showToast(`Warm receiver '${email}' removed.`, 'success');
          await loadWarmupTargets();
        } catch (err) {
          showToast(`Failed to remove warm receiver: ${err.message}`, 'error');
        }
      },
    });
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
    showToast('🛡️ Initiating comprehensive 4-vector audit (DNS Matrix, 12 RBLs, AI Content, Placement)...', 'info');
    try {
      const token = await resolveToken();
      const res = await runComprehensiveDeliverabilityAudit(
        {
          domain: 'olfmailer.com',
          subject: testCopySubject || 'morning docket records for your jurisdiction',
          body: testCopyBody || undefined,
        },
        token
      );
      if (res && res.report) {
        setDeliverabilityReport(res.report);
        showToast(
          `✅ 4-Vector Audit Complete: Health Score ${res.report.composite_score}% (${res.report.tier})!`,
          'success'
        );
      } else {
        await loadDeliverabilityStatus();
        showToast('✅ Deliverability scorecard updated!', 'success');
      }
    } catch (err) {
      showToast(`Deliverability audit failed: ${err.message}`, 'error');
    } finally {
      setAuditingDeliverability(false);
    }
  };

  const handleAuditTestCopy = async () => {
    if (!testCopyBody.trim()) {
      showToast('Please enter sample cold outreach copy to audit', 'warning');
      return;
    }
    setAuditingContent(true);
    try {
      const token = await resolveToken();
      const res = await checkContentSpamScore(testCopySubject, testCopyBody, token);
      if (res && res.result) {
        setContentAuditResult(res.result);
        showToast(`📋 Copy audit complete: Score ${res.result.score}/100 (${res.result.status})`, 'success');
      }
    } catch (err) {
      showToast(`Copy audit failed: ${err.message}`, 'error');
    } finally {
      setAuditingContent(false);
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
    showToast('⚡ Flushing outreach queue across all active olfmailer.com inboxes...', 'info');
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
        provider: 'olfmailer',
        daily_limit: 5,
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

      let matchesChannel = true;
      if (channelFilter !== 'ALL') {
        const chan = (l.discovery_channel || '').toUpperCase();
        matchesChannel = chan === channelFilter.toUpperCase();
      }

      return matchesSearch && matchesState && matchesPayment && matchesScore && matchesChannel;
    });
  }, [pipeline, searchQuery, stateFilter, paymentFilter, scoreFilter, channelFilter]);

  // Vetted Backlog Leads (for 14-Day High-Volume Prospector)
  const backlogLeads = useMemo(() => {
    return pipeline.filter((l) => {
      if (l.state === 'ARCHIVED') return false;
      const isBacklog = (
        l.outreach_status === 'BACKLOG_VETTED' ||
        l.state === 'REVIEW' ||
        l.state === 'PITCH_PENDING_APPROVAL' ||
        l.state === 'PROSPECTING'
      );
      if (!isBacklog) return false;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        (l.company_name && l.company_name.toLowerCase().includes(q)) ||
        (l.contact_email && l.contact_email.toLowerCase().includes(q)) ||
        (l.jurisdiction && l.jurisdiction.toLowerCase().includes(q)) ||
        (l.lead_id && l.lead_id.toLowerCase().includes(q));

      let matchesChannel = true;
      if (selectedProspectorChannel !== 'ALL') {
        const chan = (l.discovery_channel || '').toUpperCase();
        matchesChannel = chan === selectedProspectorChannel.toUpperCase();
      }
      return matchesSearch && matchesChannel;
    });
  }, [pipeline, searchQuery, selectedProspectorChannel]);

  // 14-Day Prospector Campaign Action Handlers
  const handleStartProspector = async (days = 14, volume = 3) => {
    setProspectorLoading(true);
    showToast(`Starting 14-Day High-Volume Prospecting Campaign (${volume} leads/burst)...`, 'info');
    try {
      const token = await resolveToken();
      const res = await startProspectorCampaign(days, volume, null, token);
      setProspectorStatus(res);
      showToast(res.status_message || '14-Day Campaign started successfully!', 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Campaign start error: ${err.message}`, 'error');
    } finally {
      setProspectorLoading(false);
    }
  };

  const handlePauseProspector = async () => {
    setProspectorLoading(true);
    try {
      const token = await resolveToken();
      const res = await pauseProspectorCampaign(token);
      setProspectorStatus(res);
      showToast('14-Day High-Volume Campaign paused.', 'info');
    } catch (err) {
      showToast(`Pause error: ${err.message}`, 'error');
    } finally {
      setProspectorLoading(false);
    }
  };

  const handleResumeProspector = async () => {
    setProspectorLoading(true);
    try {
      const token = await resolveToken();
      const res = await resumeProspectorCampaign(token);
      setProspectorStatus(res);
      showToast('14-Day High-Volume Campaign resumed.', 'success');
    } catch (err) {
      showToast(`Resume error: ${err.message}`, 'error');
    } finally {
      setProspectorLoading(false);
    }
  };

  const handleTriggerBurst = async (count = 3, channel = null) => {
    setProspectorLoading(true);
    showToast(`Executing high-volume discovery pass (${count} candidates)...`, 'info');
    try {
      const token = await resolveToken();
      const chan = channel && channel !== 'ALL' ? channel : null;
      const res = await triggerProspectorBurst(count, chan, token);
      if (res && res.metrics) {
        setProspectorStatus((prev) => ({ ...prev, metrics: res.metrics }));
      }
      showToast(`Discovery burst complete: +${res.qualified_count} vetted leads added to backlog.`, 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Burst error: ${err.message}`, 'error');
    } finally {
      setProspectorLoading(false);
    }
  };

  const handleRefreshFreshness = async (leadId) => {
    setFreshnessRefreshingLeadId(leadId);
    showToast(`Pulling live same-day filings for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      const res = await refreshLeadFreshness(leadId, token);
      showToast(res.message || 'Records refreshed with today’s filings!', 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Freshness refresh error: ${err.message}`, 'error');
    } finally {
      setFreshnessRefreshingLeadId(null);
    }
  };

  const handleBatchRefreshStale = async () => {
    setSweepingStaleRecords(true);
    showToast('Sweeping all backlog leads for same-day freshness...', 'info');
    try {
      const token = await resolveToken();
      const res = await batchRefreshStaleBacklog(token);
      showToast(res.message || 'Freshness sweep complete!', 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Sweep error: ${err.message}`, 'error');
    } finally {
      setSweepingStaleRecords(false);
    }
  };

  const handleAdvanceCountyCursor = async () => {
    setOrchestratorLoading(true);
    showToast('Advancing national prospecting cursor to next county...', 'info');
    try {
      const token = await resolveToken();
      const res = await advanceCountyOrchestratorCursor(token);
      showToast(res.message || 'Advanced to next county/state!', 'success');
      const statusRes = await fetchCountyOrchestratorStatus(token);
      if (statusRes?.ok) setCountyOrchestrator(statusRes);
    } catch (err) {
      showToast(`Advance error: ${err.message}`, 'error');
    } finally {
      setOrchestratorLoading(false);
    }
  };

  const handleSetStateFocus = async (stateCode) => {
    setOrchestratorLoading(true);
    try {
      const token = await resolveToken();
      const res = await setCountyOrchestratorStateFocus(stateCode || null, token);
      showToast(res.message || 'State focus updated!', 'success');
      const statusRes = await fetchCountyOrchestratorStatus(token);
      if (statusRes?.ok) setCountyOrchestrator(statusRes);
    } catch (err) {
      showToast(`State focus error: ${err.message}`, 'error');
    } finally {
      setOrchestratorLoading(false);
    }
  };

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

  const handleTriggerWebScout = async (overrideChannel = null, overrideQuery = null, overrideBatch = null) => {
    setScoutingInProgress(true);
    const targetChannel = overrideChannel !== null ? overrideChannel : selectedScoutChannel;
    const targetQuery = overrideQuery !== null ? overrideQuery : scoutSearchQuery;
    const countToScout = overrideBatch !== null ? overrideBatch : scoutBatchCount;
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
      : 'All High-ROI Channels';

    if (countToScout > 1) {
      showToast(`🚀 Swarm scouting ${countToScout} qualified leads across [${channelLabel}]...`, 'info');
    } else {
      showToast(`🔎 Hunting for a new qualified lead via [${channelLabel}] until found...`, 'info');
    }

    try {
      const token = await resolveToken();
      let res;
      if (countToScout > 1) {
        res = await triggerBatchScout(countToScout, searchTrimmed || null, targetChannel || null, token);
        if (res && res.count_discovered > 0) {
          showToast(`🎯 Batch complete! Successfully scouted & qualified ${res.count_discovered}/${countToScout} leads!`, 'success');
        } else {
          showToast(res.message || 'Batch scout pass complete.', 'info');
        }
      } else {
        res = await triggerScoutDiscovery(searchTrimmed || null, token, targetChannel || null, true);
        if (res && res.lead_id) {
          showToast(`🎯 Discovered new qualified lead: ${res.company_name || res.lead_id}!`, 'success');
        } else if (res && res.ok) {
          showToast(`🎯 Discovered new lead! Telemetry updated.`, 'success');
        } else {
          showToast(res.message || res.reason || 'Scout pass complete. Telemetry updated.', 'info');
        }
      }
      await loadAdminData();
    } catch (err) {
      showToast(`Scout trigger error: ${err.message}`, 'error');
    } finally {
      setScoutingInProgress(false);
    }
  };

  const handleDeepEnrichLead = async (leadId) => {
    setEnrichingLeadId(leadId);
    showToast(`🔬 Running live deep market & operational research on lead...`, 'info');
    try {
      const token = await resolveToken();
      const res = await deepEnrichLead(leadId, token);
      showToast(`✅ Deep research dossier updated for ${res.company_name || leadId}!`, 'success');
      await loadAdminData();
      if (scoreModal.open && scoreModal.lead?.lead_id === leadId) {
        setScoreModal((prev) => ({
          ...prev,
          lead: {
            ...prev.lead,
            research: res.research,
            contact_name: res.research.decision_maker_name || prev.lead.contact_name,
            contact_role: res.research.decision_maker_role || prev.lead.contact_role,
            decision_maker_linkedin: res.research.linkedin_url || prev.lead.decision_maker_linkedin,
            contact_phone: res.research.verified_phone || prev.lead.contact_phone,
          },
        }));
      }
    } catch (err) {
      showToast(`Enrichment failed: ${err.message}`, 'error');
    } finally {
      setEnrichingLeadId(null);
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

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <SignIn routing="hash" />
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
              Autonomous 7-Agent Dev Swarms, Live Municipal Extractors, QA Gate &amp; Setup Sprint Vault
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

              {/* Batch Count Selector */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '3px',
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(56, 189, 248, 0.35)',
                  borderRadius: '6px',
                  padding: '2px 5px',
                }}
                title="Select number of leads to hunt in this swarm batch"
              >
                <span style={{ fontSize: '10px', color: 'var(--text-dim)', fontWeight: 600, paddingRight: '2px' }}>
                  Batch:
                </span>
                {[1, 3, 5].map((cnt) => (
                  <button
                    key={cnt}
                    type="button"
                    onClick={() => setScoutBatchCount(cnt)}
                    style={{
                      background: scoutBatchCount === cnt ? 'var(--cyan)' : 'transparent',
                      color: scoutBatchCount === cnt ? '#090d16' : 'var(--cyan)',
                      border: 'none',
                      borderRadius: '4px',
                      padding: '2px 6px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                    title={`Hunt ${cnt} lead${cnt > 1 ? 's in parallel swarm batch' : ''}`}
                  >
                    {cnt === 5 ? '⚡5' : cnt}
                  </button>
                ))}
              </div>

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
                  background: scoutBatchCount > 1 ? 'rgba(56, 189, 248, 0.08)' : 'transparent',
                }}
                onClick={() => handleTriggerWebScout()}
                disabled={scoutingInProgress}
                title="Trigger autonomous swarm scout to hunt qualified B2B leads."
              >
                <span>
                  {scoutingInProgress
                    ? `⏳ Hunting ${scoutBatchCount > 1 ? `Swarm (${scoutBatchCount})...` : 'Lead...'}`
                    : scoutBatchCount > 1
                    ? `⚡ Swarm Hunt (${scoutBatchCount} Leads)`
                    : '🔎 Scout Now'}
                </span>
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
              <span className="pulse-dot-green" title="Milestone #1 deposits credited to Month 1" />
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
                🛡️ 4-Vector Deliverability Suite
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

        {/* Tab Navigation */}
        <div className="admin-tabs-nav" style={{ marginBottom: '20px' }}>
          <button
            className={`admin-tab-btn ${activeTab === 'prospector' ? 'active' : ''}`}
            onClick={() => setActiveTab('prospector')}
          >
            🗺️ 14-Day Backlog &amp; Swarm ({backlogLeads.length})
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'deals' ? 'active' : ''}`}
            onClick={() => setActiveTab('deals')}
          >
            🚀 Bespoke Deals &amp; Sandboxes ({filteredLeads.length})
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'kanban' ? 'active' : ''}`}
            onClick={() => setActiveTab('kanban')}
          >
            📋 Lifecycle Kanban
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'archived' ? 'active' : ''}`}
            onClick={() => setActiveTab('archived')}
          >
            🗄️ Archived Vault ({archivedLeads.length})
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'swarm' ? 'active' : ''}`}
            onClick={() => setActiveTab('swarm')}
          >
            🤖 Autonomous Swarm Monitor ({activeBuilds.length} Active)
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'accounting' ? 'active' : ''}`}
            onClick={() => setActiveTab('accounting')}
          >
            💳 Financial Ledger &amp; Sprints
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

        {/* TAB 0: 14-DAY HIGH-VOLUME PROSPECTOR & VETTED BACKLOG */}
        {activeTab === 'prospector' && (
          <ProspectorTab
            countyOrchestrator={countyOrchestrator}
            orchestratorLoading={orchestratorLoading}
            handleSetStateFocus={handleSetStateFocus}
            handleAdvanceCountyCursor={handleAdvanceCountyCursor}
            prospectorStatus={prospectorStatus}
            prospectorLoading={prospectorLoading}
            handlePauseProspector={handlePauseProspector}
            handleStartProspector={handleStartProspector}
            burstLeadCount={burstLeadCount}
            setBurstLeadCount={setBurstLeadCount}
            selectedProspectorChannel={selectedProspectorChannel}
            setSelectedProspectorChannel={setSelectedProspectorChannel}
            handleTriggerBurst={handleTriggerBurst}
            handleBatchRefreshStale={handleBatchRefreshStale}
            sweepingStaleRecords={sweepingStaleRecords}
            pipeline={pipeline}
            backlogLeads={backlogLeads}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            backlogPage={backlogPage}
            setBacklogPage={setBacklogPage}
            backlogPageSize={backlogPageSize}
            freshnessRefreshingLeadId={freshnessRefreshingLeadId}
            renderDiscoveryBadge={renderDiscoveryBadge}
            handleRefreshFreshness={handleRefreshFreshness}
            setScoreModal={setScoreModal}
            handleAdvance={handleAdvance}
            actionInProgress={actionInProgress}
          />
        )}

        {/* TAB 1: BESPOKE ACTIVE DEALS & VERIFIED WORKSPACES */}
        {activeTab === 'deals' && (
          <DealsTab
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            dealsPage={dealsPage}
            setDealsPage={setDealsPage}
            dealsPageSize={dealsPageSize}
            setDealsPageSize={setDealsPageSize}
            stateFilter={stateFilter}
            setStateFilter={setStateFilter}
            paymentFilter={paymentFilter}
            setPaymentFilter={setPaymentFilter}
            scoreFilter={scoreFilter}
            setScoreFilter={setScoreFilter}
            pipeline={pipeline}
            filteredLeads={filteredLeads}
            loading={loading}
            batchApproving={batchApproving}
            handleBatchApprove={handleBatchApprove}
            scoutingInProgress={scoutingInProgress}
            handleTriggerWebScout={handleTriggerWebScout}
            loadAdminData={loadAdminData}
            setScoreModal={setScoreModal}
            handleCopyText={handleCopyText}
            renderDiscoveryBadge={renderDiscoveryBadge}
            handleAdvance={handleAdvance}
            handleCancelOutreach={handleCancelOutreach}
            handleTriggerSwarm={handleTriggerSwarm}
            handleViewAudit={handleViewAudit}
            handleDeleteLead={handleDeleteLead}
            actionInProgress={actionInProgress}
          />
        )}

        {/* TAB 2: KANBAN BOARD */}
        {activeTab === 'kanban' && (
          <KanbanTab
            pipeline={pipeline}
            handleBatchApprove={handleBatchApprove}
            batchApproving={batchApproving}
            setScoreModal={setScoreModal}
            renderDiscoveryBadge={renderDiscoveryBadge}
            handleAdvance={handleAdvance}
            actionInProgress={actionInProgress}
            handleViewAudit={handleViewAudit}
          />
        )}

        {/* TAB 3: ARCHIVED LEADS & HISTORICAL VAULT */}
        {activeTab === 'archived' && (
          <ArchivedLeadsTab
            archivedLeads={archivedLeads}
            loadArchivedLeads={loadArchivedLeads}
            handleBatchEnrichArchived={handleBatchEnrichArchived}
            batchEnriching={batchEnriching}
            enrichingLeadId={enrichingLeadId}
            handleEnrichLead={handleEnrichLead}
            handleDeleteLead={handleDeleteLead}
          />
        )}

        {/* TAB 4: AUTONOMOUS SWARM MONITOR */}
        {activeTab === 'swarm' && (
          <SwarmTab
            pipeline={pipeline}
            renderDiscoveryBadge={renderDiscoveryBadge}
            handleViewSwarmProgress={handleViewSwarmProgress}
            handleOpenQaOverride={handleOpenQaOverride}
            handleTriggerSwarm={handleTriggerSwarm}
            actionInProgress={actionInProgress}
          />
        )}

        {/* TAB 5: FINANCIAL TELEMETRY & STRIPE / PAYPAL SPRINT AUDIT */}
        {activeTab === 'accounting' && (
          <AccountingTab
            pipeline={pipeline}
            depositTotal={depositTotal}
            releasedTotal={releasedTotal}
            activeMrr={activeMrr}
          />
        )}

        {/* TAB 6: SCRAPERS CATALOG */}
        {activeTab === 'scrapers' && (
          <ScrapersTab
            loadScrapers={loadScrapers}
            scrapersLoading={scrapersLoading}
            scrapers={scrapers}
            handleRunScraper={handleRunScraper}
            handleViewCode={handleViewCode}
            handleViewOutput={handleViewOutput}
            actionInProgress={actionInProgress}
          />
        )}

        {/* TAB 7: DAILY DELIVERY FEEDS */}
        {activeTab === 'daily' && (
          <DailyDeliveryTab
            loadDailyGrid={loadDailyGrid}
            pipeline={pipeline}
            handleTriggerDailyDelivery={handleTriggerDailyDelivery}
          />
        )}

        {/* TAB 8: EMAIL INBOXES & WARMUP FLEET */}
        {activeTab === 'inboxes' && (
          <InboxesAndWarmupTab
            inboxes={inboxes}
            loadInboxes={loadInboxes}
            inboxesLoading={inboxesLoading}
            warmupTargets={warmupTargets}
            loadWarmupTargets={loadWarmupTargets}
            warmupTargetsLoading={warmupTargetsLoading}
            inboundStream={inboundStream}
            loadInboundStream={loadInboundStream}
            inboundLoading={inboundLoading}
            warmupActivity={warmupActivity}
            loadWarmupActivity={loadWarmupActivity}
            warmupActivityLoading={warmupActivityLoading}
            inboxSubTab={inboxSubTab}
            setInboxSubTab={setInboxSubTab}
            handleStartWarmup={handleStartWarmup}
            startingWarmup={startingWarmup}
            handleDispatchWarmupBatch={handleDispatchWarmupBatch}
            dispatchingWarmup={dispatchingWarmup}
            handleFlushOutreachQueue={handleFlushOutreachQueue}
            flushingQueue={flushingQueue}
            showToast={showToast}
            showAddReceiverModal={showAddReceiverModal}
            setShowAddReceiverModal={setShowAddReceiverModal}
            receiverFormData={receiverFormData}
            setReceiverFormData={setReceiverFormData}
            handleSaveReceiver={handleSaveReceiver}
            showAddInboxModal={showAddInboxModal}
            setShowAddInboxModal={setShowAddInboxModal}
            inboxFormData={inboxFormData}
            setInboxFormData={setInboxFormData}
            handleSaveInbox={handleSaveInbox}
            inboxesFilter={inboxesFilter}
            setInboxesFilter={setInboxesFilter}
            filteredInboxes={filteredInboxes}
            testingInboxId={testingInboxId}
            handleTestInbox={handleTestInbox}
            handleDeleteInbox={handleDeleteInbox}
            deletingInboxId={deletingInboxId}
            inboundFilter={inboundFilter}
            setInboundFilter={setInboundFilter}
            filteredInboundLogs={filteredInboundLogs}
            deletingReceiverId={deletingReceiverId}
            handleDeleteReceiver={handleDeleteReceiver}
            handleRunWarmupMonitoring={handleRunWarmupMonitoring}
            monitoringWarmup={monitoringWarmup}
          />
        )}
      </div>

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

        let research = {};
        if (typeof lead.research === 'object' && lead.research !== null) {
          research = lead.research;
        } else if (typeof lead.research === 'string' && lead.research.trim()) {
          try {
            research = JSON.parse(lead.research);
          } catch (_) {
            research = {};
          }
        }

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
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    className="btn btn-outline"
                    style={{
                      padding: '6px 12px',
                      fontSize: '12px',
                      borderColor: 'rgba(56, 189, 248, 0.4)',
                      color: 'var(--cyan)',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                    onClick={() => handleDeepEnrichLead(lead.lead_id)}
                    disabled={enrichingLeadId === lead.lead_id}
                    title="Trigger deep LLM agent enrichment & market research on this lead"
                  >
                    {enrichingLeadId === lead.lead_id ? '⏳ Researching...' : '⚡ Deep Re-Enrich'}
                  </button>
                  <button
                    className="btn btn-outline"
                    style={{ padding: '6px 12px', fontSize: '12px' }}
                    onClick={() => setScoreModal({ open: false, lead: null })}
                  >
                    ✕ Close
                  </button>
                </div>
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
                    {qa && qa >= 0.95 ? '✓ Meets Founder Gate' : 'Data Verification Stage'}
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

              {/* Deep Market & Operational Intelligence Dossier */}
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid rgba(56, 189, 248, 0.35)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: '1px solid rgba(56, 189, 248, 0.15)',
                    paddingBottom: '8px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '16px' }}>🔬</span>
                    <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: 0 }}>
                      Deep Market &amp; Operational Intelligence Dossier
                    </h4>
                  </div>
                  <span
                    style={{
                      fontSize: '10px',
                      background: 'rgba(56, 189, 248, 0.15)',
                      color: 'var(--cyan)',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontWeight: 600,
                    }}
                  >
                    AI Agent Enriched
                  </span>
                </div>

                {/* Row 1: Org Scale, HQ & Est ROI */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>HQ Location</div>
                    <div style={{ fontSize: '12px', color: '#fff', fontWeight: 600, marginTop: '2px' }}>
                      📍 {research.headquarters_location || lead.jurisdiction || 'Regional Office'}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Company Scale</div>
                    <div style={{ fontSize: '12px', color: '#fff', fontWeight: 600, marginTop: '2px' }}>
                      🏢 {research.company_scale || 'Small-to-Mid Market Firm'}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Weekly Hours Saved</div>
                    <div style={{ fontSize: '13px', color: 'var(--green)', fontWeight: 700, marginTop: '2px' }}>
                      ⏱️ ~{research.estimated_hours_saved_weekly || 8} hrs/wk
                    </div>
                  </div>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 600 }}>Est. Labor Savings</div>
                    <div style={{ fontSize: '13px', color: 'var(--cyan)', fontWeight: 700, marginTop: '2px' }}>
                      💰 ${research.estimated_monthly_labor_savings || 1200}/mo
                    </div>
                  </div>
                </div>

                {/* Row 2: Secondary Contact & Tech Stack */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
                  {research.secondary_decision_maker && (research.secondary_decision_maker.name || research.secondary_decision_maker.role) ? (
                    <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, marginBottom: '4px' }}>
                        👥 Secondary Decision Maker / Influencer
                      </div>
                      <div style={{ fontSize: '12px', color: '#fff', fontWeight: 600 }}>
                        {research.secondary_decision_maker.name || 'Key Contact'}
                        {research.secondary_decision_maker.role && (
                          <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> — {research.secondary_decision_maker.role}</span>
                        )}
                      </div>
                      {research.secondary_decision_maker.email && (
                        <div style={{ fontSize: '11px', color: 'var(--cyan)', marginTop: '2px' }}>
                          ✉️ {research.secondary_decision_maker.email}
                        </div>
                      )}
                      {research.secondary_decision_maker.linkedin && (
                        <a
                          href={research.secondary_decision_maker.linkedin}
                          target="_blank"
                          rel="noreferrer"
                          style={{ fontSize: '11px', color: 'var(--purple)', textDecoration: 'underline', display: 'inline-block', marginTop: '2px' }}
                        >
                          LinkedIn Profile ↗
                        </a>
                      )}
                    </div>
                  ) : null}

                  {research.detected_tech_stack && (
                    <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px' }}>
                      <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, marginBottom: '6px' }}>
                        💻 Detected Software &amp; Tech Stack
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                        {(Array.isArray(research.detected_tech_stack) ? research.detected_tech_stack : [research.detected_tech_stack]).map((tool, idx) => (
                          <span
                            key={idx}
                            style={{
                              fontSize: '11px',
                              background: 'rgba(147, 51, 234, 0.15)',
                              color: '#c084fc',
                              border: '1px solid rgba(147, 51, 234, 0.3)',
                              padding: '2px 7px',
                              borderRadius: '4px',
                              fontWeight: 500,
                            }}
                          >
                            {typeof tool === 'object' ? JSON.stringify(tool) : String(tool)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Row 3: Competitors */}
                {Array.isArray(research.local_competitors) && research.local_competitors.length > 0 && (
                  <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, marginBottom: '6px' }}>
                      ⚔️ Local &amp; Regional Competitors in Vertical
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {research.local_competitors.map((comp, idx) => {
                        const compName = typeof comp === 'object' && comp !== null ? (comp.name || comp.company || JSON.stringify(comp)) : String(comp);
                        return (
                          <span
                            key={idx}
                            style={{
                              fontSize: '11px',
                              background: 'rgba(255, 255, 255, 0.05)',
                              color: 'var(--text)',
                              border: '1px solid var(--border)',
                              padding: '2px 8px',
                              borderRadius: '4px',
                            }}
                          >
                            {compName}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Row 4: Alex Objection Playbook */}
                {research.objection_playbook && typeof research.objection_playbook === 'object' && Object.keys(research.objection_playbook).length > 0 && (
                  <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid var(--border)', borderRadius: '6px', padding: '10px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--cyan)', fontWeight: 700, marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      💬 Alex Persona Tailored Objection Playbook (1-Click Copy)
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {Object.entries(research.objection_playbook).map(([objection, answer], idx) => {
                        const answerText = typeof answer === 'object' && answer !== null ? (answer.response || JSON.stringify(answer)) : String(answer);
                        return (
                          <div
                            key={idx}
                            style={{
                              background: 'rgba(15, 23, 42, 0.7)',
                              border: '1px solid rgba(255, 255, 255, 0.07)',
                              borderRadius: '5px',
                              padding: '8px 10px',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--yellow)' }}>
                                ❓ {objection.replace(/_/g, ' ')}
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  navigator.clipboard?.writeText(answerText);
                                  setToastMessage('Copied playbook answer to clipboard!');
                                  setTimeout(() => setToastMessage(''), 2500);
                                }}
                                style={{
                                  background: 'transparent',
                                  border: '1px solid rgba(56, 189, 248, 0.3)',
                                  color: 'var(--cyan)',
                                  borderRadius: '4px',
                                  padding: '2px 6px',
                                  fontSize: '10px',
                                  cursor: 'pointer',
                                }}
                                title="Copy counter-argument to clipboard"
                              >
                                📋 Copy
                              </button>
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text)', fontStyle: 'italic', lineHeight: 1.4 }}>
                              &ldquo;{answerText}&rdquo;
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
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
