import React, { useEffect, useState, useMemo } from 'react';
import { useAuth } from '@clerk/clerk-react';
import {
  fetchAdminPipeline,
  fetchAdminMetrics,
  triggerSwarmBuild,
  purgeAllData,
  advanceLeadState,
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
} from '../services/api';
import { useToast } from '../context/ToastContext';

export default function AdminPage() {
  const { getToken } = useAuth();
  const { showToast } = useToast();

  // Active Tab
  const [activeTab, setActiveTab] = useState('deals');

  // Pipeline & Data
  const [pipeline, setPipeline] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState({});

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [stateFilter, setStateFilter] = useState('ALL');
  const [paymentFilter, setPaymentFilter] = useState('ALL');

  // Scrapers & Daily Grid
  const [scrapers, setScrapers] = useState([]);
  const [scrapersLoading, setScrapersLoading] = useState(false);
  const [dailyGrid, setDailyGrid] = useState([]);
  const [activeBuilds, setActiveBuilds] = useState([]);

  // Modals state
  const [codeModal, setCodeModal] = useState({ open: false, title: '', code: '' });
  const [dataModal, setDataModal] = useState({ open: false, title: '', rows: [], count: 0, leadId: '' });
  const [auditModal, setAuditModal] = useState({ open: false, title: '', events: [] });
  const [qaOverrideModal, setQaOverrideModal] = useState({ open: false, leadId: '', company: '' });
  const [overrideScore, setOverrideScore] = useState(1.0);
  const [overrideReason, setOverrideReason] = useState('Founder verified edge-case pass');
  const [swarmProgressModal, setSwarmProgressModal] = useState({ open: false, leadId: '', company: '', data: null });

  // Load Admin Data
  const loadAdminData = async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const [pipeData, metricData, buildsData] = await Promise.allSettled([
        fetchAdminPipeline(token),
        fetchAdminMetrics(token),
        fetchActiveBuilds(token),
      ]);

      if (pipeData.status === 'fulfilled') {
        setPipeline(pipeData.value.leads || pipeData.value.pipeline || []);
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
    } catch (err) {
      console.warn('Admin load note:', err);
      showToast(`Admin load: ${err.message}`, 'info');
    } finally {
      setLoading(false);
    }
  };

  // Load Scrapers when tab changes
  useEffect(() => {
    if (activeTab === 'scrapers' && scrapers.length === 0) {
      loadScrapers();
    } else if (activeTab === 'daily' && dailyGrid.length === 0) {
      loadDailyGrid();
    }
  }, [activeTab]);

  const loadScrapers = async () => {
    setScrapersLoading(true);
    try {
      const token = await getToken();
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
      const token = await getToken();
      const data = await fetchDailyGrid(token);
      setDailyGrid(data.grid || data || []);
    } catch (err) {
      console.warn('Daily grid err:', err);
    }
  };

  useEffect(() => {
    loadAdminData();
    const interval = setInterval(loadAdminData, 20000);
    return () => clearInterval(interval);
  }, []);

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

      return matchesSearch && matchesState && matchesPayment;
    });
  }, [pipeline, searchQuery, stateFilter, paymentFilter]);

  // Actions
  const handleAdvance = async (leadId) => {
    setActionInProgress((p) => ({ ...p, [leadId]: true }));
    showToast(`Advancing deal stage for ${leadId}...`, 'info');
    try {
      const token = await getToken();
      const res = await advanceLeadState(leadId, token);
      showToast(res.message || `Lead ${leadId} advanced!`, 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Advance error: ${err.message}`, 'error');
    } finally {
      setActionInProgress((p) => ({ ...p, [leadId]: false }));
    }
  };

  const handleTriggerSwarm = async (leadId) => {
    setActionInProgress((p) => ({ ...p, [leadId]: true }));
    showToast(`Triggering autonomous 7-agent dev swarm for ${leadId}...`, 'info');
    try {
      const token = await getToken();
      await triggerSwarmBuild(leadId, token);
      showToast(`Autonomous swarm build initiated for ${leadId}!`, 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Swarm launch error: ${err.message}`, 'error');
    } finally {
      setActionInProgress((p) => ({ ...p, [leadId]: false }));
    }
  };

  const handlePurgeAllData = async () => {
    const confirmed = window.confirm(
      "⚠️ FRESH START CONFIRMATION\n\nAre you sure you want to permanently purge all test leads, sandboxes, and mock customer records?\n\nThis resets the database to a clean 0-lead state for real production customers."
    );
    if (!confirmed) return;

    showToast("Purging all test data and resetting pipeline...", "info");
    try {
      const token = await getToken();
      const res = await purgeAllData(token);
      showToast(res.message || "All test records successfully purged!", "success");
      await loadAdminData();
    } catch (err) {
      showToast(`Purge failed: ${err.message}`, "error");
    }
  };

  const handleDeleteLead = async (leadId, companyName) => {
    const confirmed = window.confirm(
      `⚠️ DELETE CONFIRMATION\n\nAre you sure you want to permanently delete lead:\n"${companyName || leadId}"?\n\nThis will remove the lead, associated sandboxes, and audit records.`
    );
    if (!confirmed) return;

    setActionInProgress((p) => ({ ...p, [leadId]: true }));
    try {
      const token = await getToken();
      await deleteLead(leadId, token);
      showToast(`Lead "${companyName || leadId}" deleted successfully.`, 'success');
      await loadAdminData();
    } catch (err) {
      showToast(`Failed to delete lead: ${err.message}`, 'error');
    } finally {
      setActionInProgress((p) => ({ ...p, [leadId]: false }));
    }
  };

  const handleToggleEmergencyStop = async () => {
    const currentState = metrics?.emergency_stop_active || false;
    const newState = !currentState;
    const reason = prompt(
      newState
        ? "Enter reason for EMERGENCY STOP (pauses all autonomous outreach & dev swarms):"
        : "Enter reason for RESUMING normal operations:",
      newState ? "Manual founder safety stop" : "Founder resumed operations"
    );
    if (reason === null) return;

    try {
      const token = await getToken();
      await toggleEmergencyStop(newState, reason, token);
      showToast(
        newState ? "🛑 EMERGENCY STOP ACTIVATED" : "✅ Systems resumed normal operation",
        newState ? "error" : "success"
      );
      await loadAdminData();
    } catch (err) {
      showToast(`Emergency toggle failed: ${err.message}`, "error");
    }
  };

  const handleViewAudit = async (leadId, companyName) => {
    try {
      const token = await getToken();
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
      const token = await getToken();
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
      const token = await getToken();
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
      const token = await getToken();
      const code = await fetchScraperCode(leadId, token);
      setCodeModal({ open: true, title: `Source: ${scraperName || leadId}`, code });
    } catch (err) {
      showToast(`Code load: ${err.message}`, 'error');
    }
  };

  const handleViewOutput = async (leadId, scraperName) => {
    try {
      const token = await getToken();
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
      const token = await getToken();
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
      const token = await getToken();
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
              {metrics?.emergency_stop_active && (
                <span className="badge-tag badge-red">🛑 EMERGENCY STOP ACTIVE</span>
              )}
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Autonomous 7-Agent Dev Swarms, Live Municipal Extractors, QA Gate &amp; Escrow Vault
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
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
                    <th>QA Gate</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeads.length === 0 ? (
                    <tr>
                      <td colSpan="7" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                        {loading ? 'Fetching pipeline deals...' : 'No deals match your search criteria.'}
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
                            <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--mono)', marginTop: '2px' }}>
                              {lead.lead_id}
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
                            {qa !== null ? (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span
                                  style={{
                                    fontWeight: 700,
                                    fontSize: '13px',
                                    color: qa >= 0.95 ? 'var(--green)' : 'var(--yellow)',
                                  }}
                                >
                                  {(qa * 100).toFixed(0)}%
                                </span>
                                <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>
                                  {qa >= 0.95 ? 'PASSED' : 'REVIEW'}
                                </span>
                              </div>
                            ) : (
                              <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>—</span>
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
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
                                style={{ padding: '4px 10px', fontSize: '11px' }}
                                onClick={() => handleAdvance(lead.lead_id)}
                                disabled={actionInProgress[lead.lead_id]}
                                title="1-Click Advance lifecycle stage"
                              >
                                ⏩ Advance
                              </button>
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
                  <div className="kanban-col-header">
                    <span>{col.label}</span>
                    <span className="badge-tag">{colLeads.length}</span>
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

                          <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                            <button
                              className="btn btn-primary"
                              style={{ padding: '4px 8px', fontSize: '11px', flex: 1 }}
                              onClick={() => handleAdvance(lead.lead_id)}
                              disabled={actionInProgress[lead.lead_id]}
                            >
                              ⏩ Advance
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
    </main>
  );
}
