import React, { useState } from 'react';

export default function Login({ setActivePage }) {
  const [email, setEmail] = useState('alex.mercer@visionops.io');
  const [password, setPassword] = useState('••••••••');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (setActivePage) setActivePage('command-center');
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 'calc(100vh - 120px)' }}>
      <div className="glass-card" style={{ width: '100%', maxWidth: '420px', padding: '36px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '10px',
            border: '1px solid var(--accent-cyan)',
            backgroundColor: 'rgba(0, 229, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justify: 'center',
            fontSize: '1.5rem',
            color: 'var(--accent-cyan)',
            margin: '0 auto 12px auto',
            boxShadow: '0 0 16px rgba(0, 229, 255, 0.25)'
          }}>
            ⌖
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>MOT Vision Authentication</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginTop: '4px' }}>
            Sign in to access tracking operation telemetry & models
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              OPERATOR EMAIL
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="font-mono"
              style={{
                width: '100%',
                padding: '12px 14px',
                borderRadius: '6px',
                backgroundColor: 'var(--bg-elevated)',
                border: '1px solid var(--border-strong)',
                color: 'var(--text-primary)',
                outline: 'none',
                fontSize: '0.85rem'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
              PASSWORD
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="font-mono"
              style={{
                width: '100%',
                padding: '12px 14px',
                borderRadius: '6px',
                backgroundColor: 'var(--bg-elevated)',
                border: '1px solid var(--border-strong)',
                color: 'var(--text-primary)',
                outline: 'none',
                fontSize: '0.85rem'
              }}
            />
          </div>

          <button type="submit" className="btn btn-cyan" style={{ marginTop: '8px', padding: '12px', justifyContent: 'center' }}>
            Authenticate Operator →
          </button>
        </form>
      </div>
    </div>
  );
}
