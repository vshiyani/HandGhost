"""Archive a complete native bundle and write its SHA-256 checksum."""

import argparse
import hashlib
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("Windows", "Linux"), required=True)
    parser.add_argument("--arch", default="X64")
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, default=Path("release"))
    args = parser.parse_args()
    bundle = args.dist / "HandGhost"
    executable = "HandGhost.exe" if args.platform == "Windows" else "HandGhost"
    if not (bundle / executable).is_file() or not (bundle / "_internal").is_dir():
        parser.error(f"Incomplete native bundle: {bundle}")
    args.output.mkdir(parents=True, exist_ok=True)
    archive = Path(
        shutil.make_archive(
            str(args.output / f"HandGhost-{args.platform}-{args.arch}"),
            "zip" if args.platform == "Windows" else "gztar",
            root_dir=args.dist,
            base_dir="HandGhost",
        )
    )
    with archive.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(
        f"{checksum}  {archive.name}\n", encoding="utf-8"
    )
    print(archive)


if __name__ == "__main__":
    main()
