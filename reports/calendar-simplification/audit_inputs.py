"""Read-only BA probes; not generator implementation or a test-suite run."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import yaml
import jsonschema
from mdf.calendar import read_calendar, compiled_calendar

out = ROOT / "reports/calendar-simplification"
backup = ROOT / "DocsForAgent/archive/draft_reviewd_by_agent_v2.pre-calendar-simplification.20261005T162512Z.md"
assert hashlib.sha256(backup.read_bytes()).hexdigest() == "4f07413bed046968e77a758c322750a03f9cf5a097afb264f9219314f34be712"
schema = json.loads((ROOT / "config/schemas/odcs_v3.0.2.json").read_text(encoding="utf-8"))
validator = jsonschema.Draft202012Validator(schema)
paths = sorted((ROOT / "DataContract").glob("*/contract/*.odcs.yaml"))
contracts = {}
for p in paths:
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    cal, missing, errors = read_calendar(data)
    contracts[p.relative_to(ROOT).as_posix()] = {
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "parsed_sha256": hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(),
        "reality_lines_hex": [line.hex() for line in p.read_bytes().splitlines() if b"# REALITY:" in line],
        "sla": data.get("slaProperties"), "missing": missing,
        "calendar_errors": errors, "compiled_calendar": compiled_calendar(data),
        "schema_errors": [e.message for e in validator.iter_errors(data)],
    }
base = yaml.safe_load((ROOT / "DataContract/cc/contract/customer.odcs.yaml").read_text(encoding="utf-8"))
probes = {}
for mode in ("root_calendar", "custom_calendar", "explicit_null_legacy", "wrong_list", "wrong_exception", "negative_latency"):
    data = copy.deepcopy(base)
    if mode == "root_calendar":
        data["calendar"] = {"timezone": None}
    elif mode == "custom_calendar":
        data["customProperties"].append({"property": "calendar", "value": {"timezone": None}})
    elif mode == "explicit_null_legacy":
        data["slaProperties"].append({"property": "expected_at", "value": None})
        data["customProperties"].extend({"property": key, "value": None} for key in ("timezone", "expected_day_offset", "business_schedule"))
    elif mode in ("wrong_list", "wrong_exception"):
        data["customProperties"].append({"property": "business_schedule", "value": {
            "type": "daily", "effective_from": "2026-01-01",
            "holidays": "not-a-list" if mode == "wrong_list" else [],
            "exceptions": ["not-a-date"] if mode == "wrong_exception" else []}})
    else:
        next(x for x in data["slaProperties"] if x["property"] == "latency")["value"] = -4
    _, missing, errors = read_calendar(data)
    probes[mode] = {"schema_errors": [e.message for e in validator.iter_errors(data)],
                    "calendar_missing": missing, "calendar_errors": errors,
                    "compiled_calendar": compiled_calendar(data)}
calendar_src = (ROOT / "src/mdf/calendar.py").read_text(encoding="utf-8")
tree = ast.parse(calendar_src)
functions = [{"name": x.name, "line": x.lineno, "end_line": x.end_lineno,
              "lines": x.end_lineno - x.lineno + 1}
             for x in tree.body if isinstance(x, ast.FunctionDef)]
keys = list(compiled_calendar(base))
traces = {key: [] for key in keys}
sibling = ROOT.parents[1] / "Medallion"
search_paths = list((ROOT / "src").rglob("*.py")) + list((ROOT / "tests").rglob("*.py"))
search_paths += list((ROOT / "scripts").glob("*.py")) + list((ROOT / ".github/workflows").glob("*.yml"))
search_paths += list(sibling.rglob("*.py")) if sibling.exists() else []
for p in search_paths:
    if any(s in p.parts for s in (".venv", "__pycache__")):
        continue
    for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for key in keys:
            if key in line:
                display = p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else "../../Medallion/" + p.relative_to(sibling).as_posix()
                traces[key].append({"path": display, "line": n, "text": line.strip()})
result = {"backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
          "backup_bytes": len(backup.read_bytes()), "backup_lines": len(backup.read_bytes().splitlines()),
          "contracts": contracts, "probes": probes, "calendar_module_lines": len(calendar_src.splitlines()),
          "calendar_functions": functions, "calendar_keys": keys, "key_traces": traces,
          "schema_root_additionalProperties": schema.get("additionalProperties"),
          "schema_root_keys": sorted(schema.get("properties", {})),
          "sibling_path": str(sibling), "sibling_exists": sibling.exists()}
(out / "audit-inputs.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in result.items() if k not in ("key_traces", "schema_root_keys", "contracts")}, ensure_ascii=False, indent=2))
print("contract_states", json.dumps({p: {k: v for k, v in d.items() if k in ("missing", "schema_errors", "calendar_errors", "compiled_calendar")} for p,d in contracts.items()}, ensure_ascii=False))
