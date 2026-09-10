// Centralized API client for OmniLeadFeeder frontend
// Uses same-origin relative URLs (/api/...) on custom domains (both www and apex) and local dev proxy

const API_BASE = (import.meta.env && import.meta.env.VITE_API_BASE_URL) || '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function fetchSandbox(slug) {
  const res = await fetch(`${API_BASE}/api/sandbox/${slug}`);
  if (!res.ok) throw new Error(`Failed loading sandbox: HTTP ${res.status}`);
  return res.json();
}

export async function suggestColumns(slug) {
  const res = await fetch(`${API_BASE}/api/sandbox/${slug}/suggest-columns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return res.json();
}

export async function payDeposit(slug, { email, cardholder, targetUrl, paypalOrderId, depositAmount = 99.0 }) {
  const res = await fetch(`${API_BASE}/api/sandbox/${slug}/pay-deposit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      cardholder,
      deposit_amount: depositAmount,
      target_url: targetUrl || '',
      paypal_order_id: paypalOrderId || `PAYID-${Date.now()}`,
      tos_accepted: true,
      sow_accepted: true,
    }),
  });
  return res.json();
}

export async function unlockBacklog(slug, { email, paypalOrderId } = {}) {
  const res = await fetch(`${API_BASE}/api/sandbox/${slug}/unlock-backlog`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      paypal_order_id: paypalOrderId || `PAYID-BACKLOG-${Date.now()}`,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Backlog unlock failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function sendChatMessage(slug, message, history = []) {
  const res = await fetch(`${API_BASE}/api/sandbox/${slug || 'lead-apex-roofing'}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  });
  return res.json();
}

export async function fetchChatHistory(slug) {
  try {
    const res = await fetch(`${API_BASE}/api/sandbox/${slug || 'lead-apex-roofing'}/chat`);
    if (!res.ok) return { ok: false, messages: [] };
    return res.json();
  } catch (e) {
    return { ok: false, messages: [] };
  }
}

export async function fetchDashboard(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  
  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}`, { headers });
  if (!res.ok) throw new Error(`Dashboard fetch error: HTTP ${res.status}`);
  return res.json();
}

export async function saveSchema(leadId, activeFields, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/schema`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ active_fields: activeFields }),
  });
  return res.json();
}

export async function fetchGoogleSheetsInfo() {
  const res = await fetch(`${API_BASE}/api/dashboard/integrations/google-sheets-info`);
  if (!res.ok) return { service_account_active: false, service_account_email: 'service@omnileadfeeder.tech' };
  return res.json();
}

export async function saveDestinations(leadId, destData, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/destinations`, {
    method: 'POST',
    headers,
    body: JSON.stringify(destData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to save destinations (HTTP ${res.status})`);
  }
  return res.json();
}

export async function testDestinationPing(leadId, type, params = {}, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const bodyData = typeof params === 'string' ? { type: params } : { type, destination_type: type, ...params };

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/test-destination`, {
    method: 'POST',
    headers,
    body: JSON.stringify(bodyData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `Test failed (HTTP ${res.status})`);
  }
  return res.json();
}

export async function sendEmailExport(leadId, recipientEmail = '', token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/export/email`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ recipient_email: recipientEmail }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.message || `Email export failed (HTTP ${res.status})`);
  }
  return res.json();
}

export async function exportJsonData(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/export/json`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `JSON export failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function downloadXlsxData(leadId, token = '') {
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/export/xlsx`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Excel XLSX export failed: HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `${leadId}_production_records.xlsx`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  return true;
}

export async function downloadJsonlData(leadId, token = '') {
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/export/jsonl`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `JSONL export failed: HTTP ${res.status}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `${leadId}_production_records.jsonl`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  return true;
}

export async function rotateFeedToken(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/feed-token/rotate`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Token rotation failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function triggerManualSync(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/sync`, {
    method: 'POST',
    headers,
  });
  return res.json();
}

export async function pauseFeed(leadId, days = 30, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/pause`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ days }),
  });
  return res.json();
}

export async function resumeFeed(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/resume`, {
    method: 'POST',
    headers,
  });
  return res.json();
}

export async function requestCancellation(slug, reason, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/sandbox/${slug}/cancel`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ reason }),
  });
  return res.json();
}

export async function claimAccount({ userId, leadId, email, token }) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/auth/claim`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      user_id: userId,
      lead_id: leadId,
      email: email,
    }),
  });
  return res.json();
}

export async function fetchEvidenceDossier(slug) {
  const res = await fetch(`${API_BASE}/api/sandbox/${slug}/evidence-dossier`);
  return res.json();
}

// Admin APIs & Token Resolution
const FALLBACK_ADMIN_TOKEN = '0baac74dfda043fdaf84c5d0b38e259b';

export function resolveAdminAuth(token = '') {
  if (token && typeof token === 'string' && token.trim()) {
    return token.trim();
  }
  if (typeof window !== 'undefined') {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const queryKey = urlParams.get('key') || urlParams.get('token') || urlParams.get('admin_key');
      if (queryKey) {
        localStorage.setItem('leadops_admin_token', queryKey);
        return queryKey;
      }
      const stored = localStorage.getItem('leadops_admin_token');
      if (stored) return stored;
    } catch (e) {
      // Ignore local storage errors
    }
  }
  return import.meta.env.VITE_LEADOPS_API_TOKEN || FALLBACK_ADMIN_TOKEN;
}

export async function fetchAdminPipeline(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/pipeline`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchAdminMetrics(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/governance/metrics`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerSwarmBuild(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/${leadId}/swarm`, {
    method: 'POST',
    headers,
  });
  return res.json();
}

export async function purgeAllData(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/system/purge-all-data`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function advanceLeadState(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/${leadId}/advance`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function batchApprovePendingPitches(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/batch-approve`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchScoutStatus(token = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scout/status`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deleteLead(leadId, token = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/${leadId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchSwarmProgress(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/${leadId}/swarm-progress`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchActiveBuilds(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/swarm/active-builds`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function overrideQA(leadId, qaScore = 1.0, justification = 'Founder verified edge-case pass', token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/swarm/${leadId}/override-qa`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ qa_score: qaScore, justification }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchScrapersCatalog(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scrapers`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchScraperCode(leadId, token = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scrapers/${leadId}/code`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.text();
}

export async function fetchScraperOutput(leadId, format = 'json', token = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scrapers/${leadId}/output?format=${format}`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return format === 'json' ? res.json() : res.blob();
}

export async function runScraperOnDemand(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scrapers/${leadId}/run`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchDailyGrid(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/delivery/daily-grid`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerDailyDelivery(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/delivery/${leadId}/run-now`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function toggleEmergencyStop(active, reason = 'Global operational emergency pause', token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/governance/emergency-stop`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ active, reason }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchAuditTrail(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/${leadId}/audit-trail`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchAutoOutreachStatus(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/auto-outreach/status`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function toggleAutoOutreach(enabled, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/auto-outreach/toggle`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerScoutDiscovery(niche = null, token = '', channel = null) {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scout/trigger-web-scout`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ niche, channel }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function cancelAutoOutreach(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/quick-action?action=cancel_auto_outreach&lead_id=${leadId}&token=${resolved}`, {
    headers: { ...headers, Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function initializePipeline(payload) {
  const res = await fetch(`${API_BASE}/api/pipeline/initialize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Pipeline initialization failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchAdminInboxes(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function upsertAdminInbox(inboxData, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes`, {
    method: 'POST',
    headers,
    body: JSON.stringify(inboxData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function testAdminInbox(inboxId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes/${inboxId}/test`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteAdminInbox(inboxId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes/${inboxId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerOutreachFlush(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/auto-outreach/flush`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function enrichLeadContact(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/${leadId}/enrich-contact`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function batchEnrichArchivedLeads(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/batch-enrich-archived`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchArchivedLeads(token = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/archived`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchMicrosoftOAuthStatus(token = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/oauth/microsoft/status`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchMicrosoftOAuthAuthorizeUrl(token = '', redirectUri = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const query = redirectUri ? `?redirect_uri=${encodeURIComponent(redirectUri)}` : '';
  const res = await fetch(`${API_BASE}/api/admin/oauth/microsoft/authorize${query}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function disconnectMicrosoftOAuth(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/oauth/microsoft/disconnect`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}


