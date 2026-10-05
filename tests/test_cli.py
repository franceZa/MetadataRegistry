import pytest

from mdf.cli import main


def test_help_exit_zero(capsys):
    """--help exits 0 and lists every subcommand."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    for cmd in ("validate", "compile", "diff", "package", "verify-package", "trace"):
        assert cmd in out


def test_validate_real_repo_exit_zero(capsys):
    """validate on the real repo exits 0 with PASS message."""
    rc = main(["validate"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "PASS" in out or "ผ่านเรียบร้อย" in out


def test_compile_exit_zero_and_writes(capsys):
    """compile exits 0 and reports written files."""
    rc = main(["compile", "--env", "dev"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "6" in out  # 6 resolved files


def test_trace_exit_zero(capsys):
    """trace silver table exits 0 and shows lineage."""
    rc = main(["trace", "silver.cc.credit_card_txn", "--env", "dev"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "cc.credit_card_txn" in out
    assert "sha256" in out


def test_diff_baseline_exit_zero(capsys):
    """diff against 88b982d has no breaking changes -> exit 0."""
    rc = main(["diff", "--base", "88b982d"])
    assert rc == 0


def test_verify_package_ok(capsys):
    """verify-package on intact package exits 0."""
    # Build fresh package first (already done in test_package, rebuild here to be safe)
    from mdf.package import build_package

    pkg = build_package(env="dev")
    rc = main(["verify-package", str(pkg)])
    assert rc == 0


def test_verify_package_tampered_exit_one(tmp_path, capsys):
    """verify-package on tampered package exits 1."""
    import shutil

    from mdf.package import build_package

    pkg = build_package(env="dev")
    tampered = tmp_path / "tampered"
    shutil.copytree(pkg, tampered)
    target = tampered / "cc" / "silver.cc.credit_card_txn.resolved.json"
    data = bytearray(target.read_bytes())
    data[len(data) // 2] ^= 0x01
    target.write_bytes(bytes(data))

    rc = main(["verify-package", str(tampered)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "TAMPERED" in out


def test_package_prints_manifest_v3_summary(capsys):
    """T-56 · FR-M.7: `mdf package` reports manifest_version 3 + file_count 9 by kind."""
    rc = main(["package", "--env", "dev"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "manifest_version=3 file_count=9 odcs_contract=3 resolved_config=6" in out


def test_verify_package_tampered_contract_exit_one(tmp_path, capsys):
    """T-56 · AC-57 (1) via CLI: 1 byte changed in a bundled contract -> exit 1 TAMPERED."""
    import shutil

    from mdf.package import build_package

    pkg = build_package(env="dev")
    tampered = tmp_path / "tampered_contract"
    shutil.copytree(pkg, tampered)
    target = tampered / "cc" / "customer.odcs.yaml"
    data = bytearray(target.read_bytes())
    data[len(data) // 2] ^= 0x01
    target.write_bytes(bytes(data))
    capsys.readouterr()
    rc = main(["verify-package", str(tampered)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "[TAMPERED]" in out and "cc/customer.odcs.yaml" in out


def test_package_release_gate_exit_one(tmp_path, capsys):
    """package --release with dummy env is refused (exit 1)."""
    # Real dev config has dummy: false and a real secret_scope — the gate passes.
    # To test the refusal path we point --config-dir at a dummy config via direct call:
    from mdf.package import ReleaseGateError, check_release_gate

    cfg = tmp_path / "config"
    (cfg / "env").mkdir(parents=True)
    (cfg / "env" / "dummyenv.yaml").write_text(
        "env: dummyenv" + chr(10) + "catalog: c" + chr(10) + "dummy: true" + chr(10),
        encoding="utf-8",
    )
    with pytest.raises(ReleaseGateError):
        check_release_gate("dummyenv", cfg)
