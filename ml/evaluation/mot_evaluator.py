"""
MOT17 Evaluation Module using py-motmetrics.
Calculates MOTA, IDF1, ID Switches, Precision, Recall, MT, ML metrics.
"""

from typing import Dict, List, Optional, Union
import logging
import os
import numpy as np

# Patch numpy 2.0 removal of np.asfarray for py-motmetrics compatibility
if not hasattr(np, "asfarray"):
    np.asfarray = lambda a, dtype=float: np.asarray(a, dtype=dtype)

logger = logging.getLogger(__name__)

try:
    import motmetrics as mm
except ImportError:
    mm = None


class MOTEvaluator:
    """Evaluates multi-object tracking results against MOT17 ground truth annotations."""

    def __init__(self, mot17_base_dir: str = "data/mot17"):
        """
        Args:
            mot17_base_dir: Path to root MOT17 dataset directory containing sequence subfolders (e.g. MOT17-02-SDP).
        """
        self.mot17_base_dir = mot17_base_dir
        if mm is None:
            logger.warning("'motmetrics' is not installed. Benchmark evaluation will raise ImportError.")

    def load_mot_file(self, file_path: str, is_gt: bool = False):
        """Load MOT format text file into pandas DataFrame or numpy matrix.
        Format: frame, id, top, left, width, height, conf, x, y, z
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"MOT file not found: {file_path}")
        if mm is not None:
            min_conf = 1.0 if is_gt else -1.0
            return mm.io.load_motchallenge(file_path, min_confidence=min_conf)
        try:
            return np.loadtxt(file_path, delimiter=",")
        except Exception:
            return np.loadtxt(file_path)

    def evaluate_sequence(
        self, sequence_name: str, tracking_result_path: str
    ) -> Dict[str, Union[float, int]]:
        """Evaluate tracking results for a single sequence.

        Args:
            sequence_name: Name of sequence directory (e.g. 'MOT17-04-SDP' or 'MOT17-04').
            tracking_result_path: Path to predicted MOT format text file.

        Returns:
            Dictionary containing metrics: mota, idf1, num_switches, precision, recall, mt, ml.
        """
        if mm is None:
            raise ImportError("Please install 'motmetrics' via 'pip install motmetrics'.")

        # Find ground truth file
        gt_path = os.path.join(self.mot17_base_dir, sequence_name, "gt", "gt.txt")
        if not os.path.exists(gt_path):
            # Try alternate path without detector suffix
            parts = sequence_name.split("-")
            if len(parts) >= 2:
                base_seq = f"{parts[0]}-{parts[1]}"
                gt_path = os.path.join(self.mot17_base_dir, base_seq, "gt", "gt.txt")
            if not os.path.exists(gt_path):
                raise FileNotFoundError(f"Ground truth file not found for sequence {sequence_name} at {gt_path}")

        gt_data = self.load_mot_file(gt_path, is_gt=True)
        res_data = self.load_mot_file(tracking_result_path, is_gt=False)

        acc = mm.utils.compare_to_groundtruth(
            gt_data, res_data, dist="iou", distth=0.5
        )

        mh = mm.metrics.create()
        summary = mh.compute(
            acc,
            metrics=[
                "mota",
                "idf1",
                "num_switches",
                "precision",
                "recall",
                "mostly_tracked",
                "mostly_lost",
            ],
            name=sequence_name,
        )

        metrics_dict = {
            "mota": float(summary["mota"].iloc[0]),
            "idf1": float(summary["idf1"].iloc[0]),
            "num_switches": int(summary["num_switches"].iloc[0]),
            "precision": float(summary["precision"].iloc[0]),
            "recall": float(summary["recall"].iloc[0]),
            "mostly_tracked": int(summary["mostly_tracked"].iloc[0]),
            "mostly_lost": int(summary["mostly_lost"].iloc[0]),
        }
        return metrics_dict

    def evaluate_benchmark(
        self, sequence_results: Dict[str, str]
    ) -> Dict[str, Union[float, int]]:
        """Evaluate tracking results across multiple sequences and compute overall benchmark metrics.

        Args:
            sequence_results: Dictionary mapping sequence names to result text file paths.
                              e.g. {'MOT17-02': 'results/MOT17-02.txt', 'MOT17-04': 'results/MOT17-04.txt'}

        Returns:
            Overall aggregated metrics dictionary.
        """
        if mm is None:
            raise ImportError("Please install 'motmetrics' via 'pip install motmetrics'.")

        accs = []
        names = []

        for seq_name, res_path in sequence_results.items():
            gt_path = os.path.join(self.mot17_base_dir, seq_name, "gt", "gt.txt")
            if not os.path.exists(gt_path):
                parts = seq_name.split("-")
                if len(parts) >= 2:
                    base_seq = f"{parts[0]}-{parts[1]}"
                    gt_path = os.path.join(self.mot17_base_dir, base_seq, "gt", "gt.txt")

            gt_data = self.load_mot_file(gt_path, is_gt=True)
            res_data = self.load_mot_file(res_path, is_gt=False)

            acc = mm.utils.compare_to_groundtruth(
                gt_data, res_data, dist="iou", distth=0.5
            )
            accs.append(acc)
            names.append(seq_name)

        mh = mm.metrics.create()
        summary = mh.compute_many(
            accs,
            names=names,
            metrics=[
                "mota",
                "idf1",
                "num_switches",
                "precision",
                "recall",
                "mostly_tracked",
                "mostly_lost",
            ],
            generate_overall=True,
        )

        overall = summary.loc["OVERALL"]
        return {
            "mota": float(overall["mota"]),
            "idf1": float(overall["idf1"]),
            "num_switches": int(overall["num_switches"]),
            "precision": float(overall["precision"]),
            "recall": float(overall["recall"]),
            "mostly_tracked": int(overall["mostly_tracked"]),
            "mostly_lost": int(overall["mostly_lost"]),
        }
