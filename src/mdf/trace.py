import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OrphanReport:
    orphan_contracts: list[str]
    orphan_pipelines: list[str]


def load_dataset(env: str, source: str, dataset: str, layer: str) -> dict[str, Any]:
    """
    Load a resolved dataset config from build/<env>/resolved/ (getter per FR-G).
    Raises FileNotFoundError if not compiled yet.
    """
    resolved_path = Path("build") / env / "resolved" / f"{layer}.{source}.{dataset}.resolved.json"
    if not resolved_path.exists():
        raise FileNotFoundError(
            f"Resolved config not found: {resolved_path}. Run 'mdf compile --env {env}' first."
        )
    with resolved_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def trace_table(table_name: str, env: str = "dev") -> dict[str, Any]:
    """
    Trace a resolved target table back to its sources (AC-18, FR-G).
    Accepts table names like 'silver.cc.credit_card_txn' or 'bronze.cc.credit_card'.
    Returns lineage info: bronze input, contract id/version/sha256, source files with sha256.
    """
    parts = table_name.split(".")
    if len(parts) != 3:
        raise ValueError(
            f"Invalid table name '{table_name}'. Expected format: <layer>.<source>.<dataset> "
            "(e.g., silver.cc.credit_card_txn)"
        )
    layer, source, dataset = parts

    resolved = load_dataset(env=env, source=source, dataset=dataset, layer=layer)

    lineage = resolved.get("lineage", {})

    trace_result: dict[str, Any] = {
        "table": resolved.get("table"),
        "layer": layer,
        "config_id": resolved.get("config_id"),
        "bronze_input": None,
        "contract_id": lineage.get("contract_id"),
        "contract_version": lineage.get("contract_version"),
        "contract_file": lineage.get("contract_file"),
        "contract_sha256": lineage.get("contract_sha256"),
        "pipeline_file": lineage.get("pipeline_file"),
        "pipeline_sha256": lineage.get("pipeline_sha256"),
        "dq_library_sha256": lineage.get("dq_library_sha256"),
        "schema_version": resolved.get("schema_version"),
        "landing": resolved.get("landing"),
    }

    # For silver, the bronze input is the bronze table of the same dataset
    if layer != "bronze":
        bronze_resolved = load_dataset(env=env, source=source, dataset=dataset, layer="bronze")
        trace_result["bronze_input"] = {
            "table": bronze_resolved.get("table"),
            "contract_id": bronze_resolved.get("lineage", {}).get("contract_id"),
            "contract_sha256": bronze_resolved.get("lineage", {}).get("contract_sha256"),
        }

    return trace_result


def format_trace(trace: dict[str, Any]) -> str:
    """Format a trace result as human-readable output (Thai)."""
    lines = [
        f"📊 Lineage: {trace['table']}",
        f"   Layer: {trace['layer']} · Config ID: {trace['config_id']}",
        f"   Landing: {trace['landing']}",
    ]
    if trace.get("bronze_input"):
        b = trace["bronze_input"]
        lines.append(
            f"   Bronze input: {b['table']} (contract {b['contract_id']}, sha256 "
            f"{b['contract_sha256'][:12]}…)"
        )
    lines.extend(
        [
            f"   Contract: {trace['contract_id']} v{trace['contract_version']}",
            f"     file: {trace['contract_file']}",
            f"     sha256: {trace['contract_sha256']}",
            f"   Pipeline: {trace['pipeline_file']}",
            f"     sha256: {trace['pipeline_sha256']}",
            f"   DQ library sha256: {trace['dq_library_sha256']}",
            f"   Schema version: {trace['schema_version']}",
        ]
    )
    return "\n".join(lines)


def find_orphans(base_dir: Path | str = "DataContract") -> OrphanReport:
    """
    Detect orphan contracts (contract without pipeline) and orphan pipelines
    (pipeline without contract) under base_dir (FR-G).
    Note: discover_datasets raises on missing pipeline pairs, so a full scan
    is done manually here to enumerate rather than fail.
    """
    base = Path(base_dir)
    orphan_contracts: list[str] = []
    orphan_pipelines: list[str] = []

    for src_dir in sorted(base.iterdir()) if base.exists() else []:
        if not src_dir.is_dir() or src_dir.name.startswith("_") or src_dir.name.startswith("."):
            continue
        source = src_dir.name
        contract_dir = src_dir / "contract"
        pipeline_dir = src_dir / "pipeline"

        contract_datasets = set()
        if contract_dir.is_dir():
            for c_file in contract_dir.glob("*.odcs.yaml"):
                ds_name = c_file.name[: -len(".odcs.yaml")]
                contract_datasets.add(ds_name)

        pipeline_datasets = set()
        if pipeline_dir.is_dir():
            for p_file in pipeline_dir.glob("*.pipeline.yaml"):
                ds_name = p_file.name[: -len(".pipeline.yaml")]
                pipeline_datasets.add(ds_name)

        for ds_name in contract_datasets - pipeline_datasets:
            orphan_contracts.append(f"{source}.{ds_name} (contract ไม่มี pipeline)")
        for ds_name in pipeline_datasets - contract_datasets:
            orphan_pipelines.append(f"{source}.{ds_name} (pipeline ไม่มี contract)")

    return OrphanReport(orphan_contracts=orphan_contracts, orphan_pipelines=orphan_pipelines)
