import React from 'react';
import { useToast } from '../../context/ToastContext';

export default function ReferralTab({ leadId, dashState }) {
  const { showToast } = useToast();
  const referralLink = `${window.location.origin}/p/${dashState?.slug || leadId}?ref=${leadId}`;

  const copyLink = () => {
    navigator.clipboard.writeText(referralLink);
    showToast('Colleague referral link copied to clipboard! ($100 credit)', 'success');
  };

  const shareLinkedIn = () => {
    const text = encodeURIComponent(
      `We automated our county public records extractions using OmniLeadFeeder. Zero manual portal searches, automated daily feed delivery, and escrow-protected crawlers. Explore a live sandbox here (includes $50 setup discount):`
    );
    const url = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(referralLink)}&summary=${text}`;
    window.open(url, '_blank', 'width=600,height=500');
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>
            🎁 Colleague Referral Program
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Give $50 off setup to a partner or colleague; earn <b>$100 in feed credits</b> when they activate.
          </p>
        </div>

        <div style={{ background: 'var(--card-alt)', border: '1px solid var(--border)', borderRadius: '8px', padding: '8px 16px', textAlign: 'right' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Credit Balance:</div>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--green)', fontFamily: 'var(--mono)' }}>
            ${(dashState?.credits?.balance_usd || 0).toFixed(2)} USD
          </div>
        </div>
      </div>

      <div style={{ background: 'var(--card-alt)', border: '1px solid var(--border)', borderRadius: '8px', padding: '16px', marginBottom: '20px' }}>
        <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, marginBottom: '6px', color: '#fff' }}>
          Your Unique Colleague Invite Link
        </label>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            readOnly
            className="form-input"
            value={referralLink}
            style={{ fontFamily: 'var(--mono)', fontSize: '12px' }}
          />
          <button className="btn btn-primary" onClick={copyLink}>
            Copy Link
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px' }}>
        <button className="btn btn-outline" onClick={shareLinkedIn}>
          Share on LinkedIn
        </button>
        <button
          className="btn btn-outline"
          onClick={() => {
            const body = encodeURIComponent(
              `Hi,\n\nI thought of your team when setting up our automated public records stream with OmniLeadFeeder.\n\nYou can explore a live 25-row sandbox for your jurisdiction and get $50 off your setup with our colleague invite link:\n${referralLink}\n\nBest,`
            );
            window.location.href = `mailto:?subject=${encodeURIComponent('Automated County Data Feeds for your team')}&body=${body}`;
          }}
        >
          Email Invitation
        </button>
      </div>
    </div>
  );
}
