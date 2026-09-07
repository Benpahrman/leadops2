// Centralized API client for OmniLeadFeeder frontend

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

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

export async function payDeposit(slug, { email, cardholder, paypalOrderId }) {
  const res = await fetch(`${API_BASE}/api/sandbox/${slug}/pay-deposit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      cardholder,
      paypal_order_id: paypalOrderId || `PAYID-${Date.now()}`,
      tos_accepted: true,
      sow_accepted: true,
    }),
  });
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

export async function saveDestinations(leadId, destData, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/destinations`, {
    method: 'POST',
    headers,
    body: JSON.stringify(destData),
  });
  return res.json();
}

export async function testDestinationPing(leadId, type, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/dashboard/${leadId}/test-destination`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ type }),
  });
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

// Admin APIs
export async function fetchAdminPipeline(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/admin/pipeline`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchAdminMetrics(token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/admin/governance/metrics`, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function triggerSwarmBuild(leadId, token = '') {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/admin/leads/${leadId}/swarm`, {
    method: 'POST',
    headers,
  });
  return res.json();
}
