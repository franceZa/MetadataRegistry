import hashlib
import json

import pytest

from mdf.package import (
    ReleaseGateError,
    TamperError,
    build_package,
    check_release_gate,
    verify_package,
)


@pytest.fixture(scope="module")
def built_package():
    """Build a package once for this test module."""
    pkg_dir = build_package(env="dev")
    return pkg_dir


def test_build_package_creates_manifest(built_package):
    """Package contains manifest.json with sha256 for every file (AC-15)."""
    manifest_path = built_package / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["file_count"] == 6  # 3 datasets x 2 layers
    assert len(manifest["files"]) == 6
    for entry in manifest["files"]:
        assert len(entry["sha256"]) == 64
        assert (built_package / entry["path"]).exists()


def test_verify_intact_package_passes(built_package):
    """AC-15: a normal package verifies OK."""
    result = verify_package(built_package)
    assert result["status"] == "OK"
    assert result["verified_files"] == 6


def test_verify_detects_one_byte_tampering(built_package, tmp_path):
    """AC-15/AC-16: flipping 1 byte in a packaged file is detected (TAMPERED)."""
    import shutil

    tampered_dir = tmp_path / "tampered_pkg"
    shutil.copytree(built_package, tampered_dir)

    # Flip 1 byte in one resolved config
    target = tampered_dir / "silver.cc.credit_card_txn.resolved.json"
    data = bytearray(target.read_bytes())
    # find a byte in the middle to flip
    idx = len(data) // 2
    data[idx] = data[idx] ^ 0x01  # flip one bit = 1 byte changed
    target.write_bytes(bytes(data))

    with pytest.raises(TamperError) as exc_info:
        verify_package(tampered_dir)
    assert "TAMPERED" in str(exc_info.value)
    assert "silver.cc.credit_card_txn" in str(exc_info.value)


def test_verify_detects_missing_file(built_package, tmp_path):
    """A file removed from the package is detected."""
    import shutil

    broken_dir = tmp_path / "missing_pkg"
    shutil.copytree(built_package, broken_dir)
    (broken_dir / "bronze.cc.customer.resolved.json").unlink()

    with pytest.raises(TamperError) as exc_info:
        verify_package(broken_dir)
    assert "bronze.cc.customer" in str(exc_info.value)


def test_verify_detects_extra_file(built_package, tmp_path):
    """An unlisted extra file is detected."""
    import shutil

    extra_dir = tmp_path / "extra_pkg"
    shutil.copytree(built_package, extra_dir)
    (extra_dir / "sneaky_file.json").write_text("{}", encoding="utf-8")

    with pytest.raises(TamperError) as exc_info:
        verify_package(extra_dir)
    assert "sneaky_file" in str(exc_info.value)


def test_release_gate_dummy_rejected(tmp_path):
    """AC-16: dummy: true refuses release packaging."""
    # Build a fake env config with dummy: true
    cfg = tmp_path / "config"
    (cfg / "env").mkdir(parents=True)
    (cfg / "env" / "dummyenv.yaml").write_text(
        "env: dummyenv" + chr(10) + "catalog: dummy_catalog" + chr(10) + "dummy: true" + chr(10),
        encoding="utf-8",
    )
    with pytest.raises(ReleaseGateError) as exc_info:
        check_release_gate("dummyenv", cfg)
    assert "dummy" in str(exc_info.value)


def _write_manifest(pkg_dir, files_meta, manifest_version, extra=None):
    manifest = {
        "manifest_version": manifest_version,
        "release_id": "mdf-testrelease",
        "environment": "dev",
        "source_commit": "abc123",
        "compiler_revision": "0+test",
        "uv_lock_sha256": None,
        "ci_run_url": None,
        "file_count": len(files_meta),
        "files": files_meta,
        "validation_report_sha256": None,
        "preview": True,
    }
    if extra:
        manifest.update(extra)
    report_bytes = b"{}\n"
    (pkg_dir / "validation-report.json").write_bytes(report_bytes)
    manifest["validation_report_sha256"] = hashlib.sha256(report_bytes).hexdigest()
    (pkg_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _make_v1_flat_package(tmp_path):
    """T-49 AC-48: minimal manifest_version:1 flat package (bare filenames)."""
    pkg = tmp_path / "v1_pkg"
    pkg.mkdir()
    content = b'{"x": 1}\n'
    (pkg / "bronze.cc.customer.resolved.json").write_bytes(content)
    files_meta = [
        {"path": "bronze.cc.customer.resolved.json", "sha256": hashlib.sha256(content).hexdigest()}
    ]
    _write_manifest(pkg, files_meta, manifest_version=1)
    return pkg


def _make_v2_package(tmp_path, name="v2_pkg"):
    """T-49 AC-46/47/48: manifest_version:2 with <source>/<file> layout."""
    pkg = tmp_path / name
    pkg.mkdir()
    (pkg / "cc").mkdir()
    content = b'{"x": 2}\n'
    (pkg / "cc" / "bronze.cc.customer.resolved.json").write_bytes(content)
    files_meta = [
        {
            "path": "cc/bronze.cc.customer.resolved.json",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    ]
    _write_manifest(pkg, files_meta, manifest_version=2)
    return pkg


def test_verify_v1_flat_package_ok_with_legacy_warning(tmp_path):
    """AC-48 (And, รอบ 6): v1 passes with [WARN] legacy flat layout, no fail."""
    pkg = _make_v1_flat_package(tmp_path)
    result = verify_package(pkg)
    assert result["status"] == "OK"
    assert result["warnings"] == ["[WARN] legacy flat layout (manifest_version 1)"]


def test_verify_v2_package_ok_no_warning(tmp_path):
    """AC-48: v2 passes with no warnings."""
    pkg = _make_v2_package(tmp_path)
    result = verify_package(pkg)
    assert result["status"] == "OK"
    assert result["warnings"] == []


def test_verify_v2_rejects_dotdot_traversal(tmp_path):
    """AC-47: path with '..' segment -> TAMPERED before reading content."""
    pkg = _make_v2_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [{"path": "../evil.json", "sha256": "0" * 64}]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    assert "TAMPERED" in str(exc_info.value)


def test_verify_v2_rejects_backslash(tmp_path):
    """AC-47: backslash path -> TAMPERED."""
    pkg = _make_v2_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [{"path": "cc\\x.json", "sha256": "0" * 64}]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    assert "TAMPERED" in str(exc_info.value)


def test_verify_v2_rejects_absolute_path(tmp_path):
    """AC-47: absolute path -> TAMPERED."""
    pkg = _make_v2_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [{"path": "/etc/passwd", "sha256": "0" * 64}]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    assert "TAMPERED" in str(exc_info.value)


def test_verify_v2_rejects_too_deep_path(tmp_path):
    """SSOT FR-F.8 / AC-47 per HRM correction: path deeper than 2 segments -> TAMPERED
    (HRM corrected ticket AC-47 wording which contradicted SSOT)."""
    pkg = _make_v2_package(tmp_path)
    (pkg / "cc" / "sub").mkdir()
    (pkg / "cc" / "sub" / "x.json").write_bytes(b"{}")
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].append({"path": "cc/sub/x.json", "sha256": "0" * 64})
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    assert "TAMPERED" in str(exc_info.value)


def test_verify_v2_rejects_source_mismatch(tmp_path):
    """AC-47/FR-F.8(4): first segment must equal source parsed from filename."""
    pkg = _make_v2_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"] = [
        {"path": "xyz/bronze.cc.customer.resolved.json", "sha256": manifest["files"][0]["sha256"]}
    ]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    assert "TAMPERED" in str(exc_info.value)


def test_verify_v2_rejects_extra_file_in_subfolder(tmp_path):
    """AC-47 (And): extra file in subfolder not in manifest -> TAMPERED, recursive check."""
    pkg = _make_v2_package(tmp_path)
    (pkg / "cc" / "extra.json").write_text("{}", encoding="utf-8")
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    assert "TAMPERED" in str(exc_info.value)


def test_verify_v2_rejects_empty_extra_folder(tmp_path):
    """AC-47 (And): empty folder not in manifest -> TAMPERED."""
    pkg = _make_v2_package(tmp_path)
    (pkg / "xyz").mkdir()
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    assert "TAMPERED" in str(exc_info.value)


def test_verify_unknown_manifest_version(tmp_path):
    """AC-48: manifest_version 3 (unknown) -> TAMPERED unknown manifest_version."""
    pkg = _make_v2_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest_version"] = 3
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    assert "unknown manifest_version" in str(exc_info.value)
    assert "TAMPERED" in str(exc_info.value)


def test_release_gate_placeholder_secret_scope(tmp_path):
    """AC-16: secret_scope placeholder (<TODO...) refuses release."""
    cfg = tmp_path / "config"
    (cfg / "env").mkdir(parents=True)
    (cfg / "env" / "todoscope.yaml").write_text(
        "env: todoscope"
        + chr(10)
        + "catalog: c"
        + chr(10)
        + "dummy: false"
        + chr(10)
        + 'secret_scope: "<TODO:set-me>"'
        + chr(10),
        encoding="utf-8",
    )
    with pytest.raises(ReleaseGateError) as exc_info:
        check_release_gate("todoscope", cfg)
    assert "secret_scope" in str(exc_info.value)
