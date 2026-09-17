// Outbound Outreach, Warmup, Inboxes & Deliverability Suite API client
import { API_BASE } from '../../../services/apiClient';

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

export async function triggerScoutDiscovery(niche = null, token = '', channel = null, runUntilFound = true) {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scout/trigger-web-scout`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ niche, channel, run_until_found: runUntilFound }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerBatchScout(count = 3, niche = null, channel = null, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scout/batch-scout`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ count, niche, channel }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function deepEnrichLead(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/${leadId}/enrich`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Enrichment failed (HTTP ${res.status})`);
  }
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

export async function fetchAdminInboxes(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function startWarmupCycle(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/warmup/start`, {
    method: 'POST',
    headers,
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function dispatchWarmupBatch(count = 3, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/warmup/dispatch-batch?count=${count}`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ count }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function runWarmupMonitoring(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/warmup/run-inbox-monitoring`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
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

export async function fetchInboundStream(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes/inbound-stream`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchWarmupTargets(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes/warmup-targets`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function addWarmupTarget(targetData, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes/warmup-targets`, {
    method: 'POST',
    headers,
    body: JSON.stringify(targetData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteWarmupTarget(targetId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes/warmup-targets/${targetId}`, {
    method: 'DELETE',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchWarmupActivity(limit = 50, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/inboxes/warmup-activity?limit=${limit}`, { headers });
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

export async function fetchDeliverabilityStatus(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/deliverability/status`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchComprehensiveDeliverabilityReport(domain = 'olfmailer.com', token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/deliverability/comprehensive-latest?domain=${encodeURIComponent(domain)}`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function runComprehensiveDeliverabilityAudit(options = {}, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/deliverability/comprehensive-audit`, {
    method: 'POST',
    headers,
    body: JSON.stringify(options),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function checkRBLBlacklists(target = 'olfmailer.com', token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/deliverability/rbl-check`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ target }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function checkContentSpamScore(subject = '', body = '', token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/deliverability/content-audit`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ subject, body }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function runDeliverabilityAudit(options = {}, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/deliverability/run-audit`, {
    method: 'POST',
    headers,
    body: JSON.stringify(options),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
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

// ─── 14-Day High-Volume Prospector & Freshness Gate ─────────────────────────

export async function fetchProspectorStatus(token = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/prospector/status`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function startProspectorCampaign(durationDays = 14, volumePerCycle = 3, channels = null, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/prospector/start`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ duration_days: durationDays, volume_per_cycle: volumePerCycle, channels }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function pauseProspectorCampaign(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/prospector/pause`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function resumeProspectorCampaign(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/prospector/resume`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function toggleProspector247Mode(enabled = true, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/prospector/toggle-24-7`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function toggleScout247Mode(enabled = true, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scout/toggle-24-7`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerProspectorBurst(count = 3, channel = null, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/prospector/trigger-burst`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ count, channel }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function refreshLeadFreshness(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/prospector/refresh-freshness/${leadId}`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function batchRefreshStaleBacklog(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/prospector/batch-refresh-stale`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ─── 50-State & County-by-County Swarm Prospecting Orchestrator ────────────

export async function fetchCountyOrchestratorStatus(token = '') {
  const headers = {};
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scout/county-orchestrator/status`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function advanceCountyOrchestratorCursor(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scout/county-orchestrator/advance`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function setCountyOrchestratorStateFocus(stateCode = null, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  const resolved = resolveAdminAuth(token);
  if (resolved) headers['Authorization'] = `Bearer ${resolved}`;

  const res = await fetch(`${API_BASE}/api/admin/scout/county-orchestrator/set-focus`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ state_code: stateCode }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
