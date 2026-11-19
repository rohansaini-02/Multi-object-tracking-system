import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getBenchmarkSequencesApi,
  getBenchmarkResultsApi,
  runBenchmarkApi,
} from '../api/client';
import { formatPercent } from '../utils/format';
import { Play, Loader2, BarChart2 } from 'lucide-react';

export default function MOT17Benchmark() {
  const [sequencePayload, setSequencePayload] = useState(null);
  const [resultPayload, setResultPayload] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [runningId, setRunningId] = useState(null);
  const [runMessage, setRunMessage] = useState(null);
  const [isRunningAll, setIsRunningAll] = useState(false);

  const loadBenchmark = useCallback(async () => {
    const [sequences, results] = await Promise.all([
      getBenchmarkSequencesApi(),
      getBenchmarkResultsApi(),
    ]);

    if (!sequences && !results) {
      setLoadError('The benchmark API is unreachable. Start the backend and reload this page.');
    } else {
      setLoadError(null);
    }

    if (sequences) setSequencePayload(sequences);
    if (results) setResultPayload(results);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let active = true;
    const fetchBenchmark = async () => {
      if (active) await loadBenchmark();
    };
    fetchBenchmark();
    return () => {
      active = false;
    };
  }, [loadBenchmark]);

  const sequences = useMemo(() => sequencePayload?.sequences || [], [sequencePayload]);
  const catalog = useMemo(() => sequencePayload?.catalog || [], [sequencePayload]);

  /* Latest evaluation per sequence, newest first. */
  const latestBySequence = useMemo(() => {
    const map = new Map();

    (resultPayload?.results || []).forEach((item) => {
      const existing = map.get(item.sequence_id);
      if (!existing || new Date(item.evaluated_at) > new Date(existing.evaluated_at)) {
        map.set(item.sequence_id, item);
      }
    });

    sequences.forEach((sequence) => {
      if (sequence.last_evaluation && !map.has(sequence.sequence_id)) {
        map.set(sequence.sequence_id, sequence.last_evaluation);
      }
    });

    return map;
  }, [resultPayload, sequences]);

  /* Aggregate the headline metrics across every evaluated sequence. */
  const aggregate = useMemo(() => {
    const items = Array.from(latestBySequence.values()).filter(
      (metric) => metric.status === 'COMPLETED'
    );
    if (items.length === 0) return null;

    const mean = (key) =>
      items.reduce((sum, metric) => sum + (Number(metric[key]) || 0), 0) / items.length;

    return {
      count: items.length,
      mota: mean('mota'),
      idf1: mean('idf1'),
      switches: items.reduce((sum, metric) => sum + (Number(metric.num_switches) || 0), 0),
      precision: mean('precision'),
      recall: mean('recall'),
    };
  }, [latestBySequence]);

  const evaluable = useMemo(
    () => sequences.filter((sequence) => sequence.gt_available && sequence.results_available),
    [sequences]
  );

  const runEvaluation = async (sequence) => {
    setRunningId(sequence.sequence_id);
    setRunMessage(null);
    try {
      const metrics = await runBenchmarkApi({
        sequenceName: sequence.sequence_id,
        resultsFile: sequence.results_file || null,
      });
      setRunMessage(
        `${sequence.sequence_id} evaluated — MOTA ${formatPercent(metrics.mota)}, IDF1 ${formatPercent(metrics.idf1)}.`
      );
      await loadBenchmark();
    } catch (err) {
      setRunMessage(`${sequence.sequence_id} failed: ${err.message}`);
    } finally {
      setRunningId(null);
    }
  };

  const runAllEvaluations = async () => {
    if (evaluable.length === 0) {
      setRunMessage('No sequence has both ground truth and a tracking results file on this server.');
      return;
    }

    setIsRunningAll(true);
    setRunMessage(null);
    const failures = [];

    for (const sequence of evaluable) {
      try {
        await runBenchmarkApi({
          sequenceName: sequence.sequence_id,
          resultsFile: sequence.results_file || null,
        });
      } catch (err) {
        failures.push(`${sequence.sequence_id}: ${err.message}`);
      }
    }

    await loadBenchmark();
    setIsRunningAll(false);
    setRunMessage(
      failures.length === 0
        ? `Evaluated ${evaluable.length} sequence(s).`
        : `Completed with errors — ${failures.join(' | ')}`
    );
  };

  const metricCards = aggregate
    ? [
        { label: 'MOTA', value: formatPercent(aggregate.mota), sub: 'Multi-Object Tracking Accuracy', color: 'var(--accent-cyan)' },
        { label: 'IDF1', value: formatPercent(aggregate.idf1), sub: 'Identity Matching Score', color: 'var(--accent-cyan)' },
        { label: 'ID SWITCHES', value: String(aggregate.switches), sub: `Times an object's ID changed (${aggregate.count} seq.)`, color: 'var(--accent-amber)' },
        { label: 'PRECISION', value: formatPercent(aggregate.precision), sub: 'Detection precision (TP/TP+FP)', color: 'var(--accent-emerald)' },
        { label: 'RECALL', value: formatPercent(aggregate.recall), sub: 'Detection recall (TP/TP+FN)', color: 'var(--accent-emerald)' },
      ]
    : [
        { label: 'MOTA', value: '—', sub: 'Multi-Object Tracking Accuracy', color: 'var(--accent-cyan)' },
        { label: 'IDF1', value: '—', sub: 'Identity Matching Score', color: 'var(--accent-cyan)' },
        { label: 'ID SWITCHES', value: '—', sub: "Times an object's ID changed", color: 'var(--accent-amber)' },
        { label: 'PRECISION', value: '—', sub: 'Detection precision (TP/TP+FP)', color: 'var(--accent-emerald)' },
        { label: 'RECALL', value: '—', sub: 'Detection recall (TP/TP+FN)', color: 'var(--accent-emerald)' },
      ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Subtext & Header */}
      <div style={{ paddingBottom: '8px', borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
          PERFORMANCE / MOT17 BENCHMARK
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
              CLEAR-MOT • IOU THRESH 0.50
            </span>
            <button
              className="btn btn-cyan btn-sm"
              onClick={runAllEvaluations}
              disabled={isRunningAll}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              {isRunningAll ? (
                <>
                  <Loader2 size={13} className="spin" /> Running...
                </>
              ) : (
                <>
                  <Play size={13} /> Run All Tests
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {loadError && (
        <div
          className="font-mono"
          style={{
            fontSize: '0.75rem',
            color: 'var(--accent-rose)',
            backgroundColor: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.35)',
            borderRadius: '6px',
            padding: '10px 14px',
          }}
        >
          {loadError}
        </div>
      )}

      {sequencePayload && !sequencePayload.dataset_available && (
        <div
          className="font-mono"
          style={{
            fontSize: '0.75rem',
            color: 'var(--accent-amber)',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            borderRadius: '6px',
            padding: '10px 14px',
          }}
        >
          MOT17 dataset not found at {sequencePayload.mot17_dir} — {catalog.length} catalogue sequences are known but none are installed, so no ground truth can be scored.
        </div>
      )}

      {/* Top 5 Metric Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '12px'
      }}>
        {metricCards.map((m, idx) => (
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
            <BarChart2 size={18} color="var(--accent-cyan)" />
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Test Video Results
            </h2>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Detailed results for each test video sequence
            </span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="badge badge-cyan">{sequences.length} SEQUENCES</span>
            <button className="btn btn-secondary btn-sm" onClick={loadBenchmark}>↻ Refresh</button>
          </div>
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
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>MT</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem' }}>ML</th>
                <th className="font-mono" style={{ padding: '10px 12px', color: 'var(--text-muted)', fontSize: '0.68rem', textAlign: 'right' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && sequences.length === 0 && (
                <tr>
                  <td colSpan={10} style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    Loading benchmark sequences...
                  </td>
                </tr>
              )}
              {!isLoading && sequences.length === 0 && (
                <tr>
                  <td colSpan={10} style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No MOT17 sequences installed on this server.
                  </td>
                </tr>
              )}
              {sequences.map((seq) => {
                const metric = latestBySequence.get(seq.sequence_id);
                const isRunning = runningId === seq.sequence_id;
                return (
                  <tr key={seq.sequence_id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    <td className="font-mono" style={{ padding: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {seq.sequence_id}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="badge badge-cyan" style={{ fontSize: '0.6rem', padding: '1px 5px' }}>{seq.env_tag}</span>
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{seq.description}</span>
                      </div>
                    </td>
                    <td className="font-mono" style={{ padding: '12px', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                      {metric ? formatPercent(metric.mota) : '—'}
                    </td>
                    <td className="font-mono" style={{ padding: '12px', color: 'var(--text-primary)' }}>
                      {metric ? formatPercent(metric.idf1) : '—'}
                    </td>
                    <td className="font-mono" style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                      {metric ? formatPercent(metric.precision) : '—'}
                    </td>
                    <td className="font-mono" style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                      {metric ? formatPercent(metric.recall) : '—'}
                    </td>
                    <td className="font-mono" style={{ padding: '12px', color: 'var(--accent-amber)', fontWeight: 700 }}>
                      {metric ? metric.num_switches : '—'}
                    </td>
                    <td className="font-mono" style={{ padding: '12px', color: 'var(--accent-emerald)' }}>
                      {metric ? metric.mostly_tracked : '—'}
                    </td>
                    <td className="font-mono" style={{ padding: '12px', color: 'var(--accent-rose)' }}>
                      {metric ? metric.mostly_lost : '—'}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <button
                        onClick={() => runEvaluation(seq)}
                        disabled={isRunning || isRunningAll}
                        className="btn btn-cyan btn-sm"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                        title={
                          seq.gt_available
                            ? 'Evaluate this sequence against its ground truth'
                            : 'Ground truth annotations are not installed for this sequence'
                        }
                      >
                        {isRunning ? (
                          <>
                            <Loader2 size={12} className="spin" /> Evaluating...
                          </>
                        ) : (
                          'Evaluate →'
                        )}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {runMessage && (
          <div
            className="font-mono"
            style={{
              fontSize: '0.72rem',
              color: 'var(--accent-cyan)',
              marginTop: '12px',
              backgroundColor: 'rgba(0, 229, 255, 0.08)',
              border: '1px solid var(--border-cyan)',
              borderRadius: '6px',
              padding: '8px 12px',
            }}
          >
            {runMessage}
          </div>
        )}
      </div>

      {/* Bottom Sequence Cards */}
      {sequences.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '16px'
        }}>
          {sequences.slice(0, 3).map((seq) => {
            const metric = latestBySequence.get(seq.sequence_id);
            return (
              <div key={seq.sequence_id} className="glass-card" style={{ overflow: 'hidden' }}>
                <div style={{
                  height: '140px',
                  background: 'linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.85) 100%), #050505',
                  position: 'relative',
                  display: 'flex',
                  alignItems: 'flex-end'
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
                    {seq.sequence_id}
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
                    MOTA {metric ? formatPercent(metric.mota) : 'n/a'}
                  </div>
                </div>
                <div style={{ padding: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>{seq.description}</span>
                  <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {seq.gt_available ? 'GT READY' : 'NO GT'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Dataset status footer */}
      {sequencePayload && (
        <div className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textAlign: 'right' }}>
          DATASET PATH: {sequencePayload.mot17_dir} • INSTALLED: {sequences.length} / {catalog.length} CATALOGUE SEQUENCES
        </div>
      )}
    </div>
  );
}
