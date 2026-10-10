import React from 'react';
import { 
  LayoutDashboard, 
  Eye, 
  UploadCloud, 
  BarChart3, 
  History, 
  Settings, 
  Target, 
  LogOut,
  Star
} from 'lucide-react';

export default function Sidebar({ activePage, setActivePage }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'workspace', label: 'Tracking Viewer', icon: Eye, star: true },
    { id: 'ingest', label: 'Upload Video', icon: UploadCloud },
    { id: 'benchmark', label: 'MOT17 Benchmark', icon: BarChart3 },
    { id: 'history', label: 'History', icon: History, badge: '2' },
    { id: 'config', label: 'Settings', icon: Settings },
  ];

  return (
    <aside style={{
      width: '240px',
      height: '100vh',
      backgroundColor: 'var(--bg-sidebar)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      justify: 'space-between',
      flexShrink: 0,
      zIndex: 10,
    }}>
      {/* Top Section */}
      <div>
        {/* Brand Header */}
        <div style={{
          padding: '20px 18px 16px 18px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            border: '1px solid var(--accent-cyan)',
            backgroundColor: 'rgba(0, 229, 255, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1rem',
            color: 'var(--accent-cyan)',
            boxShadow: '0 0 10px rgba(0, 229, 255, 0.2)'
          }}>
            ⌖
          </div>
          <div>
            <div style={{
              fontFamily: 'var(--font-heading)',
              fontWeight: 800,
              fontSize: '0.95rem',
              color: 'var(--text-primary)',
              letterSpacing: '0.04em',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              Multi-Object Tracker <span className="font-mono" style={{ fontSize: '0.6rem', color: 'var(--text-muted)', background: 'var(--bg-elevated)', padding: '1px 4px', borderRadius: '3px' }}>v0.1.0</span>
            </div>
            <div className="font-mono" style={{ fontSize: '0.6rem', color: 'var(--accent-cyan)', letterSpacing: '0.04em', marginTop: '3px', fontWeight: 600 }}>
              DETECTION & TRACKING PLATFORM
            </div>
          </div>
        </div>

        {/* Section Title */}
        <div className="font-mono" style={{
          padding: '16px 18px 8px 18px',
          fontSize: '0.65rem',
          color: 'var(--text-muted)',
          letterSpacing: '0.12em',
          fontWeight: 600
        }}>
          MAIN MENU
        </div>

        {/* Navigation Items */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '0 10px' }}>
          {navItems.map((item) => {
            const isActive = activePage === item.id;
            const IconComponent = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justify: 'space-between',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: isActive ? '1px solid var(--border-cyan)' : '1px solid transparent',
                  backgroundColor: isActive ? 'var(--accent-cyan-bg)' : 'transparent',
                  color: isActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontWeight: isActive ? 600 : 400,
                  fontSize: '0.85rem',
                  fontFamily: 'var(--font-body)',
                  transition: 'all 0.15s ease',
                  textAlign: 'left',
                  width: '100%',
                }}
                className="nav-btn"
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <IconComponent size={16} />
                  <span>{item.label}</span>
                </div>
                {item.star && (
                  <Star size={12} fill="var(--accent-cyan)" color="var(--accent-cyan)" />
                )}
                {item.badge && (
                  <span className="font-mono" style={{
                    backgroundColor: 'rgba(245, 158, 11, 0.2)',
                    color: 'var(--accent-amber)',
                    border: '1px solid rgba(245, 158, 11, 0.4)',
                    fontSize: '0.65rem',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 700
                  }}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* User Profile Footer (Pinned to absolute bottom) */}
      <div style={{
        marginTop: 'auto',
        padding: '14px 16px',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justify: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            backgroundColor: 'var(--bg-elevated)',
            border: '1px solid var(--border-strong)',
            display: 'flex',
            alignItems: 'center',
            justify: 'center',
            fontSize: '0.8rem',
            fontWeight: 700,
            color: 'var(--accent-cyan)'
          }}>
            AM
          </div>
          <div style={{ overflow: 'hidden' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', textOverflow: 'ellipsis', overflow: 'hidden', whitespace: 'nowrap' }}>
              Dr. Alex Mercer
            </div>
            <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whitespace: 'nowrap' }}>
              alex.mercer@visionops...
            </div>
          </div>
        </div>
        <button 
          onClick={() => setActivePage('login')}
          title="Switch Account / Login"
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '0.9rem',
            padding: '4px'
          }}
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  );
}
