"""T-56 evidence: derive v2 / v1 / v4 fixtures from the real v3 build and run the real CLI.

Usage: uv run python qa-evidence/E6/T056/compat_fixtures.py <scratch_dir>
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REL = Path("build/dev/release")
out = Path(sys.argv[1])
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)


def load(p):
    return json.loads((p / "manifest.json").read_text(encoding="utf-8"))


def save(p, m):
    (p / "manifest.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), "utf-8")


# v2: drop contracts + v3-only entry fields
v2 = out / "v2"
shutil.copytree(REL, v2)
m = load(v2)
for e in m["files"]:
    if e["kind"] == "odcs_contract":
        (v2 / e["path"]).unlink()
m["files"] = [{"path": e["path"], "sha256": e["sha256"]} for e in m["files"]
              if e["kind"] == "resolved_config"]
m["file_count"] = len(m["files"])
m["manifest_version"] = 2
save(v2, m)

# v1: flatten v2
v1 = out / "v1"
shutil.copytree(v2, v1)
m = load(v1)
for e in m["files"]:
    src, name = e["path"].split("/", 1)
    shutil.move(str(v1 / src / name), str(v1 / name))
    e["path"] = name
(v1 / "cc").rmdir()
m["manifest_version"] = 1
save(v1, m)

# v4: real v3 with manifest_version 4
v4 = out / "v4"
shutil.copytree(REL, v4)
m = load(v4)
m["manifest_version"] = 4
save(v4, m)

for name in ("v1", "v2", "v4"):
    r = subprocess.run(  # nosec B603 B607
        ["uv", "run", "mdf", "verify-package", str(out / name)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(f"--- fixture {name}: exit={r.returncode}")
    print((r.stdout + r.stderr).replace("warning: Failed to set cwd to temp dir\n", "").strip())
shutil.rmtree(out)
