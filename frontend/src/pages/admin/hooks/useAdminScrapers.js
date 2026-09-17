import { useState, useCallback } from 'react';
import {
  fetchScrapersCatalog,
  runScraperOnDemand,
  fetchDailyGrid,
  triggerDailyDelivery,
} from '../../../services/api';

/**
 * Custom hook for Scrapers Catalog and Daily Delivery Grid management.
 *
 * @param {Object} options
 * @param {Function} options.resolveToken - Async helper to get active admin or Clerk token.
 * @param {Function} options.showToast - Toast notification dispatcher.
 * @param {Function} [options.setActionInProgress] - State updater for per-lead action spinners.
 */
export function useAdminScrapers({ resolveToken, showToast, setActionInProgress }) {
  const [scrapers, setScrapers] = useState([]);
  const [scrapersLoading, setScrapersLoading] = useState(false);
  const [dailyGrid, setDailyGrid] = useState([]);
  const [dailyGridLoading, setDailyGridLoading] = useState(false);

  const loadScrapers = useCallback(async () => {
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
  }, [resolveToken, showToast]);

  const loadDailyGrid = useCallback(async () => {
    setDailyGridLoading(true);
    try {
      const token = await resolveToken();
      const data = await fetchDailyGrid(token);
      setDailyGrid(data.grid || data || []);
    } catch (err) {
      showToast(`Failed to load daily grid: ${err.message}`, 'error');
    } finally {
      setDailyGridLoading(false);
    }
  }, [resolveToken, showToast]);

  const handleRunScraper = useCallback(async (leadId) => {
    if (setActionInProgress) {
      setActionInProgress((p) => ({ ...p, [leadId]: true }));
    }
    showToast(`Executing extractor pipeline for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      const res = await runScraperOnDemand(leadId, token);
      showToast(`Extractor finished! ${res.rows_extracted || 0} rows extracted.`, 'success');
      await loadScrapers();
    } catch (err) {
      showToast(`Execution error: ${err.message}`, 'error');
    } finally {
      if (setActionInProgress) {
        setActionInProgress((p) => ({ ...p, [leadId]: false }));
      }
    }
  }, [resolveToken, showToast, setActionInProgress, loadScrapers]);

  const handleTriggerDailyDelivery = useCallback(async (leadId) => {
    showToast(`Dispatching live daily feed delivery for ${leadId}...`, 'info');
    try {
      const token = await resolveToken();
      await triggerDailyDelivery(leadId, token);
      showToast(`Daily delivery sent for ${leadId}!`, 'success');
      await loadDailyGrid();
    } catch (err) {
      showToast(`Delivery error: ${err.message}`, 'error');
    }
  }, [resolveToken, showToast, loadDailyGrid]);

  return {
    scrapers,
    setScrapers,
    scrapersLoading,
    dailyGrid,
    setDailyGrid,
    dailyGridLoading,
    loadScrapers,
    loadDailyGrid,
    handleRunScraper,
    handleTriggerDailyDelivery,
  };
}

export default useAdminScrapers;
