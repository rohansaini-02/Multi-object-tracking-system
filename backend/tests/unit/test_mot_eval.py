"""
Unit Test Suite for MOT17 Benchmark Protocol & Evaluation (Week 5 Milestone).

Tests py-motmetrics wrapper, ground-truth parsing, single-sequence and multi-sequence metric calculation.
"""

import os
import tempfile
import numpy as np
import pytest

from backend.app.evaluation.mot_eval import MOTEvaluator as BackendMOTEvaluator
from ml.evaluation.mot_evaluator import MOTEvaluator as StandaloneMOTEvaluator


@pytest.fixture
def mock_mot17_dataset():
    """Create a temporary mock MOT17 directory with ground truth and result text files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        seq_name = "MOT17-02-FRCNN"
        seq_dir = os.path.join(tmp_dir, seq_name)
        gt_dir = os.path.join(seq_dir, "gt")
        os.makedirs(gt_dir, exist_ok=True)

        # Create dummy ground truth data: frame, id, left, top, width, height, conf, class, visibility
        # 5 frames, 2 targets
        gt_lines = [
            "1,1,100,100,50,100,1,1,1",
            "1,2,300,300,50,100,1,1,1",
            "2,1,105,100,50,100,1,1,1",
            "2,2,305,300,50,100,1,1,1",
            "3,1,110,100,50,100,1,1,1",
            "3,2,310,300,50,100,1,1,1",
        ]
        gt_path = os.path.join(gt_dir, "gt.txt")
        with open(gt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(gt_lines) + "\n")

        # Create dummy prediction data matching ground truth (perfect predictions)
        pred_lines = [
            "1,1,100,100,50,100,0.9,-1,-1,-1",
            "1,2,300,300,50,100,0.95,-1,-1,-1",
            "2,1,105,100,50,100,0.91,-1,-1,-1",
            "2,2,305,300,50,100,0.93,-1,-1,-1",
            "3,1,110,100,50,100,0.89,-1,-1,-1",
            "3,2,310,300,50,100,0.92,-1,-1,-1",
        ]
        res_path = os.path.join(tmp_dir, "pred_MOT17-02.txt")
        with open(res_path, "w", encoding="utf-8") as f:
            f.write("\n".join(pred_lines) + "\n")

        yield tmp_dir, seq_name, res_path


def test_mot_evaluator_file_not_found():
    """Verify FileNotFoundError is raised when files are missing."""
    evaluator = StandaloneMOTEvaluator(mot17_base_dir="non_existent_dir")
    with pytest.raises(FileNotFoundError):
        evaluator.evaluate_sequence("MOT17-99", "non_existent_file.txt")


def test_mot_evaluator_sequence_metrics(mock_mot17_dataset):
    """Test single sequence evaluation metrics on synthetic ground truth."""
    tmp_dir, seq_name, res_path = mock_mot17_dataset
    evaluator = StandaloneMOTEvaluator(mot17_base_dir=tmp_dir)

    metrics = evaluator.evaluate_sequence(seq_name, res_path)

    assert isinstance(metrics, dict)
    assert "mota" in metrics
    assert "idf1" in metrics
    assert "num_switches" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "mostly_tracked" in metrics
    assert "mostly_lost" in metrics

    # Perfect predictions should give MOTA = 1.0 (100%), IDF1 = 1.0, IDSW = 0
    assert pytest.approx(metrics["mota"], abs=1e-2) == 1.0
    assert pytest.approx(metrics["idf1"], abs=1e-2) == 1.0
    assert metrics["num_switches"] == 0


def test_mot_evaluator_benchmark(mock_mot17_dataset):
    """Test overall benchmark metrics evaluation across sequence map."""
    tmp_dir, seq_name, res_path = mock_mot17_dataset
    evaluator = BackendMOTEvaluator(mot17_base_dir=tmp_dir)

    seq_results = {seq_name: res_path}
    overall_metrics = evaluator.evaluate_benchmark(seq_results)

    assert "mota" in overall_metrics
    assert "idf1" in overall_metrics
    assert pytest.approx(overall_metrics["mota"], abs=1e-2) == 1.0
