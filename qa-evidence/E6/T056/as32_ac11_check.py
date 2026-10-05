"""T-56 evidence: AS-32 sha256 comparison + AC-11 package determinism (read-only, no git writes)."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REL = Path("build/dev/release")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


print("== AS-32: bundled contract vs working tree vs HEAD vs lineage ==")
print("platform:", sys.platform)
ok = True
for ds in ("customer", "credit_card", "credit_card_txn"):
    bundle = REL / "cc" / f"{ds}.odcs.yaml"
    b_bytes = bundle.read_bytes()
    wt_path = f"DataContract/cc/contract/{ds}.odcs.yaml"
    wt_bytes = Path(wt_path).read_bytes()
    head_bytes = subprocess.run(  # nosec B603 B607
        ["git", "show", f"HEAD:{wt_path}"], capture_output=True, check=True
    ).stdout
    lin = {}
    for layer in ("bronze", "silver"):
        rj = json.loads((REL / "cc" / f"{layer}.cc.{ds}.resolved.json").read_text("utf-8"))
        lin[layer] = rj["lineage"]
    print(f"-- {ds}")
    b_crlf, wt_crlf = b"\r\n" in b_bytes, b"\r\n" in wt_bytes
    print(f"   bundle   {sha(b_bytes)}  CRLF={b_crlf}")
    print(f"   worktree {sha(wt_bytes)}  CRLF={wt_crlf}")
    print(f"   HEAD     {sha(head_bytes)}  (== worktree: {head_bytes == wt_bytes})")
    for layer, li in lin.items():
        print(
            f"   lineage.{layer}.contract_sha256 {li['contract_sha256']}"
            f"  bundle_path={li['contract_bundle_path']}  contract_file={li['contract_file']}"
        )
    checks = [
        b_bytes == wt_bytes,
        all(li["contract_sha256"] == sha(b_bytes) for li in lin.values()),
        all(li["contract_bundle_path"] == f"cc/{ds}.odcs.yaml" for li in lin.values()),
        b"\r\n" not in b_bytes,
    ]
    print(f"   bundle==worktree, sha==lineage(x2), bundle_path ok, no CRLF -> {checks}")
    ok = ok and all(checks)
print("AS-32 RESULT:", "PASS" if ok else "FAIL")

print()
print("== AC-11: package twice -> byte-identical ==")
from mdf.package import build_package  # noqa: E402

snap = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("build/_t56_snap")
if snap.exists():
    shutil.rmtree(snap)
build_package(env="dev")
shutil.copytree(REL, snap)
build_package(env="dev")
diff = []
for p in sorted(snap.rglob("*")):
    if p.is_file():
        rel = p.relative_to(snap)
        if p.read_bytes() != (REL / rel).read_bytes():
            diff.append(rel.as_posix())
extra = sorted(
    {q.relative_to(REL).as_posix() for q in REL.rglob("*") if q.is_file()}
    ^ {q.relative_to(snap).as_posix() for q in snap.rglob("*") if q.is_file()}
)
print("files compared:", sum(1 for p in snap.rglob("*") if p.is_file()))
print("differing files:", diff)
print("file-set difference:", extra)
m = json.loads((REL / "manifest.json").read_text("utf-8"))
print("commit/run-bound fields (same here because same commit):",
      {k: m[k] for k in ("release_id", "source_commit", "compiler_revision", "ci_run_url")})
print("AC-11 RESULT:", "PASS" if not diff and not extra else "FAIL")
shutil.rmtree(snap)
