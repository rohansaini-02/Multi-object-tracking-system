"""
Tracking Worker Process (Backend Application Worker Tier).

Executes the DeepSORT tracking pipeline inside a dedicated operating system
process so that the heavy Computer Vision stack (PyTorch + Ultralytics) is
isolated from the FastAPI application.

Architectural Role:
- Restores the decoupling the project architecture describes: an out-of-memory
  condition during inference can only ever kill this worker, never the web
  server that serves the operator UI.
- Keeps the API process free of the PyTorch import, which alone costs
  hundreds of megabytes of resident memory and several seconds of start-up.

Communication Protocol:
    stdin  : a JSON request document, e.g.
             {"video_path": "...", "output_video_path": "...",
              "output_mot_path": "...", "result_path": "...",
              "conf_threshold": 0.5, "max_cosine_distance": 0.2,
              "max_age": 30, "n_init": 3}
    file   : the JSON result document written to ``result_path``:
             {"ok": true,  "total_frames": 60, "processed_frames": 60,
              "total_tracks": 3, "fps": 24.1}
             {"ok": false, "error": "...", "traceback": "..."}

A result file is used instead of stdout because PyTorch and OpenCV print
banner and progress text to stdout, which would corrupt a JSON stream.
"""

import json
import os
import sys
import traceback
from typing import Any, Dict


def _run_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the tracking pipeline described by the request payload.

    The `ml` package is imported lazily *inside* this function so that merely
    importing this module (for example when the API server builds its module
    graph) never pulls PyTorch into the parent process.

    Args:
        payload: Decoded JSON request document.

    Returns:
        Dictionary describing the pipeline statistics on success.
    """
    try:
        import torch
        num_threads = min(8, max(2, (os.cpu_count() or 4) - 1))
        torch.set_num_threads(num_threads)
    except Exception:
        pass

    from ml.pipeline import TrackingPipeline

    reid_weights = payload.get("reid_weights")
    if reid_weights and str(reid_weights).strip().lower() in ("base", "none", "", "default"):
        reid_weights = None
    elif reid_weights and not os.path.isabs(reid_weights):
        # Resolve relative to project root
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        resolved = os.path.join(repo_root, reid_weights)
        if os.path.exists(resolved):
            reid_weights = resolved

    pipeline = TrackingPipeline(
        conf_threshold=float(payload.get("conf_threshold", 0.5)),
        reid_weights=reid_weights,
    )

    # Apply the per-job association hyperparameters selected by the operator.
    pipeline.tracker.max_cosine_distance = float(
        payload.get("max_cosine_distance", 0.2)
    )
    pipeline.tracker.max_age = int(payload.get("max_age", 30))
    pipeline.tracker.n_init = int(payload.get("n_init", 3))

    def on_progress(processed_count: int, total_frames: int) -> None:
        total = max(total_frames, 1)
        # Scale progress between 5% (started) and 95% (inference done, encoding output)
        pct = min(95, max(5, int((processed_count / total) * 90) + 5))
        sys.stderr.write(f"PROGRESS:{processed_count}:{total}:{pct}\n")
        sys.stderr.flush()

    result = pipeline.run(
        input_video_path=payload["video_path"],
        output_video_path=payload.get("output_video_path"),
        output_mot_path=payload.get("output_mot_path"),
        progress_callback=on_progress,
        progress_interval=5,
    )

    return {
        "ok": True,
        "total_frames": result.total_frames,
        "processed_frames": result.processed_frames,
        "total_tracks": result.total_tracks,
        "fps": result.fps,
        "output_video_path": result.output_video_path,
        "output_mot_path": result.output_mot_path,
    }


def _write_result(result_path: str, document: Dict[str, Any]) -> None:
    """Persist the result document so the parent process can read it back."""
    if not result_path:
        return
    try:
        os.makedirs(os.path.dirname(os.path.abspath(result_path)), exist_ok=True)
        with open(result_path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
    except OSError:
        # The parent process detects the missing file and reports the failure.
        pass


def main() -> int:
    """Read the request from stdin, run the pipeline and report the outcome."""
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, OSError):
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    try:
        document = _run_pipeline(payload)
    except BaseException as exc:  # noqa: BLE001 - the parent needs every failure
        exc_str = str(exc).strip()
        err_msg = f"{type(exc).__name__}: {exc_str}" if exc_str else f"{type(exc).__name__}: Execution aborted unexpectedly"
        document = {
            "ok": False,
            "error": err_msg,
            "traceback": traceback.format_exc(),
        }

    _write_result(payload.get("result_path", ""), document)

    if document.get("ok"):
        print(f"[worker] finished: {document.get('total_tracks')} tracks")
        return 0

    print(f"[worker] failed: {document.get('error')}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
