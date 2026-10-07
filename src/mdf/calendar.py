"""One SLA calendar reader shared by validation, compile, diff and package."""

import math
import re
from typing import Any


def _choice(key: str, value: Any, unit: Any) -> str | None:
    choices = ("daily", "workday", "workday_excluding_holidays", "monthly")
    return None if isinstance(value, str) and value in choices else "หนึ่งใน " + " | ".join(choices)


def _hh_mm(key: str, value: Any, unit: Any) -> str | None:
    valid = isinstance(value, str) and re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", value)
    return None if valid else 'เวลาไทยรูปแบบ HH:MM ช่วง 00:00–23:59 เช่น "06:30"'


def _int(key: str, value: Any, unit: Any) -> str | None:
    valid = isinstance(value, int) and not isinstance(value, bool)
    valid = valid and (1 <= value <= 31 if key == "day_of_month" else value >= 0)
    return None if valid else "จำนวนเต็ม " + ("1–31" if key == "day_of_month" else ">= 0")


def _lag(key: str, value: Any, unit: Any) -> str | None:
    valid = isinstance(value, int) and not isinstance(value, bool) and value <= 0
    return None if valid else "จำนวนเต็ม <= 0 (0 = วันเดียวกับวันที่รัน, -1 = T-1)"


def _duration(key: str, value: Any, unit: Any) -> str | None:
    valid = (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (not isinstance(value, float) or math.isfinite(value))
        and value >= 0
        and unit in ("h", "d")
    )
    return None if valid else "value เป็นตัวเลข finite >= 0 (ไม่ใช่ bool) และ unit: h หรือ d"


_CHECKERS = {"choice": _choice, "hh:mm": _hh_mm, "int": _int, "lag": _lag, "duration": _duration}

CALENDAR_FIELDS = {
    "schedule_type": "choice",  # daily | workday | workday_excluding_holidays | monthly
    "day_of_month": "int",  # 1..31
    "expected_at": "hh:mm",
    "business_date_lag": "lag",  # <= 0: business_date = run date + lag (-1 = T-1)
    "latency": "duration",  # value >= 0, unit: h|d
    "recovery_window": "duration",
}
CalendarError = tuple[str, str, str]  # (field, message_thai, fix_thai)


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


def compiled_calendar(
    contract: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[CalendarError]]:
    """Return (resolved calendar, null owner keys, format errors); unknown SLA keys are ignored."""
    sla = {p["property"]: p for p in contract.get("slaProperties") or [] if isinstance(p, dict)}
    values = {key: sla.get(key, {}).get("value") for key in CALENDAR_FIELDS}
    required = ["schedule_type", "expected_at", "business_date_lag", "recovery_window"]
    if values["schedule_type"] == "monthly":
        required.append("day_of_month")
    missing = [key for key in required if values[key] is None]
    calendar = {"status": "PENDING_OWNER" if missing else "COMPLETE"}
    errors: list[CalendarError] = []
    for key, kind in CALENDAR_FIELDS.items():
        value = values[key]
        unit = sla.get(key, {}).get("unit")
        fix = _CHECKERS[kind](key, value, unit) if value is not None else None
        if fix:
            errors.append(("slaProperties." + key, f"'{key}' ต้องมีรูปแบบ: {fix}", "กำหนด " + fix))
            value = None
        if kind == "duration":
            key_out = "missing_after_seconds" if key == "latency" else key + "_seconds"
            calendar[key_out] = (
                None if value is None else int(value * (3600 if unit == "h" else 86400))
            )
        else:
            calendar[key] = value
    for key in (
        "timezone",
        "expected_day_offset",
        "business_date_lag",
        "business_schedule",
        "expected_at",
        "recovery_window",
        "schedule_type",
        "day_of_month",
    ):
        if has_custom_property(contract, key):
            errors.append(
                ("customProperties." + key, f"'{key}' ต้องอยู่ใน slaProperties", "ย้ายไป slaProperties")
            )
    return calendar, missing, errors
