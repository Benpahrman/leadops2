import { useState, useCallback } from 'react';
import {
  fetchAuditTrail,
  fetchSwarmProgress,
  overrideQA,
  fetchScraperCode,
  fetchScraperOutput,
} from '../../../services/api';

/**
 * Custom hook managing modal dialogues, inspection views, and confirmation dialogs for Admin Page.
 *
 * @param {Object} options
 * @param {Function} options.resolveToken - Async token retriever.
 * @param {Function} options.showToast - Toast alert function.
 * @param {Array} [options.pipeline] - Leads pipeline array for fallback audit log lookup.
 * @param {Function} [options.loadAdminData] - Refresher for pipeline data.
 */
export function useAdminModals({ resolveToken, showToast, pipeline = [], loadAdminData }) {
  // Confirm Modal state
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

  const closeConfirmModal = useCallback(() => {
    setConfirmModal((prev) => ({ ...prev, isOpen: false }));
  }, []);

  // Quick Copy Helper
  const handleCopyText = useCallback((text, label = 'Text') => {
    if (!text) return;
    try {
      navigator.clipboard.writeText(text);
      showToast(`${label} copied to clipboard!`, 'success');
    } catch {
      showToast(`Could not copy ${label}`, 'info');
    }
  }, [showToast]);

  // Inspection Modals
  const [codeModal, setCodeModal] = useState({ open: false, title: '', code: '' });
  const [dataModal, setDataModal] = useState({ open: false, title: '', rows: [], count: 0, leadId: '' });
  const [auditModal, setAuditModal] = useState({ open: false, title: '', events: [] });
  const [scoreModal, setScoreModal] = useState({ open: false, lead: null });
  const [qaOverrideModal, setQaOverrideModal] = useState({ open: false, leadId: '', company: '' });
  const [overrideScore, setOverrideScore] = useState(1.0);
  const [overrideReason, setOverrideReason] = useState('Founder verified edge-case pass');
  const [swarmProgressModal, setSwarmProgressModal] = useState({ open: false, leadId: '', company: '', data: null });

  const handleViewAudit = useCallback(async (leadId, companyName, leadObj = null) => {
    try {
      const token = await resolveToken();
      let events = [];
      try {
        const res = await fetchAuditTrail(leadId, token);
        events = res.trail || res.audit_trail || res.events || res.audit_log || [];
      } catch (fetchErr) {
        console.warn('Network fetchAuditTrail failed, falling back to local lead data:', fetchErr);
      }

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
  }, [resolveToken, showToast, pipeline]);

  const handleViewSwarmProgress = useCallback(async (leadId, companyName) => {
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
  }, [resolveToken, showToast]);

  const handleOpenQaOverride = useCallback((leadId, companyName) => {
    setQaOverrideModal({ open: true, leadId, company: companyName || leadId });
  }, []);

  const handleSubmitQaOverride = useCallback(async () => {
    try {
      const token = await resolveToken();
      await overrideQA(qaOverrideModal.leadId, overrideScore, overrideReason, token);
      showToast(`QA Gate override applied (Score: ${overrideScore * 100}%)`, 'success');
      setQaOverrideModal({ open: false, leadId: '', company: '' });
      if (loadAdminData) {
        await loadAdminData();
      }
    } catch (err) {
      showToast(`QA override failed: ${err.message}`, 'error');
    }
  }, [resolveToken, showToast, qaOverrideModal.leadId, overrideScore, overrideReason, loadAdminData]);

  const handleViewCode = useCallback(async (leadId, scraperName) => {
    try {
      const token = await resolveToken();
      const code = await fetchScraperCode(leadId, token);
      setCodeModal({ open: true, title: `Source: ${scraperName || leadId}`, code });
    } catch (err) {
      showToast(`Code load: ${err.message}`, 'error');
    }
  }, [resolveToken, showToast]);

  const handleViewOutput = useCallback(async (leadId, scraperName) => {
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
  }, [resolveToken, showToast]);

  return {
    confirmModal,
    setConfirmModal,
    closeConfirmModal,
    handleCopyText,
    codeModal,
    setCodeModal,
    dataModal,
    setDataModal,
    auditModal,
    setAuditModal,
    scoreModal,
    setScoreModal,
    qaOverrideModal,
    setQaOverrideModal,
    overrideScore,
    setOverrideScore,
    overrideReason,
    setOverrideReason,
    swarmProgressModal,
    setSwarmProgressModal,
    handleViewAudit,
    handleViewSwarmProgress,
    handleOpenQaOverride,
    handleSubmitQaOverride,
    handleViewCode,
    handleViewOutput,
  };
}

export default useAdminModals;
