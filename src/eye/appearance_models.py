"""Inference adapters using pinned upstream definitions and user-owned checkpoints.

No research code/weights are vendored into the application. Loaded upstream source
is verified against the pinned manifest before execution. Checkpoints load as
weights-only state dictionaries, never arbitrary serialized Python objects.
"""

import sys
import types
from pathlib import Path

import cv2
import numpy as np

from src.eye.model_registry import model_status, verify_asset


def _module(path, name, replacements=()):
    source = Path(path).read_text(encoding="utf-8")
    for old, new in replacements:
        if source.count(old) != 1:
            raise ValueError("Unexpected upstream model format; reinstall pinned model sources.")
        source = source.replace(old, new)
    module = types.ModuleType(name)
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def face_box(points, width, height):
    coordinates = np.asarray([(p.x * width, p.y * height) for p in points[:468]])
    low, high = coordinates.min(axis=0), coordinates.max(axis=0)
    center = (low + high) / 2
    size = max(high - low) * 1.08
    return (
        int(center[0] - size / 2),
        int(center[1] - size / 2),
        max(2, int(size)),
        max(2, int(size)),
    )


def crop(image, box, size=224):
    x, y, width, height = box
    # Clamp to edges, reproducing the edge extension used by GazeCapture crops.
    xs = np.clip(np.arange(x, x + width), 0, image.shape[1] - 1)
    ys = np.clip(np.arange(y, y + height), 0, image.shape[0] - 1)
    return cv2.resize(image[np.ix_(ys, xs)], (size, size), interpolation=cv2.INTER_LINEAR)


class TorchGazeModel:
    def __init__(self, model, directory):
        available, reason = model_status(model, directory)
        if not available:
            raise RuntimeError(reason + ". Open Preferences → Gaze models for setup.")
        import torch

        self.torch = torch
        torch.set_num_threads(2)
        self.kind = model
        folder = Path(directory) / model
        verify_asset(folder / "model.py", model + "/model.py")
        if model == "l2cs":
            from torchvision.models.resnet import Bottleneck

            upstream = _module(folder / "model.py", "_handghost_l2cs")
            self.model = upstream.L2CS(Bottleneck, [3, 4, 6, 3], 90)
        else:
            verify_asset(folder / "resnet.py", "gazetr/resnet.py")
            _module(folder / "resnet.py", "_handghost_gazetr_resnet")
            upstream = _module(
                folder / "model.py",
                "_handghost_gazetr",
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
            )
            self.model = upstream.Model()
        state = torch.load(folder / "weights.pt", map_location="cpu", weights_only=True)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        if not isinstance(state, dict):
            raise ValueError("Expected a model state dictionary, not a serialized model.")
        state = {key.removeprefix("module."): value for key, value in state.items()}
        self.model.load_state_dict(state, strict=True)
        self.model.eval()

    def predict(self, image, points):
        face = crop(
            image,
            face_box(points, image.shape[1], image.shape[0]),
            448 if self.kind == "l2cs" else 224,
        )
        if self.kind == "l2cs":
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        data = np.ascontiguousarray(face.transpose(2, 0, 1), dtype=np.float32) / 255
        if self.kind == "l2cs":
            data = (data - np.array([0.485, 0.456, 0.406])[:, None, None]) / np.array(
                [0.229, 0.224, 0.225]
            )[:, None, None]
        tensor = self.torch.from_numpy(data.astype(np.float32)[None])
        with self.torch.inference_mode():
            if self.kind == "gazetr":
                result = self.model({"face": tensor})[0].cpu().numpy()
            else:
                result = [
                    (self.torch.softmax(head, dim=1)[0] * self.torch.arange(90)).sum().item() * 4
                    - 180
                    for head in self.model(tensor)
                ]
                result = np.deg2rad(result)
        return np.asarray(result, dtype=float).reshape(2)

    def close(self):
        self.model = None


class ITrackerModel:
    kind = "itracker"

    def __init__(self, directory):
        available, reason = model_status("itracker", directory)
        if not available:
            raise RuntimeError(reason + ". See docs/models.md.")
        from scipy.io import loadmat

        folder = Path(directory) / "itracker"
        for filename in (
            "weights.caffemodel",
            "itracker_deploy.prototxt",
            "mean_face_224.mat",
            "mean_left_224.mat",
            "mean_right_224.mat",
        ):
            verify_asset(folder / filename, "itracker/" + filename)
        self.net = cv2.dnn.readNetFromCaffe(
            str(folder / "itracker_deploy.prototxt"), str(folder / "weights.caffemodel")
        )
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self.means = {
            name: loadmat(folder / f"mean_{name}_224.mat")["image_mean"].astype(np.float32)
            for name in ("left", "right", "face")
        }

    def predict(self, image, points):
        height, width = image.shape[:2]
        box = face_box(points, width, height)
        images = {"face": crop(image, box)}
        # Anatomical left is on image right for unmirrored input. Caller supplies
        # the original (unmirrored) frame to all appearance models.
        for name, indices in (("left", (362, 263)), ("right", (33, 133))):
            a, b = points[indices[0]], points[indices[1]]
            center = ((a.x + b.x) * width / 2, (a.y + b.y) * height / 2)
            size = max(8, int(abs(a.x - b.x) * width * 1.7))
            images[name] = crop(
                image, (int(center[0] - size / 2), int(center[1] - size / 2), size, size)
            )
        for name, value in images.items():
            data = (value.astype(np.float32) - self.means[name]).transpose(2, 0, 1)[None]
            self.net.setInput(np.ascontiguousarray(data), "image_" + name)
        x, y, w, h = box
        grid = np.zeros((25, 25), dtype=np.float32)
        x0, y0 = int(np.clip(x / width * 25, 0, 24)), int(np.clip(y / height * 25, 0, 24))
        x1, y1 = (
            int(np.clip(np.ceil((x + w) / width * 25), 1, 25)),
            int(np.clip(np.ceil((y + h) / height * 25), 1, 25)),
        )
        grid[y0:y1, x0:x1] = 1
        self.net.setInput(grid.reshape(1, 625, 1, 1), "facegrid")
        return np.asarray(self.net.forward("fc3"), dtype=float).reshape(2)

    def close(self):
        self.net = None


def exercise_model(name, directory):
    """Packaging diagnostic: synthetic crops test loading/inference, not gaze accuracy."""
    from types import SimpleNamespace

    points = [SimpleNamespace(x=0.5, y=0.5) for _ in range(478)]
    for index, x, y in (
        (10, 0.5, 0.2),
        (152, 0.5, 0.85),
        (234, 0.25, 0.5),
        (454, 0.75, 0.5),
        (33, 0.33, 0.4),
        (133, 0.43, 0.4),
        (362, 0.57, 0.4),
        (263, 0.67, 0.4),
    ):
        points[index] = SimpleNamespace(x=x, y=y)
    backend = ITrackerModel(directory) if name == "itracker" else TorchGazeModel(name, directory)
    try:
        result = backend.predict(np.full((480, 640, 3), 128, np.uint8), points)
        if result.shape != (2,) or not np.isfinite(result).all():
            raise RuntimeError("Model did not return a finite gaze pair")
        return result.tolist()
    finally:
        backend.close()
