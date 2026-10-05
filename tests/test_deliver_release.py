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


def _flatten_to_v1(v2_pkg: Path, dest_parent: Path) -> Path:
    """Flatten a real v2 package (`<source>/<file>` layout) into a genuine v1 fixture
    (bare filenames, manifest_version 1) — HRM correction #4 (H-103): GitHub Release
    assets cannot contain folders, so a pre-T-52 "legacy flat asset" release was always
    truly flat. Used wherever a test simulates that legacy download path.
    """
    v1 = dest_parent / "pkg_v1"
    shutil.copytree(v2_pkg, v1)
    manifest_path = v1 / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = entry["path"]
        if "/" in path:
            source, name = path.split("/", 1)
            shutil.move(str(v1 / source / name), str(v1 / name))
            entry["path"] = name
    manifest["manifest_version"] = 1
    for child in list(v1.iterdir()):
        if child.is_dir() and not any(child.iterdir()):
            child.rmdir()
    manifest_path.write_bytes(
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    return v1


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
    pkg_v1 = _flatten_to_v1(pkg, base)
    return {"pkg": pkg, "pkg_v1": pkg_v1, "rid": rid}


@pytest.fixture()
def world(tmp_path, release):
    """Fake workspace + fake GitHub Release + PATH with fake CLIs.

    gh_rel mirrors the flat v1 fixture: GitHub Release assets are individual files and
    cannot hold folders, so a legacy (no `.zip` asset) download must be genuinely flat.
    """
    root = tmp_path / "fake"
    (root / "Volumes").mkdir(parents=True)
    gh_rel = tmp_path / "gh_releases"
    shutil.copytree(release["pkg_v1"], gh_rel / release["rid"])
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
        "pkg_v1": release["pkg_v1"],
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
    # Volume = package, byte for byte (legacy flat download, no .zip asset -> v1 layout)
    assert sorted(p.name for p in world["dest"].iterdir()) == sorted(
        p.name for p in world["pkg_v1"].iterdir()
    )
    for f in world["pkg_v1"].iterdir():
        assert _sha(world["dest"] / f.name) == _sha(f)
    # registry: exactly REGISTERED + ACTIVATED with the CD-2 hash
    rows = _registry(world)
    assert [x["event"] for x in rows] == ["REGISTERED", "ACTIVATED"]
    sha = _sha(world["pkg_v1"] / "manifest.json")
    assert {x["manifest_sha256"] for x in rows} == {sha}
    assert rows[0]["github_release_url"] == f"https://github.com/{REPO}/releases/tag/{world['rid']}"
    assert rows[0]["actor"] == "manual"
    # manifest.json is the LAST upload
    ups = _uploads(world)
    assert len(ups) == len(list(world["pkg_v1"].iterdir()))
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
    shutil.copy2(world["pkg_v1"] / "silver.cc.customer.resolved.json", world["dest"])
    r = _deliver(world, world["rid"])
    _assert_ok(r)
    assert "partial folder" in r.stdout
    for f in world["pkg_v1"].iterdir():
        assert _sha(world["dest"] / f.name) == _sha(f), f.name
    assert [x["event"] for x in _registry(world)] == ["REGISTERED", "ACTIVATED"]


# ---------- sealed but different ----------


def test_sealed_with_different_manifest_fails_and_changes_nothing(world):
    shutil.copytree(world["pkg_v1"], world["dest"])
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


# ---------- T-50 · AC-49 · FR-L.4/L.4a/L.5 — CD-3/CD-4 recursive round-trip ----------


@pytest.fixture(scope="module")
def v2_pkg(release):
    """T-48 done: build_package now produces genuine v2 (`<source>/` subfolders) directly."""
    return release["pkg"]


def test_ac49_cd3_mkdir_per_source_and_cd4_roundtrip(world, v2_pkg):
    r = _deliver(world, world["rid"], "--from-dir", v2_pkg.as_posix(), "--no-activate")
    _assert_ok(r)
    sources = sorted(p.name for p in v2_pkg.iterdir() if p.is_dir())
    assert sources  # fixture actually produced at least one <source>/ subfolder
    for s in sources:
        assert (world["dest"] / s).is_dir()
        assert sorted(p.name for p in (world["dest"] / s).iterdir()) == sorted(
            p.name for p in (v2_pkg / s).iterdir()
        )
        for f in (v2_pkg / s).iterdir():
            assert _sha(world["dest"] / s / f.name) == _sha(f)
    for f in v2_pkg.iterdir():
        if f.is_file():
            assert _sha(world["dest"] / f.name) == _sha(f)
    calls = _calls(world)
    mkdirs = [c for c in calls if c.startswith("fs mkdir")]
    for s in sources:
        assert any(c.endswith(f"/{s}") for c in mkdirs), (s, mkdirs)
    # sealed rule unchanged: manifest.json copied last (ADR-004 §3)
    ups = _uploads(world)
    assert ups[-1].endswith("/manifest.json")
    assert not any(u.endswith("/manifest.json") for u in ups[:-1])
    # v2 -> no legacy-layout warning (OQ-P5-7)
    ev = (world["work"] / world["rid"] / "evidence.md").read_text(encoding="utf-8")
    assert "[WARN] legacy flat layout" not in ev


def test_ac49_resume_partial_subfolder_copy(world, v2_pkg):
    sources = sorted(p.name for p in v2_pkg.iterdir() if p.is_dir())
    first_dir = v2_pkg / sources[0]
    first_file = next(first_dir.iterdir())
    (world["dest"] / sources[0]).mkdir(parents=True)
    shutil.copy2(first_file, world["dest"] / sources[0] / first_file.name)
    r = _deliver(world, world["rid"], "--from-dir", v2_pkg.as_posix(), "--no-activate")
    _assert_ok(r)
    assert "partial folder" in r.stdout
    for f in v2_pkg.rglob("*"):
        if f.is_file():
            rel = f.relative_to(v2_pkg)
            assert _sha(world["dest"] / rel) == _sha(f), rel


def test_t56_v3_from_dir_cd3_copies_odcs_yaml_into_source_and_registers_9(world):
    """T-56 · FR-M.7 · AC-56: real v3 package (build_package) through --from-dir.

    CD-3 copies every manifest files[].path — including `cc/<dataset>.odcs.yaml` — into
    the Volume, CD-4 re-verifies the v3 round-trip, and the registry row (register.py via
    fake job) records file_count = 9. No change to deliver_release.sh / register.py.
    """
    pkg = world["pkg"]
    m = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert m["manifest_version"] == 3 and m["file_count"] == 9
    contracts = [e["path"] for e in m["files"] if e["kind"] == "odcs_contract"]
    assert contracts == [
        "cc/credit_card.odcs.yaml",
        "cc/credit_card_txn.odcs.yaml",
        "cc/customer.odcs.yaml",
    ]
    r = _deliver(world, world["rid"], "--from-dir", pkg.as_posix())
    _assert_ok(r)
    for e in m["files"]:
        assert _sha(world["dest"] / e["path"]) == e["sha256"], e["path"]
    assert sorted(p.name for p in (world["dest"] / "cc").iterdir()) == sorted(
        p.rsplit("/", 1)[1] for p in (e["path"] for e in m["files"])
    )
    ups = _uploads(world)
    for c in contracts:
        assert any(u.endswith(f"/{c}") for u in ups), c
    assert len(ups) == 9 + 2
    assert ups[-1].endswith("/manifest.json")
    ev = (world["work"] / world["rid"] / "evidence.md").read_text(encoding="utf-8")
    assert "[WARN]" not in ev
    assert "- CD-4:" in ev
    rows = _registry(world)
    assert [x["event"] for x in rows] == ["REGISTERED", "ACTIVATED"]
    assert {str(x["file_count"]) for x in rows} == {"9"}
    assert {x["manifest_sha256"] for x in rows} == {_sha(pkg / "manifest.json")}


def test_v1_regression_flat_layout_warns_and_still_copies(world):
    r = _deliver(world, world["rid"])
    _assert_ok(r)
    assert sorted(p.name for p in world["dest"].iterdir()) == sorted(
        p.name for p in world["pkg_v1"].iterdir()
    )
    ev = (world["work"] / world["rid"] / "evidence.md").read_text(encoding="utf-8")
    assert "[WARN] legacy flat layout" in ev


# ---------- T-52 · AC-51 · FR-L.3a: zip asset / zip-slip guard / v1 fallback ----------


def _add_zip_asset(world, entries: dict[str, bytes] | None = None) -> Path:
    """Build "<rid>.zip" inside $FAKE_GH_RELEASES/<rid>/ from the real v2 package (or `entries`).

    Default entries mirror the real v2 package files (with `<source>/` subfolders) at the
    zip root, per FR-L.1a — zip assets (unlike flat GitHub Release assets) can hold folders.
    Passing `entries` overrides the archive content entirely (used for zip-slip tests).
    """
    import zipfile

    gh_dir = world["gh_rel"] / world["rid"]
    zpath = gh_dir / f"{world['rid']}.zip"
    if entries is None:
        with zipfile.ZipFile(zpath, "w") as zf:
            for f in world["pkg"].rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(world["pkg"]).as_posix())
    else:
        with zipfile.ZipFile(zpath, "w") as zf:
            for name, data in entries.items():
                zf.writestr(name, data)
    return zpath


def test_cd1_zip_happy_path_downloads_and_extracts(world):
    """T-52/AC-51: when a "<id>.zip" asset exists, CD-1 downloads+extracts it via safe_unzip."""
    _add_zip_asset(world)
    r = _deliver(world, world["rid"])
    _assert_ok(r)
    for f in world["pkg"].rglob("*"):
        if f.is_file():
            rel = f.relative_to(world["pkg"])
            assert _sha(world["dest"] / rel) == _sha(f), rel
    calls = _calls(world)
    dl = [c for c in calls if c.startswith("gh release download")]
    assert any("-p" in c and f"{world['rid']}.zip" in c for c in dl)
    ev = (world["work"] / world["rid"] / "evidence.md").read_text(encoding="utf-8")
    assert f"downloaded {world['rid']}.zip" in ev
    assert "safe_unzip.py" in ev


def test_cd1_zip_slip_rejected_before_cd2_no_files_outside_work(world):
    """T-52/AC-51: a zip with '../../etc/passwd' fails CD-1, never touches the workspace."""
    _add_zip_asset(world, entries={"manifest.json": b"{}", "../../etc/passwd": b"pwned"})
    r = _deliver(world, world["rid"])
    assert r.returncode != 0
    assert "[CD-1]" in r.stderr
    assert "[ZIP_SLIP]" in r.stderr or "zip-slip" in r.stderr.lower()
    # nothing beyond the read-only preflight check and the gh calls touched Databricks
    assert [c for c in _calls(world) if not c.startswith("gh ")] == [PREFLIGHT_CALL]
    assert not world["dest"].exists()
    assert _registry(world) == []
    escaped = world["root"].parent / "etc" / "passwd"
    assert not escaped.exists()


def test_cd1_zip_slip_absolute_path_rejected(world):
    """T-52/AC-51: an absolute-path entry is rejected the same way as '..' traversal."""
    _add_zip_asset(world, entries={"manifest.json": b"{}", "/etc/passwd": b"pwned"})
    r = _deliver(world, world["rid"])
    assert r.returncode != 0
    assert "[CD-1]" in r.stderr
    assert not world["dest"].exists()
    assert _registry(world) == []


def test_v1_legacy_release_without_zip_asset_still_downloads_cd1(world):
    """T-52/AC-51 (v1 legacy): a release with only flat assets (no .zip) uses the old CD-1 path."""
    r = _deliver(world, world["rid"])
    _assert_ok(r)
    calls = _calls(world)
    dl = [c for c in calls if c.startswith("gh release download")]
    assert dl and not any("-p" in c for c in dl)
    ev = (world["work"] / world["rid"] / "evidence.md").read_text(encoding="utf-8")
    assert "legacy flat assets" in ev


# ---------- T-57 · AC-58 (fake) — v3 via zip asset: CD-3 count = manifest file_count + 2 ----------


def test_t57_v3_zip_cd3_copies_file_count_plus_2_including_odcs_yaml(world):
    """u2m/auto transport (zip asset, FR-L.1a): CD-3 uploads exactly file_count + 2 files
    (every manifest files[].path incl. `<source>/*.odcs.yaml`, + validation-report + manifest)
    and the evidence line says so — count taken from the manifest, not hardcoded."""
    m = json.loads((world["pkg"] / "manifest.json").read_text(encoding="utf-8"))
    assert m["manifest_version"] == 3
    n = m["file_count"]
    assert n == len(m["files"])
    yamls = [e["path"] for e in m["files"] if e["path"].endswith(".odcs.yaml")]
    assert yamls and all("/" in y for y in yamls)
    _add_zip_asset(world)
    r = _deliver(world, world["rid"])
    _assert_ok(r)
    ups = _uploads(world)
    assert len(ups) == n + 2
    assert ups[-1].endswith("/manifest.json")
    for y in yamls:
        assert any(u.endswith(f"/{world['rid']}/{y}") for u in ups), y
    on_volume = [p for p in world["dest"].rglob("*") if p.is_file()]
    assert len(on_volume) == n + 2
    ev = (world["work"] / world["rid"] / "evidence.md").read_text(encoding="utf-8")
    assert f"file_count {n}" in ev
    assert f"- CD-3: copied {n + 2} files · manifest.json last" in ev
    assert {str(x["file_count"]) for x in _registry(world)} == {str(n)}
