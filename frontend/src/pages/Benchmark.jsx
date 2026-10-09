import React from 'react';

export default function Benchmark() {
  const sequences = [
    { name: 'MOT17-02-FRCNN', mota: '54.2%', idf1: '58.1%', idsw: 14, status: 'Completed' },
    { name: 'MOT17-04-FRCNN', mota: '68.7%', idf1: '71.4%', idsw: 22, status: 'Completed' },
    { name: 'MOT17-09-FRCNN', mota: '61.0%', idf1: '64.5%', idsw: 8, status: 'Completed' },
    { name: 'MOT17-10-FRCNN', mota: '57.8%', idf1: '60.2%', idsw: 19, status: 'Completed' },
  ];

  return (
    <div className="app-container">
      <h2 style={{ marginBottom: '8px' }}>MOT17 Benchmark Protocol Evaluation</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '32px' }}>
        CLEAR-MOT metrics (MOTA, IDF1, ID Switches) evaluated across MOT17 sequences.
      </p>

      <div className="glass-panel" style={{ padding: '24px', overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              <th style={{ padding: '12px' }}>Sequence</th>
              <th style={{ padding: '12px' }}>MOTA</th>
              <th style={{ padding: '12px' }}>IDF1</th>
              <th style={{ padding: '12px' }}>ID Switches</th>
              <th style={{ padding: '12px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {sequences.map((seq, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <td style={{ padding: '16px 12px', fontWeight: 600 }}>{seq.name}</td>
                <td style={{ padding: '16px 12px', color: 'var(--accent-emerald)', fontWeight: 600 }}>{seq.mota}</td>
                <td style={{ padding: '16px 12px', color: 'var(--accent-cyan)', fontWeight: 600 }}>{seq.idf1}</td>
                <td style={{ padding: '16px 12px' }}>{seq.idsw}</td>
                <td style={{ padding: '16px 12px' }}>
                  <span className="badge badge-emerald">{seq.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
