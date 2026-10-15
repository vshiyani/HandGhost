"""Optional gaze engines. Assets live outside the checkout and executable bundle."""

import hashlib
import importlib.util
import json
import os
from dataclasses import dataclass
from pathlib import Path

from src.utils.settings_manager import config_path


@dataclass(frozen=True)
class ModelInfo:
    label: str
    license: str
    files: tuple
    torch: bool = False


MODELS = {
    "mediapipe": ModelInfo("MediaPipe iris · lightweight", "Apache 2.0", ()),
    "l2cs": ModelInfo(
        "L2CS-Net · appearance",
        "MIT code; check checkpoint terms",
        ("model.py", "weights.pt"),
        True,
    ),
    "gazetr": ModelInfo(
        "GazeTR · transformer",
        "CC BY-NC-SA 4.0 · noncommercial",
        ("model.py", "resnet.py", "weights.pt"),
        True,
    ),
    "itracker": ModelInfo(
        "iTracker · research",
        "Research-only · no redistribution",
        (
            "weights.caffemodel",
            "itracker_deploy.prototxt",
            "mean_face_224.mat",
            "mean_left_224.mat",
            "mean_right_224.mat",
        ),
    ),
}


def model_directory(settings=None):
    configured = settings.get("model_directory", "") if settings else ""
    return Path(
        configured or os.environ.get("HANDGHOST_MODELS_DIR", "") or config_path().parent / "models"
    ).expanduser()


def asset_manifest():
    return json.loads(Path(__file__).with_name("model_assets.json").read_text(encoding="utf-8"))


def verify_asset(path, asset):
    expected = asset_manifest()[asset]["sha256"]
    actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"Integrity check failed for {asset}. Reinstall the official assets.")


def model_status(model, directory):
    if model not in MODELS:
        return False, "Unknown model"
    info = MODELS[model]
    missing = [name for name in info.files if not (Path(directory) / model / name).is_file()]
    if missing:
        return False, "Needs setup: " + ", ".join(missing)
    if info.torch and importlib.util.find_spec("torch") is None:
        return False, "Needs the optional PyTorch engine (see model setup guide)"
    if model == "l2cs" and importlib.util.find_spec("torchvision") is None:
        return False, "Needs the optional torchvision engine"
    return True, "Ready · " + info.license
