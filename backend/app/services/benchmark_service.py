"""
MOT17 Benchmark Evaluation Service (Backend Application Business Logic Tier).

Discovers available MOT17 sequences on disk, runs the existing `MOTEvaluator` against
ground truth annotations, and persists evaluation history so the frontend benchmark
dashboard renders real measured metrics instead of placeholders.

Architectural Role:
- Wraps `backend.app.evaluation.mot_eval.MOTEvaluator` (which itself delegates to the
  standalone `ml.evaluation.mot_evaluator` implementation) without modifying it.
- Resolves the predicted MOT results file from an explicit path, a linked tracking
  job, or the conventional `data/results` folder.
- Persists evaluation history as a lightweight JSON document so benchmark results
  survive server restarts without requiring a schema migration.
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.evaluation.mot_eval import MOTEvaluator
from backend.app.schemas.benchmark import (
    BenchmarkEvaluateRequest,
    BenchmarkMetrics,
    BenchmarkSequenceInfo,
    BenchmarkSequencesResponse,
)

logger = logging.getLogger("uvicorn.error")

# Filename of the JSON document holding the persisted evaluation history.
EVALUATION_STORE_FILENAME = "benchmark_evaluations.json"

# Standard MOT17 train/val sequence identifiers (without the detector suffix).
MOT17_BASE_SEQUENCES = [
    "MOT17-01",
    "MOT17-02",
    "MOT17-03",
    "MOT17-04",
    "MOT17-05",
    "MOT17-06",
    "MOT17-07",
    "MOT17-08",
    "MOT17-09",
    "MOT17-10",
    "MOT17-11",
    "MOT17-12",
]

# Detector variants published for every MOT17 sequence.
MOT17_DETECTORS = ["DPM", "FRCNN", "SDP"]

# Human readable environment metadata for each MOT17 base sequence.
SEQUENCE_METADATA: Dict[str, Dict[str, str]] = {
    "MOT17-01": {"env_tag": "DAY-HIGH", "description": "Pedestrian Campus Walkway"},
    "MOT17-02": {"env_tag": "STATIC", "description": "Crowded Daytime Sidewalk"},
    "MOT17-03": {"env_tag": "LOW-LIGHT", "description": "Dim Indoor Terminal"},
    "MOT17-04": {"env_tag": "NIGHT", "description": "Night Street Pedestrians"},
    "MOT17-05": {"env_tag": "RAIN", "description": "Rainy Highway Merger"},
    "MOT17-06": {"env_tag": "DAY-HIGH", "description": "Busy Pedestrian Square"},
    "MOT17-07": {"env_tag": "LOW-LIGHT", "description": "Dim Parking Lot Approach"},
    "MOT17-08": {"env_tag": "DAY-HIGH", "description": "Shadowed Terminal Corridor"},
    "MOT17-09": {"env_tag": "DAY-HIGH", "description": "Overhead Plaza Motion"},
    "MOT17-10": {"env_tag": "NIGHT", "description": "Night Market Crowd Flow"},
    "MOT17-11": {"env_tag": "CROWD", "description": "Indoor Corridors & Occlusions"},
    "MOT17-12": {"env_tag": "NIGHT", "description": "Night Exit Gate Flow"},
    "MOT17-13": {"env_tag": "RAIN", "description": "Rainy Urban Crosswalk"},
    "MOT17-16": {"env_tag": "NIGHT", "description": "Night Market Crowd Flow"},
}

# Guards concurrent writes to the on-disk evaluation store.
_STORE_LOCK = threading.Lock()


def _sequence_metadata(sequence_name: str) -> Dict[str, str]:
    """Return the environment tag / description metadata for a sequence id."""
    base = sequence_name.split("-")
    base_seq = f"{base[0]}-{base[1]}" if len(base) >= 2 else sequence_name
    return SEQUENCE_METADATA.get(
        base_seq,
        {"env_tag": "BENCH", "description": f"{base_seq} Sequence"},
    )


def _ground_truth_path(sequence_name: str) -> Optional[str]:
    """
    Locate the ground truth annotation file for a MOT17 sequence.

    Args:
        sequence_name: Sequence identifier (e.g. 'MOT17-04-FRCNN' or 'MOT17-04').

    Returns:
        Absolute-ish path of the gt.txt file, or None when it does not exist.
    """
    candidates = [
        os.path.join(settings.MOT17_DIR, sequence_name, "gt", "gt.txt"),
        os.path.join(settings.MOT17_DIR, sequence_name, "gt", "gt.txt"),
    ]
    parts = sequence_name.split("-")
    if len(parts) >= 2:
        base_seq = f"{parts[0]}-{parts[1]}"
        candidates.append(os.path.join(settings.MOT17_DIR, base_seq, "gt", "gt.txt"))

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def _default_results_path(sequence_name: str) -> str:
    """Return the conventional on-disk path for a sequence's predicted results file."""
    return os.path.join(settings.RESULTS_DIR, f"{sequence_name}.txt")


def _results_path_candidates(sequence_name: str) -> List[str]:
    """
    Return the candidate on-disk paths for a sequence's predicted results file.

    Both the fully qualified sequence id (e.g. 'MOT17-04-FRCNN') and the base
    split id (e.g. 'MOT17-04') are considered so that a single exported MOT
    file can be evaluated against either variant.

    Args:
        sequence_name: Sequence identifier to resolve.

    Returns:
        Ordered list of candidate file system paths (most specific first).
    """
    parts = sequence_name.split("-")
    base_seq = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else sequence_name

    base_paths = [
        _default_results_path(sequence_name),
        _default_results_path(base_seq),
        os.path.join(settings.RESULTS_DIR, f"{base_seq}.txt"),
        os.path.join(settings.RESULTS_DIR, f"{sequence_name}.txt"),
    ]

    seen: List[str] = []
    for path in base_paths:
        if path not in seen:
            seen.append(path)
    return seen


def _resolve_existing_results_path(sequence_name: str) -> Optional[str]:
    """Return the first existing predicted-results file for a sequence."""
    for candidate in _results_path_candidates(sequence_name):
        if os.path.isfile(candidate):
            return candidate
    return None


def _store_path() -> str:
    """Return the absolute path of the persisted benchmark evaluation store."""
    return os.path.abspath(
        os.path.join(settings.RESULTS_DIR, EVALUATION_STORE_FILENAME)
    )


def _read_store() -> Dict[str, Any]:
    """Read the persisted evaluation history from disk (returns {} when absent)."""
    path = _store_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("[BENCHMARK WARNING] Could not read evaluation store: %s", exc)
        return {}


def _write_store(data: Dict[str, Any]) -> None:
    """Persist the evaluation history to disk as pretty-printed JSON."""
    path = _store_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, default=str)
    except OSError as exc:
        logger.warning("[BENCHMARK WARNING] Could not write evaluation store: %s", exc)


def list_evaluations() -> List[BenchmarkMetrics]:
    """
    Load all persisted benchmark evaluations, newest first.

    Returns:
        List of BenchmarkMetrics DTOs ordered by evaluation timestamp descending.
    """
    store = _read_store()
    payloads = list(store.values())

    def _sort_key(item: Any) -> str:
        if isinstance(item, dict):
            return str(item.get("evaluated_at") or "")
        return ""

    payloads.sort(key=_sort_key, reverse=True)

    results: List[BenchmarkMetrics] = []
    for payload in payloads:
        try:
            results.append(BenchmarkMetrics.model_validate(payload))
        except Exception:
            continue
    return results


def _build_sequence_info(
    sequence_id: str,
    gt_path: Optional[str],
    results_path: Optional[str],
    last_evaluation: Optional[BenchmarkMetrics],
) -> BenchmarkSequenceInfo:
    """Build the API DTO describing a single benchmark sequence."""
    metadata = _sequence_metadata(sequence_id)
    return BenchmarkSequenceInfo(
        sequence_id=sequence_id,
        env_tag=metadata["env_tag"],
        description=metadata["description"],
        gt_available=gt_path is not None,
        results_available=results_path is not None,
        results_file=results_path,
        last_evaluation=last_evaluation,
    )


def list_sequences() -> BenchmarkSequencesResponse:
    """
    Discover the MOT17 sequences available for evaluation on this deployment.

    Returns:
        BenchmarkSequencesResponse with the locally installed sequences, the full
        standard catalog and the resolved dataset directory.
    """
    mot17_dir = settings.MOT17_DIR
    dataset_available = os.path.isdir(mot17_dir)

    installed: List[str] = []
    if dataset_available:
        try:
            for entry in sorted(os.listdir(mot17_dir)):
                if not entry.startswith("MOT17"):
                    continue
                if not os.path.isdir(os.path.join(mot17_dir, entry)):
                    continue
                installed.append(entry)
        except OSError:
            installed = []

    evaluations = {item.sequence_id: item for item in list_evaluations()}

    sequences: List[BenchmarkSequenceInfo] = []
    for sequence_id in installed:
        gt_path = _ground_truth_path(sequence_id)
        results_path = _resolve_existing_results_path(sequence_id)
        sequences.append(
            _build_sequence_info(
                sequence_id=sequence_id,
                gt_path=gt_path,
                results_path=results_path,
                last_evaluation=evaluations.get(sequence_id),
            )
        )

    catalog = [
        f"{base_seq}-{detector}"
        for base_seq in MOT17_BASE_SEQUENCES
        for detector in MOT17_DETECTORS
    ]

    return BenchmarkSequencesResponse(
        mot17_dir=os.path.abspath(mot17_dir),
        dataset_available=dataset_available,
        sequences=sequences,
        catalog=catalog,
    )


def resolve_results_file(
    req: BenchmarkEvaluateRequest,
    job_mot_path: Optional[str] = None,
) -> str:
    """
    Resolve the predicted tracking result file used for the evaluation.

    Resolution order: explicit request path -> linked tracking job artifact ->
    conventional `data/results/{sequence}.txt`.

    Args:
        req: Benchmark evaluation request payload.
        job_mot_path: MOT artifact path of the linked tracking job (when provided).

    Returns:
        Resolved file system path of the predicted results file.

    Raises:
        FileNotFoundError: If no readable results file could be resolved.
    """
    if req.results_file:
        candidate = os.path.abspath(req.results_file)
        allowed_roots = [
            os.path.abspath(settings.RESULTS_DIR),
            os.path.abspath(settings.UPLOAD_DIR),
            os.path.abspath(settings.MOT17_DIR),
            os.path.abspath(os.getcwd()),
        ]
        if not any(candidate.startswith(root) for root in allowed_roots):
            raise ValueError("Requested results_file path is outside allowed directories.")
        if os.path.isfile(candidate):
            return candidate

    if job_mot_path and os.path.isfile(job_mot_path):
        return job_mot_path

    existing = _resolve_existing_results_path(req.sequence_name)
    if existing:
        return existing

    raise FileNotFoundError(
        f"No tracking results file found for sequence '{req.sequence_name}'. "
        f"Provide 'results_file' or 'job_id', or place the file at {settings.RESULTS_DIR}."
    )


def persist_evaluation(metrics: BenchmarkMetrics) -> None:
    """Persist a single evaluation record into the on-disk evaluation store."""
    with _STORE_LOCK:
        store = _read_store()
        store[metrics.sequence_id] = metrics.model_dump(mode="json")
        _write_store(store)


def evaluate_sequence(
    req: BenchmarkEvaluateRequest,
    job_mot_path: Optional[str] = None,
) -> BenchmarkMetrics:
    """
    Run the MOT17 CLEAR-MOT evaluation for a single sequence.

    Args:
        req: Benchmark evaluation request payload (sequence name + optional sources).
        job_mot_path: Optional MOT artifact path of a linked tracking job.

    Returns:
        BenchmarkMetrics DTO with the measured MOTA / IDF1 / IDSW / precision / recall
        values for the evaluated sequence.

    Raises:
        FileNotFoundError: If the ground truth or the predicted results file is missing.
        ImportError: If the py-motmetrics dependency is not installed.
    """
    results_path = resolve_results_file(req, job_mot_path)

    evaluator = MOTEvaluator(mot17_base_dir=settings.MOT17_DIR)
    raw = evaluator.evaluate_sequence(req.sequence_name, results_path)

    metrics = BenchmarkMetrics(
        sequence_id=req.sequence_name,
        mota=float(raw.get("mota", 0.0)),
        idf1=float(raw.get("idf1", 0.0)),
        num_switches=int(raw.get("num_switches", 0)),
        precision=float(raw.get("precision", 0.0)),
        recall=float(raw.get("recall", 0.0)),
        mostly_tracked=int(raw.get("mostly_tracked", 0)),
        mostly_lost=int(raw.get("mostly_lost", 0)),
        evaluated_at=datetime.now(timezone.utc),
        status="COMPLETED",
    )

    persist_evaluation(metrics)
    return metrics
