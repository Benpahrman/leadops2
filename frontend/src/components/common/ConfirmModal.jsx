import React, { useState, useEffect } from 'react';

export default function ConfirmModal({
  isOpen,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDestructive = false,
  requireMatch = null,
  hasInput = false,
  inputLabel = '',
  inputPlaceholder = '',
  inputDefaultValue = '',
  onConfirm,
  onClose,
}) {
  const [inputValue, setInputValue] = useState(inputDefaultValue);

  useEffect(() => {
    if (isOpen) {
      setInputValue(inputDefaultValue);
    }
  }, [isOpen, inputDefaultValue]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const isMatchValid = !requireMatch || inputValue.trim() === requireMatch;

  const handleConfirm = () => {
    if (!isMatchValid) return;
    onConfirm(inputValue);
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div
        className="admin-modal-content"
        style={{ maxWidth: '480px', padding: '24px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: isDestructive ? 'rgba(239, 68, 68, 0.15)' : 'rgba(56, 189, 248, 0.15)',
              color: isDestructive ? 'var(--red)' : 'var(--cyan)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '18px',
            }}
          >
            {isDestructive ? '⚠️' : '⚡'}
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#fff' }}>{title}</h2>
        </div>

        <div style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '16px' }}>
          {message}
        </div>

        {requireMatch && (
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-dim)', marginBottom: '6px' }}>
              Type <strong style={{ color: 'var(--red)' }}>{requireMatch}</strong> to confirm:
            </label>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={requireMatch}
              autoFocus
              style={{
                width: '100%',
                padding: '9px 12px',
                background: 'var(--bg)',
                border: `1px solid ${isMatchValid ? 'var(--border)' : 'rgba(239, 68, 68, 0.5)'}`,
                borderRadius: 'var(--radius-sm)',
                color: '#fff',
                fontSize: '13px',
                fontFamily: 'var(--mono)',
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && isMatchValid) handleConfirm();
              }}
            />
          </div>
        )}

        {hasInput && !requireMatch && (
          <div style={{ marginBottom: '16px' }}>
            {inputLabel && (
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-dim)', marginBottom: '6px' }}>
                {inputLabel}
              </label>
            )}
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={inputPlaceholder}
              autoFocus
              style={{
                width: '100%',
                padding: '9px 12px',
                background: 'var(--bg)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                color: '#fff',
                fontSize: '13px',
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleConfirm();
              }}
            />
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '8px' }}>
          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: '8px 16px', fontSize: '12px' }}
            onClick={onClose}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!isMatchValid}
            style={{
              padding: '8px 18px',
              fontSize: '12px',
              background: isDestructive ? 'var(--red)' : undefined,
              borderColor: isDestructive ? 'var(--red)' : undefined,
              opacity: isMatchValid ? 1 : 0.45,
              cursor: isMatchValid ? 'pointer' : 'not-allowed',
            }}
            onClick={handleConfirm}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
