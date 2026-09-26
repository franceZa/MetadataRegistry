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
        assert (built_package / entry["file"]).exists()


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
