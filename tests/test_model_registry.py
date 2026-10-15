import hashlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as Point
from unittest.mock import patch

import numpy as np

from src.eye.appearance_models import ITrackerModel, crop
from src.eye.model_registry import model_status
from src.eye.model_setup import install


class TestModelSetup(unittest.TestCase):
    def test_download_rejects_bad_hash_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "l2cs/model.py"
            path.parent.mkdir()
            path.write_bytes(b"original")
            manifest = {
                "l2cs/model.py": {
                    "url": "https://example.invalid/file",
                    "sha256": hashlib.sha256(b"expected").hexdigest(),
                }
            }
            with (
                patch("src.eye.model_setup.asset_manifest", return_value=manifest),
                patch("urllib.request.urlopen", return_value=io.BytesIO(b"tampered")),
            ):
                with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                    install("l2cs", directory)
            self.assertEqual(path.read_bytes(), b"original")
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_missing_optional_models_report_setup_instead_of_falling_back(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(model_status("mediapipe", directory)[0])
            for name in ("l2cs", "gazetr", "itracker"):
                available, reason = model_status(name, directory)
                self.assertFalse(available)
                self.assertIn("Needs setup", reason)

    def test_edge_crops_preserve_channels_without_negative_index_wrapping(self):
        image = np.zeros((20, 20, 3), np.uint8)
        image[:, 0] = [10, 20, 30]
        result = crop(image, (-10, -10, 20, 20), size=20)
        np.testing.assert_array_equal(result[0, 0], [10, 20, 30])
        self.assertEqual(result.shape, (20, 20, 3))


def sample_points():
    points = [Point(x=0.5, y=0.5) for _ in range(478)]
    for i, x, y in (
        (10, 0.5, 0.2),
        (152, 0.5, 0.85),
        (234, 0.25, 0.5),
        (454, 0.75, 0.5),
        (33, 0.33, 0.4),
        (133, 0.43, 0.4),
        (362, 0.57, 0.4),
        (263, 0.67, 0.4),
    ):
        points[i] = Point(x=x, y=y)
    return points


@unittest.skipUnless(
    os.environ.get("HANDGHOST_TEST_MODELS_DIR"),
    "requires explicitly installed optional model assets",
)
class TestInstalledAdapters(unittest.TestCase):
    def test_official_itracker_checkpoint_runs_caffe_inference(self):
        model = ITrackerModel(os.environ["HANDGHOST_TEST_MODELS_DIR"])
        self.addCleanup(model.close)
        result = model.predict(np.full((480, 640, 3), 128, np.uint8), sample_points())
        self.assertEqual(result.shape, (2,))
        self.assertTrue(np.isfinite(result).all())

    def test_torch_adapter_contracts_with_random_weights_not_pretrained_accuracy(self):
        import torch
        from torchvision.models.resnet import Bottleneck

        from src.eye.appearance_models import TorchGazeModel, _module

        root = Path(os.environ["HANDGHOST_TEST_MODELS_DIR"])
        for kind in ("l2cs", "gazetr"):
            with self.subTest(model=kind), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary) / kind
                shutil.copytree(root / kind, folder, ignore=shutil.ignore_patterns("weights.pt"))
                if kind == "l2cs":
                    network = _module(folder / "model.py", "_test_l2cs").L2CS(
                        Bottleneck, [3, 4, 6, 3], 90
                    )
                else:
                    _module(folder / "resnet.py", "_handghost_gazetr_resnet")
                    network = _module(
                        folder / "model.py",
                        "_test_gazetr",
                        (
                            (
                                "from resnet import resnet18",
                                "from _handghost_gazetr_resnet import resnet18",
                            ),
                            (
                                "torch.from_numpy(np.arange(0, 50)).cuda()",
                                "torch.arange(50, device=feature.device)",
                            ),
                        ),
                    ).Model()
                torch.save(network.state_dict(), folder / "weights.pt")
                del network
                adapter = TorchGazeModel(kind, temporary)
                try:
                    output = adapter.predict(np.full((480, 640, 3), 128, np.uint8), sample_points())
                    self.assertEqual(output.shape, (2,))
                    self.assertTrue(np.isfinite(output).all())
                finally:
                    adapter.close()
