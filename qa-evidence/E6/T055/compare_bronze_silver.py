"""T-55 evidence script: confirm bronze vs silver resolved JSON agree on
`calendar` / `reader` / `schema` for each dataset (AC-52, AC-54, AC-55).

Usage: uv run python qa-evidence/E6/T055/compare_bronze_silver.py
Exits 0 and prints OK per dataset, or exits 1 and prints the mismatching key.
"""

import json
import sys
from pathlib import Path

RESOLVED_DIR = Path("build/dev/resolved/cc")
DATASETS = ("customer", "credit_card", "credit_card_txn")
KEYS = ("calendar", "reader", "schema")


def main() -> int:
    all_ok = True
    for ds in DATASETS:
        bronze = json.loads((RESOLVED_DIR / f"bronze.cc.{ds}.resolved.json").read_text(encoding="utf-8"))
        silver = json.loads((RESOLVED_DIR / f"silver.cc.{ds}.resolved.json").read_text(encoding="utf-8"))
        for key in KEYS:
            b_bytes = json.dumps(bronze[key], sort_keys=True, ensure_ascii=False)
            s_bytes = json.dumps(silver[key], sort_keys=True, ensure_ascii=False)
            if b_bytes != s_bytes:
                print(f"[MISMATCH] {ds}.{key}: bronze != silver")
                print("  bronze:", b_bytes)
                print("  silver:", s_bytes)
                all_ok = False
            else:
                print(f"[OK] {ds}.{key}: bronze == silver (json.dumps sort_keys=True)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
