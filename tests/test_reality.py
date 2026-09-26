import subprocess
from pathlib import Path
import pytest

CONTRACTS = [
    "DataContract/cc/contract/credit_card.odcs.yaml",
    "DataContract/cc/contract/credit_card_txn.odcs.yaml",
    "DataContract/cc/contract/customer.odcs.yaml",
]

@pytest.mark.parametrize("contract_path", CONTRACTS)
def test_reality_lines_byte_for_byte(contract_path):
    """AC-17: REALITY oracle - verify that all lines containing REALITY match commit 88b982d byte-for-byte."""
    res = subprocess.run(
        ["git", "show", f"88b982d:{contract_path}"],
        capture_output=True,
        text=True,
        check=True,
    )
    orig_reality_lines = [line for line in res.stdout.splitlines() if "REALITY" in line]

    with open(contract_path, "r", encoding="utf-8") as f:
        curr_reality_lines = [line for line in f.read().splitlines() if "REALITY" in line]

    assert len(orig_reality_lines) > 0, f"Expected REALITY lines in {contract_path}"
    assert curr_reality_lines == orig_reality_lines, (
        f"REALITY lines in {contract_path} do not match commit 88b982d byte-for-byte!\n"
        f"Expected: {orig_reality_lines}\n"
        f"Actual: {curr_reality_lines}"
    )

def test_no_quality_blocks_in_contracts():
    """Verify that quality[] blocks have been completely migrated out of all contracts."""
    contract_files = list(Path("DataContract").glob("**/*.odcs.yaml"))
    assert len(contract_files) >= 4, "Expected at least 4 ODCS contract files"

    for path in contract_files:
        content = path.read_text(encoding="utf-8")
        assert "quality:" not in content, f"Found deprecated 'quality:' block in {path}"
