import React, { useState } from 'react';
import { useToast } from '../../context/ToastContext';

export default function BuyoutTab({ leadId, dashState }) {
  const { showToast } = useToast();
  const [isUnlocked, setIsUnlocked] = useState(dashState?.buyout_paid || false);

  const handleSimulateBuyout = () => {
    setIsUnlocked(true);
    showToast('🎉 Codebase Buyout Unlocked! Standalone package ready for download.', 'success');
  };

  const handleDownloadZip = () => {
    showToast('Downloading standalone Playwright extractor bundle (.zip)...', 'info');
    window.location.href = `/api/dashboard/${leadId}/buyout-bundle`;
  };

  return (
    <div className="card">
      <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
        📦 Standalone Extractor Codebase Buyout ($1,500 One-Time)
      </h3>
      <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '24px', lineHeight: 1.6 }}>
        Zero vendor lock-in. You can buy out the complete, self-contained Python Playwright extraction engine for your jurisdiction. Run it forever on your own Docker or Kubernetes infrastructure.
      </p>

      {isUnlocked ? (
        <div style={{ background: 'var(--green-glow)', border: '1px solid var(--green)', borderRadius: '10px', padding: '24px', textAlign: 'center' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔓</div>
          <h4 style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>
            Perpetual Source Code License Active
          </h4>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '8px auto 16px', maxWidth: '480px' }}>
            Includes clean, typed Python 3.11+ source code, Playwright selectors, anti-bot stealth configurations, Dockerfile, and CLI runner.
          </p>
          <button className="btn btn-primary" onClick={handleDownloadZip}>
            📥 Download Extractor Source (.zip)
          </button>
        </div>
      ) : (
        <div style={{ background: 'var(--card-alt)', border: '1px solid var(--border)', borderRadius: '10px', padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <div style={{ fontSize: '24px', fontWeight: 800, color: '#fff', fontFamily: 'var(--mono)' }}>
                $1,500.00 USD
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                One-time perpetual license with commercial ownership rights.
              </div>
            </div>

            <button className="btn btn-purple" onClick={handleSimulateBuyout}>
              💳 Purchase Source Code Buyout ($1,500)
            </button>
          </div>

          <div style={{ marginTop: '20px', borderTop: '1px solid var(--border)', paddingTop: '16px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <div>✓ Full Python + Playwright code</div>
            <div>✓ Dockerfile &amp; requirements.txt</div>
            <div>✓ Standalone CLI runner script</div>
            <div>✓ Custom county DOM selectors</div>
          </div>
        </div>
      )}
    </div>
  );
}
