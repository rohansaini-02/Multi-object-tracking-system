"""
Unit Test Suite for Re-ID embedding reproducibility.

The Re-ID network is a ResNet-18 backbone followed by a linear projection
layer. No fine-tuned Re-ID checkpoint ships with the project, so that
projection keeps its initialised weights. Because ``nn.Linear`` draws them
from the global RNG, they were redrawn on every process start, which changed
the appearance embedding of every crop and made the whole tracking pipeline
non-reproducible: the same video produced different track ids from one run to
the next.

These tests pin the embedding down to a deterministic function of the input.

``pretrained=False`` is used throughout so the suite never needs the ImageNet
weight download and runs fully offline.
"""

import unittest

import numpy as np
import torch

from ml.tracker.reid_feature_extractor import (
    REID_PROJECTION_SEED,
    Net,
    _seeded_projection_init,
)


class TestSeededProjection(unittest.TestCase):
    """The projection layer must be initialised identically every time."""

    def test_two_networks_share_the_same_projection_weights(self):
        first = Net(reid_dim=128, pretrained=False)
        second = Net(reid_dim=128, pretrained=False)

        self.assertTrue(
            torch.equal(first.fc.weight, second.fc.weight),
            "the projection weights must not depend on the global RNG state",
        )
        self.assertTrue(
            torch.equal(first.fc.bias, second.fc.bias),
            "the projection bias must not depend on the global RNG state",
        )

    def test_projection_weights_are_not_the_default_initialisation(self):
        """Guard against silently dropping the deterministic re-initialisation."""
        torch.manual_seed(7)
        reference = torch.nn.Linear(512, 128)
        expected = reference.weight.detach().clone()

        actual = torch.nn.Linear(512, 128)
        _seeded_projection_init(actual, REID_PROJECTION_SEED)

        self.assertFalse(
            torch.equal(actual.weight, expected),
            "the seeded initialisation must differ from an ordinary draw",
        )

    def test_seeded_initialisation_does_not_touch_the_global_rng(self):
        """Drawing the projection must not shift the global RNG stream."""
        torch.manual_seed(1234)
        reference = torch.nn.Linear(512, 128)  # consumes the global RNG
        before = torch.randn(3)

        torch.manual_seed(1234)
        layer = torch.nn.Linear(512, 128)  # same consumption as above
        _seeded_projection_init(layer, REID_PROJECTION_SEED)
        after = torch.randn(3)

        self.assertTrue(torch.equal(before, after))

    def test_projection_accepts_a_different_seed(self):
        first = torch.nn.Linear(512, 128)
        second = torch.nn.Linear(512, 128)
        _seeded_projection_init(first, REID_PROJECTION_SEED)
        _seeded_projection_init(second, REID_PROJECTION_SEED + 1)

        self.assertFalse(torch.equal(first.weight, second.weight))


class TestEmbeddingDeterminism(unittest.TestCase):
    """The same crop must always produce the same embedding."""

    def test_same_input_produces_the_same_embedding(self):
        """The forward path must be a deterministic function of the weights."""
        torch.manual_seed(0)
        crop = torch.rand(1, 3, 64, 32)

        first = Net(reid_dim=128, pretrained=False)
        second = Net(reid_dim=128, pretrained=False)
        # The ResNet-18 backbone is randomly initialised when no checkpoint is
        # loaded, so both networks are given the very same weights here. In
        # production the backbone comes from the ImageNet checkpoint and only
        # the projection layer needs the fixed seed.
        second.load_state_dict(first.state_dict())
        first.eval()
        second.eval()

        with torch.inference_mode():
            a = first(crop)
            b = second(crop)

        self.assertTrue(torch.equal(a, b), "the embedding must be reproducible")
        self.assertAlmostEqual(
            float(a.norm(dim=1)[0]), 1.0, places=5, msg="the embedding must be L2 normalised"
        )

    def test_different_crops_produce_different_embeddings(self):
        net = Net(reid_dim=128, pretrained=False)
        net.eval()

        with torch.inference_mode():
            a = net(torch.rand(1, 3, 64, 32))
            b = net(torch.rand(1, 3, 64, 32))

        self.assertFalse(torch.equal(a, b))
        self.assertGreater(float((a - b).abs().max()), 1e-6)

    def test_embedding_carries_more_than_the_constant_offset(self):
        """A pure bias would collapse every crop onto the same direction."""
        net = Net(reid_dim=128, pretrained=False)
        net.eval()

        with torch.inference_mode():
            a = net(torch.rand(1, 3, 64, 32)).numpy()
            b = net(torch.rand(1, 3, 64, 32)).numpy()

        cosine = float(np.dot(a[0], b[0]))
        self.assertLess(cosine, 0.999, "two random crops must not be identical")


if __name__ == "__main__":
    unittest.main()
