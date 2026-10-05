"""T-35 — manifest FR-F.2, release gate FR-F.4, preview FR-F.3, --expect-release-id FR-F.6.

Tests needing a clean/dirty tree build a throwaway git repo in tmp_path; the real
working tree is never modified.
"""

import json
import shutil
import subprocess  # nosec B404
from pathlib import Path

import pytest

from mdf.cli import main
from mdf.package import (
    REQUIRED_MANIFEST_KEYS,
    ReleaseGateError,
    ReleaseIdMismatchError,
    TamperError,
    build_package,
    verify_package,
)

ROOT = Path(__file__).resolve().parents[1]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture()
def clean_repo(tmp_path, monkeypatch):
    """Copy of the project inputs committed into a fresh git repo; cwd = repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "DataContract", repo / "DataContract")
    shutil.copytree(ROOT / "config", repo / "config")
    shutil.copy2(ROOT / "uv.lock", repo / "uv.lock")
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixture")
    monkeypatch.chdir(repo)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    return repo


def _manifest(pkg: Path) -> dict:
    return json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))


# ---------- AC-35 ----------


def test_ac35_release_manifest_has_fr_f2_fields(clean_repo):
    pkg = build_package(env="dev", release=True)
    m = _manifest(pkg)
    sha = _git(clean_repo, "rev-parse", "HEAD")
    for key in REQUIRED_MANIFEST_KEYS:
        assert key in m, key
    # T-48 · FR-F.7 layout `<source>/` (POSIX) kept · T-56 · FR-M.7: manifest_version 3,
    # every entry has kind/source/dataset (+layer for resolved_config), sorted by path
    assert m["manifest_version"] == 3
    assert m["files"] and all(f["path"].count("/") == 1 for f in m["files"])
    assert all(f["path"].split("/")[0] == f["source"] for f in m["files"])
    assert [f["path"] for f in m["files"]] == sorted(f["path"] for f in m["files"])
    assert m["release_id"] == f"mdf-{sha[:12]}"
    assert m["source_commit"] == sha and len(sha) == 40
    assert m["environment"] == "dev"
    assert m["preview"] is False
    assert m["ci_run_url"] is None  # local build
    assert len(m["uv_lock_sha256"]) == 64
    assert len(m["validation_report_sha256"]) == 64
    assert m["compiler_revision"].count("+src.") == 1
    assert m["file_count"] == len(m["files"]) == 9
    for f in m["files"]:
        if f["kind"] == "resolved_config":
            assert set(f) == {"path", "sha256", "kind", "source", "dataset", "layer"}
            assert f["path"].split("/")[1].split(".")[1] == f["source"]
        else:
            assert f["kind"] == "odcs_contract"
            assert set(f) == {"path", "sha256", "kind", "source", "dataset"}
            assert f["path"] == f"{f['source']}/{f['dataset']}.odcs.yaml"
    # manifest never lists / hashes itself
    assert "manifest.json" not in {f["path"] for f in m["files"]}


def test_ac35_expect_release_id_match_and_mismatch(clean_repo, capsys):
    build_package(env="dev", release=True)
    sha12 = _git(clean_repo, "rev-parse", "--short=12", "HEAD")
    assert main(["verify-package", "build/dev/release", "--expect-release-id", f"mdf-{sha12}"]) == 0
    capsys.readouterr()
    rc = main(["verify-package", "build/dev/release", "--expect-release-id", "mdf-000000000000"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "release_id ไม่ตรง" in out


def test_ac35_mismatch_raises_specific_error(clean_repo):
    pkg = build_package(env="dev", release=True)
    with pytest.raises(ReleaseIdMismatchError):
        verify_package(pkg, expect_release_id="mdf-ffffffffffff")


def test_manifest_deterministic_no_abs_path_or_timestamp(clean_repo):
    m1 = (build_package(env="dev", release=True) / "manifest.json").read_bytes()
    m2 = (build_package(env="dev", release=True) / "manifest.json").read_bytes()
    assert m1 == m2
    text = m1.decode("utf-8")
    assert str(clean_repo) not in text
    assert str(clean_repo).replace("\\", "/") not in text


def test_ci_run_url_from_github_env(clean_repo, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    m = _manifest(build_package(env="dev", release=True))
    assert m["ci_run_url"] == "https://github.com/org/repo/actions/runs/42"


# ---------- AC-16 (extended, FR-F.3 / FR-F.4) ----------


def test_ac16_release_refuses_dirty_tree(clean_repo):
    (clean_repo / "config" / "env" / "dev.yaml").write_text(
        (clean_repo / "config" / "env" / "dev.yaml").read_text(encoding="utf-8") + "# dirty\n",
        encoding="utf-8",
    )
    with pytest.raises(ReleaseGateError) as e:
        build_package(env="dev", release=True)
    assert "dirty" in str(e.value)


def test_ac16_release_refuses_untracked_file(clean_repo):
    (clean_repo / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ReleaseGateError):
        build_package(env="dev", release=True)


def test_ac16_release_refuses_non_active_contract(clean_repo):
    contract = next((clean_repo / "DataContract").glob("*/contract/*.odcs.yaml"))
    text = contract.read_text(encoding="utf-8")
    assert "status: active" in text
    contract.write_text(text.replace("status: active", "status: draft", 1), encoding="utf-8")
    _git(clean_repo, "commit", "-q", "-am", "draft contract")
    with pytest.raises(ReleaseGateError) as e:
        build_package(env="dev", release=True)
    assert "active" in str(e.value)


def test_ac16_release_refuses_non_git_dir(tmp_path, monkeypatch):
    work = tmp_path / "nogit"
    work.mkdir()
    shutil.copytree(ROOT / "DataContract", work / "DataContract")
    shutil.copytree(ROOT / "config", work / "config")
    monkeypatch.chdir(work)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    with pytest.raises(ReleaseGateError):
        build_package(env="dev", release=True)


def test_ac16_cli_release_dirty_exit_one(clean_repo, capsys):
    (clean_repo / "stray.txt").write_text("x", encoding="utf-8")
    assert main(["package", "--env", "dev", "--release"]) == 1
    assert "RELEASE_GATE" in capsys.readouterr().out


def test_ac16_non_release_dirty_gives_preview(clean_repo):
    (clean_repo / "stray.txt").write_text("x", encoding="utf-8")
    m = _manifest(build_package(env="dev"))
    assert m["preview"] is True


def test_fr_f3_non_release_is_preview_even_when_clean(clean_repo):
    assert _manifest(build_package(env="dev"))["preview"] is True


def test_fr_f3_non_release_on_ci_is_still_preview(clean_repo, monkeypatch):
    """CI preview artifact (ci.yml, no --release) must be marked preview (SSOT §5 row 3)."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert _manifest(build_package(env="dev"))["preview"] is True


# ---------- AC-15 regression on the new package layout ----------


def test_ac15_validation_report_tamper_detected(clean_repo):
    pkg = build_package(env="dev", release=True)
    report = pkg / "validation-report.json"
    report.write_bytes(report.read_bytes() + b" ")
    with pytest.raises(TamperError) as e:
        verify_package(pkg)
    assert "validation-report.json" in str(e.value)


def test_ac15_validation_report_missing_detected(clean_repo):
    pkg = build_package(env="dev", release=True)
    (pkg / "validation-report.json").unlink()
    with pytest.raises(TamperError):
        verify_package(pkg)


def test_fr_f5_manifest_missing_key_rejected(clean_repo):
    pkg = build_package(env="dev", release=True)
    m = _manifest(pkg)
    del m["release_id"]
    (pkg / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(TamperError) as e:
        verify_package(pkg)
    assert "release_id" in str(e.value)


def test_verify_needs_no_source_checkout(clean_repo, tmp_path, monkeypatch):
    pkg = build_package(env="dev", release=True)
    elsewhere = tmp_path / "elsewhere"
    shutil.copytree(pkg, elsewhere / "pkg")
    monkeypatch.chdir(elsewhere)
    assert verify_package("pkg")["status"] == "OK"


# ---------- AC-54 (release-gate warning portion · T-54) ----------


def test_ac54_release_gate_passes_with_calendar_pending_owner_warning(clean_repo, capsys):
    """cc contracts have no calendar fields yet -> gate still passes (warning, not error)."""
    pkg = build_package(env="dev", release=True)
    assert pkg.exists()
    out = capsys.readouterr().out
    assert "[WARN] calendar PENDING_OWNER: cc.credit_card, cc.credit_card_txn, cc.customer" in out


def test_ac54_cli_package_release_prints_pending_owner_warning(clean_repo, capsys):
    assert main(["package", "--env", "dev", "--release"]) == 0
    out = capsys.readouterr().out
    assert "[WARN] calendar PENDING_OWNER: cc.credit_card, cc.credit_card_txn, cc.customer" in out


def test_ac54_malformed_calendar_still_refuses_release_not_warning(clean_repo):
    """AC-54 (And): a present-but-malformed field is an error -> build must refuse, not warn.

    compile_project() validates first (FR-D.1) and raises before the release gate even
    writes anything — so the exception here is RuntimeError, not ReleaseGateError.
    """
    contract = next((clean_repo / "DataContract" / "cc" / "contract").glob("credit_card.odcs.yaml"))
    text = contract.read_text(encoding="utf-8")
    text = text.replace(
        "slaProperties:\n  - property: frequency\n    value: daily\n",
        "slaProperties:\n  - property: frequency\n    value: daily\n"
        '  - property: expected_at\n    value: "25:00"\n',
        1,
    )
    assert '  - property: expected_at\n    value: "25:00"\n' in text
    contract.write_text(text, encoding="utf-8")
    _git(clean_repo, "commit", "-q", "-am", "bad expected_at")
    with pytest.raises(RuntimeError) as e:
        build_package(env="dev", release=True)
    assert "CALENDAR_INVALID" in str(e.value)
