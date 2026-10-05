"""T-54 — calendar parser + validator (FR-M.1, FR-M.2, FR-M.4 · AC-53, AC-54).

AC-53's 12 malformed cases are each a parametrized sub-test; every one must make
`mdf validate` exit 1 with a Thai field/fix message, and `compile_project` must
abort without writing anything. All mutate a copy of the real `cc` DataContract
in tmp_path (never the committed DataContract/**, per H-109 constraint #5).
"""

import shutil
from pathlib import Path

import pytest
import yaml

from mdf.cli import main
from mdf.compile import compile_project
from mdf.validation import validate_project

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = "DataContract/cc/contract/credit_card.odcs.yaml"


@pytest.fixture()
def project(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "DataContract", tmp_path / "DataContract")
    shutil.copytree(ROOT / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _load_contract(project: Path) -> dict:
    return yaml.safe_load((project / CONTRACT_REL).read_text(encoding="utf-8"))


def _save_contract(project: Path, data: dict) -> None:
    (project / CONTRACT_REL).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _set_custom(contract: dict, prop: str, value) -> None:
    props = [cp for cp in contract.get("customProperties", []) if cp.get("property") != prop]
    props.append({"property": prop, "value": value})
    contract["customProperties"] = props


def _set_sla(contract: dict, prop: str, value, unit: str | None = None) -> None:
    props = [sp for sp in contract.get("slaProperties", []) if sp.get("property") != prop]
    entry = {"property": prop, "value": value}
    if unit is not None:
        entry["unit"] = unit
    props.append(entry)
    contract["slaProperties"] = props


_VALID_SCHEDULE = {
    "type": "daily",
    "effective_from": "2026-01-01",
    "effective_to": "2026-12-31",
    "holidays": ["2026-01-01"],
    "explicit_dates": [],
}


def _mut_timezone_not_string(c):
    _set_custom(c, "timezone", 123)


def _mut_timezone_empty(c):
    _set_custom(c, "timezone", "   ")


def _mut_expected_at_bad(c):
    _set_sla(c, "expected_at", "25:00")


def _mut_expected_day_offset_negative(c):
    _set_custom(c, "expected_day_offset", -1)


def _mut_holiday_duplicate(c):
    sched = dict(_VALID_SCHEDULE)
    sched["holidays"] = ["2026-01-01", "2026-01-01"]
    _set_custom(c, "business_schedule", sched)


def _mut_date_not_iso(c):
    sched = dict(_VALID_SCHEDULE)
    sched["holidays"] = ["2026/01/01"]
    _set_custom(c, "business_schedule", sched)


def _mut_effective_to_before_from(c):
    sched = dict(_VALID_SCHEDULE)
    sched["effective_from"] = "2026-02-01"
    sched["effective_to"] = "2026-01-01"
    _set_custom(c, "business_schedule", sched)


def _mut_day_of_month_32(c):
    sched = dict(_VALID_SCHEDULE)
    sched["type"] = "day_of_month"
    sched["day_of_month"] = 32
    sched["day_of_month_policy"] = "last_business_day"
    _set_custom(c, "business_schedule", sched)


def _mut_day_of_month_missing_policy(c):
    sched = dict(_VALID_SCHEDULE)
    sched["type"] = "day_of_month"
    sched["day_of_month"] = 15
    _set_custom(c, "business_schedule", sched)


def _mut_explicit_dates_empty(c):
    sched = dict(_VALID_SCHEDULE)
    sched["type"] = "explicit_dates"
    sched["explicit_dates"] = []
    _set_custom(c, "business_schedule", sched)


def _mut_type_outside_enum(c):
    sched = dict(_VALID_SCHEDULE)
    sched["type"] = "weekly"
    _set_custom(c, "business_schedule", sched)


def _mut_recovery_window_lt_latency(c):
    # credit_card.odcs.yaml already has latency: 4 unit: h (slaProperties)
    _set_sla(c, "recovery_window", 2, unit="h")


def _mut_unit_invalid(c):
    _set_sla(c, "recovery_window", 2, unit="m")


AC53_CASES = [
    ("timezone_not_string", _mut_timezone_not_string, "timezone"),
    ("timezone_empty", _mut_timezone_empty, "timezone"),
    ("expected_at_bad", _mut_expected_at_bad, "expected_at"),
    ("expected_day_offset_negative", _mut_expected_day_offset_negative, "expected_day_offset"),
    ("holiday_duplicate", _mut_holiday_duplicate, "holidays"),
    ("date_not_iso", _mut_date_not_iso, "holidays"),
    ("effective_to_before_from", _mut_effective_to_before_from, "effective_to"),
    ("day_of_month_32", _mut_day_of_month_32, "day_of_month"),
    ("day_of_month_missing_policy", _mut_day_of_month_missing_policy, "day_of_month_policy"),
    ("explicit_dates_empty", _mut_explicit_dates_empty, "explicit_dates"),
    ("type_outside_enum", _mut_type_outside_enum, "type"),
    ("recovery_window_lt_latency", _mut_recovery_window_lt_latency, "recovery_window"),
    ("unit_invalid", _mut_unit_invalid, "recovery_window"),
]


@pytest.mark.parametrize(
    "case_id,mutate,field_substr", AC53_CASES, ids=[c[0] for c in AC53_CASES]
)
def test_ac53_malformed_calendar_fails_validate_and_compile(
    project, case_id, mutate, field_substr, capsys
):
    contract = _load_contract(project)
    mutate(contract)
    _save_contract(project, contract)

    report = validate_project()
    assert report.is_valid is False
    codes = [i.code for i in report.errors]
    assert "CALENDAR_INVALID" in codes
    err = next(
        i for i in report.errors if i.code == "CALENDAR_INVALID" and field_substr in (i.field or "")
    )
    assert err.fix  # NFR-7: every error carries a Thai fix

    assert main(["validate"]) == 1
    out = capsys.readouterr().out
    assert "CALENDAR_INVALID" in out
    assert field_substr in out

    with pytest.raises(RuntimeError):
        compile_project()
    assert not (project / "build").exists()


def test_ac54_real_cc_contracts_pass_with_three_pending_owner_warnings(project, capsys):
    """AC-54: the real cc contracts (no calendar fields yet) validate OK with warnings."""
    report = validate_project()
    assert report.is_valid is True
    warn_codes = [w.code for w in report.warnings]
    assert warn_codes.count("CALENDAR_PENDING_OWNER") == 3

    assert main(["validate"]) == 0
    out = capsys.readouterr().out
    assert out.count("CALENDAR_PENDING_OWNER") == 3
    assert "expected_at" in out and "timezone" in out


def test_r29_bogus_iana_timezone_name_passes_validate(project):
    """R-29 / OQ-TRI-12a: no IANA check — a made-up zone name like 'Asia/Bangkokk' passes."""
    contract = _load_contract(project)
    _set_custom(contract, "timezone", "Asia/Bangkokk")
    _save_contract(project, contract)

    report = validate_project()
    assert report.is_valid is True
    codes = [i.code for i in report.issues]
    assert "CALENDAR_INVALID" not in codes


def test_complete_and_correct_calendar_has_no_warning_for_that_dataset(project):
    """A contract with every calendar field present and valid gets no PENDING_OWNER warning."""
    contract = _load_contract(project)
    _set_custom(contract, "timezone", "Asia/Bangkok")
    _set_custom(contract, "expected_day_offset", 0)
    _set_custom(contract, "business_schedule", dict(_VALID_SCHEDULE))
    _set_sla(contract, "expected_at", "06:30")
    _set_sla(contract, "recovery_window", 8, unit="h")
    _save_contract(project, contract)

    report = validate_project()
    assert report.is_valid is True
    cc_warnings = [
        w
        for w in report.warnings
        if w.code == "CALENDAR_PENDING_OWNER" and "credit_card.odcs.yaml" in w.file_path
    ]
    assert cc_warnings == []


def test_ac52_compiled_calendar_complete_status_and_sorted_lists(project):
    """AC-52 (T-55): a contract with every calendar field present compiles `calendar.status`
    = COMPLETE, `missing_after_seconds`/`recovery_window_seconds` derived from slaProperties
    (not hardcoded), and bronze/silver get byte-identical `calendar` for that dataset.
    """
    import json

    from mdf.calendar import compiled_calendar

    contract = _load_contract(project)
    _set_custom(contract, "timezone", "Asia/Bangkok")
    _set_custom(contract, "expected_day_offset", 0)
    schedule = dict(_VALID_SCHEDULE)
    schedule["holidays"] = sorted(["2026-01-01", "2026-04-13"])  # must already be sorted
    _set_custom(contract, "business_schedule", schedule)
    _set_sla(contract, "expected_at", "06:30")
    _set_sla(contract, "recovery_window", 2, unit="d")
    _save_contract(project, contract)

    calendar = compiled_calendar(contract)
    assert calendar["status"] == "COMPLETE"
    assert calendar["missing_after_seconds"] == 14400  # latency 4h * 3600, not hardcoded
    assert calendar["recovery_window_seconds"] == 172800  # recovery_window 2d * 86400
    assert calendar["holidays"] == sorted(calendar["holidays"])
    assert calendar["schedule_type"] == "daily"

    written = compile_project(env="dev")
    by_name = {p.name: p for p in written}
    bronze = json.loads(
        by_name["bronze.cc.credit_card.resolved.json"].read_text(encoding="utf-8")
    )
    silver = json.loads(
        by_name["silver.cc.credit_card.resolved.json"].read_text(encoding="utf-8")
    )
    assert json.dumps(bronze["calendar"], sort_keys=True) == json.dumps(
        silver["calendar"], sort_keys=True
    )
    assert bronze["calendar"]["status"] == "COMPLETE"
