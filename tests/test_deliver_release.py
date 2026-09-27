"""T-39 — scripts/deliver_release.sh against fake `databricks` / `gh` (no network).

AC-38 immutable rerun + tamper · AC-39 resume partial copy · sealed-but-different = fail ·
manifest copied last · evidence has no host/user/token · release_id required.
"""

import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

import pytest

from mdf.package import build_package

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "deliver_release.sh"
FAKES = ROOT / "tests" / "fakes"
REPO = "franceZa/MetadataRegistry"
# fake CLI log line of the read-only login check (preflight) — the only call allowed before CD-1
PREFLIGHT_CALL = "current-user me --output json"


def _bash() -> str | None:
    if os.name == "nt":
        for c in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
            if Path(c).exists():
                return c
    return shutil.which("bash")


BASH = _bash()
pytestmark = pytest.mark.skipif(BASH is None, reason="bash not available")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    """Real `--release` package built in a throwaway clean git repo."""
    base = tmp_path_factory.mktemp("t39pkg")
    repo = base / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "DataContract", repo / "DataContract")
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copy2(ROOT / "uv.lock", repo / "uv.lock")
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
    for args in (
        ("init", "-q"),
        ("config", "user.email", "t@example.invalid"),
        ("config", "user.name", "t"),
        ("config", "core.autocrlf", "false"),
        ("add", "-A"),
        ("commit", "-q", "-m", "fixture"),
    ):
        _git(repo, *args)
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        pkg = repo / build_package(env="dev", release=True)
    finally:
        os.chdir(cwd)
    rid = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))["release_id"]
    return {"pkg": pkg, "rid": rid}


@pytest.fixture()
def world(tmp_path, release):
    """Fake workspace + fake GitHub Release + PATH with fake CLIs."""
    root = tmp_path / "fake"
    (root / "Volumes").mkdir(parents=True)
    gh_rel = tmp_path / "gh_releases"
    shutil.copytree(release["pkg"], gh_rel / release["rid"])
    bindir = tmp_path / "bin"
    bindir.mkdir()
    py = Path(sys.executable).as_posix()
    for name, target in (("databricks", "fake_databricks.py"), ("gh", "fake_gh.py")):
        w = bindir / name
        w.write_text(
            f'#!/usr/bin/env bash\nexec "{py}" "{(FAKES / target).as_posix()}" "$@"\n',
            encoding="utf-8",
            newline="\n",
        )
        w.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(bindir) + os.pathsep + os.environ.get("PATH", ""),
        "FAKE_ROOT": str(root),
        "FAKE_GH_RELEASES": str(gh_rel),
        "MDF_PY": py,
        "MDF_WORK_DIR": (tmp_path / "work").as_posix(),
        "MDF_REPO": REPO,
        "MDF_POLL_SECONDS": "0",
        "MDF_ACTOR": "manual",
    }
    env.pop("GITHUB_ACTIONS", None)
    dest = root / "Volumes" / "dev_catalog" / "ops" / "files" / "releases" / release["rid"]
    return {
        "env": env,
        "root": root,
        "dest": dest,
        "gh_rel": gh_rel,
        "work": tmp_path / "work",
        "rid": release["rid"],
        "pkg": release["pkg"],
    }


def _deliver(world, *extra):
    return subprocess.run(  # nosec B603
        [BASH, SCRIPT.as_posix(), *extra],
        env=world["env"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=ROOT,
        timeout=300,
    )


def _registry(world) -> list[dict]:
    p = world["root"] / "registry.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _calls(world) -> list[str]:
    p = world["root"] / "calls.log"
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def _uploads(world, calls=None) -> list[str]:
    """Single-file `fs cp <local> dbfs:/...` calls = writes to the Volume."""
    out = []
    for c in calls if calls is not None else _calls(world):
        parts = c.split()
        if parts[:2] == ["fs", "cp"] and "-r" not in parts:
            paths = [x for x in parts[2:] if not x.startswith("-")]
            if not paths[0].startswith("dbfs:") and paths[1].startswith("dbfs:"):
                out.append(paths[1])
    return out


def _assert_ok(r):
    assert r.returncode == 0, f"rc={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"


# ---------- happy path (CD-1…8) ----------


def test_happy_path_cd1_to_cd8(world):
    r = _deliver(world, world["rid"])
    _assert_ok(r)
    # Volume = package, byte for byte
    assert sorted(p.name for p in world["dest"].iterdir()) == sorted(
        p.name for p in world["pkg"].iterdir()
    )
    for f in world["pkg"].iterdir():
        assert _sha(world["dest"] / f.name) == _sha(f)
    # registry: exactly REGISTERED + ACTIVATED with the CD-2 hash
    rows = _registry(world)
    assert [x["event"] for x in rows] == ["REGISTERED", "ACTIVATED"]
    sha = _sha(world["pkg"] / "manifest.json")
    assert {x["manifest_sha256"] for x in rows} == {sha}
    assert rows[0]["github_release_url"] == f"https://github.com/{REPO}/releases/tag/{world['rid']}"
    assert rows[0]["actor"] == "manual"
    # manifest.json is the LAST upload
    ups = _uploads(world)
    assert len(ups) == len(list(world["pkg"].iterdir()))
    assert ups[-1].endswith("/manifest.json")
    assert not any(u.endswith("/manifest.json") for u in ups[:-1])
    # bundle deployed twice (CD-5 + CD-8 var)
    deploys = [c for c in _calls(world) if c.startswith("bundle deploy")]
    assert len(deploys) == 2 and f"active_release_id={world['rid']}" in deploys[1]


def test_evidence_masked_and_labelled_manual(world):
    _assert_ok(_deliver(world, world["rid"]))
    ev = (world["work"] / world["rid"] / "evidence.md").read_text(encoding="utf-8")
    for bad in ("dbc-0000-fake", "cloud.databricks.com", "@", "dapi", "token"):
        assert bad not in ev, bad
    assert "https://<host>" in ev
    assert "manual run" in ev and "NOT proven" in ev
    for step in ("CD-1", "CD-2", "CD-3", "CD-4", "CD-5", "CD-6", "CD-7", "CD-8"):
        assert f"- {step}:" in ev, step


# ---------- AC-38 ----------


def test_ac38_rerun_same_id_no_copy_no_new_rows(world):
    _assert_ok(_deliver(world, world["rid"]))
    before_rows = _registry(world)
    n_calls = len(_calls(world))
    r = _deliver(world, world["rid"])
    _assert_ok(r)
    second = _calls(world)[n_calls:]
    assert _uploads(world, second) == []
    assert _registry(world) == before_rows
    assert "already sealed" in r.stdout


def test_ac38_tampered_package_fails_at_cd2_without_touching_workspace(world):
    f = world["gh_rel"] / world["rid"] / "silver.cc.customer.resolved.json"
    data = bytearray(f.read_bytes())
    data[len(data) // 2] ^= 0x01
    f.write_bytes(bytes(data))
    r = _deliver(world, world["rid"])
    assert r.returncode != 0
    assert "[CD-2]" in r.stderr
    # only the read-only login check (preflight) — no fs / bundle / api call reached Databricks
    assert [c for c in _calls(world) if not c.startswith("gh ")] == [PREFLIGHT_CALL]
    assert not world["dest"].exists()
    assert _registry(world) == []


# ---------- AC-39 ----------


def test_ac39_partial_copy_is_resumed(world):
    world["dest"].mkdir(parents=True)
    (world["dest"] / "bronze.cc.customer.resolved.json").write_text("half-written", "utf-8")
    shutil.copy2(world["pkg"] / "silver.cc.customer.resolved.json", world["dest"])
    r = _deliver(world, world["rid"])
    _assert_ok(r)
    assert "partial folder" in r.stdout
    for f in world["pkg"].iterdir():
        assert _sha(world["dest"] / f.name) == _sha(f), f.name
    assert [x["event"] for x in _registry(world)] == ["REGISTERED", "ACTIVATED"]


# ---------- sealed but different ----------


def test_sealed_with_different_manifest_fails_and_changes_nothing(world):
    shutil.copytree(world["pkg"], world["dest"])
    m = world["dest"] / "manifest.json"
    m.write_bytes(m.read_bytes() + b"\n")
    snapshot = {p.name: _sha(p) for p in world["dest"].iterdir()}
    r = _deliver(world, world["rid"])
    assert r.returncode != 0
    assert "[CD-3]" in r.stderr and "immutable" in r.stderr
    assert {p.name: _sha(p) for p in world["dest"].iterdir()} == snapshot
    assert _registry(world) == []
    assert not [c for c in _calls(world) if c.startswith("bundle")]


# ---------- inputs ----------


@pytest.mark.parametrize("args", [[], ["latest"], ["mdf-XYZ"], ["mdf-0123456789ab", "--bogus"]])
def test_release_id_required_and_validated(world, args):
    r = _deliver(world, *args)
    assert r.returncode != 0
    assert "[USAGE]" in r.stderr
    assert _calls(world) == []


def test_unknown_github_release_fails_at_cd1(world):
    r = _deliver(world, "mdf-000000000000")
    assert r.returncode != 0
    assert "[CD-1]" in r.stderr
    # only the read-only login check (preflight) may touch Databricks before CD-1
    assert [c for c in _calls(world) if not c.startswith("gh ")] == [PREFLIGHT_CALL]


def test_from_dir_skips_github(world):
    r = _deliver(world, world["rid"], "--from-dir", world["pkg"].as_posix(), "--no-activate")
    _assert_ok(r)
    assert not [c for c in _calls(world) if c.startswith("gh ")]
    rows = _registry(world)
    assert [x["event"] for x in rows] == ["REGISTERED"]
    assert rows[0]["github_release_url"] is None


def test_deploy_failure_stops_before_registry(world):
    world["env"]["FAKE_FAIL_ON"] = "deploy"
    r = _deliver(world, world["rid"])
    assert r.returncode != 0
    assert _registry(world) == []


# ---------- T-45 · FR-L.14 (ค): fail early with a concrete next step ----------


def test_auth_failure_stops_before_any_step_with_login_next_step(world):
    world["env"]["FAKE_FAIL_ON"] = "auth"
    world["env"]["DATABRICKS_CONFIG_PROFILE"] = "mdf-free"
    r = _deliver(world, world["rid"])
    assert r.returncode != 0
    assert "[PREFLIGHT]" in r.stderr
    assert "ขั้นต่อไป: databricks auth login" in r.stderr
    assert "--profile mdf-free" in r.stderr
    assert "python scripts/next_steps.py manual " + world["rid"] in r.stderr
    # nothing downloaded, nothing copied, nothing registered
    assert [c for c in _calls(world)] == [PREFLIGHT_CALL]
    assert _registry(world) == []


def test_auth_failure_in_ci_points_to_federation_or_u2m(world):
    world["env"]["FAKE_FAIL_ON"] = "auth"
    world["env"]["MDF_ACTOR"] = "github-oidc"
    r = _deliver(world, world["rid"])
    assert r.returncode != 0
    assert "DEP-3" in r.stderr and "delivery_mode: u2m" in r.stderr


def test_missing_databricks_cli_points_to_manual_mode(world, tmp_path):
    bindir = tmp_path / "bin_no_dbx"
    bindir.mkdir()
    shutil.copy2(tmp_path / "bin" / "gh", bindir / "gh")
    # keep only system tools + gh on PATH (no databricks)
    system = [
        d
        for d in world["env"]["PATH"].split(os.pathsep)[1:]
        if not shutil.which("databricks", path=d)
    ]
    world["env"]["PATH"] = os.pathsep.join([str(bindir), *system])
    r = _deliver(world, world["rid"])
    assert r.returncode != 0
    assert "ไม่พบคำสั่ง databricks" in r.stderr
    assert "mode manual" in r.stderr and "runbooks/release-delivery.md" in r.stderr
