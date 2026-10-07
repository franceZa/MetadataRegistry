"""T-58: six SLA entries, one reader/validator, seven resolved keys."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from mdf.calendar import CALENDAR_FIELDS, compiled_calendar
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


def _sla(**values):
    return {
        "slaProperties": [
            {
                "property": key,
                "value": value,
                **(
                    {"unit": "h"}
                    if key == "latency"
                    else {"unit": "d"}
                    if key == "recovery_window"
                    else {}
                ),
            }
            for key, value in values.items()
        ]
    }


def test_authoring_has_exact_six_keys_and_unknown_owner_nulls():
    paths = [ROOT / "DataContract/_template/contract/my_dataset.odcs.yaml"]
    paths += sorted((ROOT / "DataContract/cc/contract").glob("*.odcs.yaml"))
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        entries = data["slaProperties"]
        assert [p["property"] for p in entries] == list(CALENDAR_FIELDS)
        calendar, missing, errors = compiled_calendar(data)
        assert errors == []
        assert calendar["missing_after_seconds"] == 14400
        # owner values pass through as-is (null -> null); only the template must stay blank
        sla = {p["property"]: p.get("value") for p in entries}
        for key in ("schedule_type", "day_of_month", "expected_at", "business_date_lag"):
            assert calendar[key] == sla[key]
        if "_template" in path.parts:
            assert calendar["status"] == "PENDING_OWNER"
            owner_keys = ("schedule_type", "expected_at", "business_date_lag")
            assert all(sla[k] is None for k in owner_keys)
            assert calendar["recovery_window_seconds"] is None
        else:
            assert calendar["recovery_window_seconds"] == 172800


@pytest.mark.parametrize(
    "key,value,unit",
    [
        ("schedule_type", "explicit_dates", None),
        ("schedule_type", {}, None),
        ("expected_at", "25:00", None),
        ("expected_at", "06:30\n", None),
        ("day_of_month", True, None),
        ("day_of_month", 32, None),
        ("business_date_lag", 1, None),
        ("business_date_lag", -1.5, None),
        ("business_date_lag", True, None),
        ("latency", -1, "h"),
        ("latency", float("nan"), "h"),
        ("latency", float("inf"), "h"),
        ("recovery_window", False, "d"),
        ("recovery_window", "2", "d"),
        ("recovery_window", {}, "d"),
        ("recovery_window", 2, "m"),
    ],
)
def test_non_null_format_mismatch_reports_one_thai_error(key, value, unit):
    _, _, errors = compiled_calendar(
        {
            "slaProperties": [
                {"property": key, "value": value, "unit": unit},
            ]
        }
    )
    assert len(errors) == 1
    field, message, fix = errors[0]
    assert field == "slaProperties." + key
    assert "ต้อง" in message
    assert "กำหนด" in fix


def test_null_sla_fields_are_pending_with_exact_seven_key_output():
    contract = {
        "slaProperties": [
            {"property": "schedule_type", "value": None},
            {"property": "latency", "value": 4, "unit": "h"},
            {"property": "recovery_window", "value": 2, "unit": "d"},
        ]
    }
    calendar, missing, errors = compiled_calendar(contract)
    assert calendar == {
        "status": "PENDING_OWNER",
        "schedule_type": None,
        "day_of_month": None,
        "expected_at": None,
        "business_date_lag": None,
        "missing_after_seconds": 14400,
        "recovery_window_seconds": 172800,
    }
    assert missing == ["schedule_type", "expected_at", "business_date_lag"]
    assert errors == []


@pytest.mark.parametrize(
    "key",
    [
        "timezone",
        "expected_day_offset",
        "business_date_lag",
        "business_schedule",
        "expected_at",
        "recovery_window",
        "schedule_type",
        "day_of_month",
    ],
)
def test_legacy_custom_key_even_null_is_an_actionable_error(key):
    _, _, errors = compiled_calendar({"customProperties": [{"property": key, "value": None}]})
    assert errors == [
        ("customProperties." + key, f"'{key}' ต้องอยู่ใน slaProperties", "ย้ายไป slaProperties")
    ]


@pytest.mark.parametrize(
    "key,value,unit",
    [
        ("schedule_type", "daily", None),
        ("schedule_type", "workday", None),
        ("schedule_type", "workday_excluding_holidays", None),
        ("schedule_type", "monthly", None),
        ("day_of_month", 1, None),
        ("day_of_month", 31, None),
        ("business_date_lag", 0, None),
        ("business_date_lag", -1, None),
        ("business_date_lag", -10, None),
        ("expected_at", "00:00", None),
        ("expected_at", "23:59", None),
        ("latency", 0, "h"),
        ("latency", 1.5, "d"),
        ("recovery_window", 0.5, "h"),
    ],
)
def test_per_kind_good_values(key, value, unit):
    _, _, errors = compiled_calendar(
        {"slaProperties": [{"property": key, "value": value, "unit": unit}]}
    )
    assert errors == []


def test_absent_and_explicit_null_are_equal_even_with_unused_units():
    assert compiled_calendar({}) == compiled_calendar(_sla(**dict.fromkeys(CALENDAR_FIELDS)))


def test_unknown_sla_is_ignored_and_no_duplicate_collision_rules():
    unknown = {"property": "frequency", "value": {"arbitrary": "metadata"}}
    assert compiled_calendar({"slaProperties": [unknown, unknown]}) == compiled_calendar({})
    calendar, _, errors = compiled_calendar(
        {
            "slaProperties": [
                {"property": "expected_at", "value": "06:30"},
                {"property": "expected_at", "value": "07:45"},
            ]
        }
    )
    assert calendar["expected_at"] == "07:45"
    assert errors == []


def test_no_cross_field_or_holiday_requirements():
    data = _sla(
        schedule_type="workday_excluding_holidays",
        expected_at="06:30",
        business_date_lag=0,
        latency=30,
        recovery_window=0,
    )
    calendar, missing, errors = compiled_calendar(data)
    assert calendar["status"] == "COMPLETE"
    assert missing == errors == []


def test_monthly_null_day_is_pending_not_invalid():
    data = _sla(
        schedule_type="monthly", expected_at="06:30", business_date_lag=0, recovery_window=3
    )
    calendar, missing, errors = compiled_calendar(data)
    assert calendar["status"] == "PENDING_OWNER"
    assert missing == ["day_of_month"]
    assert errors == []


@pytest.mark.parametrize("mode", ["daily", "workday", "workday_excluding_holidays", "monthly"])
def test_complete_contract_nondefault_seconds_and_layer_equality(project, mode):
    path = project / CONTRACT_REL
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(
        _sla(
            schedule_type=mode,
            day_of_month=31 if mode == "monthly" else None,
            expected_at="06:30",
            business_date_lag=-1,
            latency=30,
            recovery_window=3,
        )
    )
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    report = validate_project()
    assert report.is_valid
    assert not any(
        w.code == "CALENDAR_PENDING_OWNER" and "credit_card.odcs.yaml" in w.file_path
        for w in report.warnings
    )
    calendar, missing, errors = compiled_calendar(data)
    assert calendar["status"] == "COMPLETE"
    assert calendar["missing_after_seconds"] == 108000
    assert calendar["recovery_window_seconds"] == 259200
    assert missing == errors == []
    written = compile_project(env="dev")
    by_name = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in written}
    assert by_name["bronze.cc.credit_card.resolved.json"]["calendar"] == calendar
    assert by_name["silver.cc.credit_card.resolved.json"]["calendar"] == calendar


@pytest.mark.parametrize(
    "key,value,unit",
    [
        ("schedule_type", "explicit_dates", None),
        ("expected_at", "25:00", None),
        ("day_of_month", True, None),
        ("business_date_lag", 1, None),
        ("latency", -1, "h"),
        ("recovery_window", 2, "minutes"),
    ],
)
def test_invalid_cli_reports_field_fix_and_compile_writes_nothing(
    project, capsys, key, value, unit
):
    path = project / CONTRACT_REL
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for entry in data["slaProperties"]:
        if entry["property"] == key:
            entry.update(value=value, unit=unit)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert main(["validate"]) == 1
    out = capsys.readouterr().out
    assert "CALENDAR_INVALID" in out
    assert "credit_card.odcs.yaml" in out
    assert "slaProperties." + key in out
    assert "กำหนด" in out
    with pytest.raises(RuntimeError, match="CALENDAR_INVALID"):
        compile_project(env="dev")
    assert not (project / "build").exists()


def test_new_field_needs_only_table_line_and_contract_entry(monkeypatch):
    # The whole extension: one table line plus one contract entry. No mapper/checker edits.
    monkeypatch.setitem(CALENDAR_FIELDS, "future_offset", "int")
    contract = {"slaProperties": [{"property": "future_offset", "value": 2}]}
    calendar, _, errors = compiled_calendar(contract)
    assert calendar["future_offset"] == 2
    assert errors == []
    contract["slaProperties"][0]["value"] = -1
    assert compiled_calendar(contract)[2][0][0] == "slaProperties.future_offset"


def test_old_expected_day_offset_in_sla_is_ignored_and_lag_is_pending():
    calendar, missing, errors = compiled_calendar(
        {"slaProperties": [{"property": "expected_day_offset", "value": 1}]}
    )
    assert "expected_day_offset" not in calendar
    assert calendar["business_date_lag"] is None
    assert "business_date_lag" in missing
    assert errors == []
