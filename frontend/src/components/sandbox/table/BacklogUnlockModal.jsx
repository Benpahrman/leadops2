import React from 'react';

export default function BacklogUnlockModal({
  isOpen,
  onClose,
  companyName,
  email,
  setEmail,
  backlogPaypalReady,
  backlogPaypalError,
  isProcessing,
}) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <button className="modal-close" onClick={onClose}>✕</button>

        <div style={{ textAlign: 'center', marginBottom: '18px' }}>
          <div style={{
            width: '44px', height: '44px', borderRadius: '50%',
            background: 'rgba(56, 189, 248, 0.12)', border: '1px solid rgba(56, 189, 248, 0.3)',
            display: 'grid', placeItems: 'center', margin: '0 auto 12px', color: 'var(--cyan)',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </div>
          <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff' }}>
            Instant Backlog Unlock: 30-Day Records ($49)
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Full Historical Dataset for <b style={{ color: 'var(--cyan)' }}>{companyName}</b>
          </div>
        </div>

        {/* Value Highlights Box */}
        <div style={{ background: 'var(--card-alt)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', marginBottom: '20px', fontSize: '12px', lineHeight: 1.6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Historical Depth:</span>
            <span style={{ color: '#fff', fontWeight: 700, fontFamily: 'var(--mono)' }}>Past 30 Days (200–500 Rows)</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-muted)' }}>Delivery Format:</span>
            <span style={{ color: 'var(--cyan)', fontWeight: 700, fontFamily: 'var(--mono)' }}>Instant CSV Download</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-muted)' }}>One-Time Cost:</span>
            <span style={{ color: 'var(--green)', fontWeight: 800, fontFamily: 'var(--mono)', fontSize: '14px' }}>$49.00 USD</span>
          </div>
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '8px', marginTop: '8px', color: 'var(--green)', fontWeight: 600 }}>
            100% Credited: Upgrade to an automated daily feed anytime, and your $49 is credited toward your setup sprint!
          </div>
        </div>

        {/* Billing Email */}
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#fff' }}>
            Delivery / Work Email *
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

        {/* PayPal Buttons Container */}
        <div style={{ minHeight: '100px' }}>
          {backlogPaypalError ? (
            <div style={{ textAlign: 'center', padding: '14px', color: '#f87171', fontSize: '12px', background: 'rgba(239,68,68,0.1)', borderRadius: '8px', border: '1px solid rgba(239,68,68,0.25)' }}>
              ⚠️ {backlogPaypalError}
              <div style={{ marginTop: '8px' }}>
                <button type="button" onClick={() => window.location.reload()} className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 12px' }}>Reload Page</button>
              </div>
            </div>
          ) : !backlogPaypalReady && !isProcessing ? (
            <div style={{ textAlign: 'center', padding: '14px', color: 'var(--text-muted)', fontSize: '12px' }}>
              <div className="spinner" style={{ width: '22px', height: '22px', margin: '0 auto 8px' }}></div>
              Connecting to secure PayPal checkout...
            </div>
          ) : null}
          {backlogPaypalReady && !isProcessing && (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '8px' }}>
              Select payment method below to pay $49 and instantly download your backlog:
            </div>
          )}
          <div id="paypal-backlog-button-container"></div>
        </div>

        <div style={{ textAlign: 'center', marginTop: '14px', borderTop: '1px solid var(--border)', paddingTop: '10px', fontSize: '10px', color: 'var(--text-dim)' }}>
          🔒 256-Bit Encrypted Payment • PayPal, Visa, Mastercard, AMEX &amp; Discover Accepted
        </div>
      </div>
    </div>
  );
}
