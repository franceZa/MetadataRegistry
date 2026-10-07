"""Extract ID-addressable current obligations; archive narrative history only."""
from pathlib import Path
import collections
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/calendar-simplification"
backup = ROOT / "DocsForAgent/archive/draft_reviewd_by_agent_v2.pre-calendar-simplification.20261005T162512Z.md"
assert hashlib.sha256(backup.read_bytes()).hexdigest() == "4f07413bed046968e77a758c322750a03f9cf5a097afb264f9219314f34be712"
text = backup.read_text(encoding="utf-8")
lines = text.splitlines()
pattern = re.compile(r"\b(?:FR-[A-Z]\.\d+[a-z]?|NFR-\d+|AC-\d+|DQ-\d+|BR-\d+|DPR-\d+|BF-\d+|BL-M\d+|D-P\d-\d+|DC-\d+r?|OQ-(?:P\d-\d+|TRI-[\w-]+)|AS-\d+|R-\d+|DEP-\d+|X-\d+|CD-\d+|M-\d+|T-\d+|US-\d+|CONFLICT-\d+|E\d+)\b")
occurrences = collections.defaultdict(list)
for n,line in enumerate(lines,1):
    for ident in sorted(set(pattern.findall(line))):
        occurrences[ident].append(n)
records = collections.defaultdict(list)
for i,line in enumerate(lines):
    # Named requirement/AC/assumption/risk rows: first table cell, never a prose mention.
    if line.startswith("|"):
        first_cell = line.split("|")[1]
        ids = pattern.findall(first_cell)
        if ids:
            for ident in ids:
                records[ident].append({"start": i+1, "end": i+1, "text": line})
    bullet = re.match(r"^- \*\*((?:DQ|BF)-\d+)\b", line)
    if bullet:
        records[bullet.group(1)].append({"start": i+1, "end": i+1, "text": line})
    match = re.match(r"^### (DC-11r)\b", line)
    if match:
        end = i+1
        while end < len(lines) and not lines[end].startswith("#"):
            end += 1
        records[match.group(1)].append({"start": i+1, "end": end, "text": "\n".join(lines[i:end]).strip()})
    match = re.match(r"^#### (AC-\d+):", line)
    if match:
        end = i+1
        while end < len(lines) and not lines[end].startswith("#"):
            end += 1
        records[match.group(1)].append({"start": i+1, "end": end, "text": "\n".join(lines[i:end]).strip()})
# BF rules are table rows. Closed assumptions/questions/history are excluded from active records.
active_prefix = ("FR-", "NFR-", "AC-", "DQ-", "BR-", "DPR-", "BF-", "BL-M", "CD-", "X-", "US-")
closed = {"AS-1", "AS-2", "AS-6", "AS-10", "AS-13", "OQ-P1-1", "OQ-P1-10", "OQ-P1-13", "OQ-P1-15", "OQ-P1-16", "OQ-P2-1", "OQ-P2-10", "OQ-P5-7", "OQ-P5-8", "OQ-P5-9", "OQ-TRI-12a", "CONFLICT-13", "CONFLICT-15", "CONFLICT-16", "CONFLICT-18"}
manual_cancelled = {"AC-44", "AC-50"}
live = (ROOT / "DocsForAgent/draft_reviewd_by_agent_v2.md").read_text(encoding="utf-8")
live_definitions = set()
for line in live.splitlines():
    if line.startswith("|"):
        live_definitions.update(pattern.findall(line.split("|")[1]))
    if line.startswith("- **D-"):
        live_definitions.update(pattern.findall(line))
# Existing FR-M exact details reside here too; live summaries/control statements take precedence.
decision_summaries = {
    "D-P0-1": "SSOT ชี้ขาด; ขัดกันให้ถามผู้ใช้ ไม่เลือก draft เก่าอัตโนมัติ.",
    "D-P0-2": "Metadata อยู่ Git ไม่มี meta.* database.",
    "D-P0-6": "Resolved JSON ต่อ table ใต้ build ไม่ commit; CI publish manifest/hash ไม่มี intermediate spec/bot push.",
    "D-P0-8": "Contract/pipeline technical validator rules ใน JSON; data DQ อยู่ YAML library.",
    "D-P0-9": "dev env เดียว; catalog จาก control file; เพิ่ม env ด้วยไฟล์ ไม่ hardcode.",
    "D-P0-10": "Gold layout DataContract/_gold/<domain>/<table>.gold.yaml + SQL/DAG อยู่ Phase 3.",
    "D-P0-11": "Managed storage only; reserved storage field ไม่อนุญาต unsupported mode.",
    "D-P0-13": "REALITY lines เป็น test oracle; ไม่กู้ legacy มาแก้ข้อมูลให้ผ่าน.",
    "D-P0-14": "Agent แก้ DataContract ได้ ยกเว้น landing path ต้องตาม confirmed template.",
    "D-P1-1": "Landing prefix /Volumes/{catalog}/landing_{source}/; resolve placeholders + suffix ตาม DC-11r/FR-A.5.",
    "D-P1-2": "Data DQ execution อยู่ Phase 3; Phase 1 compile only.",
    "D-P1-3": "Catalog dev_catalog ได้; TODO host/secret_scope ต้อง release fail จน configured จริง.",
    "D-P2-1": "DQ 3 ส่วน: ODCS tags/params, BU+DE library YAML, BU SQL/derived pipeline; contract no SQL.",
    "D-P2-2": "ODCS ไม่มี relationships/standard valid-values; customProperties.foreign_key/valid_values; description บังคับ.",
    "D-P2-3": "required:true auto not_null.",
    "D-P2-4": "Library default_action, per-column pipeline override.",
    "D-P2-5": "BU constraints/normalise/tokenise/dedup/load/retention อยู่ pipeline เดียวต่อ dataset.",
    "D-P2-6": "Library+non-derived BU หลัง cast ก่อน tokenise; derived BU หลัง derived.",
    "D-P2-7": "Library/BU/derived description บังคับ.",
    "D-P2-8": "ทุก contract column description nonempty.",
    "D-P2-9": "valid_values / foreign_key ใช้ customProperties.",
    "D-P3-1": "BR-10 birth_date <= business_date ไม่ใช้ current_date.",
    "D-P3-2": "Backfill ได้ทุก stage ตาม explicit human flow; ห้าม ordinary retry เริ่ม older-date backfill (confirmed later Q6).",
    "D-P3-3": "Raw landing 1825 วัน; bronze30/90วัน; rebuild bronze จาก rawเมื่อ expired.",
    "D-P3-4": "Human replay recovery RESTORE+rerun เฉพาะ retention window; primary partition replaceWhere.",
    "D-P3-5": "Backfill default current release, explicit old release allowed; log release_id.",
    "D-P3-6": "customer/credit_card SCD2 business-date valid_from/to, as-of1825วัน; time travel short recovery only.",
    "D-P3-7": "Partition replaceWhere primary; human RESTORE/replay within retention, no vault/erasure_list/run_log RESTORE.",
    "D-P3-8": "Erasure token list filters every run incl backfill; raw archive runtime SP only.",
    "D-P4-2": "Master-missing fact/gold policy OQ-P1-22 deferred Phase3.",
    "D-P4-3": "Gold compile/DAG/input_asof/SCD2 trace อยู่ Phase3.",
    "D-P4-4": "Phase1 CLI validate/compile/trace-orphan/diff/package/verify.",
    "D-P4-5": "Phase1 static/local proof distinct from Phase2 actual delivery; no URL fabrication.",
    "D-P4-7": "Missing config FK target compile defect; data FK defect sends BA/source; no invented unknown member, OQ-P1-23.",
    "D-P5-2": "Phase2 actual release delivery to Volume + managedDelta registry; not data runtime.",
    "D-P5-3": "PySpark runtime/DQ/backfill/gold/ABAC tagging Phase3.",
    "D-P5-4": "AI semantic/PII/classification/auto-suggest ABAC Phase4.",
    "D-P5-5": "github-oidc federation auth; no PAT/clientsecret in GitHub/artifacts.",
    "D-P5-6": "Recursive copy to release_id Volume; fallback honest U2M/manual when auto unavailable.",
    "D-P5-7": "Explicit runtime release_id input, not inferred latest.",
    "D-P5-8": "download→verify→immutable copy→remoteverify→deploy/update→explicitrelease→smoke→activate schedule.",
    "D-P5-9": "Actual evidence required before delivery PASS; HG_PROD before first workspace write.",
    "D-P5-10": "auto/u2m/manual modes remain; actual registry delivery proved; manual acceptance cancelled H-119 not PASS.",
    "D-P5-11": "Per-source localbuild→recursivecopy; manifest explicit POSIXpaths, newv3 after round12, oldv1/v2 untouched; v1warn; gold2directorylevels interpret/clarify beforeenable; zipassetone, zip-slipcheck, manifestdigestsummary+notes.",
    "D-P5-12": "Calendar/reader/privacyflags/ODCSbundle selected only; unknownownerpending; resolvedauthority; PIImaskdefer; ordinaryolderdateblock/humanbackfill; timezone static stringonly no tzdata.",
}
for ident, summary in decision_summaries.items():
    source = records.get(ident, [])
    assert source, ident
    records[ident] = [{"start": source[0]["start"], "end": source[-1]["end"], "text": summary}]
phase3_tasks = {"T-04", "T-18", "T-19", "T-20", "T-21", "T-22", "T-23", "T-24", "T-25", "T-30", "T-31", "T-32", "T-33"}
active_ids = set()
for ident, defs in records.items():
    if ident in decision_summaries or ident in phase3_tasks or ident == "DC-11r":
        active_ids.add(ident)
        continue
    if ident in closed or ident in manual_cancelled or ident.startswith("D-P") or ident.startswith("DC-") or ident.startswith("T-") or ident.startswith("M-") or ident.startswith("E"):
        continue
    if ident.startswith(active_prefix) or ident.startswith(("AS-", "R-", "DEP-", "OQ-")):
        # Table questions explicitly closed are archive, even if not listed in closed set.
        if ident.startswith("OQ-") and all("ปิด" in d["text"] and "ยัง" not in d["text"] for d in defs):
            continue
        active_ids.add(ident)
header = """# Active obligations — ID-addressable detail

เอกสารประกอบของ live SSOT ไม่ใช่ draft อีกฉบับ: เปิดเฉพาะ ID ที่ ticket ต้องใช้.
ย้ายเฉพาะ requirement/AC/rule/risk/open item ที่ยังต้องรักษา; ไม่คัด chronology, closed tasks หรือภาคผนวกคำตอบเต็ม.
บรรทัด source อ้าง backup ที่ตรวจ hash แล้ว. Phase 1/2 ที่ส่งแล้วเป็น **maintenance constraints**, Phase 3/4 เป็น **backlog ไม่ deployed**.
ข้อความเก่าที่ขัดกันให้ใช้ precedence ด้านล่างก่อน; report นี้ห้ามปลุก manual acceptance ที่ผู้ใช้ยกเลิก.

## Effective precedence / partial supersessions

- T-53 DONE by H-119 manual cancellation. AC-44/AC-50 live manual execution waived (ไม่ใช่ PASS); manual subsetของ AC-58/X-1…X-8/X-5 waived. Capability/SQL safeguards/runbookเดิมยังคง. ไม่ต้องเปิดใหม่โดยอัตโนมัติ.
- FR-M.7 supersedes FR-F.7/AC-46 requirementให้ **new** manifestเป็นv2: new=v3; archivedv1/v2readcompatibilityคงเดิม. FR-M.8 supersedes AC-48 unknownv3 failure: unknownv4fail; v1warn,v2ไม่warn.
- FR-D.8/source layout supersedes flat **new** FR-D.1/FR-F.1. Version decides layoutไม่เดาจากfolder. Gold `_gold/<domain>/<file>` เป็นreserved Phase3 interpretation: จำนวนdirectorylevelsกับpathsegmentsต้องclarifyก่อนimplement.
- FR-L.1a/1b/3a supersede loose asset newrelease: zipassetเดียว, zip-slipcheck, manifestdigestในsummary+notes; zipไม่เป็นidentity; legacyflatdownloadsตามversion.
- FR-M.2 / confirmed OQ-TRI-12a: static timezoneเป็นstringไม่ว่างเท่านั้น ไม่IANAlookup/tzdata. Ownerรับผิดชอบชื่อ; Phase3runtimeinvalidtimezoneต้องfailactionable ไม่fallbackUTC.
- FR-M.10 supersedes Phase3อ่านODCSpolicyจากGitหรือbundle: resolvedเป็นauthority; bundleaudit/hashเท่านั้น. Legacyreleaseที่ไม่มีruntimefieldsต้องfailบอกupgrade; explicit sample fallbackไม่production.
- D-P5-12 Q5/BL-M1: national_id/full_nameยังtokenise ไม่adoptmaskจากsiblingdraft. Q6/BL-M2 supersedes NFR-11/FR-I/BF/AC-27 unrestrictedautomaticout-of-order: ordinaryrunblockolderdateและquarantine; คนสั่งrangebackfillเท่านั้น. ความเท่าเทียมbackfill/SCD2ยังเป็นเป้าภายในauthorizedflow; cascadeยังต้องownerclarify.
- FR-M.1…4 legacyauthoringยังเป็นcurrentimplementation. FR-N.1…6เสนอcutoverหนึ่งcalendarobject+nullableownerinputsโดยcoordinatedSWEเท่านั้น; ไม่ตีความreportว่าparserปัจจุบันรับnullแล้ว.

## Current rules by ID

"""
parts = [header]
for ident in sorted(active_ids):
    parts.append(f"<a id=\"{ident.lower().replace('.', '-')}\"></a>\n\n### {ident}\n")
    for d in records[ident]:
        # Appendix decisions never selected here; preserve exact substantive row or AC body.
        parts.append(f"Source backup lines {d['start']}–{d['end']}; apply effective precedence above.\n\n")
        raw = d["text"]
        if raw.startswith("|"):
            # Render the cell text as prose, not an orphan table without a header.
            parts.append(raw.strip("|").strip() + "\n\n")
        else:
            parts.append(raw + "\n\n")
# Un-ID'd structures with current constraints would be lost by an ID-only check.
parts.append("## Data entities / security boundary (no standalone requirement IDs)\n\n")
parts.append("Source backup lines 223–273 (source/entity definitions), 307–323 (security); apply precedence above.\n\n")
parts.append("\n".join(lines[222:273]) + "\n\n" + "\n".join(lines[306:323]) + "\n\n")
parts.append("## Phase 4 boundary\n\nAI semantic layer/PII detection/classification/auto-suggest UC ABAC: backlog only; real UC ABAC attachment is Phase 3. No Phase 4 implementation ticket is authorized.\n")
(OUT / "active-obligations.md").write_text("".join(parts), encoding="utf-8", newline="\n")
# Build total census: an ID in history must still have an explicit disposition.
entries = []
for ident in sorted(occurrences):
    if ident in manual_cancelled:
        action, target, reason = "supersede", "DocsForAgent/draft_reviewd_by_agent_v2.md#current-fr--migration-fr", "D-CS-5/H-119 cancels manual acceptance, not a PASS; existing capability preserved"
    elif ident in active_ids:
        action = "retain" if ident in live_definitions else "relocate"
        target = "reports/calendar-simplification/active-obligations.md#" + ident.lower().replace(".", "-")
        reason = "Active maintenance/backlog obligation; effective precedence applies, not historical deployment proof"
    elif ident in ("D-P0-5", "AS-10", "DC-11", "D-P4-1", "D-P4-6"):
        action, target, reason = "supersede", "DocsForAgent/draft_reviewd_by_agent_v2.md", "Confirmed later DQ/landing/phase scope replaced old policy; current guarantees and exact FR/AC details retained"
    elif ident.startswith(("D-P", "DC-")):
        action, target, reason = "archive", "DocsForAgent/archive/" + backup.name + "#L" + str(occurrences[ident][0]), "Decision provenance archived, not discarded: operative requirements retained in current FR/DQ/BR/BF/security plus effective precedence"
    else:
        action, target, reason = "archive", "DocsForAgent/archive/" + backup.name + "#L" + str(occurrences[ident][0]), "Historical/completed/cancelled/reference-only record; no authoring/runtime requirement inferred from a citation"
    entries.append({"id": ident, "action": action, "source_lines": occurrences[ident], "definition_lines": [d["start"] for d in records.get(ident, [])], "active_obligation": ident in active_ids, "target": target, "reason": reason})
counts = dict(collections.Counter(x["action"] for x in entries))
result = {"backup": backup.relative_to(ROOT).as_posix(), "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest(), "census_method": "Unique explicit identifiers, definitions from first table cells and AC headings; ranges are references, not fresh definitions. Citation-only/closed items are archive. Un-ID'd data/security constraints separately retained.", "total_unique_ids": len(entries), "active_obligation_count": len(active_ids), "counts": counts, "entries": entries}
(ROOT / "DocsForAgent/archive/calendar-simplification-id-map.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: v for k,v in result.items() if k != "entries"}, ensure_ascii=False, indent=2))
print("active detail bytes", (OUT / "active-obligations.md").stat().st_size)
print("active missing definitions", sorted(set(ident for ident in occurrences if ident.startswith(("FR-", "NFR-", "AC-", "DQ-", "BR-", "DPR-", "BF-", "BL-M"))) - set(records)))
