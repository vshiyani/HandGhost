"""Install checksum-pinned upstream assets outside the app. Never fetch on GUI startup."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.eye.model_registry import MODELS, model_directory
from src.eye.model_setup import install


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", choices=["l2cs", "gazetr", "itracker"])
    parser.add_argument("--directory", default=str(model_directory()))
    parser.add_argument(
        "--checkpoint", help="Local official L2CS ResNet50 or GazeTR-Hybrid state dictionary"
    )
    args = parser.parse_args()
    print(MODELS[args.model].license)
    print(install(args.model, args.directory, args.checkpoint))


if __name__ == "__main__":
    main()
