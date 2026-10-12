"""Build a byte-reproducible contract-kit release archive and checksum file."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import tarfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).parents[2]
KIT_ROOT = REPOSITORY_ROOT / "contract-kit"
EXCLUDED_PARTS = {".pytest_cache", ".venv", "__pycache__"}


def release_files() -> list[tuple[Path, Path]]:
    files: list[tuple[Path, Path]] = []
    for path in KIT_ROOT.rglob("*"):
        relative = path.relative_to(REPOSITORY_ROOT)
        if path.is_file() and not EXCLUDED_PARTS.intersection(relative.parts):
            if path.suffix not in {".pyc", ".pyo"}:
                files.append((path, relative))
    for relative in (Path("LICENSE"), Path("NOTICE")):
        files.append((REPOSITORY_ROOT / relative, relative))
    for path in (REPOSITORY_ROOT / "LICENSES").glob("*"):
        if path.is_file():
            files.append((path, path.relative_to(REPOSITORY_ROOT)))
    return sorted(files, key=lambda item: item[1].as_posix())


def build_release(output_dir: Path) -> tuple[Path, Path]:
    version = (KIT_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    release_name = f"contract-kit-v{version}"
    archive_path = output_dir / f"{release_name}.tar.gz"
    checksum_path = output_dir / "SHA256SUMS"
    output_dir.mkdir(parents=True, exist_ok=True)

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for source, relative in release_files():
            payload = source.read_bytes()
            info = tarfile.TarInfo(f"{release_name}/{relative.as_posix()}")
            info.size = len(payload)
            info.mode = 0o644
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(payload))

    with archive_path.open("wb") as destination:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=destination, compresslevel=9, mtime=0
        ) as compressed:
            compressed.write(tar_buffer.getvalue())

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path.write_text(
        f"{digest}  {archive_path.name}\n", encoding="utf-8", newline="\n"
    )
    return archive_path, checksum_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path, default=REPOSITORY_ROOT / "dist"
    )
    args = parser.parse_args()
    archive_path, checksum_path = build_release(args.output_dir)
    print(archive_path)
    print(checksum_path)


if __name__ == "__main__":
    main()
