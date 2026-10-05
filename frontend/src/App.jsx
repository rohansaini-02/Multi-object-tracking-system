import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import TopHeader from './components/TopHeader';

import CommandCenter from './pages/CommandCenter';
import UploadIngest from './pages/UploadIngest';
import DetectionWorkspace from './pages/DetectionWorkspace';
import MOT17Benchmark from './pages/MOT17Benchmark';
import JobHistory from './pages/JobHistory';
import Login from './pages/Login';

export default function App() {
  const [activePage, setActivePage] = useState('command-center');
  const [selectedJobId, setSelectedJobId] = useState('job-101');
  const [uploadedVideoUrl, setUploadedVideoUrl] = useState(null);

  const renderPage = () => {
    switch (activePage) {
      case 'command-center':
        return <CommandCenter setActivePage={setActivePage} setSelectedJobId={setSelectedJobId} />;
      case 'ingest':
      case 'upload':
        return <UploadIngest setActivePage={setActivePage} setSelectedJobId={setSelectedJobId} setUploadedVideoUrl={setUploadedVideoUrl} />;
      case 'workspace':
      case 'results':
        return <DetectionWorkspace selectedJobId={selectedJobId} uploadedVideoUrl={uploadedVideoUrl} />;
      case 'benchmark':
        return <MOT17Benchmark setActivePage={setActivePage} setSelectedJobId={setSelectedJobId} />;
      case 'history':
      case 'dashboard':
        return <JobHistory setActivePage={setActivePage} setSelectedJobId={setSelectedJobId} />;
      case 'login':
        return <Login setActivePage={setActivePage} />;
      case 'config':
        return (
          <div className="glass-card" style={{ padding: '32px' }}>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px' }}>
              Operational Configuration
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              System environment settings, GPU acceleration parameters, and API integration tokens.
            </p>
            <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: '6px' }}>
                <span style={{ fontWeight: 600 }}>Backend API Host:</span> <code className="font-mono" style={{ color: 'var(--accent-cyan)' }}>http://localhost:8000/api/v1</code>
              </div>
              <div style={{ padding: '16px', background: 'var(--bg-elevated)', borderRadius: '6px' }}>
                <span style={{ fontWeight: 600 }}>Inference Device:</span> <code className="font-mono" style={{ color: 'var(--accent-emerald)' }}>CUDA (NVIDIA RTX 4090 / CUDA 12.2)</code>
              </div>
            </div>
          </div>
        );
      default:
        return <CommandCenter setActivePage={setActivePage} setSelectedJobId={setSelectedJobId} />;
    }
  };

  return (
    <div className="app-layout">
      {/* Left Vertical Sidebar */}
      <Sidebar activePage={activePage} setActivePage={setActivePage} />

      {/* Main Right Content Workspace */}
      <div className="main-wrapper">
        <TopHeader />
        <main className="page-content">
          {renderPage()}
        </main>
      </div>
    </div>
  );
}
