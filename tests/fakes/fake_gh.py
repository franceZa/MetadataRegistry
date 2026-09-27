"""Fake `gh` for T-39 tests: `release download <id> -R <repo> -D <dir>` copies
$FAKE_GH_RELEASES/<id>/* ; `release view <id> -R <repo> --json url -q .url` prints a URL."""

import os
import shutil
import sys
from pathlib import Path


def main(argv):
    root = Path(os.environ["FAKE_ROOT"])
    with (root / "calls.log").open("a", encoding="utf-8") as f:
        f.write("gh " + " ".join(argv) + "\n")
    if argv[:2] == ["release", "download"]:
        src = Path(os.environ["FAKE_GH_RELEASES"]) / argv[2]
        if not src.is_dir():
            print(f"release not found: {argv[2]}", file=sys.stderr)
            return 1
        dst = Path(argv[argv.index("-D") + 1])
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            shutil.copy2(f, dst / f.name)
        return 0
    if argv[:2] == ["release", "view"]:
        repo = argv[argv.index("-R") + 1]
        print(f"https://github.com/{repo}/releases/tag/{argv[2]}")
        return 0
    print(f"fake gh: unsupported {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
