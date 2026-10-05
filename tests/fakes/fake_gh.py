"""Fake `gh` for T-39/T-52 tests.

release download <id> -R <repo> -D <dir> [-p PATTERN]
    copies $FAKE_GH_RELEASES/<id>/* into <dir>; with -p PATTERN (fnmatch) only matching
    file names are copied (used by T-52 CD-1 to fetch a single "<id>.zip" asset).
release view <id> -R <repo> --json url -q .url
    prints a release URL.
release view <id> -R <repo> --json assets -q '.assets[].name'
    prints one asset file name per line (the files under $FAKE_GH_RELEASES/<id>/).
"""

import fnmatch
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
        pattern = argv[argv.index("-p") + 1] if "-p" in argv else None
        names = [f.name for f in src.iterdir()]
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
            if not names:
                print(f"no assets match pattern: {pattern}", file=sys.stderr)
                return 1
        for name in names:
            shutil.copy2(src / name, dst / name)
        return 0
    if argv[:2] == ["release", "view"]:
        rid = argv[2]
        repo = argv[argv.index("-R") + 1]
        if "--json" in argv and argv[argv.index("--json") + 1] == "assets":
            src = Path(os.environ["FAKE_GH_RELEASES"]) / rid
            if not src.is_dir():
                print(f"release not found: {rid}", file=sys.stderr)
                return 1
            for name in sorted(f.name for f in src.iterdir()):
                print(name)
            return 0
        print(f"https://github.com/{repo}/releases/tag/{rid}")
        return 0
    print(f"fake gh: unsupported {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
