import React, { useState, useEffect, useRef } from 'react';
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
  const [sdkReady, setSdkReady] = useState(false);

  const emailRef = useRef(email);
  const cardholderRef = useRef(cardholder);
  const targetUrlRef = useRef(targetUrl);
  const tosAgreedRef = useRef(tosAgreed);

  useEffect(() => { emailRef.current = email; }, [email]);
  useEffect(() => { cardholderRef.current = cardholder; }, [cardholder]);
  useEffect(() => { targetUrlRef.current = targetUrl; }, [targetUrl]);
  useEffect(() => { tosAgreedRef.current = tosAgreed; }, [tosAgreed]);

  // Keep target URL and email in sync if default props arrive
  useEffect(() => {
    if (defaultTargetUrl && !targetUrl) {
      setTargetUrl(defaultTargetUrl);
    }
  }, [defaultTargetUrl]);

  useEffect(() => {
    if (defaultEmail && !email) {
      setEmail(defaultEmail);
    }
  }, [defaultEmail]);

  // Render official PayPal Buttons when modal is opened
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    if (!isOpen) {
      setSdkReady(false);
      setLoadError(null);
      return;
    }

    let isMounted = true;
    let buttonsInstance = null;
    let retryCount = 0;

    const renderPayPal = () => {
      if (!isMounted) return;

      const clientId = window.__PAYPAL_CLIENT_ID__ || 'BAAa18mhTonKniN6UJij6PasfiTBu0_sQgMKP9XwyMeXtBurHvoUD4YkDD09KTmC8RHwVTpOW_qbqalGkY';

      // Ensure SDK script tag exists in document.head
      if (!window.paypal || !window.paypal.Buttons) {
        let script = document.getElementById('paypal-js-sdk');
        if (!script) {
          script = document.createElement('script');
          script.id = 'paypal-js-sdk';
          script.src = `https://www.paypal.com/sdk/js?client-id=${clientId}&currency=USD`;
          script.onload = () => { if (isMounted) renderPayPal(); };
          script.onerror = () => { if (isMounted) setLoadError('Unable to reach PayPal servers. Please check your network or disable content blockers.'); };
          document.head.appendChild(script);
        }

        if (retryCount < 20) {
          retryCount++;
          setTimeout(() => {
            if (isMounted) renderPayPal();
          }, 350);
        } else {
          setLoadError('PayPal checkout took too long to load. Please refresh the page or try again.');
        }
        return;
      }

      const container = document.getElementById('paypal-button-container');
      if (!container) return;
      container.innerHTML = '';

      try {
        buttonsInstance = window.paypal.Buttons({
          style: {
            layout: 'vertical',
            color: 'gold',
            shape: 'rect',
            label: 'pay',
            height: 48,
          },
          createOrder: async (data, actions) => {
            if (!tosAgreedRef.current) {
              showToast('Please check the box to agree to the Statement of Work & Terms of Service.', 'error');
              throw new Error('SOW agreement required');
            }
            if (!emailRef.current || !emailRef.current.includes('@')) {
              showToast('Please enter a valid company billing email address.', 'error');
              throw new Error('Valid email required');
            }
            if (!targetUrlRef.current || !targetUrlRef.current.trim()) {
              showToast('Please confirm or enter your target registry URL.', 'error');
              throw new Error('Target URL required');
            }

            try {
              // Primary: Request server-side PayPal Order ID
              const res = await fetch(`/api/paypal/create-order/${slug}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  deposit_amount: 99.00,
                  email: emailRef.current,
                  cardholder: cardholderRef.current || companyName,
                  target_url: targetUrlRef.current.trim(),
                }),
              });
              if (res.ok) {
                const orderData = await res.json();
                if (orderData.order_id) {
                  return orderData.order_id;
                }
              }
            } catch (serverErr) {
              console.warn('Backend PayPal order creation fallback to client:', serverErr);
            }

            // Fallback: Client-side SDK order creation
            return actions.order.create({
              purchase_units: [{
                description: `LeadOps $99 Setup Sprint Refundable Deposit - ${companyName || 'Custom Feed'}`,
                custom_id: 'deposit',
                invoice_id: `setup-${slug}`,
                amount: {
                  currency_code: 'USD',
                  value: '99.00',
                  breakdown: {
                    item_total: {
                      currency_code: 'USD',
                      value: '99.00',
                    }
                  }
                },
                items: [{
                  name: '$99 Setup Sprint Refundable Deposit',
                  description: '100% credited toward Month 1 ($151 net balance due only upon >=95% QA pass)',
                  unit_amount: {
                    currency_code: 'USD',
                    value: '99.00',
                  },
                  quantity: '1',
                }],
              }],
              application_context: {
                shipping_preference: 'NO_SHIPPING',
                user_action: 'PAY_NOW',
                brand_name: 'LeadOps / OmniLeadFeeder',
              }
            });
          },
          onApprove: async (data, actions) => {
            setIsProcessing(true);
            showToast('✓ Authorizing $99.00 Refundable Deposit...', 'info');

            try {
              let captureId = data.orderID;

              // Primary: Capture PayPal Order on server side
              try {
                const captureRes = await fetch(`/api/paypal/capture-order/${slug}`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    order_id: data.orderID,
                    email: emailRef.current,
                    cardholder: cardholderRef.current || companyName,
                    target_url: targetUrlRef.current.trim(),
                  }),
                });
                if (captureRes.ok) {
                  const captureData = await captureRes.json();
                  captureId = captureData.capture_id || data.orderID;
                }
              } catch (srvCaptureErr) {
                console.warn('Server capture fallback:', srvCaptureErr);
                const orderDetails = await actions.order.capture();
                captureId =
                  orderDetails?.purchase_units?.[0]?.payments?.captures?.[0]?.id ||
                  orderDetails?.id ||
                  data.orderID;
              }

              const res = await payDeposit(slug, {
                email: emailRef.current,
                cardholder: cardholderRef.current || companyName,
                targetUrl: targetUrlRef.current.trim(),
                paypalOrderId: captureId,
                depositAmount: 99.0,
              });

              showToast('✓ Down Payment Secured ($99.00)! SOW Signed & Autonomous Swarm Initiated!', 'success', 6000);
              if (res.lead_id) {
                localStorage.setItem('leadops_active_lead_id', res.lead_id);
              }
              onClose();
              navigate(`/checkout/success?lead_id=${res.lead_id || slug}&slug=${slug}`);
            } catch (err) {
              console.error('PayPal onApprove error:', err);
              showToast(`Error securing payment: ${err.message}`, 'error');
            } finally {
              setIsProcessing(false);
            }
          },
          onError: (err) => {
            console.error('PayPal transaction error:', err);
            showToast('PayPal could not complete the transaction. Please check your payment method or try again.', 'error');
          },
          onCancel: () => {
            showToast('Payment window closed. Your setup sprint is saved and waiting.', 'info');
          }
        });

        if (isMounted && container) {
          buttonsInstance.render('#paypal-button-container');
          setSdkReady(true);
        }
      } catch (err) {
        console.error('Failed to render PayPal Buttons:', err);
        setLoadError('Failed to initialize PayPal Buttons. Please reload.');
      }
    };

    renderPayPal();

    return () => {
      isMounted = false;
      if (buttonsInstance && buttonsInstance.close) {
        try { buttonsInstance.close(); } catch (e) {}
      }
    };
  }, [isOpen, slug, companyName, showToast, onClose, navigate]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '540px' }}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div style={{ textAlign: 'center', marginBottom: '18px' }}>
          <div style={{ fontSize: '32px', marginBottom: '6px' }}>🛡️</div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff' }}>
            Authorize $99 Setup Sprint Refundable Down Payment
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Statement of Work (SOW) for <b style={{ color: 'var(--cyan)' }}>{companyName}</b> • <span style={{ color: 'var(--green)', fontWeight: 700 }}>100% Credited to Month 1</span>
          </div>
        </div>

        {/* Down Payment Terms Box */}
        <div style={{ background: 'var(--card-alt)', border: '1px solid var(--border)', borderRadius: '8px', padding: '14px', marginBottom: '16px', fontSize: '12px', lineHeight: 1.6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Milestone #1 Setup Sprint Down Payment:</span>
            <span style={{ color: '#fff', fontWeight: 800, fontFamily: 'var(--mono)' }}>$99.00 USD (Due Now, 100% Refundable)</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Milestone #2 Final Balance:</span>
            <span style={{ color: 'var(--cyan)', fontFamily: 'var(--mono)', fontWeight: 600 }}>$151.00 ($250 plan − $99 credit; due ONLY upon QA pass)</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Recurring Delivery Retainer:</span>
            <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>$250.00/month begins 30 days after live delivery</span>
          </div>
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '6px', marginTop: '6px', color: 'var(--green)', fontWeight: 600, fontSize: '11px' }}>
            ✓ 100% Refundable Guarantee: Your $99 down payment is 100% credited to Month 1. If our 7-agent dev swarm does not deliver verified live data with &gt;=95% accuracy within 24 hours, it is immediately refunded in full.
          </div>
        </div>

        {/* Form Details */}
        <div style={{ marginBottom: '14px' }}>
          {/* Target Public Records / Docket Source URL Verification */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.08), rgba(99, 102, 241, 0.08))',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '8px',
            padding: '12px',
            marginBottom: '12px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
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

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, marginBottom: '4px', color: '#fff' }}>
                Company / Billing Email *
              </label>
              <input
                type="email"
                required
                className="form-input"
                placeholder="alex@yourcompany.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ fontSize: '12px' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, marginBottom: '4px', color: '#fff' }}>
                Authorized Contact / Signer *
              </label>
              <input
                type="text"
                required
                className="form-input"
                placeholder="Jane Doe"
                value={cardholder}
                onChange={(e) => setCardholder(e.target.value)}
                style={{ fontSize: '12px' }}
              />
            </div>
          </div>

          {/* Explicit Mandatory SOW & Terms Checkbox */}
          <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px 12px', marginBottom: '16px' }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer', fontSize: '11px', color: '#cbd5e1', lineHeight: 1.4 }}>
              <input
                type="checkbox"
                checked={tosAgreed}
                onChange={(e) => setTosAgreed(e.target.checked)}
                style={{ marginTop: '2px', accentColor: 'var(--cyan)' }}
              />
              <span>
                <b>I agree to the Statement of Work (SOW) &amp; Terms:</b> I authorize the $99.00 refundable down payment (100% credited to Month 1; $151 balance due only upon &gt;=95% QA pass). Auto-refunded if unfulfilled within 24 hours.
              </span>
            </label>
            <div style={{ display: 'flex', gap: '10px', marginTop: '4px', fontSize: '10px', color: 'var(--text-muted)', paddingLeft: '22px' }}>
              <a href="/terms" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--cyan)', textDecoration: 'underline' }}>
                📄 Statement of Work &amp; Terms
              </a>
              <span>•</span>
              <a href="/privacy" target="_blank" rel="noopener noreferrer" style={{ color: 'var(--cyan)', textDecoration: 'underline' }}>
                🔒 Privacy Policy
              </a>
            </div>
          </div>
        </div>

        {/* Official PayPal Checkout Buttons Container */}
        <div style={{ minHeight: '120px', marginTop: '12px' }}>
          {loadError ? (
            <div style={{ textAlign: 'center', padding: '16px', color: '#f87171', fontSize: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.25)' }}>
              ⚠️ {loadError}
              <div style={{ marginTop: '8px' }}>
                <button
                  type="button"
                  onClick={() => window.location.reload()}
                  className="btn btn-secondary"
                  style={{ fontSize: '11px', padding: '4px 12px' }}
                >
                  Reload Page
                </button>
              </div>
            </div>
          ) : !sdkReady && !isProcessing ? (
            <div style={{ textAlign: 'center', padding: '16px', color: 'var(--text-muted)', fontSize: '12px' }}>
              <div className="spinner" style={{ width: '24px', height: '24px', margin: '0 auto 8px' }}></div>
              Connecting to secure PayPal checkout...
            </div>
          ) : null}

          {sdkReady && !isProcessing && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '8px' }}>
              Select payment method below to authorize $99 refundable down payment:
            </div>
          )}

          <div id="paypal-button-container"></div>
        </div>

        <div style={{ textAlign: 'center', marginTop: '14px', borderTop: '1px solid var(--border)', paddingTop: '10px', fontSize: '10px', color: 'var(--text-dim)' }}>
          🔒 256-Bit Encrypted Payment • PayPal, Visa, Mastercard, AMEX &amp; Discover Accepted
        </div>
      </div>
    </div>
  );
}
