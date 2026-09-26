import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from mdf.loading import load_yaml_file
from mdf.rules import RuleConfigError


class DQValidationError(Exception):
    """Raised when DQ tag or contract configuration violates DQ model rules."""

    def __init__(self, code: str, message: str, column: Optional[str] = None):
        self.code = code
        self.message = message
        self.column = column
        col_str = f" for column '{column}'" if column else ""
        super().__init__(f"[{code}]{col_str}: {message}")


@dataclass
class DQLibraryRule:
    name: str
    description: str
    kind: str  # "sql" | "function"
    sql: Optional[str] = None
    function: Optional[str] = None
    params: Dict[str, str] = field(default_factory=dict)
    default_action: str = "reject"  # "reject" | "flag" | "block"
    auto: Optional[str] = None
    enabled: bool = True


class DQLibrary:
    """Manages DQ Rule Library loaded from config/dq_library.yaml."""

    def __init__(self, rules: Dict[str, DQLibraryRule], version: int = 1):
        self.version = version
        self.rules = rules

    @classmethod
    def load(cls, filepath: Union[Path, str] = "config/dq_library.yaml") -> "DQLibrary":
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"DQ library file not found: {p}")

        data = load_yaml_file(p)
        if not isinstance(data, dict):
            raise RuleConfigError("DQ library root must be a mapping", file_path=str(p))

        version = data.get("library_version", 1)
        raw_rules = data.get("rules", {})
        if not isinstance(raw_rules, dict):
            raise RuleConfigError("DQ library 'rules' must be a dictionary of rules", file_path=str(p))

        rules: Dict[str, DQLibraryRule] = {}
        for r_name, r_cfg in raw_rules.items():
            rule = cls._validate_rule(r_name, r_cfg, str(p))
            rules[r_name] = rule

        return cls(rules=rules, version=version)

    @staticmethod
    def _validate_rule(name: str, cfg: Dict[str, Any], filepath: str) -> DQLibraryRule:
        """Self-check rule definition per FR-C.6."""
        if not isinstance(cfg, dict):
            raise RuleConfigError(f"Rule definition for '{name}' must be a mapping", rule_id=name, file_path=filepath)

        desc = cfg.get("description")
        if not desc or not isinstance(desc, str) or not desc.strip():
            raise RuleConfigError("Rule description is required and cannot be empty", rule_id=name, file_path=filepath)

        kind = cfg.get("kind")
        if kind not in ("sql", "function"):
            raise RuleConfigError(f"Invalid kind '{kind}'. Must be 'sql' or 'function'", rule_id=name, file_path=filepath)

        sql_expr = cfg.get("sql")
        func_name = cfg.get("function")

        params = cfg.get("params", {})
        if not isinstance(params, dict):
            raise RuleConfigError("Rule 'params' must be a mapping of param name to contract property", rule_id=name, file_path=filepath)

        if kind == "sql":
            if not sql_expr or not isinstance(sql_expr, str):
                raise RuleConfigError("Rule with kind 'sql' requires a non-empty 'sql' string", rule_id=name, file_path=filepath)
            # Check placeholders in sql
            placeholders = set(re.findall(r"\{([a-zA-Z0-9_]+)\}", sql_expr))
            if "col" not in placeholders:
                raise RuleConfigError("SQL expression must contain '{col}' placeholder", rule_id=name, file_path=filepath)
            for ph in placeholders - {"col"}:
                if ph not in params:
                    raise RuleConfigError(f"SQL placeholder '{{{ph}}}' not declared in 'params'", rule_id=name, file_path=filepath)

        elif kind == "function":
            if not func_name or not isinstance(func_name, str):
                raise RuleConfigError("Rule with kind 'function' requires a 'function' name", rule_id=name, file_path=filepath)

        action = cfg.get("default_action", "reject")
        if action not in ("reject", "flag", "block"):
            raise RuleConfigError(f"Invalid default_action '{action}'. Must be reject, flag, or block", rule_id=name, file_path=filepath)

        return DQLibraryRule(
            name=name,
            description=desc,
            kind=kind,
            sql=sql_expr,
            function=func_name,
            params=params,
            default_action=action,
            auto=cfg.get("auto"),
            enabled=cfg.get("enabled", True),
        )


@dataclass
class DQResolvedRule:
    rule_name: str
    column: str
    kind: str
    description: str
    action: str
    stage: str = "pre_tokenise"
    sql: Optional[str] = None
    function: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


def _get_custom_property(col_def: Dict[str, Any], prop_name: str) -> Any:
    for cp in col_def.get("customProperties", []):
        if isinstance(cp, dict) and cp.get("property") == prop_name:
            return cp.get("value")
    return None


def resolve_column_dq_rules(
    col_def: Dict[str, Any],
    dq_library: DQLibrary,
    pipeline_actions: Optional[Dict[str, str]] = None,
) -> List[DQResolvedRule]:
    """
    Resolve and validate DQ rules for a given contract column definition.
    Enforces DQ-1..DQ-4 and raises DQValidationError for violations.
    """
    col_name = col_def.get("name", "unknown")

    # DQ-3: Contract cannot have quality[]
    if "quality" in col_def and col_def["quality"]:
        raise DQValidationError(
            code="USE_TAG",
            message="Contract cannot contain 'quality[]' blocks. Use 'tags: [dq:<rule>]' instead.",
            column=col_name,
        )

    resolved: List[DQResolvedRule] = []
    actions = pipeline_actions or {}

    # Extract tags
    raw_tags = col_def.get("tags", [])
    dq_tags: List[str] = []
    if isinstance(raw_tags, list):
        for t in raw_tags:
            if isinstance(t, str) and t.startswith("dq:"):
                dq_tags.append(t[3:])

    # DQ-1: Auto rules (required: true -> not_null)
    auto_not_null = col_def.get("required") is True
    if auto_not_null and "not_null" in dq_library.rules:
        r_def = dq_library.rules["not_null"]
        if r_def.enabled:
            action = actions.get(f"not_null@{col_name}", r_def.default_action)
            resolved.append(
                DQResolvedRule(
                    rule_name="not_null",
                    column=col_name,
                    kind=r_def.kind,
                    description=r_def.description,
                    action=action,
                    sql=r_def.sql.format(col=col_name) if r_def.sql else None,
                    function=r_def.function,
                    params={},
                )
            )

    # Check DQ-2 reverse: pattern exists but tag missing
    pattern_val = col_def.get("logicalTypeOptions", {}).get("pattern")
    if pattern_val and "pattern" not in dq_tags:
        raise DQValidationError(
            code="PARAM_WITHOUT_TAG",
            message="Column defines 'logicalTypeOptions.pattern' but missing 'dq:pattern' tag.",
            column=col_name,
        )

    # Process explicit dq tags
    for tag_name in dq_tags:
        if tag_name not in dq_library.rules:
            raise DQValidationError(
                code="UNKNOWN_TAG",
                message=f"Tag 'dq:{tag_name}' is not defined in config/dq_library.yaml.",
                column=col_name,
            )

        r_def = dq_library.rules[tag_name]
        if not r_def.enabled:
            continue

        resolved_params: Dict[str, Any] = {}
        for p_name, p_target in r_def.params.items():
            val = None
            if p_target == "logicalTypeOptions.pattern":
                val = col_def.get("logicalTypeOptions", {}).get("pattern")
            elif p_target.startswith("customProperties."):
                prop_key = p_target[len("customProperties.") :]
                val = _get_custom_property(col_def, prop_key)

            if val is None:
                raise DQValidationError(
                    code="TAG_WITHOUT_PARAM",
                    message=f"Tag 'dq:{tag_name}' requires parameter '{p_name}' ({p_target}), but value is missing in contract.",
                    column=col_name,
                )
            resolved_params[p_name] = val

        action_override_key = f"{tag_name}@{col_name}"
        action = actions.get(action_override_key, r_def.default_action)

        sql_rendered = None
        if r_def.kind == "sql" and r_def.sql:
            fmt_dict = {"col": col_name}
            fmt_dict.update(resolved_params)
            # handle valid_values formatting if list
            if "valid_values" in fmt_dict and isinstance(fmt_dict["valid_values"], list):
                quoted_vals = [f"'{v}'" if isinstance(v, str) else str(v) for v in fmt_dict["valid_values"]]
                fmt_dict["valid_values"] = ", ".join(quoted_vals)
            sql_rendered = r_def.sql.format(**fmt_dict)

        resolved.append(
            DQResolvedRule(
                rule_name=tag_name,
                column=col_name,
                kind=r_def.kind,
                description=r_def.description,
                action=action,
                sql=sql_rendered,
                function=r_def.function,
                params=resolved_params,
            )
        )

    return resolved
