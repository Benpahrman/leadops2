import { useState, useCallback, useMemo } from 'react';
import {
  fetchAdminPipeline,
  fetchAdminMetrics,
  fetchActiveBuilds,
  fetchScoutStatus,
  fetchAutoOutreachStatus,
  fetchAdminInboxes,
  fetchProspectorStatus,
  fetchCountyOrchestratorStatus,
  fetchArchivedLeads,
  advanceLeadState,
  batchApprovePendingPitches,
  toggleAutoOutreach,
  deepEnrichLead,
  cancelAutoOutreach,
  enrichLeadContact,
  batchEnrichArchivedLeads,
  triggerSwarmBuild,
  purgeAllData,
  deleteLead,
  toggleEmergencyStop,
  toggleScout247Mode,
} from '../../../services/api';

/**
 * Custom hook managing core pipeline state, deal metrics, lifecycle progressions,
 * contact enrichments, emergency stop, and data purging.
 *
 * @param {Object} options
 * @param {Function} options.resolveToken - Token resolver.
 * @param {Function} options.showToast - Toast alert function.
 * @param {Function} options.setConfirmModal - Confirmation modal trigger.
 * @param {Function} [options.closeConfirmModal] - Confirmation modal closer.
 * @param {Function} [options.onAdminDataLoaded] - Callback with raw responses when loadAdminData completes.
 * @param {Object} [options.scoreModalState] - Score modal state for deep enrich sync.
 * @param {Function} [options.setScoreModalState] - Score modal updater.
 */
export function useAdminPipeline({
  resolveToken,
  showToast,
  setConfirmModal,
  closeConfirmModal,
  onAdminDataLoaded,
  scoreModalState,
  setScoreModalState,
}) {
  // Core Pipeline & Metric State
  const [pipeline, setPipeline] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeBuilds, setActiveBuilds] = useState([]);
  const [scoutStatus, setScoutStatus] = useState(null);
  const [autoOutreachStatus, setAutoOutreachStatus] = useState(null);
  const [autoOutreachLoading, setAutoOutreachLoading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState({});
  const [batchApproving, setBatchApproving] = useState(false);

  // Archived Leads State
  const [archivedLeads, setArchivedLeads] = useState([]);
  const [archivedLoading, setArchivedLoading] = useState(false);
  const [enrichingLeadId, setEnrichingLeadId] = useState(null);
  const [batchEnriching, setBatchEnriching] = useState(false);

  // Filtering & Pagination State
  const [searchQuery, setSearchQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('ALL');
  const [paymentFilter, setPaymentFilter] = useState('ALL');
  const [scoreFilter, setScoreFilter] = useState('ALL');
  const [channelFilter, setChannelFilter] = useState('ALL');
  const [dealsPage, setDealsPage] = useState(1);
  const [dealsPageSize, setDealsPageSize] = useState(25);

  // Load Admin Data (all core telemetry)
  const loadAdminData = useCallback(async () => {
    setLoading(true);
    try {
      const token = await resolveToken();
      const [
        pipeData,
        metricData,
        buildsData,
        scoutData,
        autoData,
        inboxesData,
        prospectorData,
        countyData,
      ] = await Promise.allSettled([
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

      // Delegate extra telemetry (inboxes, prospector, county) to listener callback
      if (onAdminDataLoaded) {
        onAdminDataLoaded({
          inboxesData: inboxesData.status === 'fulfilled' ? inboxesData.value : null,
          prospectorData: prospectorData.status === 'fulfilled' ? prospectorData.value : null,
          countyData: countyData.status === 'fulfilled' ? countyData.value : null,
        });
      }
    } catch (err) {
      console.warn('Admin load note:', err);
      showToast(`Admin load: ${err.message}`, 'info');
    } finally {
      setLoading(false);
    }
  }, [resolveToken, showToast, onAdminDataLoaded]);

  const loadArchivedLeads = useCallback(async () => {
    setArchivedLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchArchivedLeads(token);
      if (res && res.leads) {
        setArchivedLeads(res.leads);
      }
    } catch (err) {
      console.warn('Could not load archived leads:', err);
    } finally {
      setArchivedLoading(false);
    }
  }, [resolveToken]);

  // Lead Lifecycle Actions
  const handleAdvance = useCallback(async (leadId) => {
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
  }, [resolveToken, showToast, loadAdminData]);

  const handleBatchApprove = useCallback(async () => {
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
      showToast(
        res.message || `Batch approval complete: ${res.approved_count} dispatched, ${res.skipped_count} skipped.`,
        'success'
      );
      await loadAdminData();
    } catch (err) {
      showToast(`Batch approval failed: ${err.message}`, 'error');
    } finally {
      setBatchApproving(false);
    }
  }, [pipeline, resolveToken, showToast, loadAdminData]);

  const handleToggleAutoOutreach = useCallback(async () => {
    const current = autoOutreachStatus?.enabled ?? true;
    const nextState = !current;
    setAutoOutreachLoading(true);
    try {
      const token = await resolveToken();
      await toggleAutoOutreach(nextState, token);
      showToast(
        `Auto-Outreach 3-minute grace period ${nextState ? 'ENABLED (with anti-spam jitter)' : 'PAUSED'}.`,
        'success'
      );
      await loadAdminData();
    } catch (err) {
      showToast(`Failed to toggle auto-outreach: ${err.message}`, 'error');
    } finally {
      setAutoOutreachLoading(false);
    }
  }, [autoOutreachStatus, resolveToken, showToast, loadAdminData]);

  const handleToggleScout247 = useCallback(async () => {
    try {
      const token = await resolveToken();
      const nextState = !(scoutStatus?.run_24_7 ?? true);
      const res = await toggleScout247Mode(nextState, token);
      if (res?.status) {
        setScoutStatus(res.status);
      } else {
        setScoutStatus((prev) => ({ ...prev, run_24_7: nextState }));
      }
      showToast(
        nextState
          ? '⚡ 24/7 All-Day Scouting Activated: Scout is scouting prospects round-the-clock without work hours restrictions!'
          : '🌙 Office Hours Mode: Scout will respect standard 8:00 AM – 5:00 PM CST hours.',
        'success'
      );
    } catch (err) {
      showToast(`Scout 24/7 toggle error: ${err.message}`, 'error');
    }
  }, [scoutStatus, resolveToken, showToast]);

  const handleDeepEnrichLead = useCallback(async (leadId) => {
    setEnrichingLeadId(leadId);
    showToast(`Deep-enriching decision maker intelligence for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      const res = await deepEnrichLead(leadId, token);
      showToast(res.message || 'Lead successfully enriched!', 'success');
      await loadAdminData();

      if (scoreModalState?.open && scoreModalState.lead?.lead_id === leadId && setScoreModalState) {
        setScoreModalState((prev) => ({
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
  }, [resolveToken, showToast, loadAdminData, scoreModalState, setScoreModalState]);

  const handleCancelOutreach = useCallback(async (leadId, companyName) => {
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
  }, [resolveToken, showToast, loadAdminData, loadArchivedLeads]);

  const handleEnrichLead = useCallback(async (leadId, companyName) => {
    setEnrichingLeadId(leadId);
    showToast(`🤖 Contact Enricher Agent researching alternatives for ${companyName || leadId}...`, 'info');
    try {
      const token = await resolveToken();
      const res = await enrichLeadContact(leadId, token);
      if (res.recovered) {
        showToast(
          `🎉 Contact Recovered! ${res.company_name} updated to ${res.new_email} and moved to Review stage!`,
          'success'
        );
        await loadAdminData();
        await loadArchivedLeads();
      } else {
        showToast(
          `⚠️ Research complete for ${companyName || leadId}: ${res.reason || 'No deliverable contact found'}. Lead remains archived.`,
          'warning'
        );
        await loadArchivedLeads();
      }
    } catch (err) {
      showToast(`Contact enrichment error: ${err.message}`, 'error');
    } finally {
      setEnrichingLeadId(null);
    }
  }, [resolveToken, showToast, loadAdminData, loadArchivedLeads]);

  const handleBatchEnrichArchived = useCallback(async () => {
    setBatchEnriching(true);
    showToast('🤖 Triggering Contact Enricher Researcher Agent across all archived leads...', 'info');
    try {
      const token = await resolveToken();
      const res = await batchEnrichArchivedLeads(token);
      showToast(
        res.message || `Processed ${res.total_archived} archived leads, recovering ${res.recovered_count}.`,
        'success'
      );
      await loadAdminData();
      await loadArchivedLeads();
    } catch (err) {
      showToast(`Batch recovery error: ${err.message}`, 'error');
    } finally {
      setBatchEnriching(false);
    }
  }, [resolveToken, showToast, loadAdminData, loadArchivedLeads]);

  const handleTriggerSwarm = useCallback(async (leadId) => {
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
  }, [resolveToken, showToast, loadAdminData]);

  const handlePurgeAllData = useCallback(() => {
    setConfirmModal({
      isOpen: true,
      title: 'Reset & Purge All Test Records',
      message:
        'This will permanently remove all test leads, sandboxes, and customer records, resetting the database to a clean 0-lead state for real production customers.',
      confirmText: 'Purge Database',
      cancelText: 'Cancel',
      isDestructive: true,
      requireMatch: 'PURGE',
      hasInput: false,
      onConfirm: async () => {
        if (closeConfirmModal) closeConfirmModal();
        showToast('Purging all test data and resetting pipeline...', 'info');
        try {
          const token = await resolveToken();
          const res = await purgeAllData(token);
          showToast(res.message || 'All test records successfully purged!', 'success');
          await loadAdminData();
        } catch (err) {
          showToast(`Purge failed: ${err.message}`, 'error');
        }
      },
    });
  }, [setConfirmModal, closeConfirmModal, showToast, resolveToken, loadAdminData]);

  const handleDeleteLead = useCallback((leadId, companyName) => {
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
        if (closeConfirmModal) closeConfirmModal();
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
  }, [setConfirmModal, closeConfirmModal, showToast, resolveToken, loadAdminData]);

  const handleToggleEmergencyStop = useCallback(() => {
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
        if (closeConfirmModal) closeConfirmModal();
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
  }, [metrics?.emergency_stop_active, setConfirmModal, closeConfirmModal, resolveToken, showToast, loadAdminData]);

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

  // Financial calculations
  const depositTotal = useMemo(() => {
    return pipeline
      .filter((l) => l.deposit_paid)
      .reduce((sum, l) => sum + (l.deposit_amount_usd || 99.0), 0);
  }, [pipeline]);

  const releasedTotal = useMemo(() => {
    return pipeline
      .filter((l) => l.final_paid)
      .reduce((sum, l) => sum + (l.final_amount_usd || 151.0), 0);
  }, [pipeline]);

  const activeMrr = useMemo(() => {
    return pipeline
      .filter((l) => l.subscription_active)
      .reduce((sum, l) => sum + (l.tier === 'STARTER' ? 150 : l.tier === 'ENTERPRISE' ? 590 : 250), 0);
  }, [pipeline]);

  return {
    pipeline,
    setPipeline,
    metrics,
    setMetrics,
    loading,
    activeBuilds,
    scoutStatus,
    autoOutreachStatus,
    autoOutreachLoading,
    actionInProgress,
    setActionInProgress,
    batchApproving,
    archivedLeads,
    setArchivedLeads,
    archivedLoading,
    enrichingLeadId,
    batchEnriching,
    searchQuery,
    setSearchQuery,
    stateFilter,
    setStateFilter,
    paymentFilter,
    setPaymentFilter,
    scoreFilter,
    setScoreFilter,
    channelFilter,
    setChannelFilter,
    dealsPage,
    setDealsPage,
    dealsPageSize,
    setDealsPageSize,
    filteredLeads,
    depositTotal,
    releasedTotal,
    activeMrr,
    loadAdminData,
    loadArchivedLeads,
    handleAdvance,
    handleBatchApprove,
    handleToggleAutoOutreach,
    handleToggleScout247,
    handleDeepEnrichLead,
    handleCancelOutreach,
    handleEnrichLead,
    handleBatchEnrichArchived,
    handleTriggerSwarm,
    handlePurgeAllData,
    handleDeleteLead,
    handleToggleEmergencyStop,
  };
}

export default useAdminPipeline;
