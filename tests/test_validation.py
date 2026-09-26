import pytest
from pathlib import Path
from mdf.validation import validate_project, validate_contract_file, validate_pipeline_file, ValidationReport
from mdf.loading import load_yaml_file

def test_validate_real_project():
    """Verify that current repository passes full static validation."""
    report = validate_project()
    assert report.is_valid is True
    assert len(report.errors) == 0

def test_ac01_thai_report_format():
    report = ValidationReport()
    report.add_error(
        code="TEST_ERROR",
        message="เกิดข้อผิดพลาดในการทดสอบ",
        file_path="DataContract/test.yaml",
        field="test_field",
        fix="แก้ไขตามข้อกำหนด",
    )
    summary = report.format_thai_summary()
    assert "ตรวจพบข้อผิดพลาด 1 รายการ" in summary
    assert "รหัส: TEST_ERROR" in summary
    assert "ฟิลด์: test_field" in summary
    assert "วิธีแก้ไข: แก้ไขตามข้อกำหนด" in summary

def test_ac03_unknown_key_rejected_extensions_allowed(tmp_path):
    report = ValidationReport()
    bad_pipeline = tmp_path / "bad.pipeline.yaml"
    bad_pipeline.write_text("""dedupe: true
columns: {}
extensions:
  custom_info: "ok"
""", encoding="utf-8")

    from mdf.rules import load_rules_json
    rules = load_rules_json("config/rules/pipeline.rules.json")
    validate_pipeline_file(bad_pipeline, rules, contract_data=None, report=report)

    assert report.is_valid is False
    codes = [e.code for e in report.errors]
    assert "PL_ALLOWED_KEYS" in codes

def test_ac04_pipeline_column_not_in_contract(tmp_path):
    report = ValidationReport()
    p_file = tmp_path / "test.pipeline.yaml"
    p_file.write_text("""columns:
  non_existent_column:
    normalise: [strip_whitespace]
""", encoding="utf-8")

    contract_data = {
        "schema": [
            {
                "name": "ds",
                "properties": [{"name": "actual_col", "physicalType": "string"}],
            }
        ]
    }

    from mdf.rules import load_rules_json
    rules = load_rules_json("config/rules/pipeline.rules.json")
    validate_pipeline_file(p_file, rules, contract_data=contract_data, report=report)

    assert report.is_valid is False
    err = next(e for e in report.errors if e.code == "UNKNOWN_COLUMN_REF")
    assert "non_existent_column" in err.message

def test_ac05_use_tag_for_quality_block(tmp_path):
    report = ValidationReport()
    c_file = tmp_path / "bad.odcs.yaml"
    c_file.write_text("""apiVersion: v3.0.2
kind: DataContract
id: test.bad
name: bad
version: 1.0.0
status: active
domain: test
description:
  purpose: "Test dataset with quality block."
servers:
  - server: landing-dev
    environment: dev
    type: custom
    location: "/Volumes/{catalog}/landing_{source}/files/bad/"
schema:
  - name: bad
    physicalType: table
    properties:
      - name: id
        logicalType: string
        physicalType: string
        required: true
        description: "Primary key"
        quality:
          - type: custom
            implementation: foo
""", encoding="utf-8")

    import json, jsonschema
    from mdf.dq import DQLibrary
    from mdf.rules import load_rules_json

    with open("config/schemas/odcs_v3.0.2.json", "r", encoding="utf-8") as f:
        schema = json.load(f)
    validator = jsonschema.Draft202012Validator(schema)
    c_rules = load_rules_json("config/rules/contract.rules.json")
    dq_lib = DQLibrary.load("config/dq_library.yaml")

    validate_contract_file(c_file, validator, c_rules, dq_lib, report)
    assert report.is_valid is False
    assert any(e.code == "USE_TAG" for e in report.errors)
