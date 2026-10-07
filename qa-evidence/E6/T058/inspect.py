"""Check actual artifacts/preservation; never print configs or endpoints."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "qa-evidence/E6/T058"
EXPECTED = {
    "status": "PENDING_OWNER", "schedule_type": None, "day_of_month": None,
    "expected_at": None, "expected_day_offset": None,
    "missing_after_seconds": 14400, "recovery_window_seconds": 172800,
}


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "build/dev/resolved").rglob("*.resolved.json"))}


def resolved():
    values = hashes()
    assert len(values) == 6, values
    for source in ("credit_card", "credit_card_txn", "customer"):
        pair = []
        for layer in ("bronze", "silver"):
            path = ROOT / f"build/dev/resolved/cc/{layer}.cc.{source}.resolved.json"
            calendar = json.loads(path.read_text(encoding="utf-8"))["calendar"]
            assert calendar == EXPECTED and len(calendar) == 7, calendar
            pair.append(calendar)
            if source == "credit_card_txn":
                print(layer + " cc.credit_card_txn calendar = " + json.dumps(calendar))
        assert pair[0] == pair[1]
    print("All three datasets: bronze == silver; exact seven-key calendar verified.")
    return values


if sys.argv[1] == "scope":
    import fnmatch
    handoff = (ROOT / "handoffs/123-hrm-to-swe-t058.md").read_text(encoding="utf-8")
    allowed = yaml.safe_load(handoff.split("---", 2)[1])["allowed_writes"]
    status = subprocess.run(["git", "status", "--porcelain", "-z"], cwd=ROOT,
                            capture_output=True, check=True).stdout.decode("utf-8")
    changed = [entry[3:] for entry in status.split("\0") if entry]
    preexisting = {"qa-evidence/E6/T053/", "reports/calendar-simplification/"}
    for relative in changed:
        if relative in preexisting:
            print(relative + ": pre-existing untracked input, not written")
            continue
        assert any(fnmatch.fnmatchcase(relative, pattern) for pattern in allowed) or relative == "qa-evidence/E6/T058/", relative
        print(relative + ": H-123 allowed write")
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, check=True)
    assert not diff.stdout and not diff.stderr
    print("git diff --check: exit 0; no whitespace errors.")
    print("Only H-123-authorized tracked paths modified; protected logs/workflows/pipelines/config rules untouched.")
elif sys.argv[1] == "sanitize":
    for path in sorted(EVIDENCE.glob("*.xml")):
        tree = ET.parse(path)
        before_counts = [dict((k, s.get(k)) for k in ("tests", "failures", "errors", "skipped"))
                         for s in tree.getroot().iter("testsuite")]
        for suite in tree.getroot().iter("testsuite"):
            suite.attrib.pop("hostname", None)
        tree.write(path, encoding="utf-8", xml_declaration=True)
        reread = ET.parse(path)
        after_counts = [dict((k, s.get(k)) for k in ("tests", "failures", "errors", "skipped"))
                        for s in reread.getroot().iter("testsuite")]
        assert before_counts == after_counts
        assert all("hostname" not in s.attrib for s in reread.getroot().iter("testsuite"))
        print(path.name + ": workstation hostname omitted; measured counts unchanged")
elif sys.argv[1] == "first":
    values = resolved()
    (EVIDENCE / "compile-sha256-first.json").write_text(json.dumps(values, indent=2), encoding="utf-8")
    print(json.dumps(values, indent=2))
elif sys.argv[1] == "second":
    values = resolved()
    first = json.loads((EVIDENCE / "compile-sha256-first.json").read_text(encoding="utf-8"))
    assert values == first, "compile output changed"
    print(json.dumps(values, indent=2))
    print("Second compile: byte-identical SHA-256 for all 6 resolved JSON files.")
elif sys.argv[1] == "preservation":
    before = json.loads((EVIDENCE / "before.json").read_text(encoding="utf-8"))
    for relative, original in ((key, value) for key, value in before.items() if key.startswith("DataContract/")):
        current = (ROOT / relative).read_text(encoding="utf-8")
        lines = lambda text: [line for line in text.splitlines() if "# REALITY:" in line]
        assert lines(original) == lines(current), relative
        old, new = yaml.safe_load(original), yaml.safe_load(current)
        old.pop("slaProperties", None)
        new.pop("slaProperties", None)
        assert old == new, relative
        # All bytes before the SLA/comment section are unchanged (including team/email).
        marker = "# CALENDAR AUTHORING"
        old_prefix = original.split(marker)[0] if marker in original else original.split("slaProperties:")[0]
        new_prefix = current.split("# Calendar: slaProperties")[0]
        assert old_prefix == new_prefix, relative
        baseline = subprocess.run(["git", "show", "HEAD:" + relative], cwd=ROOT,
                                  capture_output=True, check=True).stdout.decode("utf-8")
        assert yaml.safe_load(baseline)["version"] == new["version"], relative
        print(relative + ": REALITY, non-calendar prefix/content, team/email and version preserved")
    helpers = "def custom_property"
    old_src = subprocess.run(["git", "show", "HEAD:src/mdf/calendar.py"], cwd=ROOT,
                             capture_output=True, check=True).stdout.decode("utf-8")
    new_src = (ROOT / "src/mdf/calendar.py").read_text(encoding="utf-8")
    old_helpers = old_src[old_src.index(helpers):old_src.index("\n\ndef compiled_calendar")]
    new_helpers = new_src[new_src.index(helpers):new_src.index("\n\ndef compiled_calendar")]
    assert old_helpers == new_helpers, "custom_property helpers changed"
    print("custom_property / has_custom_property: byte-identical to HEAD.")
    old_config = subprocess.run(["git", "show", "HEAD:config/env/dev.yaml"], cwd=ROOT,
                                capture_output=True, check=True).stdout.decode("utf-8")
    new_config = (ROOT / "config/env/dev.yaml").read_text(encoding="utf-8")
    assert old_config.replace('timezone: "Asia/Bangkok"\n', '') == new_config
    print("dev config: only timezone line removed.")
    print(f"calendar.py line count: {before['calendar_lines']} -> {len(new_src.splitlines())}")
    tree = ET.parse(EVIDENCE / "targeted-final.xml")
    counts = {key: sum(int(s.get(key, 0)) for s in tree.getroot().iter("testsuite"))
              for key in ("tests", "failures", "errors", "skipped")}
    assert counts["failures"] == counts["errors"] == counts["skipped"] == 0
    print("Targeted JUnit counts: " + json.dumps(counts))
    print("Calendar test count: " + str(sum(1 for c in tree.getroot().iter("testcase")
                                          if c.get("classname") == "tests.test_calendar")))
