"""Build BA authoring comments and staged data, not a generator migration."""
from pathlib import Path
import hashlib
import json
import re
import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/calendar-simplification"
evidence = json.loads((OUT / "audit-inputs.json").read_text(encoding="utf-8"))
backup = ROOT / "DocsForAgent/archive/draft_reviewd_by_agent_v2.pre-calendar-simplification.20261005T162512Z.md"
assert hashlib.sha256(backup.read_bytes()).hexdigest() == evidence["backup_sha256"]
for relative, before in evidence["contracts"].items():
    path = ROOT / relative
    raw = path.read_bytes()
    data = yaml.safe_load(raw.decode("utf-8"))
    assert hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest() == before["parsed_sha256"]
    sla = {x["property"]: x for x in data.get("slaProperties", [])}
    cal = {
        "frequency": sla.get("frequency", {}).get("value"),
        "schedule_type": None, "timezone": None, "expected_at": None,
        "expected_day_offset": None, "effective_from": None,
        "latency": {k: sla.get("latency", {}).get(k) for k in ("value", "unit")},
        "recovery_window": {k: sla.get("recovery_window", {}).get(k) for k in ("value", "unit")},
    }
    if "recovery_window" not in sla:
        cal["recovery_window"] = None
    fragment = yaml.safe_dump({"property": "calendar", "value": cal}, sort_keys=False, allow_unicode=True).rstrip()
    header = (
        "# CALENDAR AUTHORING — STAGED, not parsed by the current generator.\n"
        "# Owner values are unconfigured; do not infer schedule/timezone from frequency/env.\n"
        "# One ODCS-compatible customProperties entry is proposed below (comments only).\n"
        "# Keep executable SLA fields below until coordinated SWE migration (FR-N.1–N.6).\n"
        "# Never uncomment beside legacy calendar fields: one source only after cutover.\n"
        "# See reports/calendar-simplification/analysis.md and proposed/ for staged YAML.\n"
        "# customProperties calendar entry (proposed, not production defaults):\n"
    )
    block = header + "\n".join("# " + line for line in fragment.splitlines()) + "\n\n"
    text = raw.decode("utf-8").replace("\r\n", "\n")
    if "# CALENDAR AUTHORING — STAGED" not in text:
        assert text.count("slaProperties:\n") == 1
        text = text.replace("slaProperties:\n", block + "slaProperties:\n")
    if "/_template/" in relative:
        text = text.replace("# กฎทั้งหมดที่ใช้ตรวจอยู่ที่ metadata/_rules/rules.yaml", "# DQ library: config/dq_library.yaml; structural rules: config/rules/*.rules.json")
        text = text.replace("metadata/env/*.yaml", "config/env/*.yaml")
        text = text.replace("unit: h # m | h | d", "unit: h # h | d (current calendar parser)")
        text = text.replace('  # - property: expected_at   # optional: เวลาที่คาดว่าไฟล์จะมาถึง (HH:MM)\n  #   value: "02:00"\n', "  # Current legacy parser: expected_at/offset/timezone/schedule remain absent until owner supplies them.\n")
    else:
        text = re.sub(r"DataContract/cc/dq/(\w+)\.dq\.yaml", r"DataContract/cc/pipeline/\1.pipeline.yaml", text)
    newline = "\r\n" if b"\r\n" in raw else "\n"
    written = text.replace("\n", newline).encode("utf-8")
    after = yaml.safe_load(written.decode("utf-8"))
    assert after == data, relative
    assert [x.hex() for x in written.splitlines() if b"# REALITY:" in x] == before["reality_lines_hex"]
    path.write_bytes(written)
    # Stage a complete ODCS document for the future source-reader, never in live discovery paths.
    data["slaProperties"] = [x for x in data.get("slaProperties", []) if x["property"] not in ("frequency", "latency", "recovery_window", "expected_at")]
    if not data["slaProperties"]:
        del data["slaProperties"]
    data["customProperties"] = [x for x in data.get("customProperties", []) if x["property"] not in ("calendar", "timezone", "expected_day_offset", "business_schedule")]
    data["customProperties"].append({"property": "calendar", "value": cal})
    target = OUT / "proposed" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    # Preserve all source comments, including REALITY lines, while replacing only source blocks.
    proposed = raw.decode("utf-8").replace("\r\n", "\n")
    match = re.search(r"(?ms)^slaProperties:\n.*?(?=^customProperties:)", proposed)
    assert match
    retained_oracles = "\n".join(line for line in match.group().splitlines() if "# REALITY:" in line)
    proposed = proposed[:match.start()] + (retained_oracles + "\n\n" if retained_oracles else "") + proposed[match.end():]
    insert_at = proposed.index("\nschema:\n")
    staged_entry = yaml.safe_dump([{"property": "calendar", "value": cal}], sort_keys=False, allow_unicode=True)
    proposed = proposed[:insert_at] + "".join("  " + line + "\n" for line in staged_entry.splitlines()) + proposed[insert_at:]
    proposed = "# PROPOSED / NOT ACTIVE. Requires FR-N migration before discovery/compile.\n# Unknown owner inputs are null; known SLA values copied, not guessed.\n" + proposed
    assert yaml.safe_load(proposed) == data
    actual_reality = [x.hex() for x in proposed.encode().splitlines() if b"# REALITY:" in x]
    if actual_reality != before["reality_lines_hex"]:
        print(relative, "REALITY mismatch", actual_reality, before["reality_lines_hex"])
    assert actual_reality == before["reality_lines_hex"]
    target.write_text(proposed, encoding="utf-8", newline="\n")
    print(relative, "comments_only", "parsed_payload_unchanged", "REALITY_unchanged")
