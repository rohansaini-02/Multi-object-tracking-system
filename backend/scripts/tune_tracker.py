"""
Hyperparameter Grid Search Tuning Script for DeepSORT Tracker (Week 5 Milestone).

Optimizes:
  - conf_threshold: [0.3, 0.5, 0.7]
  - max_cosine_distance: [0.15, 0.2, 0.3]
  - max_age: [15, 30, 45]

Saves best hyperparameter combination based on MOTA & IDF1 scores.
"""

import argparse
import itertools
import logging
import os
import sys

# Ensure project root is in sys.path when script is executed directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.evaluation.mot_eval import MOTEvaluator
from backend.app.ml.pipeline import TrackingPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tune_tracker")


def grid_search_hyperparameters(
    mot17_dir: str = "data/mot17",
    sequences: list = None,
    output_dir: str = "data/results/tuning",
):
    """Run grid search over hyperparameter combinations on MOT17 sequence splits.

    Args:
        mot17_dir: Path to root MOT17 dataset directory.
        sequences: List of MOT17 sequence names to evaluate against.
        output_dir: Output folder for temporary tuning result files.
    """
    if sequences is None:
        sequences = ["MOT17-02-FRCNN", "MOT17-04-FRCNN"]

    os.makedirs(output_dir, exist_ok=True)
    evaluator = MOTEvaluator(mot17_base_dir=mot17_dir)

    # Define hyperparameter search grid
    conf_grid = [0.3, 0.5, 0.7]
    dist_grid = [0.15, 0.2, 0.3]
    age_grid = [15, 30, 45]

    combinations = list(itertools.product(conf_grid, dist_grid, age_grid))
    logger.info("Starting grid search across %d hyperparameter combinations...", len(combinations))

    best_score = -float("inf")
    best_params = None

    for idx, (conf, dist, age) in enumerate(combinations, start=1):
        logger.info(
            "Trial [%d/%d]: conf=%.2f, dist=%.2f, max_age=%d",
            idx,
            len(combinations),
            conf,
            dist,
            age,
        )

        seq_results = {}
        for seq in sequences:
            seq_video_path = os.path.join(mot17_dir, seq, "img1")
            res_file = os.path.join(output_dir, f"trial_{idx}_{seq}.txt")

            if not os.path.exists(seq_video_path):
                logger.warning("Sequence image directory missing: %s. Skipping.", seq_video_path)
                continue

            # Run tracking pipeline with candidate hyperparameters
            pipeline = TrackingPipeline(
                conf_threshold=conf,
                max_cosine_distance=dist,
                max_age=age,
            )
            try:
                pipeline.run(input_video_path=seq_video_path, output_mot_path=res_file)
                seq_results[seq] = res_file
            except Exception as e:
                logger.warning("Pipeline run failed for %s: %s", seq, e)

        if not seq_results:
            continue

        try:
            metrics = evaluator.evaluate_benchmark(seq_results)
            score = metrics["mota"] * 0.7 + metrics["idf1"] * 0.3
            logger.info(
                "Trial [%d] Metrics -> MOTA: %.2f%%, IDF1: %.2f%%, IDSW: %d",
                idx,
                metrics["mota"] * 100,
                metrics["idf1"] * 100,
                metrics["num_switches"],
            )

            if score > best_score:
                best_score = score
                best_params = {
                    "conf_threshold": conf,
                    "max_cosine_distance": dist,
                    "max_age": age,
                    "mota": metrics["mota"],
                    "idf1": metrics["idf1"],
                    "num_switches": metrics["num_switches"],
                }
        except Exception as e:
            logger.warning("Evaluation failed for trial [%d]: %s", idx, e)

    logger.info("\n=== Grid Search Tuning Complete ===")
    if best_params:
        logger.info("Best Parameters Found:")
        logger.info("  conf_threshold:       %.2f", best_params["conf_threshold"])
        logger.info("  max_cosine_distance:  %.2f", best_params["max_cosine_distance"])
        logger.info("  max_age:              %d", best_params["max_age"])
        logger.info("  MOTA:                 %.2f%%", best_params["mota"] * 100)
        logger.info("  IDF1:                 %.2f%%", best_params["idf1"] * 100)
        logger.info("  ID Switches:          %d", best_params["num_switches"])
    else:
        logger.info("No valid evaluation trials completed. Ensure MOT17 dataset is present in %s", mot17_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tune DeepSORT Hyperparameters on MOT17")
    parser.add_argument("--mot17-dir", default="data/mot17", help="Path to MOT17 root directory")
    args = parser.parse_args()

    grid_search_hyperparameters(mot17_dir=args.mot17_dir)
