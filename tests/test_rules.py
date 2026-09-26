import json
import pytest
from mdf.rules import (
    Rule,
    RuleConfigError,
    evaluate_operator,
    evaluate_rules,
    load_rules_json,
    validate_rule_definition,
)

def test_validate_rule_definition_valid():
    rule_dict = {
        "id": "R001",
        "description": "Ensure dataset id is present",
        "scope": "file",
        "field": "id",
        "operator": "required",
        "message": "Dataset ID is missing",
        "severity": "error",
    }
    seen = set()
    rule = validate_rule_definition(rule_dict, seen)
    assert rule.id == "R001"
    assert rule.operator == "required"
    assert "R001" in seen

def test_validate_rule_definition_duplicate_id():
    rule_dict = {
        "id": "R001",
        "description": "Rule 1",
        "scope": "file",
        "field": "id",
        "operator": "required",
        "message": "Error 1",
    }
    seen = {"R001"}
    with pytest.raises(RuleConfigError) as exc_info:
        validate_rule_definition(rule_dict, seen)
    assert "Duplicate rule id 'R001'" in str(exc_info.value)

def test_validate_rule_definition_missing_desc():
    rule_dict = {
        "id": "R002",
        "description": "",
        "scope": "file",
        "field": "id",
        "operator": "required",
        "message": "Error",
    }
    with pytest.raises(RuleConfigError) as exc_info:
        validate_rule_definition(rule_dict, set())
    assert "description" in str(exc_info.value)

def test_validate_rule_definition_unknown_operator():
    rule_dict = {
        "id": "R003",
        "description": "Desc",
        "scope": "file",
        "field": "id",
        "operator": "magic_check",
        "message": "Error",
    }
    with pytest.raises(RuleConfigError) as exc_info:
        validate_rule_definition(rule_dict, set())
    assert "Unknown operator" in str(exc_info.value)

def test_load_rules_json(tmp_path):
    rules_file = tmp_path / "test.rules.json"
    rules_data = [
        {
            "id": "T01",
            "description": "Must have name",
            "scope": "file",
            "field": "name",
            "operator": "required",
            "message": "Name is required",
        }
    ]
    rules_file.write_text(json.dumps(rules_data), encoding="utf-8")
    loaded = load_rules_json(rules_file)
    assert len(loaded) == 1
    assert loaded[0].id == "T01"

def test_evaluate_operators():
    # required
    assert evaluate_operator("required", "value", None) is True
    assert evaluate_operator("required", "", None) is False
    assert evaluate_operator("required", None, None) is False

    # type
    assert evaluate_operator("type", "hello", "string") is True
    assert evaluate_operator("type", 123, "int") is True
    assert evaluate_operator("type", "123", "int") is False
    assert evaluate_operator("type", [1, 2], "list") is True

    # regex
    assert evaluate_operator("regex", "abc-123", "^[a-z]+-[0-9]+$") is True
    assert evaluate_operator("regex", "ABC", "^[0-9]+$") is False

    # in
    assert evaluate_operator("in", "active", ["active", "inactive"]) is True
    assert evaluate_operator("in", "deleted", ["active", "inactive"]) is False

    # allowed_keys with extensions bypass (FR-B.3)
    data = {"name": "test", "extensions": {"custom": 123}}
    assert evaluate_operator("allowed_keys", data, ["name"]) is True
    data_bad = {"name": "test", "unknown": 456}
    assert evaluate_operator("allowed_keys", data_bad, ["name"]) is False

def test_evaluate_rules_property_scope():
    rules = [
        Rule(
            id="PROP_DESC",
            description="Column description required",
            scope="property",
            field="description",
            operator="required",
            message="คอลัมน์ต้องมีคำอธิบาย (description)",
        )
    ]
    doc = {
        "schema": [
            {
                "name": "customer",
                "properties": [
                    {"name": "id", "description": "Customer ID"},
                    {"name": "bad_col", "description": ""},
                ],
            }
        ]
    }
    violations = evaluate_rules(rules, doc)
    assert len(violations) == 1
    assert violations[0].rule_id == "PROP_DESC"
    assert "bad_col" in violations[0].path
