import pytest

from mdf.loading import (
    DiscoveryError,
    DuplicateKeyError,
    discover_datasets,
    load_yaml,
)


def test_duplicate_key_detection_ac02():
    """AC-02: Duplicate YAML key is rejected and reports line number."""
    yaml_text = """apiVersion: v3.0.2
kind: DataContract
version: 1.0.0
id: cc.credit_card
version: 2.0.0
"""
    with pytest.raises(DuplicateKeyError) as exc_info:
        load_yaml(yaml_text)

    err = exc_info.value
    assert err.key == "version"
    assert err.line == 5
    assert "Duplicate key 'version' found at line 5" in str(err)


def test_duplicate_key_nested():
    yaml_text = """schema:
  name: test
  name: test_duplicate
"""
    with pytest.raises(DuplicateKeyError) as exc_info:
        load_yaml(yaml_text)

    assert exc_info.value.key == "name"
    assert exc_info.value.line == 3


def test_valid_yaml_loading():
    yaml_text = """apiVersion: v3.0.2
kind: DataContract
version: 1.0.0
status: active
"""
    data = load_yaml(yaml_text)
    assert data["apiVersion"] == "v3.0.2"
    assert data["version"] == "1.0.0"


def test_discover_datasets_success():
    """Verify discovery finds the 3 cc datasets and skips _template."""
    datasets = discover_datasets("DataContract")
    names = [(d.source, d.dataset) for d in datasets]
    assert ("cc", "credit_card") in names
    assert ("cc", "credit_card_txn") in names
    assert ("cc", "customer") in names
    assert len(datasets) == 3
    # Verify paths exist
    for d in datasets:
        assert d.contract_path.exists()
        assert d.pipeline_path.exists()


def test_discover_legacy_layout_error(tmp_path):
    """Verify legacy dq/ folder triggers LEGACY_LAYOUT."""
    dc = tmp_path / "DataContract"
    src = dc / "test_src"
    (src / "contract").mkdir(parents=True)
    (src / "dq").mkdir(parents=True)
    (src / "contract" / "my_ds.odcs.yaml").write_text("id: test", encoding="utf-8")
    (src / "dq" / "my_ds.dq.yaml").write_text("dq: test", encoding="utf-8")

    with pytest.raises(DiscoveryError) as exc_info:
        discover_datasets(dc)
    assert exc_info.value.code == "LEGACY_LAYOUT"


def test_discover_missing_pipeline_error(tmp_path):
    """Verify missing pipeline triggers FILE_LAYOUT."""
    dc = tmp_path / "DataContract"
    src = dc / "test_src"
    (src / "contract").mkdir(parents=True)
    (src / "pipeline").mkdir(parents=True)
    (src / "contract" / "my_ds.odcs.yaml").write_text("id: test", encoding="utf-8")

    with pytest.raises(DiscoveryError) as exc_info:
        discover_datasets(dc)
    assert exc_info.value.code == "FILE_LAYOUT"
