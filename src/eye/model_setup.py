"""Explicit, checksum-verified installation of optional upstream assets."""

import hashlib
import shutil
import tempfile
import urllib.request
from pathlib import Path

from src.eye.model_registry import MODELS, asset_manifest

SOURCES = {
    "l2cs": "https://drive.google.com/drive/folders/17p6ORr-JQJcw-eYtG2WGNiuS_qVKwdWd",
    "gazetr": "https://drive.google.com/file/d/1WEiKZ8Ga0foNmxM7xFabI4D5ajThWAWj/view",
}


def install(model, destination, checkpoint=None):
    destination = Path(destination)
    assets = asset_manifest()
    for name, metadata in assets.items():
        if not name.startswith(model + "/"):
            continue
        target = destination / name
        if (
            target.exists()
            and hashlib.sha256(target.read_bytes()).hexdigest() == metadata["sha256"]
        ):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with urllib.request.urlopen(metadata["url"], timeout=90) as response:
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    shutil.copyfileobj(response, stream)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != metadata["sha256"]:
                raise ValueError(f"Checksum mismatch: {name}")
            temporary.replace(target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    if checkpoint is not None:
        source = Path(checkpoint).expanduser().resolve(strict=True)
        target = destination / model / "weights.pt"
        # No unpickling: runtime uses torch.load(weights_only=True) and strict state keys.
        if source != target.resolve():
            import torch

            state = torch.load(source, map_location="cpu", weights_only=True)
            if isinstance(state, dict) and "state_dict" in state:
                state = state["state_dict"]
            key = "fc_yaw_gaze.weight" if model == "l2cs" else "feed.weight"
            if not isinstance(state, dict) or not any(
                name.removeprefix("module.") == key for name in state
            ):
                raise ValueError(
                    "Checkpoint does not match the selected model. Use the official ResNet50 / GazeTR-Hybrid state dictionary."
                )
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    with source.open("rb") as original:
                        shutil.copyfileobj(original, stream)
                temporary.replace(target)
            finally:
                if temporary is not None and temporary.exists():
                    temporary.unlink()
    if model in SOURCES and not (destination / model / "weights.pt").is_file():
        return (
            f"Upstream source installed. Download your checkpoint from {SOURCES[model]}\n"
            f"Then rerun with --checkpoint /path/to/weights. See docs/models.md."
        )
    else:
        return f"Installed {MODELS[model].label} in {destination / model}"
