"""T-37 static checks for sql/bootstrap/ops.sql (FR-J.3 Phase 2 part, AC-40)."""

import re
from pathlib import Path

SQL = Path("sql/bootstrap/ops.sql")

REGISTRY_COLUMNS = [
    "release_id",
    "event",
    "source_commit",
    "manifest_sha256",
    "file_count",
    "volume_path",
    "github_release_url",
    "ci_run_url",
    "actor",
    "event_ts",
]


def _statements() -> list[str]:
    body = "\n".join(
        line for line in SQL.read_text(encoding="utf-8").splitlines() if not line.startswith("--")
    )
    return [s.strip() for s in body.split(";") if s.strip()]


def test_three_statements_all_idempotent():
    stmts = _statements()
    assert len(stmts) == 3
    for s in stmts:
        assert re.match(r"CREATE (SCHEMA|VOLUME|TABLE) IF NOT EXISTS ", s), s[:60]


def test_catalog_is_parameter_not_hardcoded():
    raw = SQL.read_text(encoding="utf-8")
    assert "dev_catalog" not in raw
    for s in _statements():
        assert "${catalog}.ops" in s


def test_registry_is_append_only_delta():
    table = next(s for s in _statements() if "release_registry" in s)
    assert "USING DELTA" in table
    assert "'delta.appendOnly' = 'true'" in table


def test_registry_has_ssot_columns_in_order():
    table = next(s for s in _statements() if "release_registry" in s)
    cols = re.findall(r"^\s{2}([a-z][a-z0-9_]*)\s+[A-Z]+", table, flags=re.M)
    assert cols == REGISTRY_COLUMNS


def test_no_destructive_statements():
    raw = SQL.read_text(encoding="utf-8").upper()
    for word in ("DROP ", "DELETE ", "UPDATE ", "TRUNCATE ", "OR REPLACE"):
        assert word not in raw
