import React from 'react';

export default function TestResultBanner({ testResult }) {
  if (!testResult) return null;

  return (
    <div
      style={{
        marginTop: '16px',
        padding: '12px 16px',
        borderRadius: '8px',
        background: testResult.ok ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
        border: `1px solid ${testResult.ok ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px',
      }}
    >
      <span style={{ fontSize: '18px' }}>{testResult.ok ? '✅' : '❌'}</span>
      <div style={{ fontSize: '13px', lineHeight: 1.5 }}>
        <div style={{ fontWeight: 700, color: testResult.ok ? 'var(--green)' : '#f87171' }}>
          {testResult.ok ? 'Connection Verified' : 'Connection Verification Issue'}
        </div>
        <div style={{ color: '#cbd5e1', marginTop: '2px' }}>{testResult.message}</div>
      </div>
    </div>
  );
}
