"""T-54 -- single calendar parser (FR-M.1, FR-M.2, FR-M.4).

`read_calendar()` is the ONE place that reads ODCS calendar fields
(`slaProperties.expected_at`/`recovery_window`,
`customProperties.timezone`/`expected_day_offset`/`business_schedule`).
T-55's `mdf compile` must call this same function -- do not re-parse these
fields anywhere else (HRM correction #6, H-109).

"missing" (key absent) is a warning (`[CALENDAR_PENDING_OWNER]`, FR-M.4).
"errors" (key present but malformed) always fails validation (FR-M.2).

OQ-TRI-12a (closed): no IANA timezone check -- `timezone` only needs to be a
non-empty `str`. Do not import `zoneinfo`/`tzdata`, do not add an allowlist.
"""

import re
from datetime import date
from typing import Any

_MISSING = object()
_SCHEDULE_TYPES = {
    "daily",
    "workday",
    "workday_excluding_holidays",
    "day_of_month",
    "explicit_dates",
}
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CalendarError = tuple[str, str, str]  # (field, message_thai, fix_thai)


def _sla_entry(contract: dict[str, Any], prop: str) -> dict[str, Any] | None:
    for item in contract.get("slaProperties", []) or []:
        if isinstance(item, dict) and item.get("property") == prop:
            return item
    return None


def _custom_value(contract: dict[str, Any], prop: str) -> Any:
    for item in contract.get("customProperties", []) or []:
        if isinstance(item, dict) and item.get("property") == prop:
            return item.get("value")
    return _MISSING


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _duration_seconds(
    entry: dict[str, Any], field: str, errors: list[CalendarError]
) -> int | None:
    """Convert an sla entry {value, unit: h|d} to seconds; appends error if unit is bad."""
    unit = entry.get("unit")
    value = entry.get("value")
    if unit not in ("h", "d") or not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(
            (
                field,
                f"'{field}' ต้องมี unit เป็น 'h' หรือ 'd' และ value เป็นตัวเลข "
                f"(ได้ unit={unit!r}, value={value!r})",
                "กำหนด unit: h หรือ unit: d พร้อม value เป็นตัวเลข",
            )
        )
        return None
    return int(value * (3600 if unit == "h" else 86400))


def _check_timezone(
    contract: dict[str, Any], missing: list[str], errors: list[CalendarError]
) -> str | None:
    value = _custom_value(contract, "timezone")
    if value is _MISSING:
        missing.append("timezone")
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(
            (
                "timezone",
                f"'timezone' ต้องเป็น string ไม่ว่าง (ได้ {value!r}) — ไม่ตรวจชื่อ IANA จริง "
                "ผู้เขียน contract ต้องใส่ให้ถูกเอง",
                "กำหนด timezone เป็น string ที่ไม่ว่าง เช่น timezone: Asia/Bangkok",
            )
        )
        return None
    return value


def _check_expected_at(
    contract: dict[str, Any], missing: list[str], errors: list[CalendarError]
) -> str | None:
    entry = _sla_entry(contract, "expected_at")
    if entry is None:
        missing.append("expected_at")
        return None
    value = entry.get("value")
    if not isinstance(value, str) or not _TIME_RE.match(value):
        errors.append(
            (
                "expected_at",
                f"'expected_at' ต้องเป็นเวลารูปแบบ HH:MM ช่วง 00:00–23:59 (ได้ {value!r})",
                'กำหนด expected_at เป็น string รูปแบบ HH:MM เช่น "06:30"',
            )
        )
        return None
    return value


def _check_expected_day_offset(
    contract: dict[str, Any], missing: list[str], errors: list[CalendarError]
) -> int | None:
    value = _custom_value(contract, "expected_day_offset")
    if value is _MISSING:
        missing.append("expected_day_offset")
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(
            (
                "expected_day_offset",
                f"'expected_day_offset' ต้องเป็นจำนวนเต็ม >= 0 (ได้ {value!r})",
                "กำหนด expected_day_offset เป็นจำนวนเต็ม >= 0 เช่น 0 หรือ 1",
            )
        )
        return None
    return value


def _check_recovery_window(
    contract: dict[str, Any],
    missing: list[str],
    errors: list[CalendarError],
    latency_seconds: int | None,
) -> int | None:
    entry = _sla_entry(contract, "recovery_window")
    if entry is None:
        missing.append("recovery_window")
        return None
    recovery_seconds = _duration_seconds(entry, "recovery_window", errors)
    too_short = (
        recovery_seconds is not None
        and latency_seconds is not None
        and recovery_seconds < latency_seconds
    )
    if too_short:
        errors.append(
            (
                "recovery_window",
                f"'recovery_window' ({recovery_seconds}s) ต้องไม่น้อยกว่า "
                f"'latency' ({latency_seconds}s)",
                "เพิ่มค่า recovery_window ให้ >= latency หรือลด latency",
            )
        )
        return None
    return recovery_seconds


def _check_date_list(
    values: Any, field: str, errors: list[CalendarError], check_duplicate: bool = True
) -> list[str]:
    """Validate a list of YYYY-MM-DD date strings; returns the sorted, de-duplicated list."""
    if not isinstance(values, list):
        return []
    seen: set[str] = set()
    for v in values:
        if _parse_date(v) is None:
            errors.append(
                (
                    field,
                    f"'{field}' มีค่า {v!r} ที่ไม่ใช่วันที่รูปแบบ YYYY-MM-DD",
                    "แก้วันที่ให้เป็นรูปแบบ YYYY-MM-DD",
                )
            )
            continue
        if check_duplicate and v in seen:
            errors.append(
                (field, f"'{field}' มีวันที่ซ้ำกัน: {v!r}", f"ลบรายการ {v!r} ที่ซ้ำใน {field}")
            )
            continue
        seen.add(v)
    return sorted(seen)


def _check_schedule_type(sched_type: Any, errors: list[CalendarError]) -> None:
    if sched_type not in _SCHEDULE_TYPES:
        errors.append(
            (
                "business_schedule.type",
                f"'type' ต้องเป็นหนึ่งใน {sorted(_SCHEDULE_TYPES)} (ได้ {sched_type!r})",
                "กำหนด type ให้ตรงกับประเภทตารางที่รองรับ",
            )
        )


def _check_schedule_date_range(from_date: Any, to_date: Any, errors: list[CalendarError]) -> None:
    if _parse_date(from_date) is None:
        errors.append(
            (
                "business_schedule.effective_from",
                f"'effective_from' ต้องเป็นวันที่ YYYY-MM-DD (ได้ {from_date!r})",
                "กำหนด effective_from เป็นวันที่รูปแบบ YYYY-MM-DD",
            )
        )
        return
    if to_date is None:
        return
    if _parse_date(to_date) is None:
        errors.append(
            (
                "business_schedule.effective_to",
                f"'effective_to' ต้องเป็นวันที่ YYYY-MM-DD (ได้ {to_date!r})",
                "กำหนด effective_to เป็นวันที่รูปแบบ YYYY-MM-DD",
            )
        )
    elif _parse_date(to_date) < _parse_date(from_date):
        errors.append(
            (
                "business_schedule.effective_to",
                f"'effective_to' ({to_date}) ต้องไม่น้อยกว่า 'effective_from' ({from_date})",
                "แก้ effective_to ให้ไม่น้อยกว่า effective_from",
            )
        )


def _check_day_of_month(
    sched_type: Any,
    day_of_month: Any,
    day_of_month_policy: Any,
    errors: list[CalendarError],
) -> None:
    if sched_type != "day_of_month":
        return
    valid_dom = (
        not isinstance(day_of_month, bool)
        and isinstance(day_of_month, int)
        and 1 <= day_of_month <= 31
    )
    if not valid_dom:
        errors.append(
            (
                "business_schedule.day_of_month",
                f"'day_of_month' ต้องเป็นจำนวนเต็ม 1–31 (ได้ {day_of_month!r})",
                "กำหนด day_of_month เป็นจำนวนเต็มช่วง 1–31",
            )
        )
    if not day_of_month_policy:
        errors.append(
            (
                "business_schedule.day_of_month_policy",
                "type เป็น 'day_of_month' แต่ไม่มี 'day_of_month_policy'",
                "เพิ่ม day_of_month_policy เช่น last_business_day",
            )
        )


def _check_business_schedule(
    contract: dict[str, Any], missing: list[str], errors: list[CalendarError]
) -> dict[str, Any] | None:
    value = _custom_value(contract, "business_schedule")
    if value is _MISSING:
        missing.append("business_schedule")
        return None
    if not isinstance(value, dict):
        errors.append(
            (
                "business_schedule",
                "'business_schedule' ต้องเป็น object",
                "กำหนด business_schedule เป็น object ตามรูปแบบ ODCS",
            )
        )
        return None

    sched_type = value.get("type")
    from_date = value.get("effective_from")
    to_date = value.get("effective_to")
    _check_schedule_type(sched_type, errors)
    _check_schedule_date_range(from_date, to_date, errors)

    holidays = _check_date_list(value.get("holidays", []), "business_schedule.holidays", errors)
    explicit_dates = _check_date_list(
        value.get("explicit_dates", []), "business_schedule.explicit_dates", errors
    )
    if sched_type == "explicit_dates" and not explicit_dates:
        errors.append(
            (
                "business_schedule.explicit_dates",
                "type เป็น 'explicit_dates' แต่ 'explicit_dates' ว่างหรือไม่มี",
                "เพิ่มรายการวันที่ลงใน explicit_dates",
            )
        )

    day_of_month = value.get("day_of_month")
    day_of_month_policy = value.get("day_of_month_policy")
    _check_day_of_month(sched_type, day_of_month, day_of_month_policy, errors)

    return {
        "type": sched_type,
        "effective_from": from_date,
        "effective_to": to_date,
        "holidays": holidays,
        "explicit_dates": explicit_dates,
        "exceptions": value.get("exceptions", []) or [],
        "day_of_month": day_of_month,
        "day_of_month_policy": day_of_month_policy,
    }


def read_calendar(
    contract: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[CalendarError]]:
    """Parse ODCS calendar fields (FR-M.1). Returns (calendar, missing, errors).

    - calendar: parsed values (None where missing or unparsable)
    - missing: top-level field names entirely absent (-> warning, FR-M.4)
    - errors: (field, message, fix) for values present but malformed (-> error, FR-M.2)
    """
    missing: list[str] = []
    errors: list[CalendarError] = []

    latency_entry = _sla_entry(contract, "latency")
    latency_seconds = (
        _duration_seconds(latency_entry, "latency", errors) if latency_entry else None
    )

    timezone = _check_timezone(contract, missing, errors)
    expected_at = _check_expected_at(contract, missing, errors)
    expected_day_offset = _check_expected_day_offset(contract, missing, errors)
    recovery_window_seconds = _check_recovery_window(contract, missing, errors, latency_seconds)
    business_schedule = _check_business_schedule(contract, missing, errors)

    calendar = {
        "timezone": timezone,
        "expected_at": expected_at,
        "expected_day_offset": expected_day_offset,
        "business_schedule": business_schedule,
        "missing_after_seconds": latency_seconds,
        "recovery_window_seconds": recovery_window_seconds,
    }
    return calendar, missing, errors


# ---------------------------------------------------------------------------
# T-55 additions (FR-M.3, FR-M.5, FR-M.6, FR-M.11) -- kept in this module so
# compile.py, validation.py and diff.py share one parser / one shared
# accessor (HRM correction #1/#6, H-111).
# ---------------------------------------------------------------------------


def custom_property(obj: dict[str, Any], prop: str) -> Any:
    """Return the `value` of a `customProperties` entry, or None if absent.

    Works on any ODCS object that carries its own `customProperties` list:
    the contract root, a `schema[].properties[]` column, etc. (T-55).
    """
    for item in obj.get("customProperties", []) or []:
        if isinstance(item, dict) and item.get("property") == prop:
            return item.get("value")
    return None


def has_custom_property(obj: dict[str, Any], prop: str) -> bool:
    """True if a `customProperties` entry named `prop` exists (even if its value is None)."""
    return any(
        isinstance(item, dict) and item.get("property") == prop
        for item in obj.get("customProperties", []) or []
    )


def compiled_calendar(contract: dict[str, Any]) -> dict[str, Any]:
    """FR-M.3: the ONE flat `calendar` object compiled into bronze AND silver resolved JSON.

    Wraps `read_calendar()` (T-54) and reshapes it to the flat key set required by
    runtime: `status`, `schedule_type`, `timezone`, `expected_at`, `expected_day_offset`,
    `effective_from`, `effective_to`, `holidays`, `explicit_dates`, `exceptions`,
    `day_of_month`, `day_of_month_policy`, `missing_after_seconds`,
    `recovery_window_seconds`, `frequency`.

    Values that are missing/unparsable are `null`; list fields default to `[]`.
    `status` is `PENDING_OWNER` whenever `read_calendar()` reports any missing field,
    else `COMPLETE` (FR-M.4). `mdf compile` and `mdf diff` (FR-M.11) must both call this
    function rather than re-deriving the flat shape themselves -- it must be byte-identical
    between bronze and silver of the same dataset.

    Must only be called on a contract that already passed validation (no CALENDAR_INVALID
    errors) -- malformed values are not re-checked here.
    """
    calendar, missing, _errors = read_calendar(contract)
    schedule = calendar.get("business_schedule") or {}

    frequency_entry = _sla_entry(contract, "frequency")
    frequency = frequency_entry.get("value") if frequency_entry else None

    return {
        "status": "PENDING_OWNER" if missing else "COMPLETE",
        "schedule_type": schedule.get("type"),
        "timezone": calendar.get("timezone"),
        "expected_at": calendar.get("expected_at"),
        "expected_day_offset": calendar.get("expected_day_offset"),
        "effective_from": schedule.get("effective_from"),
        "effective_to": schedule.get("effective_to"),
        "holidays": schedule.get("holidays") or [],
        "explicit_dates": schedule.get("explicit_dates") or [],
        "exceptions": schedule.get("exceptions") or [],
        "day_of_month": schedule.get("day_of_month"),
        "day_of_month_policy": schedule.get("day_of_month_policy"),
        "missing_after_seconds": calendar.get("missing_after_seconds"),
        "recovery_window_seconds": calendar.get("recovery_window_seconds"),
        "frequency": frequency,
    }
