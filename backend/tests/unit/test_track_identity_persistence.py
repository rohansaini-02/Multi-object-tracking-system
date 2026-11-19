"""
Unit Test Suite for Track Identity Persistence (bounding boxes + stable track ids).

These tests pin down the four properties the tracking pipeline has to guarantee:

1. every detected object receives its own bounding box,
2. the bounding box follows the object while it moves,
3. the track id stays constant while the object is visible,
4. the track id survives movement, overlap and temporary occlusion, and is never
   swapped between two objects.

The Re-ID network is replaced by a deterministic stub so the association logic is
exercised offline and without loading neural network weights.
"""

import unittest
from unittest import mock

import numpy as np

from ml.tracker import deep_sort
from ml.tracker.deep_sort import DeepSortTracker
from ml.types import BoundingBox, Detection

FRAME = np.zeros((720, 1280, 3), dtype=np.uint8)


class DeterministicReidExtractor:
    """Stand-in for the ResNet18 Re-ID network.

    Emits one stable one-hot embedding per object identity so that the
    appearance matcher can be exercised deterministically and offline.
    """

    def __init__(self, feature_dim: int = 128, model_path=None, device=None):
        self.feature_dim = feature_dim

    def extract(self, frame, detections):
        for det in detections:
            feat = np.zeros(self.feature_dim, dtype=np.float32)
            feat[int(det.class_id) % self.feature_dim] = 1.0
            det.feature = feat
        return detections


def make_tracker(**kwargs):
    """Build a tracker whose Re-ID extractor is the deterministic stub."""
    kwargs.setdefault("max_cosine_distance", 0.2)
    kwargs.setdefault("max_age", 30)
    kwargs.setdefault("n_init", 1)
    with mock.patch.object(deep_sort, "ReidFeatureExtractor", DeterministicReidExtractor):
        return DeepSortTracker(**kwargs)


def detection(x, y, w=40, h=80, obj_id=0, confidence=0.9):
    """Build a detection for the object identified by ``obj_id``."""
    return Detection(
        bbox=BoundingBox(float(x), float(y), float(x + w), float(y + h)),
        confidence=confidence,
        class_id=obj_id,
    )


def run_tracker(tracker, frame_detections):
    """Feed a list of per-frame detection lists through the tracker."""
    return [tracker.update(dets, frame=FRAME) for dets in frame_detections]


class TestBoundingBoxPerObject(unittest.TestCase):
    """Every detected object has to end up with its own bounding box."""

    def test_each_detected_object_gets_its_own_bounding_box(self):
        tracker = make_tracker()
        frames = [
            [detection(100 + i * 10, 200, obj_id=0), detection(600, 400, obj_id=1)]
            for i in range(8)
        ]
        results = run_tracker(tracker, frames)

        for index, tracks in enumerate(results):
            if index == 0:
                self.assertEqual(len(tracks), 0, "frame 1: tracks are still tentative")
                continue
            self.assertEqual(
                len(tracks), 2, f"frame {index + 1} must expose one box per detected object"
            )

        last = results[-1]
        self.assertNotAlmostEqual(
            last[0].bbox.x1, last[1].bbox.x1, delta=1.0, msg="the two objects share a box"
        )

    def test_bounding_box_follows_the_moving_object(self):
        tracker = make_tracker()
        true_x = [100 + i * 15 for i in range(12)]
        results = run_tracker(tracker, [[detection(x, 200)] for x in true_x])

        tracked_x = [t.bbox.x1 for tracks in results for t in tracks]
        self.assertGreaterEqual(len(tracked_x), 8, "the object must be boxed on every frame")
        self.assertEqual(
            tracked_x, sorted(tracked_x), "the box must move forward with the object"
        )
        for true, tracked in zip(true_x[1:], tracked_x):
            self.assertLess(
                abs(tracked - true), 40.0, "the tracked box must stay on the moving object"
            )


class TestTrackIdStability(unittest.TestCase):
    """A track id has to stay constant while the object is visible."""

    def test_track_ids_stay_constant_across_frames(self):
        tracker = make_tracker()
        frames = [
            [detection(100 + i * 8, 200, obj_id=0), detection(600 - i * 8, 400, obj_id=1)]
            for i in range(15)
        ]
        results = run_tracker(tracker, frames)

        id_sets = {
            frozenset(t.track_id for t in tracks) for tracks in results if tracks
        }
        self.assertEqual(len(id_sets), 1, f"the track ids changed across frames: {id_sets}")

        unique_ids = sorted({t.track_id for tracks in results for t in tracks})
        self.assertEqual(len(unique_ids), 2, f"expected two identities, got {unique_ids}")

    def test_identity_survives_a_temporary_occlusion(self):
        tracker = make_tracker()
        frames = []
        for i in range(8):
            frames.append([detection(100 + i * 10, 200, obj_id=0)])
        for _ in range(4):
            frames.append([])  # the object is fully occluded
        for i in range(8, 16):
            frames.append([detection(100 + i * 10, 200, obj_id=0)])

        results = run_tracker(tracker, frames)
        ids = sorted({t.track_id for tracks in results for t in tracks})
        self.assertEqual(len(ids), 1, f"the identity must survive the occlusion, got {ids}")

    def test_ids_are_not_swapped_when_objects_cross(self):
        tracker = make_tracker()
        frames = [
            [
                detection(100 + i * 30, 200 + i * 10, obj_id=0),
                detection(520 - i * 30, 200 + i * 10, obj_id=1),
            ]
            for i in range(14)
        ]
        results = run_tracker(tracker, frames)

        binding = {}
        for tracks in results:
            for track in tracks:
                previous = binding.setdefault(track.track_id, track.class_id)
                self.assertEqual(
                    previous,
                    track.class_id,
                    "a track id changed the object it follows",
                )

        self.assertEqual(len(binding), 2, f"expected two identities, got {sorted(binding)}")


class TestFastMotionRegression(unittest.TestCase):
    """Regression guard for objects that move faster than the IoU gate allows.

    A 40x80 box moving 30 px per frame only overlaps its own previous position
    by ~12%, which the classic DeepSORT IoU gate (>= 30% overlap) rejects. The
    rejected tentative track used to be deleted on its very first miss, so a new
    track id was minted on every single frame and no box was drawn at all.
    """

    def test_fast_moving_object_keeps_its_id_and_its_box(self):
        tracker = make_tracker()
        frames = [[detection(100 + i * 30, 200 + i * 10)] for i in range(12)]
        results = run_tracker(tracker, frames)

        for index, tracks in enumerate(results[1:], start=2):
            self.assertEqual(len(tracks), 1, f"frame {index} must expose exactly one box")

        ids = sorted({t.track_id for tracks in results for t in tracks})
        self.assertEqual(ids, [1], f"the object must keep a single stable id, got {ids}")

    def test_fast_moving_object_keeps_its_id_with_a_strict_n_init(self):
        tracker = make_tracker(n_init=3)
        frames = [[detection(100 + i * 30, 200 + i * 10)] for i in range(12)]
        results = run_tracker(tracker, frames)

        ids = sorted({t.track_id for tracks in results for t in tracks})
        self.assertEqual(ids, [1], f"the object must keep a single stable id, got {ids}")


class TestTentativeTrackGracePeriod(unittest.TestCase):
    """A track that is seen once, misses a frame and returns must keep its id."""

    def test_tentative_track_survives_a_single_missed_frame(self):
        tracker = make_tracker()
        frames = [
            [detection(100, 200, obj_id=0)],  # frame 1 - the track is born
            [],  # frame 2 - the detection is missed
            [detection(100, 200, obj_id=0)],  # frame 3 - the object is back
            [detection(100, 200, obj_id=0)],  # frame 4 - confirmed
        ]
        results = run_tracker(tracker, frames)

        ids = sorted({t.track_id for tracks in results for t in tracks})
        self.assertEqual(ids, [1], f"the re-acquired object must keep its id, got {ids}")

    def test_tentative_track_is_eventually_discarded(self):
        tracker = make_tracker()
        frames = [[detection(100, 200, obj_id=0)]] + [[]] * 12
        results = run_tracker(tracker, frames)

        self.assertEqual(
            [len(tracks) for tracks in results],
            [0] * len(results),
            "a track that never reappears must not keep producing boxes",
        )
        self.assertEqual(
            len(tracker.tracks), 0, "the abandoned tentative track must be discarded"
        )


if __name__ == "__main__":
    unittest.main()
