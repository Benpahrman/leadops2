import React, { useEffect, useState, useMemo } from 'react';
import { useAuth, useUser, SignIn } from '@clerk/clerk-react';
import { resolveAdminAuth } from '../services/api';
import { useToast } from '../context/ToastContext';
import ConfirmModal from '../components/common/ConfirmModal';
import CommandPalette from '../components/common/CommandPalette';

// Domain Tab Components
import ProspectorTab from './admin/tabs/ProspectorTab';
import DealsTab from './admin/tabs/DealsTab';
import KanbanTab from './admin/tabs/KanbanTab';
import ArchivedLeadsTab from './admin/tabs/ArchivedLeadsTab';
import SwarmTab from './admin/tabs/SwarmTab';
import AccountingTab from './admin/tabs/AccountingTab';
import ScrapersTab from './admin/tabs/ScrapersTab';
import DailyDeliveryTab from './admin/tabs/DailyDeliveryTab';
import InboxesAndWarmupTab from './admin/tabs/InboxesAndWarmupTab';

// Modal Dialogs
import {
  CodeViewerModal,
  DatasetRecordsModal,
  AuditTrailModal,
  QAOverrideModal,
  SwarmProgressModal,
  LeadScoringModal,
  SpamReportModal,
} from './admin/modals';

// Custom Domain Hooks
import {
  useAdminPipeline,
  useAdminProspector,
  useAdminInboxes,
  useAdminScrapers,
  useAdminModals,
} from './admin/hooks';

// Modular Admin Components
import { AdminHeader, AdminStatsBar, DiscoveryBadge } from './admin/components';

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

  // Navigation tab state
  const [activeTab, setActiveTab] = useState(() => getInitialParam('tab', 'prospector'));

  // Discovery Badge Renderer
  const renderDiscoveryBadge = (channel, filingCaseNumber) => (
    <DiscoveryBadge channel={channel} filingCaseNumber={filingCaseNumber} />
  );

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

  // 1. Modals Hook
  const modals = useAdminModals({
    resolveToken,
    showToast,
    pipeline: [],
    loadAdminData: null,
  });

  // 2. Inboxes Hook
  const inboxes = useAdminInboxes({
    resolveToken,
    showToast,
    setConfirmModal: modals.setConfirmModal,
    loadAdminData: null,
    user,
  });

  // 3. Pipeline Hook
  const pipeline = useAdminPipeline({
    resolveToken,
    showToast,
    setConfirmModal: modals.setConfirmModal,
    closeConfirmModal: modals.closeConfirmModal,
    onAdminDataLoaded: ({ inboxesData, prospectorData, countyData }) => {
      if (inboxesData?.inboxes) inboxes.setInboxes(inboxesData.inboxes);
      if (inboxesData?.fleet_summary) inboxes.setFleetSummary(inboxesData.fleet_summary);
      if (inboxesData?.warmup_cycle) inboxes.setWarmupCycle(inboxesData.warmup_cycle);
      if (prospectorData) prospector.setProspectorStatus(prospectorData);
      if (countyData?.ok) prospector.setCountyOrchestrator(countyData);
    },
    scoreModalState: modals.scoreModal,
    setScoreModalState: modals.setScoreModal,
  });

  // 4. Prospector Hook
  const prospector = useAdminProspector({
    resolveToken,
    showToast,
    pipeline: pipeline.pipeline,
    searchQuery: pipeline.searchQuery,
    loadAdminData: pipeline.loadAdminData,
  });

  // 5. Scrapers Hook
  const scrapers = useAdminScrapers({
    resolveToken,
    showToast,
    setActionInProgress: pipeline.setActionInProgress,
  });

  // Polling loop for active admin users
  useEffect(() => {
    if (isSignedIn || masterAuth) {
      pipeline.loadAdminData();
      inboxes.loadInboxes();
      const interval = setInterval(pipeline.loadAdminData, 20000);
      return () => clearInterval(interval);
    }
  }, [isSignedIn, masterAuth]);

  // Load Scrapers / Inboxes / Archived when tab changes
  useEffect(() => {
    if (activeTab === 'scrapers' && scrapers.scrapers.length === 0) {
      scrapers.loadScrapers();
    } else if (activeTab === 'daily' && scrapers.dailyGrid.length === 0) {
      scrapers.loadDailyGrid();
    } else if (activeTab === 'inboxes') {
      inboxes.loadInboxes();
      inboxes.loadMsOAuthStatus();
    } else if (activeTab === 'archived') {
      pipeline.loadArchivedLeads();
    }
  }, [activeTab]);

  // Sync tab & filters to URL query string
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const params = new URLSearchParams(window.location.search);
      params.set('tab', activeTab);
      if (pipeline.searchQuery.trim()) params.set('q', pipeline.searchQuery.trim()); else params.delete('q');
      if (pipeline.stateFilter !== 'ALL') params.set('state', pipeline.stateFilter); else params.delete('state');
      if (pipeline.paymentFilter !== 'ALL') params.set('payment', pipeline.paymentFilter); else params.delete('payment');
      if (pipeline.scoreFilter !== 'ALL') params.set('score', pipeline.scoreFilter); else params.delete('score');

      const newUrl = `${window.location.pathname}?${params.toString()}`;
      window.history.replaceState(null, '', newUrl);
    } catch (e) {
      console.warn('URL sync note:', e);
    }
  }, [activeTab, pipeline.searchQuery, pipeline.stateFilter, pipeline.paymentFilter, pipeline.scoreFilter]);

  // Command Palette Actions
  const commandPaletteActions = useMemo(() => [
    {
      id: 'act-refresh',
      label: 'Refresh Pipeline & Telemetry',
      icon: '🔄',
      category: 'Actions',
      run: () => pipeline.loadAdminData(),
    },
    {
      id: 'act-scout',
      label: 'Trigger Scout Prospecting Cycle',
      icon: '🔎',
      category: 'Actions',
      run: () => prospector.handleTriggerWebScout(),
    },
    {
      id: 'act-auto-outreach',
      label: `Toggle Auto-Outreach (${pipeline.autoOutreachStatus?.enabled ? 'Pause' : 'Enable'})`,
      icon: '⏱️',
      category: 'Actions',
      run: () => pipeline.handleToggleAutoOutreach(),
    },
    {
      id: 'act-emergency',
      label: pipeline.metrics?.emergency_stop_active ? 'Resume Normal Operations' : 'Activate Emergency Stop',
      icon: '🛑',
      category: 'Actions',
      run: () => pipeline.handleToggleEmergencyStop(),
    },
    {
      id: 'act-purge',
      label: 'Purge All Test Records',
      icon: '🧹',
      category: 'Danger Zone',
      run: () => pipeline.handlePurgeAllData(),
    },
  ], [pipeline, prospector]);

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
              Autonomous 7-agent pipeline, client sandbox monitor, and deployment engine. Authenticate with an authorized admin account.
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
        <AdminHeader
          pipeline={pipeline}
          prospector={prospector}
          user={user}
          masterAuth={masterAuth}
          isSignedIn={isSignedIn}
          setMasterAuth={setMasterAuth}
          setCommandPaletteOpen={setCommandPaletteOpen}
        />

        {/* Top Summary Stats Bar - 5 Color-Coded Live KPIs */}
        <AdminStatsBar pipeline={pipeline} inboxes={inboxes} />

        {/* Tab Navigation */}
        <div className="admin-tabs-nav" style={{ marginBottom: '20px' }}>
          <button
            className={`admin-tab-btn ${activeTab === 'prospector' ? 'active' : ''}`}
            onClick={() => setActiveTab('prospector')}
          >
            🗺️ 14-Day Backlog &amp; Swarm ({prospector.backlogLeads.length})
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'deals' ? 'active' : ''}`}
            onClick={() => setActiveTab('deals')}
          >
            🚀 Bespoke Deals &amp; Sandboxes ({pipeline.filteredLeads.length})
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
            🗄️ Archived Vault ({pipeline.archivedLeads.length})
          </button>
          <button
            className={`admin-tab-btn ${activeTab === 'swarm' ? 'active' : ''}`}
            onClick={() => setActiveTab('swarm')}
          >
            🤖 Autonomous Swarm Monitor ({pipeline.activeBuilds.length} Active)
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
            📬 Email Inboxes ({inboxes.inboxes.length})
          </button>
        </div>

        {/* TAB 0: 14-DAY HIGH-VOLUME PROSPECTOR & VETTED BACKLOG */}
        {activeTab === 'prospector' && (
          <ProspectorTab
            countyOrchestrator={prospector.countyOrchestrator}
            orchestratorLoading={prospector.orchestratorLoading}
            handleSetStateFocus={prospector.handleSetStateFocus}
            handleAdvanceCountyCursor={prospector.handleAdvanceCountyCursor}
            prospectorStatus={prospector.prospectorStatus}
            prospectorLoading={prospector.prospectorLoading}
            handlePauseProspector={prospector.handlePauseProspector}
            handleResumeProspector={prospector.handleResumeProspector}
            handleStartProspector={prospector.handleStartProspector}
            handleToggleProspector247={prospector.handleToggleProspector247}
            burstLeadCount={prospector.burstLeadCount}
            setBurstLeadCount={prospector.setBurstLeadCount}
            selectedProspectorChannel={prospector.selectedProspectorChannel}
            setSelectedProspectorChannel={prospector.setSelectedProspectorChannel}
            handleTriggerBurst={prospector.handleTriggerBurst}
            handleBatchRefreshStale={prospector.handleBatchRefreshStale}
            sweepingStaleRecords={prospector.sweepingStaleRecords}
            pipeline={pipeline.pipeline}
            backlogLeads={prospector.backlogLeads}
            searchQuery={pipeline.searchQuery}
            setSearchQuery={pipeline.setSearchQuery}
            backlogPage={prospector.backlogPage}
            setBacklogPage={prospector.setBacklogPage}
            backlogPageSize={prospector.backlogPageSize}
            freshnessRefreshingLeadId={prospector.freshnessRefreshingLeadId}
            renderDiscoveryBadge={renderDiscoveryBadge}
            handleRefreshFreshness={prospector.handleRefreshFreshness}
            setScoreModal={modals.setScoreModal}
            handleAdvance={pipeline.handleAdvance}
            actionInProgress={pipeline.actionInProgress}
          />
        )}

        {/* TAB 1: BESPOKE ACTIVE DEALS & VERIFIED WORKSPACES */}
        {activeTab === 'deals' && (
          <DealsTab
            pipeline={pipeline.pipeline}
            filteredLeads={pipeline.filteredLeads}
            searchQuery={pipeline.searchQuery}
            setSearchQuery={pipeline.setSearchQuery}
            stateFilter={pipeline.stateFilter}
            setStateFilter={pipeline.setStateFilter}
            paymentFilter={pipeline.paymentFilter}
            setPaymentFilter={pipeline.setPaymentFilter}
            scoreFilter={pipeline.scoreFilter}
            setScoreFilter={pipeline.setScoreFilter}
            actionInProgress={pipeline.actionInProgress}
            handleAdvance={pipeline.handleAdvance}
            handleDeleteLead={pipeline.handleDeleteLead}
            handleVerifyData={pipeline.handleVerifyData}
            handleSendLifecycleEmail={pipeline.handleSendLifecycleEmail}
            sendingEmailLeadId={pipeline.sendingEmailLeadId}
            handleSimulateChargeback={pipeline.handleSimulateChargeback}
            handleBatchApproveQA={pipeline.handleBatchApproveQA}
            batchApproving={pipeline.batchApproving}
            selectedLeadIds={pipeline.selectedLeadIds}
            toggleSelectAll={pipeline.toggleSelectAll}
            toggleSelectLead={pipeline.toggleSelectLead}
            handleBatchAdvance={pipeline.handleBatchAdvance}
            handleBatchDelete={pipeline.handleBatchDelete}
            openCodeModal={modals.openCodeModal}
            openDataModal={modals.openDataModal}
            openAuditModal={modals.openAuditModal}
            openQaOverrideModal={modals.openQaOverrideModal}
            openSwarmProgressModal={modals.openSwarmProgressModal}
            setScoreModal={modals.setScoreModal}
            renderDiscoveryBadge={renderDiscoveryBadge}
          />
        )}

        {/* TAB 2: LIFECYCLE KANBAN */}
        {activeTab === 'kanban' && (
          <KanbanTab
            pipeline={pipeline.pipeline}
            actionInProgress={pipeline.actionInProgress}
            handleAdvance={pipeline.handleAdvance}
            renderDiscoveryBadge={renderDiscoveryBadge}
            setScoreModal={modals.setScoreModal}
          />
        )}

        {/* TAB 3: ARCHIVED LEADS VAULT */}
        {activeTab === 'archived' && (
          <ArchivedLeadsTab
            archivedLeads={pipeline.archivedLeads}
            archivedLoading={pipeline.archivedLoading}
            archivedEnriching={pipeline.archivedEnriching}
            enrichArchivedResults={pipeline.enrichArchivedResults}
            loadArchivedLeads={pipeline.loadArchivedLeads}
            handleEnrichAllArchived={pipeline.handleEnrichAllArchived}
            handleAdvance={pipeline.handleAdvance}
            actionInProgress={pipeline.actionInProgress}
            renderDiscoveryBadge={renderDiscoveryBadge}
            showToast={showToast}
          />
        )}

        {/* TAB 4: SWARM MONITOR */}
        {activeTab === 'swarm' && (
          <SwarmTab
            pipeline={pipeline.pipeline}
            activeBuilds={pipeline.activeBuilds}
            openSwarmProgressModal={modals.openSwarmProgressModal}
          />
        )}

        {/* TAB 5: FINANCIAL LEDGER */}
        {activeTab === 'accounting' && (
          <AccountingTab
            pipeline={pipeline.pipeline}
            depositTotal={pipeline.depositTotal}
            releasedTotal={pipeline.releasedTotal}
            activeMrr={pipeline.activeMrr}
          />
        )}

        {/* TAB 6: SCRAPERS & EXTRACTED DATASETS */}
        {activeTab === 'scrapers' && (
          <ScrapersTab
            scrapers={scrapers.scrapers}
            scrapersLoading={scrapers.scrapersLoading}
            loadScrapers={scrapers.loadScrapers}
            openCodeModal={modals.openCodeModal}
            pipeline={pipeline.pipeline}
          />
        )}

        {/* TAB 7: AUTOMATED DAILY FEEDS */}
        {activeTab === 'daily' && (
          <DailyDeliveryTab
            dailyGrid={scrapers.dailyGrid}
            dailyLoading={scrapers.dailyLoading}
            loadDailyGrid={scrapers.loadDailyGrid}
            pipeline={pipeline.pipeline}
            handleTriggerDailyDelivery={scrapers.handleTriggerDailyDelivery}
          />
        )}

        {/* TAB 8: EMAIL INBOXES & WARMUP FLEET */}
        {activeTab === 'inboxes' && (
          <InboxesAndWarmupTab
            inboxes={inboxes.inboxes}
            loadInboxes={inboxes.loadInboxes}
            inboxesLoading={inboxes.inboxesLoading}
            warmupTargets={inboxes.warmupTargets}
            loadWarmupTargets={inboxes.loadWarmupTargets}
            warmupTargetsLoading={inboxes.warmupTargetsLoading}
            inboundStream={inboxes.inboundStream}
            loadInboundStream={inboxes.loadInboundStream}
            inboundLoading={inboxes.inboundLoading}
            warmupActivity={inboxes.warmupActivity}
            loadWarmupActivity={inboxes.loadWarmupActivity}
            warmupActivityLoading={inboxes.warmupActivityLoading}
            inboxSubTab={inboxes.inboxSubTab}
            setInboxSubTab={inboxes.setInboxSubTab}
            handleStartWarmup={inboxes.handleStartWarmup}
            startingWarmup={inboxes.startingWarmup}
            handleDispatchWarmupBatch={inboxes.handleDispatchWarmupBatch}
            dispatchingWarmup={inboxes.dispatchingWarmup}
            handleFlushOutreachQueue={inboxes.handleFlushOutreachQueue}
            flushingQueue={inboxes.flushingQueue}
            showToast={showToast}
            showAddReceiverModal={inboxes.showAddReceiverModal}
            setShowAddReceiverModal={inboxes.setShowAddReceiverModal}
            receiverFormData={inboxes.receiverFormData}
            setReceiverFormData={inboxes.setReceiverFormData}
            handleSaveReceiver={inboxes.handleSaveReceiver}
            showAddInboxModal={inboxes.showAddInboxModal}
            setShowAddInboxModal={inboxes.setShowAddInboxModal}
            inboxFormData={inboxes.inboxFormData}
            setInboxFormData={inboxes.setInboxFormData}
            handleSaveInbox={inboxes.handleSaveInbox}
            testingInboxId={inboxes.testingInboxId}
            handleTestInbox={inboxes.handleTestInbox}
            handleDeleteInbox={inboxes.handleDeleteInbox}
            deletingInboxId={inboxes.deletingInboxId}
            deletingReceiverId={inboxes.deletingReceiverId}
            handleDeleteReceiver={inboxes.handleDeleteReceiver}
            handleRunWarmupMonitoring={inboxes.handleRunWarmupMonitoring}
            monitoringWarmup={inboxes.monitoringWarmup}
          />
        )}
      </div>

      {/* =========================================================
          MODALS
         ========================================================= */}
      <CodeViewerModal
        modalState={modals.codeModal}
        onClose={() => modals.setCodeModal({ open: false, title: '', code: '' })}
        showToast={showToast}
      />

      <DatasetRecordsModal
        modalState={modals.dataModal}
        onClose={() => modals.setDataModal({ open: false, title: '', rows: [], count: 0, leadId: '' })}
        showToast={showToast}
      />

      <AuditTrailModal
        modalState={modals.auditModal}
        onClose={() => modals.setAuditModal({ open: false, title: '', events: [] })}
      />

      <QAOverrideModal
        modalState={modals.qaOverrideModal}
        onClose={() => modals.setQaOverrideModal({ open: false, leadId: '', company: '' })}
        overrideScore={modals.overrideScore}
        setOverrideScore={modals.setOverrideScore}
        overrideReason={modals.overrideReason}
        setOverrideReason={modals.setOverrideReason}
        onSubmit={modals.handleSubmitQaOverride}
      />

      <SwarmProgressModal
        modalState={modals.swarmProgressModal}
        onClose={() => modals.setSwarmProgressModal({ open: false, leadId: '', company: '', data: null })}
      />

      <LeadScoringModal
        modalState={modals.scoreModal}
        onClose={() => modals.setScoreModal({ open: false, lead: null })}
        handleDeepEnrichLead={pipeline.handleDeepEnrichLead}
        enrichingLeadId={pipeline.enrichingLeadId}
        renderDiscoveryBadge={renderDiscoveryBadge}
        showToast={showToast}
      />

      <SpamReportModal
        report={inboxes.selectedSpamReport}
        onClose={() => inboxes.setSelectedSpamReport(null)}
      />

      <ConfirmModal
        isOpen={modals.confirmModal.isOpen}
        title={modals.confirmModal.title}
        message={modals.confirmModal.message}
        confirmText={modals.confirmModal.confirmText}
        cancelText={modals.confirmModal.cancelText}
        isDestructive={modals.confirmModal.isDestructive}
        requireMatch={modals.confirmModal.requireMatch}
        hasInput={modals.confirmModal.hasInput}
        inputLabel={modals.confirmModal.inputLabel}
        inputPlaceholder={modals.confirmModal.inputPlaceholder}
        inputDefaultValue={modals.confirmModal.inputDefaultValue}
        onConfirm={modals.confirmModal.onConfirm}
        onClose={modals.closeConfirmModal}
      />

      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        activeTab={activeTab}
        onSelectTab={(tabKey) => {
          setActiveTab(tabKey);
        }}
        pipeline={pipeline.pipeline}
        onSelectLead={(selectedLead) => {
          modals.setScoreModal({ open: true, lead: selectedLead });
        }}
        actions={commandPaletteActions}
      />
    </main>
  );
}
