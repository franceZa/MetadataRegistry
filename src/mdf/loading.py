import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml


class DuplicateKeyError(ValueError):
    """Raised when a YAML document contains duplicate mapping keys."""

    def __init__(self, key: str, line: int, column: int = 1, filepath: Optional[str] = None):
        self.key = key
        self.line = line
        self.column = column
        self.filepath = filepath
        msg = f"Duplicate key '{key}' found at line {line}, column {column}"
        if filepath:
            msg += f" in {filepath}"
        super().__init__(msg)


class DiscoveryError(Exception):
    """Raised when discovering datasets violates layout requirements."""

    def __init__(self, code: str, message: str, path: Optional[str] = None):
        self.code = code
        self.message = message
        self.path = path
        full_msg = f"[{code}] {message}"
        if path:
            full_msg += f" (at {path})"
        super().__init__(full_msg)


class UniqueKeyLoader(yaml.SafeLoader):
    """PyYAML SafeLoader that prohibits duplicate keys in mappings."""

    filepath: Optional[str] = None


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> Dict[str, Any]:
    loader.flatten_mapping(node)
    mapping: Dict[str, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            line = key_node.start_mark.line + 1
            col = key_node.start_mark.column + 1
            raise DuplicateKeyError(
                key=str(key),
                line=line,
                column=col,
                filepath=getattr(loader, "filepath", None),
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def load_yaml(content: str, filepath: Optional[str] = None) -> Any:
    """Load a YAML string, rejecting duplicate keys."""
    loader = UniqueKeyLoader(content)
    loader.filepath = filepath
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def load_yaml_file(filepath: Path | str) -> Any:
    """Load a YAML file, rejecting duplicate keys."""
    p = Path(filepath)
    with p.open("r", encoding="utf-8") as f:
        content = f.read()
    return load_yaml(content, filepath=str(p))


class DiscoveredDataset:
    """Represents a discovered contract-pipeline pair."""

    def __init__(
        self,
        source: str,
        dataset: str,
        contract_path: Path,
        pipeline_path: Path,
    ):
        self.source = source
        self.dataset = dataset
        self.contract_path = contract_path
        self.pipeline_path = pipeline_path

    def __repr__(self) -> str:
        return f"DiscoveredDataset({self.source}.{self.dataset})"


def discover_datasets(base_dir: Path | str = "DataContract") -> List[DiscoveredDataset]:
    """
    Discover dataset contracts and pipelines under base_dir according to FR-A.1.
    - Expected layout: DataContract/<source>/contract/<dataset>.odcs.yaml
                       DataContract/<source>/pipeline/<dataset>.pipeline.yaml
    - Legacy layout (dq/*.dq.yaml) raises DiscoveryError(LEGACY_LAYOUT)
    - Skips _template
    - Misplaced files raise DiscoveryError(FILE_LAYOUT)
    """
    base = Path(base_dir)
    if not base.exists():
        return []

    # Check for legacy layout
    for dq_dir in base.glob("*/dq"):
        if dq_dir.name == "dq" and dq_dir.is_dir():
            raise DiscoveryError(
                code="LEGACY_LAYOUT",
                message=(
                    f"Found legacy dq directory at '{dq_dir}'. "
                    "DataContract layout requires 'pipeline/' instead of 'dq/'. "
                    "Please run migration."
                ),
                path=str(dq_dir),
            )

    discovered: List[DiscoveredDataset] = []

    for src_dir in sorted(base.iterdir()):
        if not src_dir.is_dir():
            continue
        # Skip template or legacy/hidden dirs
        if src_dir.name.startswith("_") or src_dir.name.startswith("."):
            continue

        source = src_dir.name
        contract_dir = src_dir / "contract"
        pipeline_dir = src_dir / "pipeline"

        if not contract_dir.is_dir():
            continue

        for c_file in sorted(contract_dir.glob("*.odcs.yaml")):
            dataset = c_file.name[: -len(".odcs.yaml")]
            p_file = pipeline_dir / f"{dataset}.pipeline.yaml"

            if not p_file.exists():
                raise DiscoveryError(
                    code="FILE_LAYOUT",
                    message=f"Missing corresponding pipeline file for contract '{c_file}' (expected '{p_file}')",
                    path=str(p_file),
                )

            discovered.append(
                DiscoveredDataset(
                    source=source,
                    dataset=dataset,
                    contract_path=c_file,
                    pipeline_path=p_file,
                )
            )

    return discovered
