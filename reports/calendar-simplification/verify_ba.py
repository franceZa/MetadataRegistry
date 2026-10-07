"""Verify BA document/source scope and preservation. No implementation tests."""
from pathlib import Path
import collections
import hashlib
import json
import re
import subprocess
import sys
import yaml
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/calendar-simplification"
sys.path.insert(0, str(ROOT / "src"))
from mdf.calendar import compiled_calendar
from mdf.validation import validate_project

backup = ROOT / "DocsForAgent/archive/draft_reviewd_by_agent_v2.pre-calendar-simplification.20261005T162512Z.md"
backup_bytes = backup.read_bytes()
assert hashlib.sha256(backup_bytes).hexdigest() == "4f07413bed046968e77a758c322750a03f9cf5a097afb264f9219314f34be712"
live = ROOT / "DocsForAgent/draft_reviewd_by_agent_v2.md"
before = json.loads((OUT / "audit-inputs.json").read_text(encoding="utf-8"))
ledger = json.loads((ROOT / "DocsForAgent/archive/calendar-simplification-id-map.json").read_text(encoding="utf-8"))
entries = ledger["entries"]
ids = [x["id"] for x in entries]
# Independently reconstruct the backup census and core requirement definitions.
identifier_re = re.compile(r"\b(?:FR-[A-Z]\.\d+[a-z]?|NFR-\d+|AC-\d+|DQ-\d+|BR-\d+|DPR-\d+|BF-\d+|BL-M\d+|D-P\d-\d+|DC-\d+r?|OQ-(?:P\d-\d+|TRI-[\w-]+)|AS-\d+|R-\d+|DEP-\d+|X-\d+|CD-\d+|M-\d+|T-\d+|US-\d+|CONFLICT-\d+|E\d+)\b")
assert set(ids) == set(identifier_re.findall(backup_bytes.decode("utf-8")))
core_definitions = set()
for line in backup_bytes.decode("utf-8").splitlines():
    cell = line.split("|")[1] if line.startswith("|") else line if line.startswith(("#### AC-", "- **DQ-", "- **BF-")) else ""
    core_definitions.update(x for x in identifier_re.findall(cell) if x.startswith(("FR-", "NFR-", "AC-", "DQ-", "BR-", "DPR-", "BF-", "BL-M")))
entry_by_id = {x["id"]: x for x in entries}
assert all(entry_by_id[x]["action"] in ("retain", "relocate", "supersede") for x in core_definitions)
assert len(ids) == len(set(ids)) == ledger["total_unique_ids"]
assert dict(collections.Counter(x["action"] for x in entries)) == ledger["counts"]
active = [x for x in entries if x["active_obligation"]]
assert len(active) == ledger["active_obligation_count"]
assert all(x["action"] in ("retain", "relocate", "supersede") for x in active)
for x in entries:
    path, _, anchor = x["target"].partition("#")
    target = ROOT / path
    assert target.exists(), x
    if x["action"] in ("retain", "relocate"):
        assert 'id="' + anchor + '"' in target.read_text(encoding="utf-8"), x
        assert x["definition_lines"], x
assert all(any(x["id"] == key and x["action"] != "archive" for x in entries) for key in ("FR-M.1", "FR-M.11", "DQ-1", "DQ-8", "BF-1", "BF-10", "FR-I.18", "AC-29", "NFR-11", "D-P5-12"))

schema = json.loads((ROOT / "config/schemas/odcs_v3.0.2.json").read_text(encoding="utf-8"))
validator = jsonschema.Draft202012Validator(schema)
contracts = {}
for relative, original in before["contracts"].items():
    raw = (ROOT / relative).read_bytes()
    data = yaml.safe_load(raw.decode("utf-8"))
    assert hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest() == original["parsed_sha256"], relative
    reality = [line.hex() for line in raw.splitlines() if b"# REALITY:" in line]
    assert reality == original["reality_lines_hex"], relative
    assert compiled_calendar(data) == original["compiled_calendar"], relative
    assert not list(validator.iter_errors(data)), relative
    # Compare against actual git HEAD too; pre-audit evidence is not the only oracle.
    r = subprocess.run(["git", "show", "HEAD:" + relative], cwd=ROOT, capture_output=True, check=True)
    head_data = yaml.safe_load(r.stdout.decode("utf-8"))
    assert data == head_data, relative
    assert reality == [line.hex() for line in r.stdout.splitlines() if b"# REALITY:" in line]
    proposed = OUT / "proposed" / relative
    p_raw = proposed.read_bytes()
    p_data = yaml.safe_load(p_raw.decode("utf-8"))
    assert not list(validator.iter_errors(p_data)), str(proposed)
    props = p_data["customProperties"]
    calendars = [x for x in props if x["property"] == "calendar"]
    assert len(calendars) == 1
    cal = calendars[0]["value"]
    assert all(cal[key] is None for key in ("schedule_type", "timezone", "expected_at", "expected_day_offset", "effective_from"))
    sla = {x["property"]: x for x in data.get("slaProperties", [])}
    assert cal["frequency"] == sla["frequency"]["value"]
    assert cal["latency"] == {k: sla["latency"][k] for k in ("value", "unit")}
    expected_recovery = {k: sla["recovery_window"][k] for k in ("value", "unit")} if "recovery_window" in sla else None
    assert cal["recovery_window"] == expected_recovery
    assert all(x["property"] not in ("frequency", "latency", "recovery_window", "expected_at") for x in p_data.get("slaProperties", []))
    assert all(x["property"] not in ("timezone", "expected_day_offset", "business_schedule") for x in props)
    assert [line.hex() for line in p_raw.splitlines() if b"# REALITY:" in line] == reality
    def without_calendar(doc):
        doc = json.loads(json.dumps(doc))
        doc["slaProperties"] = [x for x in doc.get("slaProperties", []) if x["property"] not in ("frequency", "latency", "recovery_window", "expected_at")]
        if not doc["slaProperties"]:
            del doc["slaProperties"]
        doc["customProperties"] = [x for x in doc.get("customProperties", []) if x["property"] not in ("calendar", "timezone", "expected_day_offset", "business_schedule")]
        return doc
    assert without_calendar(data) == without_calendar(p_data), relative
    contracts[relative] = {"parsed_payload_matches_HEAD": True, "reality_lines_unchanged": True,
        "calendar_output_unchanged": True, "odcs_schema_pass": True,
        "staged_odcs_schema_pass": True, "staged_one_calendar_source": True,
        "staged_unknown_owner_null": True, "staged_noncalendar_unchanged": True}
report = validate_project(base_dir=ROOT / "DataContract", config_dir=ROOT / "config")
assert report.is_valid and len(report.errors) == 0 and len(report.warnings) == 3
assert all(x.code == "CALENDAR_PENDING_OWNER" for x in report.warnings)
transcript = (OUT / "validate.txt").read_text(encoding="utf-8")
assert "EXIT: 0" in transcript and "PASS" in transcript

# Markdown structural checks: not an assertion of semantic business correctness.
markdown = [live, ROOT / "DocsForAgent/START_HERE.md", OUT / "analysis.md", OUT / "active-obligations.md", ROOT / "handoffs/120-ba-to-hrm-calendar-simplification.md"]
md_results = {}
for p in markdown:
    text = p.read_text(encoding="utf-8")
    fenced = False
    headings = []
    table_width = None
    tables = 0
    for n,line in enumerate(text.splitlines(),1):
        if re.match(r"^\s*```", line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if re.match(r"^#{1,6} ", line):
            headings.append(line)
        if line.startswith("|"):
            sanitized = re.sub(r"`[^`]*`", "CODE", line).replace("\\|", "ESCAPED")
            width = len(sanitized.split("|")) - 2
            if table_width is None:
                table_width = width
                tables += 1
            assert width == table_width, (str(p), n, width, table_width)
        else:
            table_width = None
    assert not fenced, str(p)
    assert len(headings) == len(set(headings)), (str(p), "duplicate headings")
    links = re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", text)
    checked = 0
    for link in links:
        if link.startswith(("http:", "https:", "mailto:", "#")):
            continue
        destination = link.split("#",1)[0]
        assert (p.parent / destination).exists(), (str(p), link)
        checked += 1
    md_results[p.relative_to(ROOT).as_posix()] = {"fences_balanced": True, "headings_unique": True, "table_widths_consistent": True, "tables": tables, "local_links_checked": checked}
assert live.stat().st_size <= 30000
changed = subprocess.run(["git", "-c", "core.quotepath=false", "diff", "--name-only"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout.splitlines()
allowed_tracked = {"DocsForAgent/draft_reviewd_by_agent_v2.md", "DocsForAgent/START_HERE.md", *before["contracts"]}
assert set(changed) <= allowed_tracked, changed
status = subprocess.run(["git", "-c", "core.quotepath=false", "status", "--short"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True).stdout
assert subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True).returncode == 0
branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
assert branch == "add_config_manual_deployed"
created = [p.relative_to(ROOT).as_posix() for p in OUT.rglob("*") if p.is_file()]
created += ["DocsForAgent/archive/calendar-simplification-id-map.json", "handoffs/120-ba-to-hrm-calendar-simplification.md"]
result = {"status": "PASS", "backup_sha256": hashlib.sha256(backup_bytes).hexdigest(),
          "backup_bytes": len(backup_bytes), "backup_lines": len(backup_bytes.splitlines()),
          "live_bytes": live.stat().st_size, "live_lines": len(live.read_bytes().splitlines()),
          "reduction_percent": round((1 - live.stat().st_size / len(backup_bytes)) * 100, 2),
          "id_census": {k: ledger[k] for k in ("total_unique_ids", "active_obligation_count", "counts")},
          "active_archive_count": len([x for x in active if x["action"] == "archive"]),
          "contracts": contracts, "mdf_validate": {"exit": 0, "errors": 0, "warnings": 3, "code": "CALENDAR_PENDING_OWNER"},
          "markdown": md_results, "git_diff_check": "PASS", "branch": branch,
          "core_requirement_definition_count": len(core_definitions),
          "independent_original_ID_census_pass": True,
          "ignored_worktree_files_verified": ["DocsForAgent/draft_reviewd_by_agent_v2.md", "DocsForAgent/START_HERE.md", "DocsForAgent/archive/calendar-simplification-id-map.json", "handoffs/120-ba-to-hrm-calendar-simplification.md"],
          "tracked_changed_files": changed, "created_ba_files": sorted(set(created)),
          "git_status": status, "no_full_suite": True, "no_implementation_or_deployment": True}
(OUT / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
