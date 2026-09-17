import React from 'react';
import { PACKAGES } from './packages';

export default function PackageSelector({ selectedPlanId, onSelectPlan }) {
  return (
    <div style={{ marginBottom: '32px' }}>
      <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: 'var(--cyan)', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '12px' }}>
        Selected Ingestion Package
      </label>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
        {PACKAGES.map((pkg) => {
          const isSelected = pkg.id === selectedPlanId;
          return (
            <div
              key={pkg.id}
              onClick={() => onSelectPlan(pkg.id)}
              style={{
                padding: '16px 18px',
                borderRadius: '10px',
                background: isSelected ? 'rgba(56, 189, 248, 0.08)' : 'rgba(15, 23, 42, 0.6)',
                border: isSelected ? '2px solid var(--cyan)' : '1px solid #1e3355',
                cursor: 'pointer',
                transition: 'all 0.2s',
                position: 'relative',
                boxShadow: isSelected ? '0 0 20px rgba(56, 189, 248, 0.15)' : 'none',
              }}
            >
              {pkg.badge && (
                <span style={{
                  position: 'absolute',
                  top: '-10px',
                  right: '12px',
                  background: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
                  color: '#fff',
                  fontSize: '9px',
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: '10px',
                  letterSpacing: '0.5px',
                }}>
                  {pkg.badge}
                </span>
              )}
              <div style={{ fontSize: '14px', fontWeight: 800, color: '#fff', marginBottom: '4px' }}>
                {pkg.name}
              </div>
              <div style={{ fontSize: '18px', fontWeight: 900, color: isSelected ? 'var(--cyan)' : '#e2e8f0', marginBottom: '8px' }}>
                {pkg.price}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--cyan)', fontWeight: 600, marginBottom: '2px' }}>
                ⏱️ {pkg.cadence}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginBottom: '8px' }}>
                📊 {pkg.records}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                {pkg.desc}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
