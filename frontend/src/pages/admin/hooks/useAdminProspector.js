import { useState, useCallback, useMemo, useEffect } from 'react';
import {
  startProspectorCampaign,
  pauseProspectorCampaign,
  resumeProspectorCampaign,
  triggerProspectorBurst,
  refreshLeadFreshness,
  batchRefreshStaleBacklog,
  fetchCountyOrchestratorStatus,
  advanceCountyOrchestratorCursor,
  setCountyOrchestratorStateFocus,
  triggerScoutDiscovery,
  triggerBatchScout,
  toggleProspector247Mode,
  fetchCandidateEvaluations,
} from '../../../services/api';

/**
 * Custom hook managing 14-Day High-Volume Prospector, National County Orchestrator,
 * and Multi-channel B2B Web Scout actions.
 *
 * @param {Object} options
 * @param {Function} options.resolveToken - Token getter.
 * @param {Function} options.showToast - Toast alert function.
 * @param {Array} options.pipeline - Full leads pipeline for backlog calculation.
 * @param {string} options.searchQuery - Global search query for backlog filtering.
 * @param {Function} options.loadAdminData - Admin data refresher.
 */
export function useAdminProspector({
  resolveToken,
  showToast,
  pipeline = [],
  searchQuery = '',
  loadAdminData,
}) {
  // Campaign & Burst State
  const [prospectorStatus, setProspectorStatus] = useState(null);
  const [prospectorLoading, setProspectorLoading] = useState(false);
  const [freshnessRefreshingLeadId, setFreshnessRefreshingLeadId] = useState(null);
  const [sweepingStaleRecords, setSweepingStaleRecords] = useState(false);
  const [burstLeadCount, setBurstLeadCount] = useState(3);
  const [selectedProspectorChannel, setSelectedProspectorChannel] = useState('ALL');

  // National County Orchestrator State
  const [countyOrchestrator, setCountyOrchestrator] = useState(null);
  const [orchestratorLoading, setOrchestratorLoading] = useState(false);

  // Web Scout State
  const [scoutingInProgress, setScoutingInProgress] = useState(false);
  const [scoutBatchCount, setScoutBatchCount] = useState(1);
  const [selectedScoutChannel, setSelectedScoutChannel] = useState('');
  const [scoutSearchQuery, setScoutSearchQuery] = useState('');

  // Candidate Scope Filter ('STAGED' | 'ALL' | 'OUTREACH_SENT' | 'EVALUATED')
  const [candidateScope, setCandidateScope] = useState('STAGED');
  const [candidateEvaluations, setCandidateEvaluations] = useState([]);
  const [evaluationsLoading, setEvaluationsLoading] = useState(false);

  // Pagination for backlog
  const [backlogPage, setBacklogPage] = useState(1);
  const backlogPageSize = 25;

  // Vetted Backlog & Evaluated Leads (for 14-Day High-Volume Prospector)
  const backlogLeads = useMemo(() => {
    return pipeline.filter((l) => {
      if (l.state === 'ARCHIVED') return false;

      if (candidateScope === 'STAGED') {
        const isBacklog =
          l.outreach_status === 'BACKLOG_VETTED' ||
          l.state === 'REVIEW' ||
          l.state === 'PITCH_PENDING_APPROVAL' ||
          l.state === 'PROSPECTING';
        if (!isBacklog) return false;
      } else if (candidateScope === 'OUTREACH_SENT') {
        if (l.state !== 'OUTREACH_SENT') return false;
      }
      // if candidateScope === 'ALL', include all non-archived evaluated candidates

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
  }, [pipeline, searchQuery, selectedProspectorChannel, candidateScope]);

  // Handlers
  const handleStartProspector = useCallback(async (days = 14, volume = 3) => {
    setProspectorLoading(true);
    showToast(`Starting 14-Day High-Volume Prospecting Campaign (${volume} leads/burst)...`, 'info');
    try {
      const token = await resolveToken();
      const res = await startProspectorCampaign(days, volume, null, token);
      setProspectorStatus(res);
      showToast(res.status_message || '14-Day Campaign started successfully!', 'success');
      if (loadAdminData) await loadAdminData();
    } catch (err) {
      showToast(`Campaign start error: ${err.message}`, 'error');
    } finally {
      setProspectorLoading(false);
    }
  }, [resolveToken, showToast, loadAdminData]);

  const handlePauseProspector = useCallback(async () => {
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
  }, [resolveToken, showToast]);

  const handleResumeProspector = useCallback(async () => {
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
  }, [resolveToken, showToast]);

  const handleToggleProspector247 = useCallback(async () => {
    setProspectorLoading(true);
    const nextState = !prospectorStatus?.run_24_7;
    try {
      const token = await resolveToken();
      const res = await toggleProspector247Mode(nextState, token);
      if (res?.status) {
        setProspectorStatus(res.status);
      } else {
        setProspectorStatus((prev) => ({ ...prev, run_24_7: nextState }));
      }
      showToast(
        nextState
          ? '⚡ 24/7 All-Day Prospecting Activated: Scout will hunt round-the-clock without office hours restrictions!'
          : '🌙 Office Hours Mode: Scout will prospect during 8:00 AM – 5:00 PM CST.',
        'success'
      );
    } catch (err) {
      showToast(`Failed to toggle 24/7 mode: ${err.message}`, 'error');
    } finally {
      setProspectorLoading(false);
    }
  }, [prospectorStatus, resolveToken, showToast]);

  const handleTriggerBurst = useCallback(async (count = 3, channel = null) => {
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
      if (loadAdminData) await loadAdminData();
    } catch (err) {
      showToast(`Burst error: ${err.message}`, 'error');
    } finally {
      setProspectorLoading(false);
    }
  }, [resolveToken, showToast, loadAdminData]);

  const handleRefreshFreshness = useCallback(async (leadId) => {
    setFreshnessRefreshingLeadId(leadId);
    showToast(`Pulling live same-day filings for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      const res = await refreshLeadFreshness(leadId, token);
      showToast(res.message || 'Records refreshed with today’s filings!', 'success');
      if (loadAdminData) await loadAdminData();
    } catch (err) {
      showToast(`Freshness refresh error: ${err.message}`, 'error');
    } finally {
      setFreshnessRefreshingLeadId(null);
    }
  }, [resolveToken, showToast, loadAdminData]);

  const handleBatchRefreshStale = useCallback(async () => {
    setSweepingStaleRecords(true);
    showToast('Sweeping all backlog leads for same-day freshness...', 'info');
    try {
      const token = await resolveToken();
      const res = await batchRefreshStaleBacklog(token);
      showToast(res.message || 'Freshness sweep complete!', 'success');
      if (loadAdminData) await loadAdminData();
    } catch (err) {
      showToast(`Sweep error: ${err.message}`, 'error');
    } finally {
      setSweepingStaleRecords(false);
    }
  }, [resolveToken, showToast, loadAdminData]);

  const handleAdvanceCountyCursor = useCallback(async () => {
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
  }, [resolveToken, showToast]);

  const handleSetStateFocus = useCallback(async (stateCode) => {
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
  }, [resolveToken, showToast]);

  const handleTriggerWebScout = useCallback(
    async (overrideChannel = null, overrideQuery = null, overrideBatch = null) => {
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
            showToast(
              `🎯 Batch complete! Successfully scouted & qualified ${res.count_discovered}/${countToScout} leads!`,
              'success'
            );
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
        if (loadAdminData) await loadAdminData();
      } catch (err) {
        showToast(`Scout trigger error: ${err.message}`, 'error');
      } finally {
        setScoutingInProgress(false);
      }
    },
    [
      resolveToken,
      showToast,
      selectedScoutChannel,
      scoutSearchQuery,
      scoutBatchCount,
      loadAdminData,
    ]
  );

  const loadCandidateEvaluations = useCallback(async () => {
    setEvaluationsLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchCandidateEvaluations(100, selectedProspectorChannel, null, token);
      if (res && res.evaluations) {
        setCandidateEvaluations(res.evaluations);
      }
    } catch (err) {
      console.warn('Could not load candidate evaluations:', err);
    } finally {
      setEvaluationsLoading(false);
    }
  }, [resolveToken, selectedProspectorChannel]);

  useEffect(() => {
    if (candidateScope === 'EVALUATED') {
      loadCandidateEvaluations();
    }
  }, [candidateScope, selectedProspectorChannel, loadCandidateEvaluations]);

  return {
    prospectorStatus,
    setProspectorStatus,
    prospectorLoading,
    burstLeadCount,
    setBurstLeadCount,
    selectedProspectorChannel,
    setSelectedProspectorChannel,
    freshnessRefreshingLeadId,
    sweepingStaleRecords,
    countyOrchestrator,
    setCountyOrchestrator,
    orchestratorLoading,
    scoutingInProgress,
    scoutBatchCount,
    setScoutBatchCount,
    selectedScoutChannel,
    setSelectedScoutChannel,
    scoutSearchQuery,
    setScoutSearchQuery,
    backlogPage,
    setBacklogPage,
    backlogPageSize,
    backlogLeads,
    candidateScope,
    setCandidateScope,
    candidateEvaluations,
    evaluationsLoading,
    loadCandidateEvaluations,
    handleStartProspector,
    handlePauseProspector,
    handleResumeProspector,
    handleToggleProspector247,
    handleTriggerBurst,
    handleRefreshFreshness,
    handleBatchRefreshStale,
    handleAdvanceCountyCursor,
    handleSetStateFocus,
    handleTriggerWebScout,
  };
}

export default useAdminProspector;
