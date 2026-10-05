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


def test_register_reads_the_volume_recursively_and_matches_full_relative_path():
    """T-51 · FR-L.13/FR-L.14 · AC-50: layout v2 stores files under <source>/<file>, so the
    SQL must walk the Volume recursively and compare each file's path RELATIVE TO THE RELEASE
    ROOT (not just its basename) against manifest.files[].path — v1 (flat, no subfolder) stays
    correct because its relative path already equals its basename.
    """
    code_lines = [
        line
        for line in REG.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    ]
    code = "\n".join(code_lines)
    assert code.count("recursiveFileLookup => 'true'") == 2, "both read_files() calls must recurse"
    assert "'[^/]+$'" not in code, "no leftover basename-only extraction"
    name_lines = [line for line in code_lines if "regexp_extract(f.path" in line]
    assert len(name_lines) == 2, "guard (2) and INSERT (3) must use the same path formula"
    assert name_lines[0] == name_lines[1]
    assert "concat(:release_id, '/(.*)$')" in code


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


# ---------- T-57 · AC-58 (static/unit) — v3 `<source>/*.odcs.yaml` passes the guard ----------

V3_FILES = [  # manifest v3 files[] shape (T-56): 6 resolved + 3 odcs_contract under cc/
    *(
        f"cc/{layer}.cc.{d}.resolved.json"
        for layer in ("bronze", "silver")
        for d in ("credit_card", "credit_card_txn", "customer")
    ),
    *(f"cc/{d}.odcs.yaml" for d in ("credit_card", "credit_card_txn", "customer")),
]
RID = "mdf-0123456789ab"


def _code() -> str:
    return "\n".join(
        line
        for line in REG.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    )


def _vol_ctes() -> list[str]:
    code = _code()
    return re.findall(r"vol AS \((.*?)\n\)", code, re.S)


def test_t57_vol_cte_does_not_filter_by_file_extension():
    """Every file in the Volume (any extension) is listed — nothing restricts to .json."""
    vols = _vol_ctes()
    assert len(vols) == 2, "guard (2) and INSERT (3) each build vol"
    for vol in vols:
        assert "WHERE" not in vol.upper(), "vol must list every file, unfiltered"
        assert "pathGlobFilter" not in vol and "fileNamePattern" not in vol
        assert ".json" not in vol and ".yaml" not in vol
        assert not re.search(r"(?i)\bLIKE\b|RLIKE|endswith", vol.replace(":release_id", ""))
    code = _code()
    assert "pathGlobFilter" not in code and "'%.json'" not in code


def test_t57_manifest_schema_reads_path_and_sha256_only():
    """v3 `kind`/`source`/`dataset` are ignored by from_json — path+sha256 suffice (kind = P2)."""
    code = _code()
    assert code.count("files ARRAY<STRUCT<path: STRING, sha256: STRING>>") == 2


def _sql_name(vol_path: str) -> str:
    """Python twin of `regexp_extract(f.path, concat(:release_id, '/(.*)$'), 1)`."""
    m = re.search(re.escape(RID) + "/(.*)$", vol_path)
    return m.group(1) if m else ""


def _problems(volume: list[str]) -> list[str]:
    """Twin of guard rules 4 (missing) + 6 (extra) on names; hashes are covered live (T-44)."""
    names = {_sql_name(f"dbfs:/Volumes/dev_catalog/ops/files/releases/{RID}/{p}") for p in volume}
    listed = set(V3_FILES)
    out = [f"[TAMPERED] missing {n}" for n in sorted(listed - names)]
    out += [
        f"[TAMPERED] extra {n}"
        for n in sorted(names - listed - {"manifest.json", "validation-report.json"})
    ]
    return out


def test_t57_v3_odcs_yaml_in_source_folder_counts_as_a_manifest_file():
    sql = REG.read_text(encoding="utf-8")
    assert "regexp_extract(f.path, concat(:release_id, '/(.*)$'), 1)" in sql
    full = [*V3_FILES, "validation-report.json", "manifest.json"]
    assert _problems(full) == []
    assert _sql_name(f"/Volumes/x/{RID}/cc/customer.odcs.yaml") == "cc/customer.odcs.yaml"


def test_t57_forgetting_odcs_yaml_is_tampered_and_flat_yaml_is_extra():
    no_yaml = [p for p in V3_FILES if not p.endswith(".odcs.yaml")]
    probs = _problems([*no_yaml, "validation-report.json", "manifest.json"])
    assert probs == [
        "[TAMPERED] missing cc/credit_card.odcs.yaml",
        "[TAMPERED] missing cc/credit_card_txn.odcs.yaml",
        "[TAMPERED] missing cc/customer.odcs.yaml",
    ]
    flat = [*no_yaml, "customer.odcs.yaml", "validation-report.json", "manifest.json"]
    assert "[TAMPERED] extra customer.odcs.yaml" in _problems(flat)
