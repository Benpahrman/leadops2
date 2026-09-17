// Sandbox & Prospect Onboarding API client
import { API_BASE } from '../../../services/apiClient';

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
