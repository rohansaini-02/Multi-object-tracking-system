import React from 'react';

export default function Navbar({ activePage, setActivePage }) {
  const navItems = [
    { id: 'home', label: 'Home' },
    { id: 'upload', label: 'Upload & Track' },
    { id: 'results', label: 'Results' },
    { id: 'benchmark', label: 'MOT17 Benchmark Performance' },
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'login', label: 'Login' },
  ];

  return (
    <nav className="navbar">
      <div 
        className="nav-brand" 
        onClick={() => setActivePage('home')}
        style={{ cursor: 'pointer' }}
      >
        <span style={{ fontSize: '1.5rem' }}>🎯</span>
        <span>TrackPulse MOT</span>
      </div>
      
      <div className="nav-links">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActivePage(item.id)}
            className={`nav-link ${activePage === item.id ? 'active' : ''}`}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: activePage === item.id ? 600 : 400,
              color: activePage === item.id ? 'var(--primary)' : 'var(--text-secondary)',
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
