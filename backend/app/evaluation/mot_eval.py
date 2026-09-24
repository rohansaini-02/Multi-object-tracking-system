"""
MOT17 Benchmark Protocol Evaluation Module for Backend Pipeline (Week 5 Milestone).

Wraps py-motmetrics to calculate MOTA, IDF1, ID Switches (IDSW), Precision, Recall, MT, ML metrics.
"""

from typing import Dict, List, Union
import logging

from ml.evaluation.mot_evaluator import MOTEvaluator as StandaloneMOTEvaluator

logger = logging.getLogger(__name__)


class MOTEvaluator:
    """Backend adapter for MOT17 ground truth evaluation."""

    def __init__(self, mot17_base_dir: str = "data/mot17"):
        """
        Args:
            mot17_base_dir: Root directory containing MOT17 sequence subfolders.
        """
        self.evaluator = StandaloneMOTEvaluator(mot17_base_dir=mot17_base_dir)

    def evaluate_sequence(
        self, sequence_name: str, tracking_result_path: str
    ) -> Dict[str, Union[float, int]]:
        """Evaluate predicted tracking result file against ground truth for a single sequence.

        Args:
            sequence_name: Name of sequence folder (e.g. 'MOT17-04-FRCNN' or 'MOT17-04').
            tracking_result_path: Path to predicted MOT format text file on disk.

        Returns:
            Dictionary containing mota, idf1, num_switches, precision, recall, mt, ml.
        """
        return self.evaluator.evaluate_sequence(sequence_name, tracking_result_path)

    def evaluate_benchmark(
        self, sequence_results: Dict[str, str]
    ) -> Dict[str, Union[float, int]]:
        """Evaluate tracking results across multiple sequence splits and compute overall metrics.

        Args:
            sequence_results: Map of sequence names to predicted result file paths.

        Returns:
            Overall aggregated benchmark metrics dictionary.
        """
        return self.evaluator.evaluate_benchmark(sequence_results)
