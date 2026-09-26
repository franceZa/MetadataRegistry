import pytest
from mdf.dq import (
    DQLibrary,
    DQValidationError,
    resolve_column_dq_rules,
)
from mdf.rules import RuleConfigError

def test_load_official_dq_library():
    lib = DQLibrary.load("config/dq_library.yaml")
    assert "not_null" in lib.rules
    assert "pattern" in lib.rules
    assert "valid_values" in lib.rules
    assert "luhn" in lib.rules
    assert "fk" in lib.rules
    assert lib.rules["not_null"].kind == "sql"
    assert lib.rules["luhn"].kind == "function"

def test_resolve_auto_and_tags():
    lib = DQLibrary.load("config/dq_library.yaml")
    col_def = {
        "name": "card_pan",
        "required": True,
        "logicalTypeOptions": {"pattern": "^[0-9]{15,16}$"},
        "tags": ["dq:pattern", "dq:luhn"],
    }
    rules = resolve_column_dq_rules(col_def, lib)
    rule_names = [r.rule_name for r in rules]
    assert "not_null" in rule_names
    assert "pattern" in rule_names
    assert "luhn" in rule_names

    pattern_rule = next(r for r in rules if r.rule_name == "pattern")
    assert "card_pan IS NULL OR card_pan RLIKE ^[0-9]{15,16}$" in pattern_rule.sql
    assert pattern_rule.action == "reject"

def test_action_override_from_pipeline():
    lib = DQLibrary.load("config/dq_library.yaml")
    col_def = {
        "name": "national_id",
        "required": True,
        "logicalTypeOptions": {"pattern": "^[0-9]{13}$"},
        "tags": ["dq:pattern"],
    }
    actions = {"pattern@national_id": "flag"}
    rules = resolve_column_dq_rules(col_def, lib, pipeline_actions=actions)
    pattern_rule = next(r for r in rules if r.rule_name == "pattern")
    assert pattern_rule.action == "flag"

def test_error_unknown_tag():
    lib = DQLibrary.load("config/dq_library.yaml")
    col_def = {
        "name": "test_col",
        "tags": ["dq:non_existent_rule"],
    }
    with pytest.raises(DQValidationError) as exc:
        resolve_column_dq_rules(col_def, lib)
    assert exc.value.code == "UNKNOWN_TAG"

def test_error_tag_without_param():
    lib = DQLibrary.load("config/dq_library.yaml")
    col_def = {
        "name": "test_col",
        "tags": ["dq:pattern"],
        # logicalTypeOptions.pattern missing!
    }
    with pytest.raises(DQValidationError) as exc:
        resolve_column_dq_rules(col_def, lib)
    assert exc.value.code == "TAG_WITHOUT_PARAM"

def test_error_param_without_tag():
    lib = DQLibrary.load("config/dq_library.yaml")
    col_def = {
        "name": "test_col",
        "logicalTypeOptions": {"pattern": "^[0-9]+$"},
        "tags": [],  # missing dq:pattern
    }
    with pytest.raises(DQValidationError) as exc:
        resolve_column_dq_rules(col_def, lib)
    assert exc.value.code == "PARAM_WITHOUT_TAG"

def test_error_use_tag_when_quality_present():
    lib = DQLibrary.load("config/dq_library.yaml")
    col_def = {
        "name": "test_col",
        "quality": [{"type": "custom", "implementation": "foo"}],
    }
    with pytest.raises(DQValidationError) as exc:
        resolve_column_dq_rules(col_def, lib)
    assert exc.value.code == "USE_TAG"
