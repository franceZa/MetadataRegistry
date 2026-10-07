import subprocess
from pathlib import Path

import pytest

CONTRACTS = [
    "DataContract/cc/contract/credit_card.odcs.yaml",
    "DataContract/cc/contract/credit_card_txn.odcs.yaml",
    "DataContract/cc/contract/customer.odcs.yaml",
]

# User-approved oracle amendments (2026-10-06, H-128 F2): the calendar cutover replaced
# credit_card's "never delivered" marker and added a LATE marker to customer.
# Every other REALITY line must still match 88b982d byte-for-byte.
LATE = "  # REALITY: business_date=2026-09-11 arrives LATE (outside the normal"
AMENDED = {
    "DataContract/cc/contract/credit_card.odcs.yaml": {
        "  # REALITY: the file for business_date=2026-09-10 is never delivered.": LATE,
    },
    "DataContract/cc/contract/customer.odcs.yaml": {
        # inserted before the first column-level REALITY line
        '            "^[0-9]{13}$" # REALITY: one row per file is "123". The gate': (
            LATE,
            '            "^[0-9]{13}$" # REALITY: one row per file is "123". The gate',
        ),
    },
}


def _expected(contract_path: str, orig: list[str]) -> list[str]:
    out: list[str] = []
    for line in orig:
        new = AMENDED.get(contract_path, {}).get(line, line)
        out.extend(new if isinstance(new, tuple) else [new])
    return out


@pytest.mark.parametrize("contract_path", CONTRACTS)
def test_reality_lines_byte_for_byte(contract_path):
    """AC-17: REALITY oracle - REALITY lines match commit 88b982d plus AMENDED, byte-for-byte."""
    res = subprocess.run(
        ["git", "show", f"88b982d:{contract_path}"],
        capture_output=True,
        text=True,
        check=True,
    )
    orig_reality_lines = [line for line in res.stdout.splitlines() if "REALITY" in line]
    expected = _expected(contract_path, orig_reality_lines)

    with open(contract_path, encoding="utf-8") as f:
        curr_reality_lines = [line for line in f.read().splitlines() if "REALITY" in line]

    assert len(orig_reality_lines) > 0, f"Expected REALITY lines in {contract_path}"
    assert curr_reality_lines == expected, (
        f"REALITY lines in {contract_path} do not match 88b982d + AMENDED!\n"
        f"Expected: {expected}\n"
        f"Actual: {curr_reality_lines}"
    )


def test_no_quality_blocks_in_contracts():
    """Verify that quality[] blocks have been completely migrated out of all contracts."""
    contract_files = list(Path("DataContract").glob("**/*.odcs.yaml"))
    assert len(contract_files) >= 4, "Expected at least 4 ODCS contract files"

    for path in contract_files:
        content = path.read_text(encoding="utf-8")
        assert "quality:" not in content, f"Found deprecated 'quality:' block in {path}"
