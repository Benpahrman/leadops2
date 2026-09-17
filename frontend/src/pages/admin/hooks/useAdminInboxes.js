import { useState, useCallback, useEffect } from 'react';
import {
  fetchAdminInboxes,
  upsertAdminInbox,
  testAdminInbox,
  deleteAdminInbox,
  fetchInboundStream,
  fetchWarmupTargets,
  addWarmupTarget,
  deleteWarmupTarget,
  fetchWarmupActivity,
  startWarmupCycle,
  dispatchWarmupBatch,
  runWarmupMonitoring,
  triggerOutreachFlush,
  fetchMicrosoftOAuthStatus,
  fetchMicrosoftOAuthAuthorizeUrl,
  disconnectMicrosoftOAuth,
  fetchDeliverabilityStatus,
  runComprehensiveDeliverabilityAudit,
  checkContentSpamScore,
} from '../../../services/api';

/**
 * Custom hook managing Email Inboxes, Peer Warmup Network, Deliverability Suite, and OAuth.
 *
 * @param {Object} options
 * @param {Function} options.resolveToken - Async token retriever.
 * @param {Function} options.showToast - Toast notification dispatcher.
 * @param {Function} options.setConfirmModal - Modal confirmation trigger.
 * @param {Function} [options.loadAdminData] - Refreshes overall admin pipeline.
 * @param {Object} [options.user] - Active Clerk user (for OAuth email fallback).
 */
export function useAdminInboxes({ resolveToken, showToast, setConfirmModal, loadAdminData, user }) {
  // Inboxes & Fleet State
  const [inboxes, setInboxes] = useState([]);
  const [inboxesLoading, setInboxesLoading] = useState(false);
  const [fleetSummary, setFleetSummary] = useState(null);
  const [warmupCycle, setWarmupCycle] = useState(null);
  const [inboxSubTab, setInboxSubTab] = useState('fleet'); // 'fleet' | 'inbound' | 'receivers' | 'activity'
  const [testingInboxId, setTestingInboxId] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [deletingInboxId, setDeletingInboxId] = useState(null);
  const [flushingQueue, setFlushingQueue] = useState(false);

  // Modal form states
  const [showAddInboxModal, setShowAddInboxModal] = useState(false);
  const [inboxFormData, setInboxFormData] = useState({
    inbox_id: '',
    email_address: '',
    password: '',
    from_name: 'Alex | OmniLeadFeeder',
    provider: 'olfmailer',
    daily_limit: 5,
  });

  // Warmup state
  const [startingWarmup, setStartingWarmup] = useState(false);
  const [dispatchingWarmup, setDispatchingWarmup] = useState(false);
  const [monitoringWarmup, setMonitoringWarmup] = useState(false);
  const [warmupTargets, setWarmupTargets] = useState([]);
  const [warmupTargetsLoading, setWarmupTargetsLoading] = useState(false);
  const [warmupActivity, setWarmupActivity] = useState(null);
  const [warmupActivityLoading, setWarmupActivityLoading] = useState(false);
  const [showAddReceiverModal, setShowAddReceiverModal] = useState(false);
  const [deletingReceiverId, setDeletingReceiverId] = useState(null);
  const [receiverFormData, setReceiverFormData] = useState({
    email: '',
    name: '',
    password: '',
    provider: 'gmail',
    is_monitored: true,
  });

  // Inbound Prospect Stream
  const [inboundStream, setInboundStream] = useState(null);
  const [inboundLoading, setInboundLoading] = useState(false);

  // Deliverability Suite State
  const [deliverabilityReport, setDeliverabilityReport] = useState(null);
  const [auditingDeliverability, setAuditingDeliverability] = useState(false);
  const [selectedSpamReport, setSelectedSpamReport] = useState(null);
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

  // Loaders
  const loadInboxes = useCallback(async () => {
    setInboxesLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchAdminInboxes(token);
      if (res) {
        if (res.inboxes) setInboxes(res.inboxes);
        if (res.fleet_summary) setFleetSummary(res.fleet_summary);
        if (res.warmup_cycle) setWarmupCycle(res.warmup_cycle);
      }
    } catch (err) {
      console.warn('Could not load inboxes:', err);
    } finally {
      setInboxesLoading(false);
    }
  }, [resolveToken]);

  const loadInboundStream = useCallback(async () => {
    setInboundLoading(true);
    try {
      const token = await resolveToken();
      const res = await fetchInboundStream(50, token);
      if (res && res.inbound_events) {
        setInboundStream(res.inbound_events);
      }
    } catch (err) {
      console.warn('Could not load inbound stream:', err);
    } finally {
      setInboundLoading(false);
    }
  }, [resolveToken]);

  const loadWarmupTargets = useCallback(async () => {
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
  }, [resolveToken]);

  const loadWarmupActivity = useCallback(async () => {
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
  }, [resolveToken]);

  const loadDeliverabilityStatus = useCallback(async () => {
    try {
      const token = await resolveToken();
      const res = await fetchDeliverabilityStatus(token);
      if (res && res.report) {
        setDeliverabilityReport(res.report);
      }
    } catch (err) {
      console.warn('Could not load deliverability status:', err);
    }
  }, [resolveToken]);

  const loadMsOAuthStatus = useCallback(async () => {
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
  }, [resolveToken]);

  // Actions
  const handleConnectMicrosoftOAuth = useCallback(async () => {
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
  }, [resolveToken, showToast]);

  const handleDisconnectMicrosoftOAuth = useCallback(async () => {
    try {
      const token = await resolveToken();
      await disconnectMicrosoftOAuth(token);
      showToast('Outlook account disconnected successfully.', 'info');
      await loadMsOAuthStatus();
      await loadInboxes();
    } catch (err) {
      showToast(`Disconnect error: ${err.message}`, 'error');
    }
  }, [resolveToken, showToast, loadMsOAuthStatus, loadInboxes]);

  const handleStartWarmup = useCallback(async () => {
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
  }, [resolveToken, showToast, loadInboxes]);

  const handleDispatchWarmupBatch = useCallback(async (count = 3) => {
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
  }, [resolveToken, showToast, loadInboxes, inboxSubTab, loadWarmupActivity]);

  const handleRunWarmupMonitoring = useCallback(async () => {
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
  }, [resolveToken, showToast, inboxSubTab, loadWarmupTargets]);

  const handleSaveReceiver = useCallback(async () => {
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
  }, [receiverFormData, resolveToken, showToast, loadWarmupTargets]);

  const handleDeleteReceiver = useCallback(async (targetId, email) => {
    setConfirmModal({
      isOpen: true,
      title: 'Remove Warm Receiver',
      message: `Remove '${email}' from the peer warmup network?`,
      confirmText: 'Remove Receiver',
      cancelText: 'Cancel',
      isDestructive: true,
      onConfirm: async () => {
        try {
          setDeletingReceiverId(targetId);
          const token = await resolveToken();
          await deleteWarmupTarget(targetId, token);
          showToast(`Warm receiver '${email}' removed.`, 'success');
          await loadWarmupTargets();
        } catch (err) {
          showToast(`Failed to remove warm receiver: ${err.message}`, 'error');
        } finally {
          setDeletingReceiverId(null);
        }
      },
    });
  }, [setConfirmModal, resolveToken, showToast, loadWarmupTargets]);

  const handleRunDeliverabilityAudit = useCallback(async () => {
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
  }, [resolveToken, showToast, testCopySubject, testCopyBody, loadDeliverabilityStatus]);

  const handleAuditTestCopy = useCallback(async () => {
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
  }, [testCopyBody, testCopySubject, resolveToken, showToast]);

  const handleTestInbox = useCallback(async (inboxId) => {
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
  }, [resolveToken, showToast]);

  const handleFlushOutreachQueue = useCallback(async () => {
    setFlushingQueue(true);
    showToast('⚡ Flushing outreach queue across all active olfmailer.com inboxes...', 'info');
    try {
      const token = await resolveToken();
      const res = await triggerOutreachFlush(token);
      showToast(res.message || 'Outreach dispatch worker triggered with anti-spam jitter!', 'success');
      await loadInboxes();
      if (loadAdminData) {
        await loadAdminData();
      }
    } catch (err) {
      showToast(`Flush queue failed: ${err.message}`, 'error');
    } finally {
      setFlushingQueue(false);
    }
  }, [resolveToken, showToast, loadInboxes, loadAdminData]);

  const handleSaveInbox = useCallback(async () => {
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
  }, [inboxFormData, resolveToken, showToast, loadInboxes, handleTestInbox]);

  const handleDeleteInbox = useCallback(async (inboxId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Remove Inbox Account',
      message: `Are you sure you want to remove inbox '${inboxId}' from active rotation?`,
      confirmText: 'Remove Inbox',
      cancelText: 'Cancel',
      isDestructive: true,
      onConfirm: async () => {
        try {
          setDeletingInboxId(inboxId);
          const token = await resolveToken();
          await deleteAdminInbox(inboxId, token);
          showToast(`Inbox '${inboxId}' removed.`, 'success');
          await loadInboxes();
        } catch (err) {
          showToast(`Failed to delete inbox: ${err.message}`, 'error');
        } finally {
          setDeletingInboxId(null);
        }
      },
    });
  }, [setConfirmModal, resolveToken, showToast, loadInboxes]);

  const handleToggleInboxActive = useCallback(async (inbox) => {
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
  }, [resolveToken, showToast, loadInboxes]);

  // OAuth redirect handler
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
  }, [showToast, user, loadMsOAuthStatus]);

  return {
    inboxes,
    setInboxes,
    inboxesLoading,
    fleetSummary,
    warmupCycle,
    inboxSubTab,
    setInboxSubTab,
    testingInboxId,
    testResults,
    deletingInboxId,
    flushingQueue,
    showAddInboxModal,
    setShowAddInboxModal,
    inboxFormData,
    setInboxFormData,
    startingWarmup,
    dispatchingWarmup,
    monitoringWarmup,
    warmupTargets,
    warmupTargetsLoading,
    warmupActivity,
    warmupActivityLoading,
    showAddReceiverModal,
    setShowAddReceiverModal,
    deletingReceiverId,
    receiverFormData,
    setReceiverFormData,
    inboundStream,
    inboundLoading,
    deliverabilityReport,
    auditingDeliverability,
    selectedSpamReport,
    setSelectedSpamReport,
    testCopySubject,
    setTestCopySubject,
    testCopyBody,
    setTestCopyBody,
    contentAuditResult,
    auditingContent,
    msOAuthStatus,
    msOAuthLoading,
    msOAuthConnecting,
    loadInboxes,
    loadInboundStream,
    loadWarmupTargets,
    loadWarmupActivity,
    loadDeliverabilityStatus,
    loadMsOAuthStatus,
    handleConnectMicrosoftOAuth,
    handleDisconnectMicrosoftOAuth,
    handleStartWarmup,
    handleDispatchWarmupBatch,
    handleRunWarmupMonitoring,
    handleSaveReceiver,
    handleDeleteReceiver,
    handleRunDeliverabilityAudit,
    handleAuditTestCopy,
    handleTestInbox,
    handleFlushOutreachQueue,
    handleSaveInbox,
    handleDeleteInbox,
    handleToggleInboxActive,
  };
}

export default useAdminInboxes;
