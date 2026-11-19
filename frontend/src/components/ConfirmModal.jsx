import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';

export default function ConfirmModal({
  isOpen,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmText = 'Delete',
  cancelText = 'Cancel',
  isDestructive = true,
  isBusy = false,
  onConfirm,
  onCancel,
}) {
  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px',
      }}
      onClick={onCancel}
    >
      <div
        className="glass-card"
        style={{
          width: '100%',
          maxWidth: '440px',
          padding: '24px',
          borderRadius: '12px',
          border: isDestructive ? '1px solid rgba(244, 63, 94, 0.4)' : '1px solid var(--border-subtle)',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.6)',
          backgroundColor: '#0c0f14',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          {isDestructive ? (
            <AlertTriangle size={20} color="var(--accent-rose)" />
          ) : (
            <Info size={20} color="var(--accent-cyan)" />
          )}
          <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {title}
          </h3>
        </div>

        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: 1.5, marginBottom: '24px' }}>
          {message}
        </p>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onCancel}
            disabled={isBusy}
            style={{ padding: '8px 16px' }}
          >
            {cancelText}
          </button>
          <button
            type="button"
            className={`btn btn-sm ${isDestructive ? 'btn-rose' : 'btn-cyan'}`}
            onClick={onConfirm}
            disabled={isBusy}
            style={{
              padding: '8px 18px',
              backgroundColor: isDestructive ? 'var(--accent-rose)' : undefined,
              color: '#fff',
            }}
          >
            {isBusy ? 'Processing...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

