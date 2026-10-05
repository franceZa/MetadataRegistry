"""T-38 — release registration job logic (AC-40, AC-42, FR-L.7, FR-L.8) without Spark."""

import json
import shutil
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mdf.package import build_package
from mdf.register import (
    ACTIVATED,
    COLUMNS,
    REGISTERED,
    RegisterError,
    main,
    release_dir,
    run,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "dev_catalog"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


class FakeRegistry:
    def __init__(self):
        self.rows: list[dict] = []

    def rows_for(self, release_id):
        return [r for r in self.rows if r["release_id"] == release_id]

    def latest_activated(self):
        act = [r for r in self.rows if r["event"] == ACTIVATED]
        return max(act, key=lambda r: r["event_ts"])["release_id"] if act else None

    def append(self, row):
        self.rows.append(dict(row))


@pytest.fixture(scope="module")
def sealed(tmp_path_factory):
    """A real --release package from a throwaway clean git repo, placed in a fake Volume."""
    base = tmp_path_factory.mktemp("t38")
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
    import os

    cwd = os.getcwd()
    os.chdir(repo)
    try:
        pkg = build_package(env="dev", release=True)
    finally:
        os.chdir(cwd)
    manifest = json.loads((repo / pkg / "manifest.json").read_text(encoding="utf-8"))
    rid = manifest["release_id"]
    vol = base / "Volumes"
    shutil.copytree(repo / pkg, release_dir(vol, CATALOG, rid))
    return {"vol": vol, "rid": rid, "manifest": manifest}


def _run(reg, sealed, **kw):
    args = dict(
        release_id=sealed["rid"],
        mode="register",
        catalog=CATALOG,
        actor="manual",
        volume_root=sealed["vol"],
    )
    args.update(kw)
    return run(reg, **args)


# ---------- AC-42: explicit release_id only ----------


@pytest.mark.parametrize("rid", [None, ""])
def test_ac42_missing_release_id_fails_without_guessing(sealed, rid):
    reg = FakeRegistry()
    with pytest.raises(RegisterError, match="NO_RELEASE_ID"):
        _run(reg, sealed, release_id=rid)
    assert reg.rows == []


def test_ac42_unknown_release_id_fails_with_path(sealed):
    with pytest.raises(RegisterError, match="RELEASE_NOT_FOUND") as e:
        _run(FakeRegistry(), sealed, release_id="mdf-000000000000")
    assert "releases" in str(e.value) and "mdf-000000000000" in str(e.value)


def test_ac42_known_release_id_registers(sealed):
    reg = FakeRegistry()
    out = _run(reg, sealed)
    assert out.action == "appended" and out.event == REGISTERED
    assert len(reg.rows) == 1
    row = reg.rows[0]
    assert tuple(row) == COLUMNS
    assert row["release_id"] == sealed["rid"]
    assert row["source_commit"] == sealed["manifest"]["source_commit"]
    assert row["file_count"] == 9  # T-56 · FR-M.7: v3 = 6 resolved + 3 ODCS contracts
    assert len(row["manifest_sha256"]) == 64
    assert row["volume_path"].endswith(f"/dev_catalog/ops/files/releases/{sealed['rid']}")


@pytest.mark.parametrize("bad", ["latest", "mdf-XYZ", "mdf-0123456789ab/../x"])
def test_bad_release_id_format_rejected(sealed, bad):
    with pytest.raises(RegisterError, match="BAD_RELEASE_ID"):
        _run(FakeRegistry(), sealed, release_id=bad)


def test_bad_catalog_rejected(sealed):
    with pytest.raises(RegisterError, match="BAD_CATALOG"):
        _run(FakeRegistry(), sealed, catalog="dev_catalog; DROP")


# ---------- AC-40: idempotent + hash conflict ----------


def test_ac40_register_twice_is_one_row(sealed):
    reg = FakeRegistry()
    assert _run(reg, sealed).action == "appended"
    assert _run(reg, sealed).action == "skipped"
    assert [r["event"] for r in reg.rows] == [REGISTERED]


def test_ac40_registered_with_other_hash_fails(sealed):
    reg = FakeRegistry()
    _run(reg, sealed)
    reg.rows[0]["manifest_sha256"] = "0" * 64
    with pytest.raises(RegisterError, match="HASH_CONFLICT"):
        _run(reg, sealed)
    assert len(reg.rows) == 1


def test_tampered_volume_fails_verify(sealed, tmp_path):
    vol = tmp_path / "Volumes"
    shutil.copytree(sealed["vol"], vol)
    f = release_dir(vol, CATALOG, sealed["rid"]) / "cc" / "silver.cc.customer.resolved.json"
    data = bytearray(f.read_bytes())
    data[len(data) // 2] ^= 0x01
    f.write_bytes(bytes(data))
    reg = FakeRegistry()
    with pytest.raises(RegisterError, match="VERIFY_FAILED"):
        _run(reg, sealed, volume_root=vol)
    assert reg.rows == []


def test_unsealed_folder_without_manifest_fails(sealed, tmp_path):
    vol = tmp_path / "Volumes"
    shutil.copytree(sealed["vol"], vol)
    (release_dir(vol, CATALOG, sealed["rid"]) / "manifest.json").unlink()
    with pytest.raises(RegisterError, match="RELEASE_NOT_FOUND"):
        _run(FakeRegistry(), sealed, volume_root=vol)


# ---------- FR-L.8: activate ----------


def test_activate_requires_registered(sealed):
    reg = FakeRegistry()
    with pytest.raises(RegisterError, match="NOT_REGISTERED"):
        _run(reg, sealed, mode="activate")
    assert reg.rows == []


def test_activate_appends_once_then_skips(sealed):
    reg = FakeRegistry()
    _run(reg, sealed)
    t = datetime(2026, 9, 27, tzinfo=UTC)
    assert _run(reg, sealed, mode="activate", now=t).action == "appended"
    assert _run(reg, sealed, mode="activate").action == "skipped"
    assert [r["event"] for r in reg.rows] == [REGISTERED, ACTIVATED]
    assert reg.rows[1]["manifest_sha256"] == reg.rows[0]["manifest_sha256"]


def test_reactivate_after_other_release_appends_again(sealed):
    """Rollback config = activate an older release again (FR-J.5) -> new ACTIVATED row."""
    reg = FakeRegistry()
    _run(reg, sealed)
    _run(reg, sealed, mode="activate", now=datetime(2026, 9, 27, 1, tzinfo=UTC))
    reg.append(
        {
            "release_id": "mdf-bbbbbbbbbbbb",
            "event": ACTIVATED,
            "manifest_sha256": "x",
            "event_ts": datetime(2026, 9, 27, 2, tzinfo=UTC),
        }
    )
    out = _run(reg, sealed, mode="activate", now=datetime(2026, 9, 27, 3, tzinfo=UTC))
    assert out.action == "appended"


# ---------- CLI ----------


def test_cli_without_release_id_exit_one(sealed, capsys):
    rc = main(["--volume-root", str(sealed["vol"])], registry=FakeRegistry())
    assert rc == 1
    assert "NO_RELEASE_ID" in capsys.readouterr().out


def test_cli_register_exit_zero(sealed, capsys):
    reg = FakeRegistry()
    rc = main(
        [
            "--release-id",
            sealed["rid"],
            "--volume-root",
            str(sealed["vol"]),
            "--github-release-url",
            "https://example.invalid/r",
        ],
        registry=reg,
    )
    assert rc == 0
    assert "REGISTERED appended" in capsys.readouterr().out
    assert reg.rows[0]["github_release_url"] == "https://example.invalid/r"
