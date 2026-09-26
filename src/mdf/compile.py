import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mdf.dq import DQLibrary, resolve_column_dq_rules
from mdf.loading import discover_datasets, load_yaml_file
from mdf.validation import get_contract_column_names, validate_project


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_template(template: str, env_cfg: Dict[str, Any], source: str, dataset: str, layer: str) -> str:
    """Resolve a naming/landing template with variables from env config (FR-D.2)."""
    catalog = env_cfg.get("catalog", "{env}_catalog".replace("{env}", env_cfg.get("env", "dev")))
    return template.format(
        env=env_cfg.get("env", "dev"),
        catalog=catalog,
        source=source,
        dataset=dataset,
        layer=layer,
    )


def load_env_config(config_dir: Path | str, env: str) -> Dict[str, Any]:
    """Load config/env/<env>.yaml."""
    env_path = Path(config_dir) / "env" / f"{env}.yaml"
    if not env_path.exists():
        raise FileNotFoundError(f"Environment config not found: {env_path}")
    return load_yaml_file(env_path)


def load_naming_config(config_dir: Path | str) -> Dict[str, str]:
    """Load config/naming.yaml."""
    naming_path = Path(config_dir) / "naming.yaml"
    if not naming_path.exists():
        raise FileNotFoundError(f"Naming config not found: {naming_path}")
    return load_yaml_file(naming_path)


def _deterministic_json_bytes(data: Any) -> bytes:
    """Serialize to deterministic JSON bytes: sorted keys, no extra whitespace, LF endings (AC-11)."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")


def compile_project(
    env: str = "dev",
    base_dir: Path | str = "DataContract",
    config_dir: Path | str = "config",
) -> List[Path]:
    """
    Compile all discovered datasets into resolved JSON configs (FR-D.1, FR-D.3).
    - Validates first; on error, writes nothing.
    - Writes resolved JSON per target table (bronze, silver) to build/<env>/resolved/.
    - Deterministic: same input -> byte-identical output (AC-11).
    """
    # Validate first (FR-D.1): if errors exist, write nothing
    report = validate_project(base_dir=base_dir, config_dir=config_dir)
    if not report.is_valid:
        raise RuntimeError(
            f"Validation failed with {len(report.errors)} errors — compile aborted, nothing written.\n"
            + report.format_thai_summary()
        )

    cfg_base = Path(config_dir)
    env_cfg = load_env_config(cfg_base, env)
    naming = load_naming_config(cfg_base)
    dq_lib = DQLibrary.load(cfg_base / "dq_library.yaml")
    dq_lib_sha = sha256_file(cfg_base / "dq_library.yaml")

    datasets = discover_datasets(base_dir)
    output_dir = Path("build") / env / "resolved"
    output_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for ds in datasets:
        contract = load_yaml_file(ds.contract_path)
        pipeline = load_yaml_file(ds.pipeline_path)

        contract_sha = sha256_file(ds.contract_path)
        pipeline_sha = sha256_file(ds.pipeline_path)
        contract_id = contract.get("id", f"{ds.source}.{ds.dataset}")
        contract_version = contract.get("version", "unknown")

        # Resolve pipeline actions overrides (rule@col -> action)
        pipeline_actions: Dict[str, str] = {}
        if isinstance(pipeline.get("actions"), dict):
            pipeline_actions = pipeline["actions"]

        # Expand DQ checks per column (FR-D.3, DQ-5 staging)
        checks: List[Dict[str, Any]] = []
        schemas = contract.get("schema", [])
        if isinstance(schemas, list):
            for s in schemas:
                if not isinstance(s, dict):
                    continue
                for p in s.get("properties", []):
                    if not isinstance(p, dict):
                        continue
                    col_name = p.get("name")
                    if not col_name:
                        continue
                    try:
                        resolved_rules = resolve_column_dq_rules(p, dq_lib, pipeline_actions)
                    except Exception:
                        resolved_rules = []
                    for r in resolved_rules:
                        checks.append(
                            {
                                "rule_id": f"{r.rule_name}@{col_name}",
                                "description": r.description,
                                "column": col_name,
                                "kind": r.kind,
                                "sql": r.sql,
                                "function": r.function,
                                "action": r.action,
                                "stage": r.stage,
                                "params": r.params,
                                "library_version": dq_lib.version,
                            }
                        )

        lineage = {
            "contract_id": contract_id,
            "contract_version": contract_version,
            "contract_file": str(ds.contract_path).replace("\\", "/"),
            "contract_sha256": contract_sha,
            "pipeline_file": str(ds.pipeline_path).replace("\\", "/"),
            "pipeline_sha256": pipeline_sha,
            "dq_library_sha256": dq_lib_sha,
        }

        schema_version = contract.get("version", "unknown")

        # Column schema from contract
        columns: List[Dict[str, Any]] = []
        for s in schemas:
            if isinstance(s, dict):
                for p in s.get("properties", []):
                    if isinstance(p, dict) and "name" in p:
                        col: Dict[str, Any] = {
                            "name": p["name"],
                            "logicalType": p.get("logicalType"),
                            "physicalType": p.get("physicalType"),
                            "required": p.get("required", False),
                            "classification": p.get("classification", "none"),
                            "description": p.get("description", ""),
                        }
                        columns.append(col)

        for layer in ("bronze", "silver"):
            resolved = {
                "config_id": resolve_template(naming["config_id"], env_cfg, ds.source, ds.dataset, layer),
                "layer": layer,
                "source": ds.source,
                "dataset": ds.dataset,
                "contract_id": contract_id,
                "table": resolve_template(naming["table"], env_cfg, ds.source, ds.dataset, layer),
                "landing": resolve_template(naming["landing"], env_cfg, ds.source, ds.dataset, layer),
                "quarantine": resolve_template(naming["quarantine"], env_cfg, ds.source, ds.dataset, layer),
                "vault": resolve_template(naming["vault"], env_cfg, ds.source, ds.dataset, layer),
                "checkpoint": resolve_template(naming["checkpoint"], env_cfg, ds.source, ds.dataset, layer),
                "run_log": resolve_template(naming["run_log"], env_cfg, ds.source, ds.dataset, layer),
                "schema": columns,
                "checks": checks,
                "pipeline": pipeline,
                "lineage": lineage,
                "schema_version": schema_version,
                "library_version": dq_lib.version,
            }

            out_path = output_dir / f"{layer}.{ds.source}.{ds.dataset}.resolved.json"
            out_path.write_bytes(_deterministic_json_bytes(resolved))
            written.append(out_path)

    return written
