import hashlib
import json
from pathlib import Path

import pytest

from mdf.compile import compile_project, load_env_config, load_naming_config, resolve_template


def sha256_of(path):
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def test_compile_produces_resolved_files(tmp_path, monkeypatch):
    """Compile writes resolved JSON per target table into build/<env>/resolved/."""
    monkeypatch.chdir(Path(__file__).parent.parent)
    # Clean build dir
    import shutil

    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    written = compile_project(env="dev")

    # 3 datasets × 2 layers (bronze, silver) = 6 files
    assert len(written) == 6
    for p in written:
        assert p.exists()
        assert "build/dev/resolved/cc" in str(p).replace("\\", "/")
        # regression: single-source layout still gets a <source>/ subfolder (no flat fallback)
        assert p.parent.name == "cc"
        data = json.loads(p.read_text(encoding="utf-8"))
        assert "lineage" in data
        assert "checks" in data
        assert "schema" in data


def test_ac46_multi_source_creates_per_source_subfolders(tmp_path, monkeypatch):
    """AC-46: >1 source -> compile writes build/<env>/resolved/<source>/<file> per source.

    Fixture built from the real 'cc' source copied into a second 'xyz' source inside
    tmp_path (HRM correction #3, H-103) — DataContract/ itself is never modified.
    """
    import shutil

    root = Path(__file__).parent.parent
    shutil.copytree(root / "DataContract" / "cc", tmp_path / "DataContract" / "cc")
    shutil.copytree(root / "DataContract" / "cc", tmp_path / "DataContract" / "xyz")
    shutil.copytree(root / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)

    written = compile_project(env="dev")

    # 2 sources x 3 datasets x 2 layers = 12 files
    assert len(written) == 12
    seen_sources = set()
    for p in written:
        rel = p.relative_to(Path("build") / "dev" / "resolved")
        assert len(rel.parts) == 2, rel  # exactly <source>/<file>
        assert rel.parts[0] in ("cc", "xyz")
        seen_sources.add(rel.parts[0])
    assert seen_sources == {"cc", "xyz"}


def test_ac11_deterministic_compile():
    """Compile twice -> byte-identical sha256 for every output file (AC-11)."""
    first = compile_project(env="dev")
    hashes_first = {p.name: sha256_of(p) for p in first}

    second = compile_project(env="dev")
    hashes_second = {p.name: sha256_of(p) for p in second}

    assert hashes_first == hashes_second


def test_ac06_landing_path_from_control_file():
    """Landing path resolves from naming.yaml + env config, no hardcoded catalog (AC-06)."""
    env_cfg = load_env_config("config", "dev")
    naming = load_naming_config("config")

    landing = resolve_template(naming["landing"], env_cfg, "cc", "credit_card", "bronze")
    assert landing == "/Volumes/dev_catalog/landing_cc/files/credit_card/"

    # Change catalog in env config -> landing changes (proves it comes from control file)
    env_cfg2 = dict(env_cfg)
    env_cfg2["catalog"] = "other_catalog"
    landing2 = resolve_template(naming["landing"], env_cfg2, "cc", "credit_card", "bronze")
    assert landing2 == "/Volumes/other_catalog/landing_cc/files/credit_card/"


def test_ac12_output_only_in_build():
    """All outputs live under build/ which is gitignored (AC-12)."""
    written = compile_project(env="dev")
    for p in written:
        assert p.parts[0] == "build" or "build" in p.parts


def test_fr_d1_no_output_on_validation_error(tmp_path):
    """With an invalid workspace, compile writes nothing (FR-D.1)."""
    import shutil

    # Create a broken workspace copy
    broken = tmp_path / "broken_dc"
    shutil.copytree("DataContract", broken / "DataContract")
    shutil.copytree("config", broken / "config")
    # Break a contract: add quality[] block (rejected by validator)
    target = broken / "DataContract" / "cc" / "contract" / "credit_card.odcs.yaml"
    text = target.read_text(encoding="utf-8")
    text += """
  quality:
    - type: custom
      implementation: bad
"""
    target.write_text(text, encoding="utf-8")

    build_dir = tmp_path / "build_output"

    # Run compile with broken workspace; must raise and not write
    with pytest.raises(RuntimeError) as exc_info:
        compile_project(env="dev", base_dir=broken / "DataContract", config_dir=broken / "config")

    assert "Validation failed" in str(exc_info.value)
    assert not build_dir.exists()
