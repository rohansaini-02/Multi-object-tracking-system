import React from 'react';

export default function MOT17Benchmark({ setActivePage, setSelectedJobId }) {
  const sequences = [
    {
      id: 'MOT17-04-FRCNN',
      envTag: 'NIGHT',
      desc: 'Night Street Pedestrians',
      mota: 74.8,
      idf1: 78.2,
      precision: 89.4,
      recall: 82.6,
      idSwitches: 14,
      mt: 82.1,
      ml: 6.4,
      img: 'https://images.unsplash.com/photo-1506521782023-6058fda6888d?q=80&w=600&auto=format&fit=crop',
    },
    {
      id: 'MOT17-09-SDP',
      envTag: 'DAY-HIGH',
      desc: 'Overhead Plaza Motion',
      mota: 77.1,
      idf1: 81.5,
      precision: 91.2,
      recall: 85.0,
      idSwitches: 8,
      mt: 86.4,
      ml: 4.2,
      img: 'https://images.unsplash.com/photo-1517649763962-0c623266de01?q=80&w=600&auto=format&fit=crop',
    },
    {
      id: 'MOT17-11-FRCNN',
      envTag: 'CROWD',
      desc: 'Indoor Corridors & Occlusions',
      mota: 71.6,
      idf1: 74.9,
      precision: 87.3,
      recall: 80.2,
      idSwitches: 22,
      mt: 76.5,
      ml: 9.8,
      img: 'https://images.unsplash.com/photo-1519501025264-65ba15a82390?q=80&w=600&auto=format&fit=crop',
    },
    {
      id: 'MOT17-02-DPM',
      envTag: 'STATIC',
      desc: 'Crowded Daytime Sidewalk',
      mota: 68.2,
      idf1: 72.1,
      precision: 84.7,
      recall: 77.5,
      idSwitches: 31,
      mt: 71.0,
      ml: 12.3,
      img: 'https://images.unsplash.com/photo-1477959858617-67f30ac4ce78?q=80&w=600&auto=format&fit=crop',
    },
  ];

  const handleSeqClick = (seqId) => {
    if (setSelectedJobId) setSelectedJobId(seqId);
    setActivePage('workspace');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Subtext & Header */}
      <div style={{ paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
          VALIDATION / STANDARDIZED BENCHMARK / MOT17 TRAIN-TEST SPLIT
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
          <div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              MOT17 Benchmark Evaluation Suite
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginTop: '2px' }}>
              Standardized benchmark metrics calculated against official ground truth sequences using py-motmetrics and CLEAR-MOT protocols.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span className="badge badge-cyan font-mono" style={{ fontSize: '0.7rem' }}>
              EVAL ENGINE: py-motmetrics v1.4.3 • IOU THRESH 0.50
            </span>
            <button className="btn btn-cyan btn-sm">▶ Run Batch Suite</button>
          </div>
        </div>
      </div>

      {/* Top 5 Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '12px'
      }}>
        {[
          { label: 'MOTA', value: '74.8 %', sub: 'Multi-Object Tracking Accuracy', color: 'var(--accent-cyan)' },
          { label: 'IDF1', value: '78.2 %', sub: 'Identification F1 Score', color: 'var(--accent-cyan)' },
          { label: 'ID SWITCHES', value: '14', sub: 'Identity transitions across GT', color: 'var(--accent-amber)' },
          { label: 'PRECISION', value: '89.4 %', sub: 'Detection precision (TP/TP+FP)', color: 'var(--accent-emerald)' },
          { label: 'RECALL', value: '82.6 %', sub: 'Detection recall (TP/TP+FN)', color: 'var(--accent-emerald)' },
        ].map((m, idx) => (
          <div key={idx} className="glass-card" style={{ padding: '16px' }}>
            <div className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-muted)', letterSpacing: '0.08em', marginBottom: '4px' }}>
              {m.label}
            </div>
            <div className="font-mono" style={{ fontSize: '1.8rem', fontWeight: 800, color: m.color, lineHeight: 1.1, marginBottom: '6px' }}>
              {m.value}
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', lineHeight: 1.2 }}>
              {m.sub}
            </div>
          </div>
        ))}
      </div>

      {/* Sequence Benchmark Records Table */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem', color: 'var(--accent-cyan)' }}>📊</span>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Sequence Benchmark Records
            </h2>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Frame-level evaluation results on official public detector baselines
            </span>
          </div>
          <span className="badge badge-cyan">4 ACTIVE SEQUENCES</span>
        </div>

        {/* Table */}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>SEQUENCE ID</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>ENVIRONMENT / SENSOR</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>MOTA</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>IDF1</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>PRECISION</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>RECALL</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>ID SWITCHES</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>MT %</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>ML %</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {sequences.map((seq) => (
                <tr key={seq.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td className="font-mono" style={{ padding: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {seq.id}
                  </td>
                  <td style={{ padding: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge badge-cyan" style={{ fontSize: '0.6rem', padding: '1px 5px' }}>{seq.envTag}</span>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{seq.desc}</span>
                    </div>
                  </td>
                  <td className="font-mono" style={{ padding: '12px', fontWeight: 700, color: 'var(--accent-cyan)' }}>{seq.mota}%</td>
                  <td className="font-mono" style={{ padding: '12px', color: 'var(--text-primary)' }}>{seq.idf1}%</td>
                  <td className="font-mono" style={{ padding: '12px', color: 'var(--text-secondary)' }}>{seq.precision}%</td>
                  <td className="font-mono" style={{ padding: '12px', color: 'var(--text-secondary)' }}>{seq.recall}%</td>
                  <td className="font-mono" style={{ padding: '12px', color: 'var(--accent-amber)', fontWeight: 700 }}>{seq.idSwitches}</td>
                  <td className="font-mono" style={{ padding: '12px', color: 'var(--accent-emerald)' }}>{seq.mt}%</td>
                  <td className="font-mono" style={{ padding: '12px', color: 'var(--accent-rose)' }}>{seq.ml}%</td>
                  <td style={{ padding: '12px', textAlign: 'right' }}>
                    <button onClick={() => handleSeqClick(seq.id)} className="btn btn-cyan btn-sm">
                      View Job Results →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bottom Sequence Thumbnail Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '16px'
      }}>
        {sequences.slice(0, 3).map((seq) => (
          <div key={seq.id} className="glass-card" style={{ overflow: 'hidden', cursor: 'pointer' }} onClick={() => handleSeqClick(seq.id)}>
            <div style={{
              height: '140px',
              backgroundImage: `url("${seq.img}")`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              position: 'relative'
            }}>
              <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.8) 100%)' }} />
              <div className="font-mono" style={{
                position: 'absolute',
                top: '8px',
                left: '8px',
                backgroundColor: 'rgba(0,0,0,0.8)',
                color: 'var(--accent-cyan)',
                fontSize: '0.65rem',
                padding: '2px 6px',
                borderRadius: '3px'
              }}>
                {seq.id}
              </div>
              <div className="font-mono" style={{
                position: 'absolute',
                bottom: '8px',
                right: '8px',
                backgroundColor: 'var(--accent-cyan)',
                color: '#040D14',
                fontWeight: 800,
                fontSize: '0.72rem',
                padding: '2px 8px',
                borderRadius: '3px'
              }}>
                MOTA {seq.mota}%
              </div>
            </div>
            <div style={{ padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>{seq.desc}</span>
              <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>FPS: 30.0</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
