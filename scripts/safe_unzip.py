"""T-52 · FR-L.1a/L.1b/L.3a — extract a release zip while guarding against zip-slip.

Shared by `.github/workflows/release.yml` (idempotency check) and `scripts/deliver_release.sh`
CD-1 so the same rule applies in CI and locally. stdlib `zipfile` only — no shelling out to
`unzip` (some distros do not guard against zip-slip themselves).

Every entry is validated BEFORE any file is written. If a single entry is rejected, nothing is
extracted (the destination directory is not even created). Rejected entries print
`[ZIP_SLIP] <reason>: <entry name>` to stderr and the process exits 1.

usage: python scripts/safe_unzip.py <zip_path> <dest_dir>
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path, PurePosixPath


class ZipSlipError(Exception):
    pass


def _check_entry(info: zipfile.ZipInfo) -> None:
    name = info.filename
    if not name:
        raise ZipSlipError(f"empty entry name: {name!r}")
    if name.startswith("/") or name.startswith("\\"):
        raise ZipSlipError(f"absolute path: {name}")
    if len(name) >= 2 and name[1] == ":":
        raise ZipSlipError(f"drive letter: {name}")
    if "\\" in name:
        raise ZipSlipError(f"backslash in path: {name}")
    parts = PurePosixPath(name).parts
    if ".." in parts:
        raise ZipSlipError(f"parent traversal: {name}")
    if any(p.startswith("/") for p in parts):
        raise ZipSlipError(f"absolute path: {name}")
    # symlink entries: unix mode bits live in the high 16 bits of external_attr
    mode = (info.external_attr >> 16) & 0xFFFF
    if mode and (mode & 0o170000) == 0o120000:
        raise ZipSlipError(f"symlink entry: {name}")


def safe_unzip(zip_path: str | Path, dest_dir: str | Path) -> None:
    """Validate every entry of `zip_path`, then extract all of them into `dest_dir`.

    Raises ZipSlipError (nothing written) or zipfile.BadZipFile if the archive is malformed.
    """
    dest = Path(dest_dir)
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        for info in infos:
            _check_entry(info)
        dest.mkdir(parents=True, exist_ok=True)
        zf.extractall(dest)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python scripts/safe_unzip.py <zip_path> <dest_dir>", file=sys.stderr)
        return 2
    zip_path, dest_dir = argv
    if not Path(zip_path).is_file():
        print(f"[SAFE_UNZIP] zip not found: {zip_path}", file=sys.stderr)
        return 1
    try:
        safe_unzip(zip_path, dest_dir)
    except ZipSlipError as e:
        print(f"[ZIP_SLIP] {e}", file=sys.stderr)
        return 1
    except zipfile.BadZipFile as e:
        print(f"[SAFE_UNZIP] bad zip file: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
