import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema

from mdf.dq import DQLibrary, DQValidationError, resolve_column_dq_rules
from mdf.loading import (
    DiscoveryError,
    DuplicateKeyError,
    discover_datasets,
    load_yaml_file,
)
from mdf.rules import Rule, evaluate_rules, load_rules_json


@dataclass
class ValidationIssue:
    code: str
    message: str
    file_path: str
    field: str | None = None
    fix: str | None = None
    severity: str = "error"  # "error" | "warning"

    def format_thai(self) -> str:
        lines = [f"- [{self.severity.upper()}] รหัส: {self.code}"]
        if self.field:
            lines.append(f"  ฟิลด์: {self.field}")
        lines.append(f"  ข้อความ: {self.message}")
        if self.fix:
            lines.append(f"  วิธีแก้ไข: {self.fix}")
        return "\n".join(lines)


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def add_error(
        self,
        code: str,
        message: str,
        file_path: str,
        field: str | None = None,
        fix: str | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                file_path=file_path,
                field=field,
                fix=fix,
                severity="error",
            )
        )

    def add_warning(
        self,
        code: str,
        message: str,
        file_path: str,
        field: str | None = None,
        fix: str | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                file_path=file_path,
                field=field,
                fix=fix,
                severity="warning",
            )
        )

    def format_thai_summary(self) -> str:
        if self.is_valid:
            warn_msg = f" (พบข้อควรระวัง {len(self.warnings)} รายการ)" if self.warnings else ""
            return f"✅ การตรวจสอบความถูกต้องผ่านเรียบร้อย (PASS){warn_msg}"

        grouped: dict[str, list[ValidationIssue]] = {}
        for issue in self.issues:
            grouped.setdefault(issue.file_path, []).append(issue)

        out = [
            f"❌ ตรวจพบข้อผิดพลาด {len(self.errors)} รายการ (และคำเตือน {len(self.warnings)} "
            "รายการ):\n"
        ]
        for file_path, items in grouped.items():
            out.append(f"📁 ไฟล์: {file_path}")
            for item in items:
                out.append(item.format_thai())
            out.append("")
        return "\n".join(out)


def get_contract_column_names(contract_data: dict[str, Any]) -> set[str]:
    """Extract all column names defined in contract schema properties."""
    columns: set[str] = set()
    schemas = contract_data.get("schema", [])
    if isinstance(schemas, list):
        for s in schemas:
            if isinstance(s, dict):
                props = s.get("properties", [])
                if isinstance(props, list):
                    for p in props:
                        if isinstance(p, dict) and "name" in p:
                            columns.add(p["name"])
    return columns


def validate_contract_file(
    contract_path: Path,
    odcs_schema_validator: jsonschema.Draft202012Validator,
    contract_rules: list[Rule],
    dq_library: DQLibrary,
    report: ValidationReport,
) -> dict[str, Any] | None:
    """Validate a single ODCS DataContract file."""
    path_str = str(contract_path)
    try:
        data = load_yaml_file(contract_path)
    except DuplicateKeyError as e:
        report.add_error(
            code="DUPLICATE_KEY",
            message=f"พบ duplicate key '{e.key}' ที่บรรทัด {e.line}",
            file_path=path_str,
            field=e.key,
            fix="ลบหรือเปลี่ยนชื่อ key ที่ซ้ำกัน",
        )
        return None
    except Exception as e:
        report.add_error(
            code="YAML_PARSE_ERROR",
            message=f"ไม่สามารถอ่านไฟล์ YAML ได้: {e}",
            file_path=path_str,
        )
        return None

    if not isinstance(data, dict):
        report.add_error(
            code="INVALID_ROOT",
            message="โครงสร้างรากของ contract ต้องเป็น dictionary",
            file_path=path_str,
        )
        return None

    # 1. Validate against ODCS JSON Schema
    for err in odcs_schema_validator.iter_errors(data):
        field_loc = ".".join(str(p) for p in err.path)
        report.add_error(
            code="ODCS_SCHEMA_VIOLATION",
            message=f"ผิดข้อกำหนด ODCS v3.0.2: {err.message}",
            file_path=path_str,
            field=field_loc,
            fix="ปรับแต่งฟิลด์ให้ตรงตามมาตรฐาน ODCS v3.0.2",
        )

    # 2. Validate structural rules
    violations = evaluate_rules(contract_rules, data)
    for v in violations:
        if v.severity == "warning":
            report.add_warning(
                code=v.rule_id, message=v.message, file_path=path_str, field=v.path, fix=v.fix
            )
        else:
            report.add_error(
                code=v.rule_id, message=v.message, file_path=path_str, field=v.path, fix=v.fix
            )

    # 3. Validate DQ tags & quality[]
    schemas = data.get("schema", [])
    if isinstance(schemas, list):
        for s_idx, s in enumerate(schemas):
            if isinstance(s, dict):
                props = s.get("properties", [])
                if isinstance(props, list):
                    for p in props:
                        if isinstance(p, dict):
                            col_name = p.get("name", "unknown")
                            try:
                                resolve_column_dq_rules(p, dq_library)
                            except DQValidationError as dq_err:
                                report.add_error(
                                    code=dq_err.code,
                                    message=dq_err.message,
                                    file_path=path_str,
                                    field=f"schema[{s_idx}].properties[{col_name}]",
                                    fix=(
                                        "ลบ 'quality[]' และเปลี่ยนไปใช้ 'tags: [dq:<rule>]'"
                                        if dq_err.code == "USE_TAG"
                                        else "ตรวจสอบนิยามใน config/dq_library.yaml "
                                        "และพารามิเตอร์ที่จำเป็น"
                                    ),
                                )

    return data


def validate_pipeline_file(
    pipeline_path: Path,
    pipeline_rules: list[Rule],
    contract_data: dict[str, Any] | None,
    report: ValidationReport,
) -> dict[str, Any] | None:
    """Validate a single Pipeline file and its cross-references to contract."""
    path_str = str(pipeline_path)
    try:
        data = load_yaml_file(pipeline_path)
    except DuplicateKeyError as e:
        report.add_error(
            code="DUPLICATE_KEY",
            message=f"พบ duplicate key '{e.key}' ที่บรรทัด {e.line}",
            file_path=path_str,
            field=e.key,
        )
        return None
    except Exception as e:
        report.add_error(
            code="YAML_PARSE_ERROR",
            message=f"ไม่สามารถอ่านไฟล์ YAML ได้: {e}",
            file_path=path_str,
        )
        return None

    if not isinstance(data, dict):
        report.add_error(
            code="INVALID_ROOT",
            message="โครงสร้างรากของ pipeline ต้องเป็น dictionary",
            file_path=path_str,
        )
        return None

    # 1. Structural rules (unknown keys check via allowed_keys)
    violations = evaluate_rules(pipeline_rules, data)
    for v in violations:
        report.add_error(
            code=v.rule_id, message=v.message, file_path=path_str, field=v.path, fix=v.fix
        )

    # 2. Cross-reference checks against contract schema
    if contract_data:
        contract_cols = get_contract_column_names(contract_data)

        # Check columns block
        cols = data.get("columns", {})
        if isinstance(cols, dict):
            for col_name in cols.keys():
                if col_name not in contract_cols:
                    report.add_error(
                        code="UNKNOWN_COLUMN_REF",
                        message=f"Pipeline กำหนด configuration ให้คอลัมน์ '{col_name}' แต่ไม่มีคอลัมน์นี้ใน "
                        "DataContract",
                        file_path=path_str,
                        field=f"columns.{col_name}",
                        fix="ตรวจสอบชื่อคอลัมน์ให้ตรงกับ DataContract (คอลัมน์ที่มี: "
                        f"{sorted(contract_cols)})",
                    )

        # Check actions block
        actions = data.get("actions", {})
        if isinstance(actions, dict):
            for action_key in actions.keys():
                if "@" in action_key:
                    rule_name, col_name = action_key.split("@", 1)
                    if col_name not in contract_cols:
                        report.add_error(
                            code="UNKNOWN_COLUMN_REF",
                            message=f"Action '{action_key}' อ้างถึงคอลัมน์ '{col_name}' ที่ไม่มีใน "
                            "DataContract",
                            file_path=path_str,
                            field=f"actions.{action_key}",
                            fix="ตรวจสอบชื่อคอลัมน์ใน action ให้ตรงกับ DataContract",
                        )

    return data


def validate_project(
    base_dir: Path | str = "DataContract",
    config_dir: Path | str = "config",
) -> ValidationReport:
    """Run full static validation across all discovered datasets and configurations."""
    report = ValidationReport()
    cfg_base = Path(config_dir)

    # Load ODCS JSON Schema
    schema_path = cfg_base / "schemas" / "odcs_v3.0.2.json"
    if not schema_path.exists():
        report.add_error("SCHEMA_NOT_FOUND", f"ไม่พบ ODCS Schema ที่ {schema_path}", str(schema_path))
        return report

    with schema_path.open("r", encoding="utf-8") as f:
        odcs_schema = json.load(f)
    odcs_validator = jsonschema.Draft202012Validator(odcs_schema)

    # Load rules and DQ library
    contract_rules_path = cfg_base / "rules" / "contract.rules.json"
    pipeline_rules_path = cfg_base / "rules" / "pipeline.rules.json"
    dq_lib_path = cfg_base / "dq_library.yaml"

    contract_rules = load_rules_json(contract_rules_path) if contract_rules_path.exists() else []
    pipeline_rules = load_rules_json(pipeline_rules_path) if pipeline_rules_path.exists() else []
    dq_lib = DQLibrary.load(dq_lib_path) if dq_lib_path.exists() else DQLibrary(rules={})

    # Discover datasets
    try:
        datasets = discover_datasets(base_dir)
    except DiscoveryError as disc_err:
        report.add_error(disc_err.code, disc_err.message, disc_err.path or str(base_dir))
        return report

    if not datasets:
        report.add_warning("NO_DATASETS", "ไม่พบ dataset ในโฟลเดอร์ DataContract", str(base_dir))
        return report

    contracts_by_id: dict[str, tuple[Path, dict[str, Any]]] = {}

    # Validate each discovered dataset
    for ds in datasets:
        contract_data = validate_contract_file(
            contract_path=ds.contract_path,
            odcs_schema_validator=odcs_validator,
            contract_rules=contract_rules,
            dq_library=dq_lib,
            report=report,
        )

        if contract_data and "id" in contract_data:
            contracts_by_id[contract_data["id"]] = (ds.contract_path, contract_data)

        validate_pipeline_file(
            pipeline_path=ds.pipeline_path,
            pipeline_rules=pipeline_rules,
            contract_data=contract_data,
            report=report,
        )

    # Run FK reference checks across all valid contracts
    validate_foreign_key_references(contracts_by_id, report)

    return report


def validate_foreign_key_references(
    contracts_by_id: dict[str, tuple[Path, dict[str, Any]]],
    report: ValidationReport,
) -> None:
    """
    Validate foreign_key config references across datasets
    (FR-B.14, D-P4-7 ก, AC-33).
    Format must be <source>.<dataset>.<column>.
    """
    # Build column lookup: "<source>.<dataset>.<column>" -> property_dict
    col_lookup: dict[str, dict[str, Any]] = {}
    for ds_id, (_c_path, c_data) in contracts_by_id.items():
        schemas = c_data.get("schema", [])
        if isinstance(schemas, list):
            for s in schemas:
                if isinstance(s, dict):
                    props = s.get("properties", [])
                    if isinstance(props, list):
                        for p in props:
                            if isinstance(p, dict) and "name" in p:
                                col_lookup[f"{ds_id}.{p['name']}"] = p

    # Now inspect all columns with foreign_key in customProperties
    for _ds_id, (c_path, c_data) in contracts_by_id.items():
        path_str = str(c_path)
        schemas = c_data.get("schema", [])
        if isinstance(schemas, list):
            for s in schemas:
                if isinstance(s, dict):
                    props = s.get("properties", [])
                    if isinstance(props, list):
                        for p in props:
                            if not isinstance(p, dict):
                                continue
                            col_name = p.get("name", "unknown")
                            fk_val = None
                            for cp in p.get("customProperties", []):
                                if isinstance(cp, dict) and cp.get("property") == "foreign_key":
                                    fk_val = cp.get("value")
                                    break

                            if not fk_val:
                                continue

                            # Validate format
                            parts = str(fk_val).split(".")
                            if len(parts) != 3:
                                report.add_error(
                                    code="FK_TARGET_NOT_FOUND",
                                    message=f"รูปแบบ foreign_key '{fk_val}' ไม่ถูกต้อง ต้องเป็น "
                                    "<source>.<dataset>.<column>",
                                    file_path=path_str,
                                    field=f"properties[{col_name}].customProperties.foreign_key",
                                    fix="กำหนด foreign_key ในรูปแบบ <source>.<dataset>.<column>",
                                )
                                continue

                            target_ds = f"{parts[0]}.{parts[1]}"
                            target_col = parts[2]
                            target_full_key = f"{target_ds}.{target_col}"

                            if target_ds not in contracts_by_id:
                                report.add_error(
                                    code="FK_TARGET_NOT_FOUND",
                                    message=f"Foreign key '{fk_val}' ชี้ไปหา dataset '{target_ds}' "
                                    "ที่ไม่มีอยู่ในระบบ",
                                    file_path=path_str,
                                    field=f"properties[{col_name}].customProperties.foreign_key",
                                    fix="ตรวจสอบชื่อ target dataset ให้ตรงกับ contract ที่มี (datasets: "
                                    f"{sorted(contracts_by_id.keys())})",
                                )
                                continue

                            if target_full_key not in col_lookup:
                                report.add_error(
                                    code="FK_TARGET_NOT_FOUND",
                                    message=f"Foreign key '{fk_val}' ชี้ไปหาคอลัมน์ '{target_col}' "
                                    f"ที่ไม่มีใน dataset '{target_ds}'",
                                    file_path=path_str,
                                    field=f"properties[{col_name}].customProperties.foreign_key",
                                    fix=f"ตรวจสอบชื่อคอลัมน์ใน target dataset '{target_ds}'",
                                )
                                continue

                            target_prop = col_lookup[target_full_key]
                            src_type = p.get("logicalType")
                            tgt_type = target_prop.get("logicalType")
                            if src_type and tgt_type and src_type != tgt_type:
                                report.add_error(
                                    code="FK_TYPE_MISMATCH",
                                    message=f"Foreign key '{fk_val}' มี logicalType ไม่ตรงกัน: source "
                                    f"'{col_name}' เป็น {src_type} แต่ target เป็น {tgt_type}",
                                    file_path=path_str,
                                    field=f"properties[{col_name}].customProperties.foreign_key",
                                    fix=f"ปรับ logicalType ให้ตรงกัน ({src_type} vs {tgt_type})",
                                )
