import React from 'react';

export default function JobHistory({ setActivePage, setSelectedJobId }) {
  const historyList = [
    { id: 'job-101', name: 'crossroad_traffic_cam_04.mp4', status: 'COMPLETED', date: '2026-10-04 14:15', tracks: 38, fps: '29.8 FPS' },
    { id: 'job-103', name: 'night_highway_junction.mp4', status: 'COMPLETED', date: '2026-10-04 13:00', tracks: 52, fps: '28.4 FPS' },
    { id: 'job-104', name: 'subway_entrance_concourse.avi', status: 'FAILED', date: '2026-10-04 11:20', tracks: 0, fps: '-' },
    { id: 'job-099', name: 'pedestrian_mall_stream_01.mp4', status: 'COMPLETED', date: '2026-10-03 18:45', tracks: 19, fps: '31.2 FPS' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)' }}>
          Tracking Job Archive & History
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Historical record of all executed multi-object tracking inference runs.
        </p>
      </div>

      <div className="glass-card" style={{ padding: '20px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', backgroundColor: '#000000' }}>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>JOB ID</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>VIDEO NAME</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>STATUS</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>EXECUTION DATE</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem' }}>TOTAL TRACKS</th>
              <th className="font-mono" style={{ padding: '12px', color: 'var(--text-muted)', fontSize: '0.7rem', textAlign: 'right' }}>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {historyList.map((item) => (
              <tr key={item.id} style={{ borderBottom: '1px solid var(--border-subtle)', backgroundColor: '#000000' }}>
                <td className="font-mono" style={{ padding: '12px', color: 'var(--accent-cyan)' }}>{item.id}</td>
                <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{item.name}</td>
                <td style={{ padding: '12px' }}>
                  <span className={`badge badge-${item.status.toLowerCase()}`}>• {item.status}</span>
                </td>
                <td className="font-mono" style={{ padding: '12px', color: 'var(--text-secondary)' }}>{item.date}</td>
                <td className="font-mono" style={{ padding: '12px', color: 'var(--text-primary)' }}>{item.tracks || '-'}</td>
                <td style={{ padding: '12px', textAlign: 'right' }}>
                  <button
                    onClick={() => {
                      if (setSelectedJobId) setSelectedJobId(item.id);
                      setActivePage('workspace');
                    }}
                    className="btn btn-cyan btn-sm"
                  >
                    Inspect Run →
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
