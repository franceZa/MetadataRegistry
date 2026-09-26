import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from mdf.loading import discover_datasets, load_yaml, load_yaml_file


@dataclass
class ChangeRecord:
    kind: str  # "breaking" | "non_breaking" | "info"
    category: str  # e.g. "column_removed", "column_type_changed", "required_changed", "library_rule_changed", "library_rule_disabled"
    dataset: str
    detail: str
    fix: Optional[str] = None


@dataclass
class DiffResult:
    changes: List[ChangeRecord] = field(default_factory=list)

    @property
    def has_breaking(self) -> bool:
        return any(c.kind == "breaking" for c in self.changes)

    def summary_thai(self) -> str:
        if not self.changes:
            return "✅ ไม่พบความแตกต่างจาก baseline (no diff)"
        breaking = [c for c in self.changes if c.kind == "breaking"]
        others = [c for c in self.changes if c.kind != "breaking"]
        lines = []
        if breaking:
            lines.append(f"❌ พบ BREAKING CHANGE {len(breaking)} รายการ:")
            for c in breaking:
                lines.append(f"  - [{c.category}] {c.dataset}: {c.detail}")
                if c.fix:
                    lines.append(f"    วิธีแก้: {c.fix}")
        if others:
            lines.append(f"ℹ️ การเปลี่ยนแปลงอื่น ๆ {len(others)} รายการ:")
            for c in others:
                lines.append(f"  - [{c.category}] {c.dataset}: {c.detail}")
        return "\n".join(lines)


def _git_show_file(rev: str, path: str) -> Optional[str]:
    """Read a file's content at a git revision. Returns None if not present."""
    try:
        result = subprocess.run(
            ["git", "show", f"{rev}:{path}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception:
        return None


def load_baseline_contracts(rev: str, base_dir: Path | str = "DataContract") -> Dict[str, Dict[str, Any]]:
    """Load all contract YAMLs from a git revision, keyed by contract id."""
    base = str(base_dir).replace("\\", "/")
    # Discover dataset list from current workspace layout (filenames are stable across revs here)
    baseline: Dict[str, Dict[str, Any]] = {}
    datasets = discover_datasets(base_dir)
    for ds in datasets:
        rel = str(ds.contract_path).replace("\\", "/")
        content = _git_show_file(rev, rel)
        if content is None:
            continue
        data = load_yaml(content, filepath=f"{rev}:{rel}")
        if isinstance(data, dict) and "id" in data:
            baseline[data["id"]] = data
    return baseline


def load_baseline_library(rev: str, library_path: str = "config/dq_library.yaml") -> Optional[Dict[str, Any]]:
    """Load DQ library from a git revision."""
    content = _git_show_file(rev, library_path)
    if content is None:
        return None
    return load_yaml(content, filepath=f"{rev}:{library_path}")


def _contract_columns(contract: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    cols: Dict[str, Dict[str, Any]] = {}
    for s in contract.get("schema", []) or []:
        if isinstance(s, dict):
            for p in s.get("properties", []) or []:
                if isinstance(p, dict) and "name" in p:
                    cols[p["name"]] = p
    return cols


def _major_version(version: str) -> int:
    try:
        return int(str(version).split(".")[0])
    except (ValueError, IndexError):
        return 0


def diff_contracts(
    current: Dict[str, Dict[str, Any]],
    baseline: Dict[str, Dict[str, Any]],
) -> List[ChangeRecord]:
    """
    Compare current contracts against baseline, detecting breaking changes per AC-13:
    - Column removed without major version bump -> breaking
    - Column type changed without major bump -> breaking
    - required true->false without major bump -> breaking (semantic)
    - With major bump: reported as info/impact but not breaking
    """
    changes: List[ChangeRecord] = []

    for cid, cur in current.items():
        base = baseline.get(cid)
        if base is None:
            changes.append(
                ChangeRecord(
                    kind="info",
                    category="new_dataset",
                    dataset=cid,
                    detail=f"Dataset ใหม่ (ไม่มีใน baseline)",
                )
            )
            continue

        major_bumped = _major_version(cur.get("version", "0")) > _major_version(base.get("version", "0"))

        cur_cols = _contract_columns(cur)
        base_cols = _contract_columns(base)

        # Removed columns
        for col_name in base_cols.keys() - cur_cols.keys():
            if major_bumped:
                changes.append(
                    ChangeRecord(
                        kind="info",
                        category="column_removed_bumped",
                        dataset=cid,
                        detail=f"ลบคอลัมน์ '{col_name}' (major version bumped แล้ว — รายงาน impact อย่างเดียว)",
                        fix="ตรวจสอบ downstream consumers ของคอลัมน์นี้",
                    )
                )
            else:
                changes.append(
                    ChangeRecord(
                        kind="breaking",
                        category="column_removed",
                        dataset=cid,
                        detail=f"ลบคอลัมน์ '{col_name}' โดยไม่ bump major version (base v{base.get('version')} → cur v{cur.get('version')})",
                        fix=f"กู้คืนคอลัมน์ หรือ bump major version (เช่น {int(str(base.get('version','1.0.0')).split('.')[0]) + 1}.0.0)",
                    )
                )

        # Type changes
        for col_name in cur_cols.keys() & base_cols.keys():
            cur_t = cur_cols[col_name].get("logicalType")
            base_t = base_cols[col_name].get("logicalType")
            if cur_t != base_t:
                kind = "info" if major_bumped else "breaking"
                changes.append(
                    ChangeRecord(
                        kind=kind,
                        category="column_type_changed" + ("_bumped" if major_bumped else ""),
                        dataset=cid,
                        detail=f"คอลัมน์ '{col_name}' เปลี่ยน logicalType จาก {base_t} → {cur_t}",
                    )
                )

            # required true -> false is a relaxation; false -> true is stricter (breaking for producers)
            cur_req = cur_cols[col_name].get("required")
            base_req = base_cols[col_name].get("required")
            if base_req and not cur_req:
                changes.append(
                    ChangeRecord(
                        kind="info",
                        category="required_relaxed",
                        dataset=cid,
                        detail=f"คอลัมน์ '{col_name}' เปลี่ยน required: true → false (ผ่อนปรน)",
                    )
                )
            elif not base_req and cur_req:
                changes.append(
                    ChangeRecord(
                        kind="breaking" if not major_bumped else "info",
                        category="required_strictened",
                        dataset=cid,
                        detail=f"คอลัมน์ '{col_name}' เปลี่ยน required: false → true (เข้มงวดขึ้น — source ต้องส่งค่าเสมอ)",
                    )
                )

    for cid in baseline.keys() - current.keys():
        changes.append(
            ChangeRecord(
                kind="breaking",
                category="dataset_removed",
                dataset=cid,
                detail="Dataset ทั้งหมดถูกลบออกจาก workspace (มีใน baseline แต่หายในปัจจุบัน)",
                fix="ยืนยันการลบ หรือกู้คืน contract",
            )
        )

    return changes


def diff_library(
    current_lib: Dict[str, Any],
    baseline_lib: Optional[Dict[str, Any]],
) -> List[ChangeRecord]:
    """
    Compare DQ library versions (DQ-6, FR-C.7): rule changes and disabled rules are reported.
    """
    changes: List[ChangeRecord] = []
    if baseline_lib is None:
        return changes

    cur_rules = current_lib.get("rules", {}) or {}
    base_rules = baseline_lib.get("rules", {}) or {}

    for r_name in base_rules.keys() - cur_rules.keys():
        changes.append(
            ChangeRecord(
                kind="breaking",
                category="library_rule_removed",
                dataset=f"dq_library:{r_name}",
                detail=f"กฎ '{r_name}' ถูกลบออกจาก library — ตารางที่อ้างถึงจะไม่ถูกตรวจอีกต่อไป",
                fix="ตรวจสอบ blast radius ก่อนลบกฎ",
            )
        )

    for r_name in cur_rules.keys() & base_rules.keys():
        cur_r = cur_rules[r_name] or {}
        base_r = base_rules[r_name] or {}
        if cur_r.get("sql") != base_r.get("sql") or cur_r.get("function") != base_r.get("function"):
            changes.append(
                ChangeRecord(
                    kind="non_breaking",
                    category="library_rule_changed",
                    dataset=f"dq_library:{r_name}",
                    detail=f"นิยามกฎ '{r_name}' เปลี่ยนแปลง — ผลการตรวจอาจต่างจากเดิม (DQ-6)",
                    fix="ตรวจสอบ blast radius ของกฎนี้",
                )
            )
        if base_r.get("enabled", True) and not cur_r.get("enabled", True):
            changes.append(
                ChangeRecord(
                    kind="non_breaking",
                    category="library_rule_disabled",
                    dataset=f"dq_library:{r_name}",
                    detail=f"กฎ '{r_name}' ถูกปิด (enabled: false) — ต้องรายงานใน diff (DQ-6)",
                )
            )

    return changes


def blast_radius(
    rule_name: str,
    base_dir: Path | str = "DataContract",
) -> List[Dict[str, str]]:
    """
    Compute blast radius of a DQ library rule: every dataset/column using it
    via dq: tags (AC-24, DQ-6).
    """
    affected: List[Dict[str, str]] = []
    for ds in discover_datasets(base_dir):
        contract = load_yaml_file(ds.contract_path)
        for s in contract.get("schema", []) or []:
            if not isinstance(s, dict):
                continue
            for p in s.get("properties", []) or []:
                if not isinstance(p, dict):
                    continue
                tags = p.get("tags", []) or []
                dq_tags = [t[3:] for t in tags if isinstance(t, str) and t.startswith("dq:")]
                if rule_name in dq_tags:
                    affected.append(
                        {
                            "dataset": contract.get("id", f"{ds.source}.{ds.dataset}"),
                            "column": p.get("name", "unknown"),
                        }
                    )
    return affected


def run_diff(rev: str, base_dir: Path | str = "DataContract") -> DiffResult:
    """
    Run a full diff of the current workspace against a git baseline revision.
    Returns a DiffResult; has_breaking is True when AC-13-breaking changes exist.
    """
    current_contracts: Dict[str, Dict[str, Any]] = {}
    for ds in discover_datasets(base_dir):
        data = load_yaml_file(ds.contract_path)
        if isinstance(data, dict) and "id" in data:
            current_contracts[data["id"]] = data

    baseline_contracts = load_baseline_contracts(rev, base_dir)

    current_lib_path = Path("config") / "dq_library.yaml"
    current_lib = load_yaml_file(current_lib_path) if current_lib_path.exists() else {"rules": {}}
    baseline_lib = load_baseline_library(rev)

    changes = diff_contracts(current_contracts, baseline_contracts)
    changes += diff_library(current_lib, baseline_lib)

    return DiffResult(changes=changes)
