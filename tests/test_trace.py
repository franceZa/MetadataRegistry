from mdf.trace import find_orphans, format_trace, load_dataset, trace_table


def test_load_dataset_silver():
    """load_dataset getter retrieves resolved config (FR-G)."""
    data = load_dataset(env="dev", source="cc", dataset="credit_card_txn", layer="silver")
    assert data["config_id"] == "silver.cc.credit_card_txn"
    assert data["source"] == "cc"
    assert data["dataset"] == "credit_card_txn"
    assert "lineage" in data


def test_trace_silver_ac18():
    """AC-18: trace silver.cc.credit_card_txn shows bronze input, contract id/version/sha256."""
    trace = trace_table("silver.cc.credit_card_txn", env="dev")
    assert trace["layer"] == "silver"
    assert trace["bronze_input"] is not None
    assert trace["bronze_input"]["table"] == "dev_catalog.bronze_cc.credit_card_txn"
    assert trace["contract_id"] == "cc.credit_card_txn"
    assert trace["contract_version"] == "1.0.0"
    assert len(trace["contract_sha256"]) == 64  # sha256 hex
    assert trace["pipeline_sha256"]
    assert trace["dq_library_sha256"]


def test_trace_all_bronze_tables():
    """Trace bronze for all 3 datasets succeeds."""
    for ds in ("credit_card", "credit_card_txn", "customer"):
        trace = trace_table(f"bronze.cc.{ds}", env="dev")
        assert trace["contract_id"] == f"cc.{ds}"
        assert trace["bronze_input"] is None  # bronze has no upstream table


def test_format_trace_readable():
    trace = trace_table("silver.cc.credit_card_txn", env="dev")
    text = format_trace(trace)
    assert "Lineage" in text
    assert "cc.credit_card_txn" in text
    assert "sha256" in text


def test_find_orphans_real_repo():
    """Real repo has no orphan contracts/pipelines."""
    report = find_orphans("DataContract")
    assert report.orphan_contracts == []
    assert report.orphan_pipelines == []


def test_find_orphans_detects_orphans(tmp_path):
    """Orphan contract (no pipeline) and orphan pipeline (no contract) are detected."""
    dc = tmp_path / "DataContract"
    # paired dataset
    (dc / "src_ok" / "contract").mkdir(parents=True)
    (dc / "src_ok" / "pipeline").mkdir(parents=True)
    (dc / "src_ok" / "contract" / "paired.odcs.yaml").write_text(
        "id: t" + chr(10), encoding="utf-8"
    )
    (dc / "src_ok" / "pipeline" / "paired.pipeline.yaml").write_text(
        "columns: {}" + chr(10), encoding="utf-8"
    )

    # orphan contract
    (dc / "src_a" / "contract").mkdir(parents=True)
    (dc / "src_a" / "contract" / "lonely.odcs.yaml").write_text("id: t" + chr(10), encoding="utf-8")

    # orphan pipeline
    (dc / "src_b" / "pipeline").mkdir(parents=True)
    (dc / "src_b" / "pipeline" / "lone.pipeline.yaml").write_text(
        "columns: {}" + chr(10), encoding="utf-8"
    )

    report = find_orphans(dc)
    assert any("src_a.lonely" in c for c in report.orphan_contracts)
    assert any("src_b.lone" in p for p in report.orphan_pipelines)
