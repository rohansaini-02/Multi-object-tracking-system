"""
Command-Line Interface (CLI) for Standalone ML Pipeline.
100% Database-Free and Redis-Free.

Usage:
  python -m ml.cli track --input video.mp4 --output output.mp4
  python -m ml.cli evaluate --sequence MOT17-04 --results-file res.txt
  python -m ml.cli train-reid --epochs 10 --output-weights weights/reid_fine_tuned.pth
"""

import argparse
import os
import sys

from ml.evaluation.mot_evaluator import MOTEvaluator
from ml.pipeline import TrackingPipeline
from ml.training.train_reid import train_reid_model


def main():
    parser = argparse.ArgumentParser(
        prog="ml.cli",
        description="Multi-Object Tracking System ML Module CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # 1. 'track' subcommand
    track_parser = subparsers.add_parser("track", help="Run object tracking on a video file")
    track_parser.add_argument("--input", "-i", required=True, help="Input video file path")
    track_parser.add_argument("--output", "-o", default=None, help="Output annotated video path")
    track_parser.add_argument("--mot-output", "-m", default=None, help="Output MOT format text file path")
    track_parser.add_argument("--weights", default="yolov8m.pt", help="Path to YOLO detector weights")
    track_parser.add_argument("--reid-weights", default=None, help="Path to custom Re-ID PyTorch weights")
    track_parser.add_argument("--conf", type=float, default=0.5, help="Detection confidence threshold")
    track_parser.add_argument("--device", default=None, help="Compute device ('cuda', 'cpu')")

    # 2. 'evaluate' subcommand
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate tracking results against MOT17 ground truth")
    eval_parser.add_argument("--mot17-dir", default="data/mot17", help="Root directory of MOT17 dataset")
    eval_parser.add_argument("--sequence", "-s", default=None, help="Sequence name (e.g. MOT17-04-FRCNN)")
    eval_parser.add_argument("--results-file", "-r", default=None, help="Path to predicted MOT text results file")

    # 3. 'train-reid' subcommand
    train_parser = subparsers.add_parser("train-reid", help="Fine-tune Re-ID appearance embedding model")
    train_parser.add_argument("--mot17-dir", default="data/mot17", help="Root directory of MOT17 dataset")
    train_parser.add_argument("--output-weights", default="weights/reid_fine_tuned.pth", help="Target output weight path")
    train_parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    train_parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    train_parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    train_parser.add_argument("--device", default=None, help="Compute device ('cuda', 'cpu')")

    args = parser.parse_args()

    if args.command == "track":
        print(f"[ML CLI] Running tracking pipeline on '{args.input}'...")
        
        def cli_progress_callback(current: int, total: int):
            pct = (current / total) * 100 if total > 0 else 0
            print(f"Progress: [{current}/{total}] frames ({pct:.1f}%)")

        pipeline = TrackingPipeline(
            detector_weights=args.weights,
            conf_threshold=args.conf,
            reid_weights=args.reid_weights,
            device=args.device,
        )
        res = pipeline.run(
            input_video_path=args.input,
            output_video_path=args.output,
            output_mot_path=args.mot_output,
            progress_callback=cli_progress_callback,
        )
        print("\n--- Pipeline Completed ---")
        print(f"Total Frames: {res.total_frames}")
        print(f"Processed Frames: {res.processed_frames}")
        print(f"Unique Track IDs: {res.total_tracks}")
        print(f"Average FPS: {res.fps:.2f}")
        if res.output_video_path:
            print(f"Annotated Video: {res.output_video_path}")
        if res.output_mot_path:
            print(f"MOT Format Results: {res.output_mot_path}")

    elif args.command == "evaluate":
        if not args.sequence or not args.results_file:
            print("Error: --sequence and --results-file are required for evaluation.")
            sys.exit(1)

        print(f"[ML CLI] Evaluating results for '{args.sequence}'...")
        evaluator = MOTEvaluator(mot17_base_dir=args.mot17_dir)
        metrics = evaluator.evaluate_sequence(args.sequence, args.results_file)

        print("\n--- Evaluation Metrics ---")
        print(f"MOTA:        {metrics['mota'] * 100:.2f}%")
        print(f"IDF1:        {metrics['idf1'] * 100:.2f}%")
        print(f"ID Switches: {metrics['num_switches']}")
        print(f"Precision:   {metrics['precision'] * 100:.2f}%")
        print(f"Recall:      {metrics['recall'] * 100:.2f}%")
        print(f"Mostly Tracked (MT): {metrics['mostly_tracked']}")
        print(f"Mostly Lost (ML):    {metrics['mostly_lost']}")

    elif args.command == "train-reid":
        print("[ML CLI] Starting Re-ID fine-tuning...")
        train_reid_model(
            mot17_dir=args.mot17_dir,
            output_weights_path=args.output_weights,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            device=args.device,
        )


if __name__ == "__main__":
    main()
