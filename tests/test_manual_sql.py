"""T-44 · FR-L.13 / AC-44: static checks for the mode-manual SQL (sql/manual/*.sql).

The live behaviour (tamper / missing / extra / no manifest / wrong id / rerun / activate before
register) is exercised on the real workspace in qa-evidence/E6/T044 and T-46.
"""

import re
from pathlib import Path

import pytest

REG = Path("sql/manual/register_release.sql")
ACT = Path("sql/manual/activate_release.sql")
ID_CHECK = "RLIKE '^mdf-[0-9a-f]{12}$'"


def _statements(path: Path) -> list[str]:
    body = "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    )
    return [s.strip() for s in body.split(";") if s.strip()]


@pytest.mark.parametrize("path", [REG, ACT])
def test_only_named_parameter_no_string_building_from_input(path):
    sql = path.read_text(encoding="utf-8")
    assert ":release_id" in sql
    assert "${" not in sql and "{release_id}" not in sql
    assert ID_CHECK in sql


@pytest.mark.parametrize("path", [REG, ACT])
def test_only_insert_into_the_registry_no_update_delete(path):
    for stmt in _statements(path):
        assert not re.match(r"(?is)^(UPDATE|DELETE|MERGE|TRUNCATE|DROP|ALTER)\b", stmt)
        if re.match(r"(?is)^INSERT\b", stmt):
            assert stmt.startswith("INSERT INTO dev_catalog.ops.release_registry")
            assert "'manual-ui'" in stmt


def test_register_guards_come_before_insert_and_are_repeated_inside_it():
    stmts = _statements(REG)
    kinds = ["INSERT" if s.startswith("INSERT") else "SELECT" for s in stmts]
    assert kinds == ["SELECT", "SELECT", "INSERT", "SELECT"]
    fmt, guard, insert = stmts[0], stmts[1], stmts[2]
    assert ID_CHECK in fmt and "raise_error" in fmt and "read_files" not in fmt
    for code in (
        "RELEASE_NOT_FOUND",
        "RELEASE_ID_MISMATCH",
        "PREVIEW_PACKAGE",
        "TAMPERED",
        "HASH_CONFLICT",
    ):
        assert f"[{code}]" in guard, code
    assert "raise_error" in guard
    # the INSERT re-checks every condition on its own (safe if run alone)
    assert ID_CHECK in insert
    assert "sha2(f.content, 256)" in insert
    assert "validation_report_sha256" in insert
    assert "LEFT ANTI JOIN" in insert
    assert "event = 'REGISTERED'" in insert and "NOT EXISTS" in insert


def test_register_hashes_files_the_same_way_as_the_job():
    sql = REG.read_text(encoding="utf-8")
    assert sql.count("format => 'binaryFile'") == 2
    assert "sha2(f.content, 256)" in sql
    assert "'manifest.json', 'validation-report.json'" in sql


def test_activate_requires_registered_and_skips_when_already_active():
    stmts = _statements(ACT)
    guard, insert, result = stmts
    assert "[NOT_REGISTERED]" in guard and "raise_error" in guard
    assert "event = 'REGISTERED'" in insert
    assert "max_by(release_id, event_ts)" in insert and "<> :release_id" in insert
    assert "active_release_id" in result


@pytest.mark.parametrize("path", [REG, ACT])
def test_result_shows_manifest_sha256(path):
    assert "manifest_sha256" in _statements(path)[-1]
