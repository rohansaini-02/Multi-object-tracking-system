import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';

import CommandCenter from './pages/CommandCenter';
import UploadIngest from './pages/UploadIngest';
import DetectionWorkspace from './pages/DetectionWorkspace';
import MOT17Benchmark from './pages/MOT17Benchmark';
import JobHistory from './pages/JobHistory';
import ModelTraining from './pages/ModelTraining';
import Login from './pages/Login';

import { getCurrentUserApi, getToken, logoutApi, API_BASE_URL, getHealthApi } from './api/client';

function SettingsView() {
  const [healthInfo, setHealthInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getHealthApi().then((data) => {
      if (!cancelled) {
        setHealthInfo(data);
        setIsLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const device = healthInfo?.device || (isLoading ? 'Detecting device...' : 'Offline (Cannot query device)');
  const status = healthInfo?.status === 'ok' ? 'Online' : (isLoading ? 'Checking...' : 'Disconnected');
  const version = healthInfo?.version ? `v${healthInfo.version}` : '—';

  return (
    <div className="glass-card" style={{ padding: '32px' }}>
      <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px' }}>
        Settings
      </h1>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
        System settings, hardware preferences, and API connections.
      </p>
      <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: '6px' }}>
          <span style={{ fontWeight: 600 }}>Backend API Host:</span>{' '}
          <code className="font-mono" style={{ color: 'var(--accent-cyan)' }}>{API_BASE_URL}</code>
        </div>
        <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: '6px' }}>
          <span style={{ fontWeight: 600 }}>Inference Device:</span>{' '}
          <code className="font-mono" style={{ color: healthInfo?.cuda_available ? 'var(--accent-emerald)' : 'var(--accent-amber)' }}>
            {device}
          </code>
        </div>
        <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: '6px' }}>
          <span style={{ fontWeight: 600 }}>Backend Status:</span>{' '}
          <span className={`badge ${healthInfo?.status === 'ok' ? 'badge-emerald' : 'badge-failed'}`}>
            • {status} ({version})
          </span>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [uploadedVideoUrl, setUploadedVideoUrl] = useState(null);
  const [clonedConfig, setClonedConfig] = useState(null);

  // Authentication state
  const [user, setUser] = useState(null);
  const [isAuthResolved, setIsAuthResolved] = useState(false);
  // Why the restore failed, surfaced on the login screen (e.g. backend down).
  const [authNotice, setAuthNotice] = useState('');

  const handleCloneJob = useCallback((jobConfig) => {
    setClonedConfig(jobConfig);
    setActivePage('ingest');
  }, []);

  // Restore the session from the persisted JWT on mount.
  useEffect(() => {
    let cancelled = false;

    const bootstrapAuth = async () => {
      const token = getToken();

      if (!token) {
        if (cancelled) return;
        setUser(null);
        setAuthNotice('');
        setActivePage('login');
        setIsAuthResolved(true);
        return;
      }

      // The gate below must always lift: a dead or booting backend used to
      // throw out of this await and leave the app on "Restoring session..."
      // forever. Distinguish "token rejected" (log out) from "backend
      // unreachable" (keep the token, show why).
      try {
        const profile = await getCurrentUserApi();
        if (cancelled) return;

        if (profile) {
          setUser(profile);
          setAuthNotice('');
          setActivePage('dashboard');
        } else {
          // Token was rejected (expired / revoked) -> force a fresh sign in.
          await logoutApi();
          if (cancelled) return;
          setUser(null);
          setAuthNotice('Your session expired. Please sign in again.');
          setActivePage('login');
        }
      } catch (err) {
        if (cancelled) return;
        console.warn('Session restore failed:', err.message);
        setUser(null);
        setAuthNotice(err.message || 'Could not reach the backend.');
        setActivePage('login');
      } finally {
        if (!cancelled) setIsAuthResolved(true);
      }
    };

    bootstrapAuth();

    const handleUnauthorized = () => {
      logoutApi();
      setUser(null);
      setSelectedJobId(null);
      setUploadedVideoUrl(null);
      setAuthNotice('Your session has expired. Please sign in again.');
      setActivePage('login');
    };

    window.addEventListener('mot:unauthorized', handleUnauthorized);

    return () => {
      cancelled = true;
      window.removeEventListener('mot:unauthorized', handleUnauthorized);
    };
  }, []);

  const handleAuthenticated = useCallback((profile) => {
    setUser(profile);
    setAuthNotice('');
    setActivePage('dashboard');
  }, []);

  const handleLogout = useCallback(async () => {
    await logoutApi();
    setUser(null);
    setSelectedJobId(null);
    setUploadedVideoUrl(null);
    setActivePage('login');
  }, []);

  const isAuthenticated = Boolean(user);

  const renderPage = () => {
    // Gate every protected page behind an active session.
    if (!isAuthenticated) {
      return (
        <Login
          setActivePage={setActivePage}
          onAuthenticated={handleAuthenticated}
          notice={authNotice}
        />
      );
    }

    switch (activePage) {
      case 'dashboard':
        return (
          <CommandCenter
            setActivePage={setActivePage}
            setSelectedJobId={setSelectedJobId}
            onCloneJob={handleCloneJob}
          />
        );
      case 'ingest':
      case 'upload':
        return (
          <UploadIngest
            setActivePage={setActivePage}
            setSelectedJobId={setSelectedJobId}
            setUploadedVideoUrl={setUploadedVideoUrl}
            clonedConfig={clonedConfig}
            setClonedConfig={setClonedConfig}
          />
        );
      case 'workspace':
      case 'results':
        return (
          <DetectionWorkspace
            selectedJobId={selectedJobId}
            uploadedVideoUrl={uploadedVideoUrl}
            onCloneJob={handleCloneJob}
            setActivePage={setActivePage}
          />
        );
      case 'benchmark':
        return <MOT17Benchmark />;
      case 'training':
      case 'models':
      case 'reid':
        return (
          <ModelTraining
            setActivePage={setActivePage}
            onSelectWeight={(weightPath) =>
              setClonedConfig((prev) => ({ ...(prev || {}), reidWeights: weightPath }))
            }
          />
        );
      case 'history':
        return (
          <JobHistory
            setActivePage={setActivePage}
            setSelectedJobId={setSelectedJobId}
            onCloneJob={handleCloneJob}
          />
        );
      case 'login':
        return (
          <Login
            setActivePage={setActivePage}
            onAuthenticated={handleAuthenticated}
            notice={authNotice}
          />
        );
      case 'config':
      case 'settings':
        return <SettingsView />;
      default:
        return (
          <CommandCenter
            setActivePage={setActivePage}
            setSelectedJobId={setSelectedJobId}
            onCloneJob={handleCloneJob}
          />
        );
    }
  };

  if (!isAuthResolved) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <div className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Restoring session...
        </div>
      </div>
    );
  }

  return (
    <div className="app-layout">
      {/* Left Vertical Sidebar */}
      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
        user={user}
        onLogout={handleLogout}
      />

      {/* Main Right Content Workspace */}
      <div className="main-wrapper">
        <TopHeader activePage={activePage} setActivePage={setActivePage} />
        <main className="page-content">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}
