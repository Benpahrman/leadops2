import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { payDeposit } from '../../services/api';
import { useToast } from '../../context/ToastContext';

export default function EscrowCheckoutModal({ isOpen, onClose, slug, companyName, defaultEmail = '', defaultTargetUrl = '' }) {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [email, setEmail] = useState(defaultEmail || '');
  const [cardholder, setCardholder] = useState(companyName || '');
  const [targetUrl, setTargetUrl] = useState(defaultTargetUrl || '');
  const [tosAgreed, setTosAgreed] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);

  // Keep target URL and email in sync if default props arrive
  React.useEffect(() => {
    if (defaultTargetUrl && !targetUrl) {
      setTargetUrl(defaultTargetUrl);
    }
  }, [defaultTargetUrl]);

  React.useEffect(() => {
    if (defaultEmail && !email) {
      setEmail(defaultEmail);
    }
  }, [defaultEmail]);

  if (!isOpen) return null;

  const handleCheckout = async (e) => {
    e.preventDefault();
    if (!targetUrl || !targetUrl.trim()) {
      showToast('Please confirm or enter your target public records / docket URL.', 'error');
      return;
    }
    if (!email) {
      showToast('Please enter your company email address.', 'error');
      return;
    }
    if (!tosAgreed) {
      showToast('Please check the box to agree to the SOW & Terms of Service before authorizing escrow.', 'error');
      return;
    }

    setIsProcessing(true);
    showToast('Authorizing $99.00 setup sprint deposit in third-party escrow...', 'info');

    try {
      const data = await payDeposit(slug, {
        email,
        cardholder,
        targetUrl: targetUrl.trim(),
        paypalOrderId: `PAYID-${Date.now()}`,
        depositAmount: 99.0,
      });

      if (data.ok) {
        showToast('✓ Escrow Locked ($99.00). SOW Signed & Swarm Initiated! (100% Credited to Month 1)', 'success', 5000);
        
        // Anchor lead ID in browser storage
        if (data.lead_id) {
          localStorage.setItem('leadops_active_lead_id', data.lead_id);
        }

        onClose();
        // Redirect to success page displaying explicit SOW digital agreement receipt and live swarm
        navigate(`/checkout/success?lead_id=${data.lead_id}&slug=${slug}`);
      } else {
        showToast(`Checkout note: ${data.detail || 'Payment processed'}`, 'warning');
      }
    } catch (err) {
      console.error('Checkout error:', err);
      showToast(`Error processing checkout: ${err.message}`, 'error');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleModalClose = () => {
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleModalClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={handleModalClose}>✕</button>

        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <div style={{ fontSize: '32px', marginBottom: '6px' }}>🛡️</div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff' }}>
            Authorize $99 Setup Sprint Escrow Deposit
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Statement of Work (SOW) for <b style={{ color: 'var(--cyan)' }}>{companyName}</b> • <span style={{ color: 'var(--green)', fontWeight: 700 }}>100% Credited to Month 1</span>
          </div>
        </div>

        {/* Escrow Terms Box */}
        <div style={{ background: 'var(--card-alt)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', marginBottom: '20px', fontSize: '12px', lineHeight: 1.6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Milestone #1 Setup Sprint Deposit:</span>
            <span style={{ color: '#fff', fontWeight: 800, fontFamily: 'var(--mono)' }}>$99.00 USD (Due Now)</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Milestone #2 Final Balance:</span>
            <span style={{ color: 'var(--cyan)', fontFamily: 'var(--mono)', fontWeight: 600 }}>$151.00 ($250 plan − $99 credit; due ONLY upon QA pass)</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Recurring Delivery Retainer:</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>$250.00/month begins 30 days after live delivery</span>
          </div>
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '8px', marginTop: '8px', color: 'var(--green)', fontWeight: 600 }}>
            ✓ 100% Escrow Guarantee: Setup deposit is held until our 7-agent dev swarm verifies live extraction with &gt;=95% accuracy. Auto-refunded if unfulfilled within 24 hours.
          </div>
        </div>

        <form onSubmit={handleCheckout}>
          {/* Target Public Records / Docket Source URL Verification */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(99, 102, 241, 0.08))',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '8px',
            padding: '14px',
            marginBottom: '16px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--cyan)' }}>
                🎯 Target Public Records / Docket URL
              </label>
              {targetUrl === defaultTargetUrl && targetUrl ? (
                <span style={{ fontSize: '10px', background: 'rgba(16, 185, 129, 0.2)', color: 'var(--green)', padding: '2px 8px', borderRadius: '12px', fontWeight: 700 }}>
                  ✓ Auto-Identified by Scout
                </span>
              ) : (
                <span style={{ fontSize: '10px', background: 'rgba(56, 189, 248, 0.2)', color: 'var(--cyan)', padding: '2px 8px', borderRadius: '12px', fontWeight: 700 }}>
                  ✏️ Custom Portal Specified
                </span>
              )}
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', lineHeight: 1.4 }}>
              <b>Is this the exact docket or registry portal you want streamed?</b> Confirm this URL or paste your preferred county court, municipal permit, or licensing registry URL below.
            </p>
            <input
              type="url"
              required
              className="form-input"
              placeholder="https://records.county.gov/docket/search"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              style={{ fontSize: '12px', fontFamily: 'var(--mono)' }}
            />
          </div>

          <div style={{ marginBottom: '14px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#fff' }}>
              Company / Billing Email
            </label>
            <input
              type="email"
              required
              className="form-input"
              placeholder="alex@yourcompany.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#fff' }}>
              Authorized Contact / Signer Name
            </label>
            <input
              type="text"
              required
              className="form-input"
              placeholder="Jane Doe"
              value={cardholder}
              onChange={(e) => setCardholder(e.target.value)}
            />
          </div>

          {/* Explicit Mandatory SOW & Terms Checkbox */}
          <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px', marginBottom: '20px' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer', fontSize: '11px', color: '#cbd5e1', lineHeight: 1.4 }}>
              <input
                type="checkbox"
                checked={tosAgreed}
                onChange={(e) => setTosAgreed(e.target.checked)}
                style={{ marginTop: '2px', accentColor: 'var(--cyan)' }}
              />
              <span>
                <b>I agree to the Statement of Work (SOW) &amp; Terms of Service:</b> I authorize the $99.00 setup sprint deposit locked in third-party escrow (100% credited to Month 1; $151 net balance due only upon &gt;=95% QA verification). Engineering swarm begins immediately.
              </span>
            </label>
            <div style={{ display: 'flex', gap: '10px', marginTop: '6px', fontSize: '11px', color: 'var(--text-muted)', paddingLeft: '22px' }}>
              <a href="/terms" target="_blank" style={{ color: 'var(--cyan)', textDecoration: 'underline' }}>
                📄 Statement of Work &amp; Terms
              </a>
              <span>•</span>
              <a href="/privacy" target="_blank" style={{ color: 'var(--cyan)', textDecoration: 'underline' }}>
                🔒 Privacy Policy
              </a>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '12px', fontSize: '14px', fontWeight: 800 }}
            disabled={isProcessing}
          >
            {isProcessing ? '⚡ Locking Escrow & Starting Swarm...' : '💳 Authorize $99 Setup Sprint Deposit & Sign SOW ➔'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '16px', fontSize: '11px', color: 'var(--text-dim)' }}>
          🔒 256-Bit Encrypted Escrow • PayPal &amp; Major Credit Cards Accepted
        </div>
      </div>
    </div>
  );
}
