import React from 'react';

export default function ScoutLoadingOverlay({
  loadingProgress,
  loadingStage,
  loadingLogs,
  targetUrl,
}) {
  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(5, 10, 20, 0.88)',
      backdropFilter: 'blur(8px)',
      zIndex: 9999,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
    }}>
      <div style={{
        background: '#0c1322',
        border: '1px solid rgba(56, 189, 248, 0.3)',
        borderRadius: '14px',
        maxWidth: '560px',
        width: '100%',
        padding: '32px',
        textAlign: 'left',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.7), 0 0 30px rgba(56, 189, 248, 0.2)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: 'var(--cyan)',
              boxShadow: '0 0 10px var(--cyan)',
              animation: 'pulse 1.2s infinite',
            }} />
            <span style={{ fontSize: '13px', fontWeight: 800, color: 'var(--cyan)', textTransform: 'uppercase', letterSpacing: '0.6px' }}>
              AI Scout Swarm Active
            </span>
          </div>
          <span style={{ fontSize: '14px', fontWeight: 800, color: '#fff', fontFamily: 'var(--mono)' }}>
            {loadingProgress}%
          </span>
        </div>

        <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>
          Harvesting 5–10 Live Records from Target Source
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px', lineHeight: 1.5 }}>
          Target: <b style={{ color: '#fff' }}>{targetUrl || 'Regional Public Registry'}</b>
        </p>

        {/* Progress Bar */}
        <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '16px' }}>
          <div
            style={{
              width: `${loadingProgress}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #38bdf8, #10b981)',
              transition: 'width 0.4s ease',
            }}
          />
        </div>

        {/* Current Stage Headline */}
        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--cyan)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--cyan)' }} />
          {loadingStage}
        </div>

        {/* Live Terminal Telemetry */}
        <div style={{
          background: '#050a14',
          border: '1px solid rgba(56, 189, 248, 0.15)',
          borderRadius: '8px',
          padding: '12px 14px',
          fontFamily: 'var(--mono)',
          fontSize: '11px',
          color: '#94a3b8',
          lineHeight: 1.6,
          maxHeight: '120px',
          overflowY: 'auto',
        }}>
          {loadingLogs.map((log, idx) => (
            <div key={idx}>
              <span style={{ color: 'var(--text-dim)' }}>[{log.time}]</span> {log.text}
            </div>
          ))}
        </div>

        <div style={{ textAlign: 'center', marginTop: '18px', fontSize: '11px', color: 'var(--text-dim)' }}>
          Connecting directly to live source • Zero mock data standard enforced
        </div>
      </div>
    </div>
  );
}
