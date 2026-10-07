import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from mdf.calendar import compiled_calendar, custom_property
from mdf.dq import DQLibrary, resolve_column_dq_rules
from mdf.loading import discover_datasets, load_yaml_file
from mdf.validation import validate_project


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_template(
    template: str, env_cfg: dict[str, Any], source: str, dataset: str, layer: str
) -> str:
    """Resolve a naming/landing template with variables from env config (FR-D.2)."""
    catalog = env_cfg.get("catalog", "{env}_catalog".replace("{env}", env_cfg.get("env", "dev")))
    return template.format(
        env=env_cfg.get("env", "dev"),
        catalog=catalog,
        source=source,
        dataset=dataset,
        layer=layer,
    )


def load_env_config(config_dir: Path | str, env: str) -> dict[str, Any]:
    """Load config/env/<env>.yaml."""
    env_path = Path(config_dir) / "env" / f"{env}.yaml"
    if not env_path.exists():
        raise FileNotFoundError(f"Environment config not found: {env_path}")
    return load_yaml_file(env_path)


def load_naming_config(config_dir: Path | str) -> dict[str, str]:
    """Load config/naming.yaml."""
    naming_path = Path(config_dir) / "naming.yaml"
    if not naming_path.exists():
        raise FileNotFoundError(f"Naming config not found: {naming_path}")
    return load_yaml_file(naming_path)


def _deterministic_json_bytes(data: Any) -> bytes:
    """Serialize to deterministic JSON: sorted keys, fixed indent, LF endings (AC-11)."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")


def build_reader(contract: dict[str, Any], env: str) -> dict[str, Any]:
    """FR-M.5: the `reader` object compiled into bronze AND silver resolved JSON.

    `format` comes from the `servers[]` entry whose `environment` matches `env`
    (None if no such server -- mdf validate must reject this before compile runs,
    see validate_servers_for_envs in mdf.validation). The rest come from the
    contract's dataset-level `customProperties`. `file_pattern`/`partition_pattern`
    keep their `{{business_date}}`/`*` templates untouched -- never resolved here.
    """
    server = next(
        (
            s
            for s in contract.get("servers", []) or []
            if isinstance(s, dict) and s.get("environment") == env
        ),
        None,
    )
    return {
        "format": server.get("format") if server else None,
        "file_pattern": custom_property(contract, "file_pattern"),
        "partition_pattern": custom_property(contract, "partition_pattern"),
        "header": custom_property(contract, "header"),
        "encoding": custom_property(contract, "encoding"),
        "run_grain": custom_property(contract, "run_grain"),
        "source_type": custom_property(contract, "source_type"),
    }


def compile_project(
    env: str = "dev",
    base_dir: Path | str = "DataContract",
    config_dir: Path | str = "config",
) -> list[Path]:
    """
    Compile all discovered datasets into resolved JSON configs (FR-D.1, FR-D.3, FR-D.8).
    - Validates first; on error, writes nothing (and nothing is cleaned/deleted either).
    - Writes resolved JSON per target table (bronze, silver) to
      build/<env>/resolved/<source>/{layer}.<source>.<dataset>.resolved.json (layout v2).
    - Deterministic: same input -> byte-identical output (AC-11).
    """
    # Validate first (FR-D.1): if errors exist, write nothing
    report = validate_project(base_dir=base_dir, config_dir=config_dir)
    if not report.is_valid:
        raise RuntimeError(
            f"Validation failed with {len(report.errors)} errors — compile aborted, nothing "
            "written.\n" + report.format_thai_summary()
        )

    cfg_base = Path(config_dir)
    env_cfg = load_env_config(cfg_base, env)
    naming = load_naming_config(cfg_base)
    dq_lib = DQLibrary.load(cfg_base / "dq_library.yaml")
    dq_lib_sha = sha256_file(cfg_base / "dq_library.yaml")

    datasets = discover_datasets(base_dir)
    output_dir = Path("build") / env / "resolved"
    # HRM correction (H-103 #2): clean stale resolved/ (flat leftovers from pre-v2 compiles)
    # only AFTER validation passed, and strictly under build/ (FR-B.6).
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for ds in datasets:
        contract = load_yaml_file(ds.contract_path)
        pipeline = load_yaml_file(ds.pipeline_path)

        contract_sha = sha256_file(ds.contract_path)
        pipeline_sha = sha256_file(ds.pipeline_path)
        contract_id = contract.get("id", f"{ds.source}.{ds.dataset}")
        contract_version = contract.get("version", "unknown")

        # Resolve pipeline actions overrides (rule@col -> action)
        pipeline_actions: dict[str, str] = {}
        if isinstance(pipeline.get("actions"), dict):
            pipeline_actions = pipeline["actions"]

        # Expand DQ checks per column (FR-D.3, DQ-5 staging)
        checks: list[dict[str, Any]] = []
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
            # FR-M.7: path of the ODCS contract bundled into the v3 release package
            # (`mdf package` copies the bytes of `contract_file` above there) -- same value on
            # bronze and silver, deterministic from source/dataset only.
            "contract_bundle_path": f"{ds.source}/{ds.dataset}.odcs.yaml",
            "pipeline_file": str(ds.pipeline_path).replace("\\", "/"),
            "pipeline_sha256": pipeline_sha,
            "dq_library_sha256": dq_lib_sha,
        }

        schema_version = contract.get("version", "unknown")

        # Column schema from contract
        columns: list[dict[str, Any]] = []
        for s in schemas:
            if isinstance(s, dict):
                for p in s.get("properties", []):
                    if isinstance(p, dict) and "name" in p:
                        col: dict[str, Any] = {
                            "name": p["name"],
                            "logicalType": p.get("logicalType"),
                            "physicalType": p.get("physicalType"),
                            "required": p.get("required", False),
                            "classification": p.get("classification", "none"),
                            "description": p.get("description", ""),
                            # FR-M.6: privacy flags + tags, straight from the contract column.
                            # mdf validate guarantees pii/pci are real bool before compile runs.
                            "pii": custom_property(p, "pii"),
                            "pci": custom_property(p, "pci"),
                            "tags": list(p.get("tags", []) or []),
                        }
                        columns.append(col)

        source_dir = output_dir / ds.source
        source_dir.mkdir(parents=True, exist_ok=True)

        # FR-M.3/FR-M.5: computed ONCE per dataset so bronze and silver get the
        # exact same object (compared byte-for-byte via json.dumps(sort_keys=True)).
        calendar, _, _ = compiled_calendar(contract)
        reader = build_reader(contract, env)

        for layer in ("bronze", "silver"):
            resolved = {
                "config_id": resolve_template(
                    naming["config_id"], env_cfg, ds.source, ds.dataset, layer
                ),
                "layer": layer,
                "source": ds.source,
                "dataset": ds.dataset,
                "contract_id": contract_id,
                "table": resolve_template(naming["table"], env_cfg, ds.source, ds.dataset, layer),
                "landing": resolve_template(
                    naming["landing"], env_cfg, ds.source, ds.dataset, layer
                ),
                "quarantine": resolve_template(
                    naming["quarantine"], env_cfg, ds.source, ds.dataset, layer
                ),
                "vault": resolve_template(naming["vault"], env_cfg, ds.source, ds.dataset, layer),
                "checkpoint": resolve_template(
                    naming["checkpoint"], env_cfg, ds.source, ds.dataset, layer
                ),
                "run_log": resolve_template(
                    naming["run_log"], env_cfg, ds.source, ds.dataset, layer
                ),
                "schema": columns,
                "checks": checks,
                "pipeline": pipeline,
                "lineage": lineage,
                "schema_version": schema_version,
                "library_version": dq_lib.version,
                "calendar": calendar,
                "reader": reader,
            }

            out_path = source_dir / f"{layer}.{ds.source}.{ds.dataset}.resolved.json"
            out_path.write_bytes(_deterministic_json_bytes(resolved))
            written.append(out_path)

    return written
