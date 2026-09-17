// Dashboard & Lead Delivery Feed API client
import { API_BASE } from '../../../services/apiClient';

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

export async function fetchEvidenceDossier(slug) {
  const res = await fetch(`${API_BASE}/api/sandbox/${slug}/evidence-dossier`);
  return res.json();
}

// Admin APIs & Token Resolution
