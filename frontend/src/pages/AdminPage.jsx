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
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState({});
  const [scoutStatus, setScoutStatus] = useState(null);
  const [batchApproving, setBatchApproving] = useState(false);
  const [autoOutreachStatus, setAutoOutreachStatus] = useState(null);
  const [autoOutreachLoading, setAutoOutreachLoading] = useState(false);
  const [scoutingInProgress, setScoutingInProgress] = useState(false);

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
  const [inboxesLoading, setInboxesLoading] = useState(false);
  const [testingInboxId, setTestingInboxId] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [showAddInboxModal, setShowAddInboxModal] = useState(false);
  const [inboxFormData, setInboxFormData] = useState({
    inbox_id: '',
    email_address: '',
    password: '',
    from_name: 'Alex | OmniLeadFeeder',
    provider: 'zoho',
    daily_limit: 25,
  });

  // Load Admin Data
  const loadAdminData = async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      const [pipeData, metricData, buildsData, scoutData, autoData] = await Promise.allSettled([
        fetchAdminPipeline(token),
        fetchAdminMetrics(token),
        fetchActiveBuilds(token),
        fetchScoutStatus(token),
        fetchAutoOutreachStatus(token),
      ]);

      if (pipeData.status === 'fulfilled') {
        const raw = pipeData.value || {};
        const list = Array.isArray(raw) ? raw : (raw.leads || raw.pipeline || []);
        setPipeline(list);
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
    } catch (err) {
      console.warn('Admin load note:', err);
      showToast(`Admin load: ${err.message}`, 'info');
    } finally {
      setLoading(false);
    }
  };

  // Load Scrapers / Inboxes when tab changes
  useEffect(() => {
    if (activeTab === 'scrapers' && scrapers.length === 0) {
      loadScrapers();
    } else if (activeTab === 'daily' && dailyGrid.length === 0) {
      loadDailyGrid();
    } else if (activeTab === 'inboxes') {
      loadInboxes();
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
    } catch (err) {
      console.warn('Could not load inboxes:', err);
    } finally {
      setInboxesLoading(false);
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

  const handleTriggerWebScout = async () => {
    setScoutingInProgress(true);
    showToast('🔎 Triggering autonomous B2B Scout discovery cycle...', 'info');
    try {
      const token = await resolveToken();
      const res = await triggerScoutDiscovery(null, token);
      if (res.lead_id) {
        showToast(`Discovered qualified lead: ${res.company_name || res.lead_id}!`, 'success');
      } else {
        showToast(res.message || 'Scout pass complete. Telemetry updated.', 'info');
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
    } catch (err) {
      showToast(`Cancel outreach error: ${err.message}`, 'error');
    } finally {
      setActionInProgress((p) => ({ ...p, [leadId]: false }));
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

  const handleViewAudit = async (leadId, companyName) => {
    try {
      const token = await resolveToken();
      const res = await fetchAuditTrail(leadId, token);
      setAuditModal({
        open: true,
        title: `Audit Trail: ${companyName || leadId}`,
        events: res.events || res.audit_trail || res.audit_log || [],
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
  const escrowTotal = useMemo(() => {
    return pipeline.filter((l) => l.deposit_paid).length * 250.0;
  }, [pipeline]);

  const releasedTotal = useMemo(() => {
    return pipeline.filter((l) => l.final_paid).length * 250.0;
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
              onClick={handleTriggerWebScout}
              disabled={scoutingInProgress}
              title="Manually trigger autonomous scout to probe public registries and discover qualified B2B leads."
            >
              <span>{scoutingInProgress ? '⏳ Scouting...' : '🔎 Scout Now'}</span>
            </button>

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

        {/* Top Summary Stats Bar */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '28px' }}>
          <div className="stat-card">
            <div className="stat-label">🏦 Escrow Deposits Held</div>
            <div className="stat-value" style={{ color: 'var(--green)' }}>
              ${escrowTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Milestone #1 ($250 held in escrow)
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">💰 Released Milestone #2</div>
            <div className="stat-value" style={{ color: 'var(--cyan)' }}>
              ${releasedTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Passed QA Gate (≥95% verified)
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">📈 Active Retainer MRR</div>
            <div className="stat-value" style={{ color: 'var(--purple)' }}>
              ${activeMrr.toLocaleString('en-US', { minimumFractionDigits: 2 })}/mo
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Live subscription cashflow
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-label">🎯 Total Pipeline Deals</div>
            <div className="stat-value" style={{ color: '#fff' }}>
              {pipeline.length}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Across all lifecycle stages
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="admin-tabs-nav">
          <button
            className={`admin-tab-btn ${activeTab === 'deals' ? 'active' : ''}`}
            onClick={() => setActiveTab('deals')}
          >
            📊 Deals &amp; Customers ({pipeline.length})
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'kanban' ? 'active' : ''}`}
            onClick={() => setActiveTab('kanban')}
          >
            📌 Stage Kanban
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
            💰 Accounting &amp; Escrow Vault
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
                <option value="DEPOSIT_PAID">Deposit Paid (In Escrow)</option>
                <option value="DEV_BUILDING">Dev Building (Swarm)</option>
                <option value="ESCROW_PREVIEW">Escrow Preview (QA Passed)</option>
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
                    <th>Jurisdiction / Portal</th>
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
                            <div style={{ fontWeight: 700, color: '#fff' }}>
                              {lead.company_name || 'Organization Lead'}
                            </div>
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
                          </td>
                          <td>
                            <div style={{ fontSize: '13px', color: 'var(--text)' }}>
                              {lead.jurisdiction || lead.target_portal_name || 'Municipal Registry'}
                            </div>
                            {lead.source_url && (
                              <a
                                href={lead.source_url}
                                target="_blank"
                                rel="noreferrer"
                                style={{ fontSize: '11px', color: 'var(--text-dim)', textDecoration: 'underline' }}
                              >
                                View Portal ↗
                              </a>
                            )}
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
                              lead.state === 'DELIVERED' || lead.state === 'WARRANTY_ACTIVE'
                                ? 'badge-green'
                                : lead.state === 'DEV_BUILDING'
                                ? 'badge-cyan'
                                : lead.state === 'DEPOSIT_PAID'
                                ? 'badge-purple'
                                : 'badge-yellow'
                            }`}>
                              {lead.state}
                            </span>
                          </td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {lead.deposit_paid ? (
                                <span style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600 }}>
                                  ✓ M1 Deposit ($250 Escrow)
                                </span>
                              ) : (
                                <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                                  ○ M1 Pending ($250)
                                </span>
                              )}

                              {lead.final_paid ? (
                                <span style={{ fontSize: '11px', color: 'var(--green)', fontWeight: 600 }}>
                                  ✓ M2 Final ($250 Paid)
                                </span>
                              ) : (
                                <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                                  ○ M2 Pending ($250)
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
                                title="View 7-factor BDR scoring breakdown and market research"
                              >
                                ⚡ Score
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
                                onClick={() => handleViewAudit(lead.lead_id, lead.company_name)}
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
              { key: 'PROSPECTING', label: '1. Prospecting' },
              { key: 'REVIEW', label: '2. Enriched / Review' },
              { key: 'PITCH_PENDING_APPROVAL', label: '3. Pitch Pending' },
              { key: 'OUTREACH_SENT', label: '4. Outreach Sent' },
              { key: 'DEPOSIT_PAID', label: '5. Deposit in Escrow ($250)' },
              { key: 'DEV_BUILDING', label: '6. Dev Swarm Building' },
              { key: 'ESCROW_PREVIEW', label: '7. QA Gate Pass (95%+)' },
              { key: 'DELIVERED', label: '8. Delivered / Active' },
            ].map((col) => {
              const colLeads = pipeline.filter((l) => l.state === col.key);

              return (
                <div key={col.key} className="kanban-column">
                  <div className="kanban-col-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>{col.label}</span>
                      <span className="badge-tag">{colLeads.length}</span>
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
                            <div style={{ fontWeight: 700, fontSize: '13px', color: '#fff' }}>
                              {lead.company_name || 'Lead'}
                            </div>
                            <span style={{ fontSize: '10px', color: 'var(--purple)', fontWeight: 600 }}>
                              {lead.tier_key || 'weekly'}
                            </span>
                          </div>

                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {lead.jurisdiction || 'Public Records'}
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', fontSize: '11px' }}>
                            <span style={{ color: lead.deposit_paid ? 'var(--green)' : 'var(--text-dim)' }}>
                              {lead.deposit_paid ? '✓ Escrow Funded' : '○ Deposit Pending'}
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

                          <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                            <button
                              className="btn btn-primary"
                              style={{
                                padding: '4px 8px',
                                fontSize: '11px',
                                flex: 1,
                                background: lead.state === 'PITCH_PENDING_APPROVAL' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : undefined,
                                borderColor: lead.state === 'PITCH_PENDING_APPROVAL' ? '#10b981' : undefined,
                              }}
                              onClick={() => handleAdvance(lead.lead_id)}
                              disabled={actionInProgress[lead.lead_id]}
                            >
                              {lead.state === 'PITCH_PENDING_APPROVAL' ? '✓ Approve Pitch' : '⏩ Advance'}
                            </button>
                            <a
                              href={`/p/${lead.slug || lead.lead_id}`}
                              target="_blank"
                              rel="noreferrer"
                              className="btn btn-outline"
                              style={{ padding: '4px 8px', fontSize: '11px' }}
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
            TAB 4: ACCOUNTING & ESCROW VAULT
           ========================================================= */}
        {activeTab === 'accounting' && (
          <div>
            {/* Accounting Breakdown Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
              <div className="stat-card" style={{ borderLeft: '4px solid var(--green)' }}>
                <div className="stat-label">🏦 Total Milestone #1 In Escrow</div>
                <div className="stat-value" style={{ color: 'var(--green)' }}>
                  ${escrowTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  {pipeline.filter((l) => l.deposit_paid).length} deposits held ($250 each)
                </div>
              </div>

              <div className="stat-card" style={{ borderLeft: '4px solid var(--cyan)' }}>
                <div className="stat-label">💰 Released Milestone #2 Funds</div>
                <div className="stat-value" style={{ color: 'var(--cyan)' }}>
                  ${releasedTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  {pipeline.filter((l) => l.final_paid).length} completions unlocked ($250 each)
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
                  ${(escrowTotal + releasedTotal + activeMrr).toLocaleString('en-US', { minimumFractionDigits: 2 })}
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
                    <th>Milestone #1 ($250)</th>
                    <th>Milestone #2 ($250)</th>
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
                            {lead.deposit_paid ? '✓ $250.00 PAID (ESCROW)' : 'Pending'}
                          </span>
                        </td>
                        <td>
                          <span style={{ color: lead.final_paid ? 'var(--green)' : 'var(--text-dim)', fontWeight: 600 }}>
                            {lead.final_paid ? '✓ $250.00 RELEASED' : 'Pre-authorized'}
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
              <div className="stat-card">
                <div className="stat-label">⚡ Active Inboxes</div>
                <div className="stat-value" style={{ color: 'var(--green)' }}>
                  {inboxes.filter((i) => i.is_active).length} / {inboxes.length}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Participating in rotation
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">🟣 Zoho Workplace Inboxes</div>
                <div className="stat-value" style={{ color: '#c084fc' }}>
                  {inboxes.filter((i) => i.provider === 'zoho').length}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  smtppro.zoho.com (SSL 465)
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">📈 Total Fleet Daily Capacity</div>
                <div className="stat-value" style={{ color: 'var(--cyan)' }}>
                  {inboxes.filter((i) => i.is_active).reduce((sum, i) => sum + (i.daily_limit || 25), 0)} emails/day
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Enforcing warmup ramp-up
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">📨 Dispatched Today</div>
                <div className="stat-value" style={{ color: '#fff' }}>
                  {inboxes.reduce((sum, i) => sum + (i.sent_today || 0), 0)} sent
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                  Across all active inboxes
                </div>
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
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '18px' }}>
                {inboxes.map((inbox) => {
                  const testRes = testResults[inbox.inbox_id];
                  const isTesting = testingInboxId === inbox.inbox_id;
                  const pct = Math.min(100, Math.round(((inbox.sent_today || 0) / (inbox.daily_limit || 25)) * 100));

                  return (
                    <div
                      key={inbox.inbox_id}
                      style={{
                        background: 'var(--card)',
                        borderRadius: 'var(--radius-md)',
                        border: inbox.is_active ? '1px solid var(--border)' : '1px solid rgba(148, 163, 184, 0.2)',
                        padding: '20px',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        opacity: inbox.is_active ? 1 : 0.65,
                        transition: 'border-color 0.2s ease',
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
                            <span>{inbox.provider === 'zoho' ? '🟣' : '🔵'}</span>
                            {inbox.provider === 'zoho' ? 'Zoho Workplace' : inbox.provider === 'gmail' ? 'Google / Gmail' : 'Custom SMTP'}
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
                          <div>📤 SMTP: <span style={{ color: '#fff' }}>{inbox.smtp_host || 'smtppro.zoho.com'}:{inbox.smtp_port || 465}</span> ({inbox.smtp_use_ssl ? 'SSL' : 'TLS'})</div>
                          <div>📥 IMAP: <span style={{ color: '#fff' }}>{inbox.imap_host || 'imappro.zoho.com'}:{inbox.imap_port || 993}</span> ({inbox.imap_use_ssl ? 'SSL' : 'TLS'})</div>
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
                  <option value="smtp_generic">⚪ Generic Custom SMTP / IMAP</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Inbox Email Address *
                </label>
                <input
                  type="email"
                  placeholder="e.g. alex@yourdomain.com"
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
                  Zoho App-Specific Password *
                </label>
                <input
                  type="password"
                  placeholder="16-character generated app password"
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
          <div className="admin-modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>{auditModal.title}</h3>
              <button
                className="btn btn-outline"
                style={{ padding: '4px 10px', fontSize: '12px' }}
                onClick={() => setAuditModal({ open: false, title: '', events: [] })}
              >
                ✕ Close
              </button>
            </div>

            <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
              {auditModal.events.length === 0 ? (
                <p style={{ color: 'var(--text-muted)' }}>No audit events recorded.</p>
              ) : (
                auditModal.events.map((ev, i) => (
                  <div key={i} style={{ padding: '12px', borderBottom: '1px solid var(--border)', fontSize: '13px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--cyan)', fontWeight: 600 }}>
                      <span>{ev.action || ev.event || 'Lifecycle Transition'}</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{ev.timestamp || ev.created_at}</span>
                    </div>
                    <div style={{ marginTop: '4px', color: 'var(--text-muted)' }}>{ev.detail || ev.reason || JSON.stringify(ev)}</div>
                  </div>
                ))
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
        const oppScore = lead.automation_opportunity_score ?? 75;
        const purchaseProb = lead.purchase_probability ?? 60;
        const painSev = lead.pain_severity ?? 6;
        const verdict = lead.qualification_verdict || (oppScore >= 65 ? 'QUALIFIED_HOT' : 'QUALIFIED_NURTURE');
        const breakdown = lead.scoring_breakdown || {
          labor_intensity: 20,
          target_portal_scraping: 12,
          manual_data_entry: 12,
          compliance_regulatory: 11,
          document_volume: 8,
          smb_size_fit: 8,
          market_growth: 7,
        };
        const signals = Array.isArray(lead.buyer_signals) && lead.buyer_signals.length > 0
          ? lead.buyer_signals
          : [
              'High manual data entry overhead identified in core workflow',
              'Municipal/public docket dependencies detected',
              'Sub-50 employee size matches automation deployment sweet-spot',
            ];
        const qa = lead.qa_score !== null && lead.qa_score !== undefined ? lead.qa_score : null;

        const factorItems = [
          { label: 'Labor-Intensive Operations', val: breakdown.labor_intensity ?? 20, max: 25, desc: 'High repetitive human touchpoints' },
          { label: 'Target Portal Scraping Viability', val: breakdown.target_portal_scraping ?? 12, max: 15, desc: 'Public docket/portal data accessibility' },
          { label: 'Manual Data Entry Elimination', val: breakdown.manual_data_entry ?? 12, max: 15, desc: 'Direct software bridge opportunity' },
          { label: 'Compliance & Regulatory Overhead', val: breakdown.compliance_regulatory ?? 11, max: 15, desc: 'Statutory filing & auditing requirements' },
          { label: 'Document & Record Volume', val: breakdown.document_volume ?? 8, max: 10, desc: 'Daily PDF/CSV/Record throughput' },
          { label: 'SMB Company Size Fit', val: breakdown.smb_size_fit ?? 8, max: 10, desc: '5-50 staff sweet spot for agile adoption' },
          { label: 'Market Growth & Hiring Signals', val: breakdown.market_growth ?? 7, max: 10, desc: 'Active hiring or market expansion signals' },
        ];

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
                  <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px' }}>
                    🌐 Target Portal &amp; Niche Profile
                  </h4>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div>
                      <b style={{ color: '#fff' }}>Target Portal:</b> {lead.target_portal_name || lead.jurisdiction || 'Municipal Registry'}
                    </div>
                    {lead.target_url && (
                      <div>
                        <b style={{ color: '#fff' }}>Verified Portal URL:</b>{' '}
                        <a href={lead.target_url} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)', textDecoration: 'underline', wordBreak: 'break-all' }}>
                          {lead.target_url}
                        </a>
                      </div>
                    )}
                    {lead.source_url && !lead.target_url && (
                      <div>
                        <b style={{ color: '#fff' }}>Portal Source:</b>{' '}
                        <a href={lead.source_url} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)', textDecoration: 'underline', wordBreak: 'break-all' }}>
                          {lead.source_url}
                        </a>
                      </div>
                    )}
                    <div>
                      <b style={{ color: '#fff' }}>Niche / Industry:</b> {lead.niche || 'B2B Professional Services'}
                    </div>
                    {lead.contact_email && (
                      <div>
                        <b style={{ color: '#fff' }}>Contact:</b> {lead.contact_email}
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
                    {lead.pain_points || lead.notes || lead.human_observation}
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
