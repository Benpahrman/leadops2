/**
 * Centralized API Barrel Facade for LeadOps Frontend.
 *
 * Deconstructed into domain feature services in conformance with:
 * - ADR-0002: Strangler Fig De-monolithization Protocol
 * - ADR-0003: Backend-Frontend Boundary Decoupling
 *
 * This barrel facade re-exports all 85 API functions for 100% backward
 * compatibility with existing components and pages.
 */

// Shared Base Client
export { API_BASE } from './apiClient';

// Sandbox & Onboarding API
export {
  fetchHealth,
  fetchSandbox,
  suggestColumns,
  payDeposit,
  unlockBacklog,
  sendChatMessage,
  fetchChatHistory,
  claimAccount,
} from '../features/sandbox/services/sandboxApi';

// Dashboard & Feed Deliveries API
export {
  fetchDashboard,
  saveSchema,
  fetchGoogleSheetsInfo,
  saveDestinations,
  testDestinationPing,
  sendEmailExport,
  exportJsonData,
  downloadXlsxData,
  downloadJsonlData,
  rotateFeedToken,
  triggerManualSync,
  pauseFeed,
  resumeFeed,
  requestCancellation,
  fetchEvidenceDossier,
} from '../features/dashboard/services/dashboardApi';

// Admin & Swarm Operations API
export {
  resolveAdminAuth,
  fetchAdminPipeline,
  fetchAdminMetrics,
  triggerSwarmBuild,
  purgeAllData,
  advanceLeadState,
  batchApprovePendingPitches,
  fetchScoutStatus,
  deleteLead,
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
  initializePipeline,
} from '../features/admin/services/adminApi';

// Outbound Outreach, Inboxes & Deliverability API
export {
  fetchAutoOutreachStatus,
  toggleAutoOutreach,
  triggerScoutDiscovery,
  triggerBatchScout,
  deepEnrichLead,
  cancelAutoOutreach,
  fetchAdminInboxes,
  startWarmupCycle,
  dispatchWarmupBatch,
  runWarmupMonitoring,
  upsertAdminInbox,
  testAdminInbox,
  deleteAdminInbox,
  fetchInboundStream,
  fetchWarmupTargets,
  addWarmupTarget,
  deleteWarmupTarget,
  fetchWarmupActivity,
  triggerOutreachFlush,
  fetchDeliverabilityStatus,
  fetchComprehensiveDeliverabilityReport,
  runComprehensiveDeliverabilityAudit,
  checkRBLBlacklists,
  checkContentSpamScore,
  runDeliverabilityAudit,
  enrichLeadContact,
  batchEnrichArchivedLeads,
  fetchArchivedLeads,
  fetchMicrosoftOAuthStatus,
  fetchMicrosoftOAuthAuthorizeUrl,
  disconnectMicrosoftOAuth,
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
  fetchCandidateEvaluations,
  toggleProspector247Mode,
  toggleScout247Mode,
} from '../features/outreach/services/outreachApi';
