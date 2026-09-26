import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple


class RuleConfigError(Exception):
    """Raised when a rule configuration file fails self-checking (FR-C.6)."""

    def __init__(self, message: str, rule_id: Optional[str] = None, file_path: Optional[str] = None):
        self.rule_id = rule_id
        self.file_path = file_path
        prefix = f"[RuleConfigError] "
        if rule_id:
            prefix += f"Rule '{rule_id}': "
        if file_path:
            prefix += f"(in {file_path}) "
        super().__init__(prefix + message)


@dataclass
class RuleViolation:
    rule_id: str
    field: str
    message: str
    severity: str = "error"  # "error" | "warning"
    fix: Optional[str] = None
    path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
            "fix": self.fix,
            "path": self.path,
        }


@dataclass
class Rule:
    id: str
    description: str
    scope: str
    field: str
    operator: str
    severity: str = "error"
    message: str = ""
    value: Any = None
    when: Optional[Dict[str, Any]] = None
    fix: Optional[str] = None
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            scope=data.get("scope", "file"),
            field=data.get("field", ""),
            operator=data["operator"],
            severity=data.get("severity", "error"),
            message=data.get("message", ""),
            value=data.get("value"),
            when=data.get("when"),
            fix=data.get("fix"),
            enabled=data.get("enabled", True),
        )


ALLOWED_SCOPES = {
    "file",
    "dataset",
    "schema",
    "properties",
    "property",
    "rules",
    "columns",
    "servers",
    "derived",
}

ALLOWED_OPERATORS = {
    "required",
    "type",
    "regex",
    "in",
    "allowed_keys",
    "unique",
    "ref_exists",
    "column_in_contract",
    "min_length",
    "not_null",
}


def validate_rule_definition(rule_dict: Dict[str, Any], seen_ids: Set[str], file_path: Optional[str] = None) -> Rule:
    """Validate a single rule definition for self-consistency (FR-C.6)."""
    if not isinstance(rule_dict, dict):
        raise RuleConfigError("Rule item must be a dictionary", file_path=file_path)

    rule_id = rule_dict.get("id")
    if not rule_id or not isinstance(rule_id, str):
        raise RuleConfigError("Rule 'id' must be a non-empty string", file_path=file_path)

    if rule_id in seen_ids:
        raise RuleConfigError(f"Duplicate rule id '{rule_id}'", rule_id=rule_id, file_path=file_path)
    seen_ids.add(rule_id)

    desc = rule_dict.get("description")
    if not desc or not isinstance(desc, str) or not desc.strip():
        raise RuleConfigError("Rule 'description' is required and cannot be empty", rule_id=rule_id, file_path=file_path)

    scope = rule_dict.get("scope")
    if scope not in ALLOWED_SCOPES:
        raise RuleConfigError(f"Unknown scope '{scope}'. Allowed: {sorted(ALLOWED_SCOPES)}", rule_id=rule_id, file_path=file_path)

    operator = rule_dict.get("operator")
    if operator not in ALLOWED_OPERATORS:
        raise RuleConfigError(f"Unknown operator '{operator}'. Allowed: {sorted(ALLOWED_OPERATORS)}", rule_id=rule_id, file_path=file_path)

    field = rule_dict.get("field")
    if field is None:
        raise RuleConfigError("Rule 'field' must be specified", rule_id=rule_id, file_path=file_path)

    msg = rule_dict.get("message")
    if not msg or not isinstance(msg, str) or not msg.strip():
        raise RuleConfigError("Rule 'message' is required and cannot be empty", rule_id=rule_id, file_path=file_path)

    severity = rule_dict.get("severity", "error")
    if severity not in ("error", "warning"):
        raise RuleConfigError(f"Invalid severity '{severity}'. Must be 'error' or 'warning'", rule_id=rule_id, file_path=file_path)

    return Rule.from_dict(rule_dict)


def load_rules_json(filepath: Union[Path, str]) -> List[Rule]:
    """Load and self-check a rules JSON file according to FR-C.5 and FR-C.6."""
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"Rules file not found: {p}")

    try:
        with p.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise RuleConfigError(f"Malformed JSON in rules file: {e}", file_path=str(p))

    if not isinstance(raw, list):
        if isinstance(raw, dict) and "rules" in raw and isinstance(raw["rules"], list):
            raw = raw["rules"]
        else:
            raise RuleConfigError("Rules JSON must contain a list of rules (or {'rules': [...]})", file_path=str(p))

    seen_ids: Set[str] = set()
    rules: List[Rule] = []
    for item in raw:
        rule = validate_rule_definition(item, seen_ids, file_path=str(p))
        rules.append(rule)

    return rules


def _get_nested_field(data: Any, field_path: str) -> Tuple[bool, Any]:
    """Resolve a dot-separated field path in a dictionary. Returns (exists, value)."""
    if not field_path:
        return True, data

    parts = field_path.split(".")
    curr = data
    for part in parts:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        elif isinstance(curr, list):
            # check if part is an index or wildcard
            if part.isdigit():
                idx = int(part)
                if 0 <= idx < len(curr):
                    curr = curr[idx]
                else:
                    return False, None
            else:
                return False, None
        else:
            return False, None
    return True, curr


def evaluate_operator(operator: str, value: Any, param: Any, context: Optional[Dict[str, Any]] = None) -> bool:
    """Evaluate a single operator. Returns True if passed, False if violated."""
    if operator == "required" or operator == "not_null":
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        return True

    if value is None:
        # If not required, None values pass other operators
        return True

    if operator == "type":
        type_str = str(param).lower()
        if type_str in ("string", "str"):
            return isinstance(value, str)
        elif type_str in ("int", "integer"):
            return isinstance(value, int) and not isinstance(value, bool)
        elif type_str in ("number", "float"):
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        elif type_str in ("bool", "boolean"):
            return isinstance(value, bool)
        elif type_str in ("list", "array"):
            return isinstance(value, list)
        elif type_str in ("dict", "object", "mapping"):
            return isinstance(value, dict)
        return False

    if operator == "regex":
        return bool(re.search(str(param), str(value)))

    if operator == "in":
        if isinstance(param, list):
            return value in param
        return False

    if operator == "min_length":
        min_len = int(param)
        return len(str(value)) >= min_len

    if operator == "allowed_keys":
        if not isinstance(value, dict):
            return True
        allowed = set(param)
        allowed.add("extensions")  # Always permit extensions per FR-B.3
        actual_keys = set(value.keys())
        return actual_keys.issubset(allowed)

    if operator == "unique":
        if not isinstance(value, list):
            return True
        return len(value) == len(set(value))

    if operator == "column_in_contract":
        # Check context for contract column names
        if context and "contract_columns" in context:
            return value in context["contract_columns"]
        return True

    if operator == "ref_exists":
        if context and "references" in context:
            return value in context["references"]
        return True

    return True


def evaluate_rule_on_item(rule: Rule, item: Any, item_path: str = "", context: Optional[Dict[str, Any]] = None) -> List[RuleViolation]:
    """Evaluate a rule against a single target dictionary or item."""
    if not rule.enabled:
        return []

    # Check 'when' condition if present
    if rule.when:
        when_field = rule.when.get("field")
        when_op = rule.when.get("operator", "==")
        when_val = rule.when.get("value")
        exists, actual_when_val = _get_nested_field(item, when_field)
        if not exists:
            return []
        if when_op == "==" and actual_when_val != when_val:
            return []
        if when_op == "!=" and actual_when_val == when_val:
            return []
        if when_op == "truthy" and not actual_when_val:
            return []

    exists, target_val = _get_nested_field(item, rule.field)

    passed = evaluate_operator(rule.operator, target_val if exists else None, rule.value, context=context)

    if not passed:
        loc = item_path
        if rule.field:
            loc = f"{loc}.{rule.field}" if loc else rule.field
        return [
            RuleViolation(
                rule_id=rule.id,
                field=rule.field,
                message=rule.message,
                severity=rule.severity,
                fix=rule.fix,
                path=loc,
            )
        ]
    return []


def evaluate_rules(
    rules: List[Rule],
    document: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> List[RuleViolation]:
    """Evaluate a list of rules across a target document structure according to rule scopes."""
    violations: List[RuleViolation] = []

    for rule in rules:
        if not rule.enabled:
            continue

        if rule.scope in ("file", "dataset"):
            violations.extend(evaluate_rule_on_item(rule, document, item_path="", context=context))

        elif rule.scope == "schema":
            schemas = document.get("schema", [])
            if isinstance(schemas, list):
                for i, s in enumerate(schemas):
                    violations.extend(evaluate_rule_on_item(rule, s, item_path=f"schema[{i}]", context=context))

        elif rule.scope == "properties":
            schemas = document.get("schema", [])
            if isinstance(schemas, list):
                for i, s in enumerate(schemas):
                    props = s.get("properties", []) if isinstance(s, dict) else []
                    if isinstance(props, list):
                        violations.extend(evaluate_rule_on_item(rule, props, item_path=f"schema[{i}].properties", context=context))

        elif rule.scope == "property":
            schemas = document.get("schema", [])
            if isinstance(schemas, list):
                for i, s in enumerate(schemas):
                    props = s.get("properties", []) if isinstance(s, dict) else []
                    if isinstance(props, list):
                        for j, p in enumerate(props):
                            col_name = p.get("name", str(j)) if isinstance(p, dict) else str(j)
                            violations.extend(evaluate_rule_on_item(rule, p, item_path=f"schema[{i}].properties[{col_name}]", context=context))

        elif rule.scope == "columns":
            cols = document.get("columns", {})
            if isinstance(cols, dict):
                for col_name, col_cfg in cols.items():
                    if isinstance(col_cfg, dict):
                        violations.extend(evaluate_rule_on_item(rule, col_cfg, item_path=f"columns.{col_name}", context=context))

        elif rule.scope == "rules":
            rules_list = document.get("rules", [])
            if isinstance(rules_list, list):
                for i, r in enumerate(rules_list):
                    r_id = r.get("id", str(i)) if isinstance(r, dict) else str(i)
                    violations.extend(evaluate_rule_on_item(rule, r, item_path=f"rules[{r_id}]", context=context))

        elif rule.scope == "servers":
            servers = document.get("servers", [])
            if isinstance(servers, list):
                for i, s in enumerate(servers):
                    violations.extend(evaluate_rule_on_item(rule, s, item_path=f"servers[{i}]", context=context))

    return violations
