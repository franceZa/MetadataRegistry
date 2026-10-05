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
    """Package contains manifest.json with sha256 for every file (AC-15, AC-56)."""
    manifest_path = built_package / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # T-56 · FR-M.7: 3 datasets x (bronze + silver + odcs contract)
    assert manifest["file_count"] == 9
    assert len(manifest["files"]) == 9
    for entry in manifest["files"]:
        assert len(entry["sha256"]) == 64
        assert (built_package / entry["path"]).exists()


def test_verify_intact_package_passes(built_package):
    """AC-15: a normal package verifies OK."""
    result = verify_package(built_package)
    assert result["status"] == "OK"
    assert result["verified_files"] == 9


def test_verify_detects_one_byte_tampering(built_package, tmp_path):
    """AC-15/AC-16: flipping 1 byte in a packaged file is detected (TAMPERED)."""
    import shutil

    tampered_dir = tmp_path / "tampered_pkg"
    shutil.copytree(built_package, tampered_dir)

    # Flip 1 byte in one resolved config
    target = tampered_dir / "cc" / "silver.cc.credit_card_txn.resolved.json"
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
    (broken_dir / "cc" / "bronze.cc.customer.resolved.json").unlink()

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
    """AC-48 (annotated รอบ 12): v3 is now known (FR-M.8) -> manifest_version 4 is the
    "unknown" case -> TAMPERED unknown manifest_version."""
    pkg = _make_v2_package(tmp_path)
    manifest_path = pkg / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["manifest_version"] = 4
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


# ---------- T-56 · FR-M.7 / FR-M.8 · AC-56 / AC-57 / AC-48 (รอบ 12) — manifest v3 ----------


def _copy_pkg(built_package, tmp_path, name="v3_pkg"):
    import shutil

    dest = tmp_path / name
    shutil.copytree(built_package, dest)
    return dest


def _load_manifest(pkg):
    return json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))


def _save_manifest(pkg, manifest):
    (pkg / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _entry(manifest, path):
    return next(e for e in manifest["files"] if e["path"] == path)


def _assert_tampered(pkg, *needles):
    with pytest.raises(TamperError) as exc_info:
        verify_package(pkg)
    msg = str(exc_info.value)
    assert "[TAMPERED]" in msg
    for needle in needles:
        assert needle in msg, msg
    return msg


def test_ac56_v3_manifest_entries_kind_source_dataset_layer(built_package):
    """AC-56 / FR-M.7: v3, 9 entries sorted by path, each with path/sha256/kind/source/
    dataset (+layer only for resolved_config); contracts bundled under cc/."""
    m = _load_manifest(built_package)
    assert m["manifest_version"] == 3
    paths = [e["path"] for e in m["files"]]
    assert paths == sorted(paths)
    assert m["file_count"] == len(m["files"]) == 9
    contracts = [e for e in m["files"] if e["kind"] == "odcs_contract"]
    resolved = [e for e in m["files"] if e["kind"] == "resolved_config"]
    assert len(contracts) == 3 and len(resolved) == 6
    assert sorted(e["path"] for e in contracts) == [
        "cc/credit_card.odcs.yaml",
        "cc/credit_card_txn.odcs.yaml",
        "cc/customer.odcs.yaml",
    ]
    for e in contracts:
        assert set(e) == {"path", "sha256", "kind", "source", "dataset"}
        assert e["path"] == f"{e['source']}/{e['dataset']}.odcs.yaml"
    for e in resolved:
        assert set(e) == {"path", "sha256", "kind", "source", "dataset", "layer"}
        assert e["layer"] in ("bronze", "silver")
        assert e["path"] == f"{e['source']}/{e['layer']}.{e['source']}.{e['dataset']}.resolved.json"
    # manifest/report stay at the root and are never listed
    assert not {"manifest.json", "validation-report.json"} & set(paths)


def test_ac56_bundled_contract_matches_lineage_and_source_bytes(built_package):
    """AC-56 / AS-32: bundled bytes == the contract file compile used, sha256 ==
    lineage.contract_sha256 of bronze+silver, lineage.contract_bundle_path == its path."""
    from pathlib import Path

    m = _load_manifest(built_package)
    for c in (e for e in m["files"] if e["kind"] == "odcs_contract"):
        bundled = (built_package / c["path"]).read_bytes()
        assert hashlib.sha256(bundled).hexdigest() == c["sha256"]
        for layer in ("bronze", "silver"):
            rpath = f"{c['source']}/{layer}.{c['source']}.{c['dataset']}.resolved.json"
            lineage = json.loads((built_package / rpath).read_text(encoding="utf-8"))["lineage"]
            assert lineage["contract_sha256"] == c["sha256"]
            assert lineage["contract_bundle_path"] == c["path"]
            assert Path(lineage["contract_file"]).read_bytes() == bundled


def test_ac56_v3_verify_ok_without_warning(built_package):
    result = verify_package(built_package)
    assert result["status"] == "OK"
    assert result["verified_files"] == 9
    assert result["warnings"] == []


def test_ac57_case1_contract_one_byte_changed(built_package, tmp_path):
    """AC-57 (1): flip 1 byte in cc/customer.odcs.yaml -> TAMPERED."""
    pkg = _copy_pkg(built_package, tmp_path)
    f = pkg / "cc" / "customer.odcs.yaml"
    data = bytearray(f.read_bytes())
    data[len(data) // 2] ^= 0x01
    f.write_bytes(bytes(data))
    _assert_tampered(pkg, "cc/customer.odcs.yaml")


def test_ac57_case2_contract_and_entry_removed(built_package, tmp_path):
    """AC-57 (2): delete the contract AND its manifest entry (file_count kept consistent)
    -> TAMPERED because the dataset no longer has exactly 1 contract (FR-M.8 (3))."""
    pkg = _copy_pkg(built_package, tmp_path)
    (pkg / "cc" / "customer.odcs.yaml").unlink()
    m = _load_manifest(pkg)
    m["files"] = [e for e in m["files"] if e["path"] != "cc/customer.odcs.yaml"]
    m["file_count"] = len(m["files"])
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "cc.customer", "odcs_contract")


def test_ac57_case3_kind_other(built_package, tmp_path):
    """AC-57 (3): kind not in whitelist -> TAMPERED."""
    pkg = _copy_pkg(built_package, tmp_path)
    m = _load_manifest(pkg)
    _entry(m, "cc/customer.odcs.yaml")["kind"] = "other"
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "kind", "'other'")


def test_ac57_case4_dataset_field_does_not_match_filename(built_package, tmp_path):
    """AC-57 (4): entry.dataset differs from the dataset in the filename -> TAMPERED."""
    pkg = _copy_pkg(built_package, tmp_path)
    m = _load_manifest(pkg)
    _entry(m, "cc/customer.odcs.yaml")["dataset"] = "credit_card"
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "cc/customer.odcs.yaml", "cc/credit_card.odcs.yaml")


def test_ac57_case5_extra_contract_not_in_manifest(built_package, tmp_path):
    """AC-57 (5): cc/extra.odcs.yaml not listed in the manifest -> TAMPERED."""
    pkg = _copy_pkg(built_package, tmp_path)
    (pkg / "cc" / "extra.odcs.yaml").write_bytes(b"id: cc.extra\n")
    _assert_tampered(pkg, "cc/extra.odcs.yaml")


def test_ac57_case6_lineage_sha_edited_and_manifest_rehashed(built_package, tmp_path):
    """AC-57 (6): edit lineage.contract_sha256 in a resolved file and fix its manifest
    sha256 so the per-file hash check passes -> still TAMPERED (FR-M.8 (4))."""
    pkg = _copy_pkg(built_package, tmp_path)
    rel = "cc/silver.cc.customer.resolved.json"
    f = pkg / rel
    data = json.loads(f.read_text(encoding="utf-8"))
    data["lineage"]["contract_sha256"] = "0" * 64
    new_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
    f.write_bytes(new_bytes)
    m = _load_manifest(pkg)
    _entry(m, rel)["sha256"] = hashlib.sha256(new_bytes).hexdigest()
    _save_manifest(pkg, m)
    _assert_tampered(pkg, rel, "lineage.contract_sha256")


def test_ac57_case7_manifest_version_4_unknown(built_package, tmp_path):
    """AC-57 (7): manifest_version 4 -> TAMPERED unknown manifest_version."""
    pkg = _copy_pkg(built_package, tmp_path)
    m = _load_manifest(pkg)
    m["manifest_version"] = 4
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "unknown manifest_version")


def test_fr_m8_kind_is_read_from_manifest_not_extension(built_package, tmp_path):
    """FR-M.7/M.8: relabel the .yaml entry as resolved_config (+layer) -> TAMPERED because
    the path does not match the resolved_config filename pattern (kind never guessed)."""
    pkg = _copy_pkg(built_package, tmp_path)
    m = _load_manifest(pkg)
    e = _entry(m, "cc/customer.odcs.yaml")
    e["kind"] = "resolved_config"
    e["layer"] = "bronze"
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "cc/customer.odcs.yaml")


def test_fr_m8_missing_kind_rejected(built_package, tmp_path):
    pkg = _copy_pkg(built_package, tmp_path)
    m = _load_manifest(pkg)
    del _entry(m, "cc/bronze.cc.customer.resolved.json")["kind"]
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "kind")


def test_fr_m8_contract_bundle_path_mismatch(built_package, tmp_path):
    """FR-M.8 (4): lineage.contract_bundle_path must equal the bundled contract path."""
    pkg = _copy_pkg(built_package, tmp_path)
    rel = "cc/bronze.cc.credit_card.resolved.json"
    f = pkg / rel
    data = json.loads(f.read_text(encoding="utf-8"))
    data["lineage"]["contract_bundle_path"] = "cc/customer.odcs.yaml"
    new_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
    f.write_bytes(new_bytes)
    m = _load_manifest(pkg)
    _entry(m, rel)["sha256"] = hashlib.sha256(new_bytes).hexdigest()
    _save_manifest(pkg, m)
    _assert_tampered(pkg, rel, "contract_bundle_path")


def test_fr_m8_file_count_mismatch_rejected(built_package, tmp_path):
    pkg = _copy_pkg(built_package, tmp_path)
    m = _load_manifest(pkg)
    m["file_count"] = 6
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "file_count")


def test_fr_m8_missing_silver_layer_rejected(built_package, tmp_path):
    """FR-M.8 (3): every dataset needs exactly 1 contract + 1 bronze + 1 silver."""
    pkg = _copy_pkg(built_package, tmp_path)
    rel = "cc/silver.cc.credit_card_txn.resolved.json"
    (pkg / rel).unlink()
    m = _load_manifest(pkg)
    m["files"] = [e for e in m["files"] if e["path"] != rel]
    m["file_count"] = len(m["files"])
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "cc.credit_card_txn", "silver")


def test_fr_m8_v3_keeps_v2_traversal_rule(built_package, tmp_path):
    """FR-M.8: v2 rules still apply to v3 ('..' rejected before any file read)."""
    pkg = _copy_pkg(built_package, tmp_path)
    m = _load_manifest(pkg)
    _entry(m, "cc/customer.odcs.yaml")["path"] = "../customer.odcs.yaml"
    _save_manifest(pkg, m)
    _assert_tampered(pkg, "'..'")


def _downgrade_to_v2(v3_pkg, tmp_path):
    """Genuine v2 fixture from the real v3 package: drop bundled contracts and the v3-only
    entry fields, manifest_version 2 (the layout `<source>/` is the same)."""
    pkg = _copy_pkg(v3_pkg, tmp_path, name="v2_from_v3")
    m = _load_manifest(pkg)
    for e in m["files"]:
        if e["kind"] == "odcs_contract":
            (pkg / e["path"]).unlink()
    m["files"] = [
        {"path": e["path"], "sha256": e["sha256"]}
        for e in m["files"]
        if e["kind"] == "resolved_config"
    ]
    m["file_count"] = len(m["files"])
    m["manifest_version"] = 2
    _save_manifest(pkg, m)
    return pkg


def test_ac57_and_as33_real_v2_package_ok_no_warning(built_package, tmp_path):
    """AC-57 (And) / AS-33: a v2 package (6 resolved, no contracts) still verifies, no warning."""
    pkg = _downgrade_to_v2(built_package, tmp_path)
    result = verify_package(pkg)
    assert result["status"] == "OK"
    assert result["verified_files"] == 6
    assert result["warnings"] == []


def test_ac57_and_real_v1_flat_package_ok_with_legacy_warning(built_package, tmp_path):
    """AC-57 (And): a v1 flat package still verifies with [WARN] legacy flat layout."""
    import shutil

    v2 = _downgrade_to_v2(built_package, tmp_path)
    v1 = tmp_path / "v1_from_v2"
    shutil.copytree(v2, v1)
    m = _load_manifest(v1)
    for e in m["files"]:
        source, name = e["path"].split("/", 1)
        shutil.move(str(v1 / source / name), str(v1 / name))
        e["path"] = name
    for child in list(v1.iterdir()):
        if child.is_dir() and not any(child.iterdir()):
            child.rmdir()
    m["manifest_version"] = 1
    _save_manifest(v1, m)
    result = verify_package(v1)
    assert result["status"] == "OK"
    assert result["warnings"] == ["[WARN] legacy flat layout (manifest_version 1)"]


def test_ac11_package_twice_byte_identical(tmp_path):
    """AC-11: two `mdf package` runs on the same tree -> every file byte-identical."""
    import shutil

    first = tmp_path / "first"
    shutil.copytree(build_package(env="dev"), first)
    second = build_package(env="dev")

    def snapshot(root):
        return {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    assert snapshot(first) == snapshot(second)
    assert len(snapshot(first)) == 11  # 9 files[] + manifest.json + validation-report.json
