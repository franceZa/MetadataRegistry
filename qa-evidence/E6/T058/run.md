# T-58 SWE run — H-123 binding scope

**Return status: BLOCKED on cleanup authority only.** Implementation and every H-123
Verify command pass. The final scope audit found a root untracked `OneDrive` file
created by the first, unquoted JUnit-path capture attempt. It is zero-test XML,
not a test result or source file. Its deletion is outside H-123 `allowed_writes`;
SWE has not removed or modified it and stops for HRM cleanup authority. Its
workstation metadata is deliberately not reproduced here.

## Observed results

| H-123 requirement | Real result | Evidence |
|---|---|---|
| Six SLA keys, null owner values, Thai comments | Four contracts converted; template recovery null; cc latency 4 h / recovery 2 d | calendar authoring test; preservation-complete.txt |
| One table / one public entry point | CALENDAR_FIELDS drives four per-kind checkers and mapping; compiled_calendar returns (calendar, missing, errors) | src/mdf/calendar.py; extension.txt |
| Format-only checks, null pending, unknown SLA ignored | Per-kind positive/negative, null/absent equivalence, unknown/duplicate SLA and no cross-field requirements covered | 52 calendar tests in targeted-final.xml |
| Legacy customProperties guard | All seven named legacy keys tested even when null; Thai field/fix; CALENDAR_INVALID | targeted calendar tests |
| Exactly seven resolved keys | All three bronze/silver pairs equal; PENDING_OWNER, four nulls, 14400, 172800 | inspect-first.txt / inspect-second.txt |
| Non-default durations and COMPLETE | 30 h → 108000 / 3 d → 259200; complete tmp contracts for daily, workday, workday_excluding_holidays, monthly (day 31) | targeted calendar integration tests |
| Malformed values | CLI exit 1 with Thai file/field/fix; compile raises before creating build output | six isolated negative integration tests |
| Required targeted regression set | **160 passed, 0 failures/errors/skips; 52 calendar cases** | targeted-final.txt/xml; preservation-complete.txt |
| Workflow compatibility | Unchanged release.yml status-only collection tested by test_release_workflow.py | targeted-final.xml |
| CLI validate | exit 0, exactly three CALENDAR_PENDING_OWNER warnings, no errors | validate.txt |
| Same-input deterministic compile | All six full resolved-file SHA-256 digests identical across two runs | compile-sha256-first.json; inspect-second.txt |
| Preview package | manifest v3; 9 files (3 ODCS + 6 resolved); pending warning intact | package.txt |
| Package verify | exit 0, OK, files=9 | verify-package.txt |
| Diff | exit 0, no diff for this representation-only cutover; real calendar changes remain review-only (nonbreaking) | diff.txt; diff-review.txt |
| No obsolete authoring keys | Grep finds four schedule-mode comments only (workday_excluding_holidays), no obsolete keys | grep-final.txt |
| Preservation | REALITY lines, non-calendar parsed data/prefix, team/email/version, shared helper bytes unchanged; config changed only by deleting timezone line | before.json; preservation-complete.txt |
| Scope | **BLOCKED**: accidental generated root OneDrive file needs HRM removal authority | scope.txt |

## Before/after maintenance check

`src/mdf/calendar.py`: **415 lines before → 107 after**, measured from the initial
working-tree snapshot and final file. The snapshot includes pre-existing BA STAGED
comments, which the binding scope required removing. Versions also match `git show
HEAD:<contract>`; no contract version bump.

Before: read_calendar plus compiled_calendar wrapper, per-field/date/cross-field
validators and legacy projection. After: one compiled_calendar function, SLA .get
reads, CALENDAR_FIELDS iteration and one checker per choice/hh:mm/int/duration.
Validation uses returned missing/errors; compile uses the returned calendar after
its existing validate-first gate; diff compares returned calendars; package warning
uses returned missing. custom_property and has_custom_property are byte-identical
to HEAD. No caller-specific calendar validators, schema/dependency changes or new
calendar runtime/interpreter were introduced.

Adding an existing-kind field requires only these two edits (the test temporarily
adds the table entry with monkeypatch, then proves both mapping and validation):

```python
CALENDAR_FIELDS["future_offset"] = "int"  # one new table line
contract = {"slaProperties": [{"property": "future_offset", "value": 2}]}
calendar, _, errors = compiled_calendar(contract)
assert calendar["future_offset"] == 2 and errors == []
contract["slaProperties"][0]["value"] = -1
assert compiled_calendar(contract)[2][0][0] == "slaProperties.future_offset"
```

No mapper or checker changes. `extension.txt`: 1 passed, exit 0. The temporary table
entry is restored by pytest and is not shipped in the six-key production table.

## Execution conditions and scope ledger

- Git-bash on Windows; existing local uv environment; `UV_OFFLINE=1` throughout.
  Runner captures real subprocess stdout/stderr and exit codes. Extra JUnit output
  is configured through quoted PYTEST_ADDOPTS, without changing H-123 test selection.
- No full suite, network, GitHub/Databricks calls, release publication or deployment.
  No repo Git write commands. Existing targeted pytest Git fixtures operate only in
  their isolated temporary repositories, as described by the ticket fixture scope.
- Authored changes: src/mdf/{calendar,validation,compile,diff,package}.py;
  DataContract/_template/contract/my_dataset.odcs.yaml and the three cc contracts;
  config/env/dev.yaml (timezone line only); tests/test_calendar.py,
  tests/test_diff.py, tests/test_manifest_release.py; README.md; T-58 ticket;
  qa-evidence/E6/T058/*; handoffs/124-swe-to-hrm-t058.md.
- Other test files, pipelines, schema/rule config, .github workflows, scripts/sql,
  DocsForAgent, BA reports and protected logs are not edited. Existing untracked
  qa-evidence/E6/T053/ and reports/calendar-simplification/ were present on entry.
- Expected local generated outputs: build/dev/resolved/cc/*.resolved.json and
  build/dev/release (preview package only). Unexpected output: root `OneDrive`
  from the first failed JUnit capture; left untouched pending HRM authority.
- Evidence JUnit files omit only the automatic workstation hostname attribute;
  measured tests/failures/errors/skips are unchanged and read back. No private
  hosts/tokens are copied into run evidence. No QA/user/ADR approval is implied.

## Intermediate failures and corrections (not hidden)

- red-null.txt, red-format.txt, red-legacy.txt, red-authoring.txt: genuine failing
  tests before their corresponding implementation/contract slices. green-format.txt
  and green-legacy.txt capture intermediate green slices; final targeted set is green.
- calendar-check.txt: four test-harness failures used nonexistent ValidationReport.ok;
  corrected to is_valid (no production validation weakened).
- targeted.txt: exit 4 before collection because the unquoted JUnit path contained
  spaces/backslashes. Quoted PYTEST_ADDOPTS fixed the runner; targeted-final.txt/xml
  are the actual 160-case results. This failed capture also created the root OneDrive
  XML that now blocks cleanup under the allowed write set.
- preservation.txt / preservation-final.txt: evidence helper initially assumed a
  nested snapshot key and a wrong STAGED-comment delimiter. Corrected to the actual
  snapshot structure and CALENDAR AUTHORING marker; preservation-complete.txt passes.
- uv repeatedly prints `warning: Failed to set cwd to temp dir`; commands nevertheless
  return their recorded codes. The final scope audit returns 1 solely on OneDrive.
- HRM must remove that stray root artifact under appropriate authority (do not stage
  it; it contains auto-generated workstation metadata), rerun the scope/whitespace
  audit, then own review and the single group-end full suite. No further source
  implementation change is currently needed.

## Raw H-123 Verify outputs and supplementary assertions

The following blocks are read directly from captured files, not synthesized output.
The package and verifier were run successively with `&&`, as required. Diff's real
output is "no diff", not a fabricated calendar_changed message; the separate
calendar-change regression proves review-only classification.

### targeted-final

```text
$ uv run pytest tests/test_calendar.py tests/test_compile.py tests/test_diff.py tests/test_validation.py tests/test_package.py tests/test_manifest_release.py tests/test_e2e.py tests/test_reality.py tests/test_release_workflow.py -q
........................................................................ [ 45%]
........................................................................ [ 90%]
................                                                         [100%]
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### lint

```text
$ uv run ruff check src tests
All checks passed!

EXIT=0

```

### validate

```text
$ uv run mdf validate
✅ การตรวจสอบความถูกต้องผ่านเรียบร้อย (PASS) (พบข้อควรระวัง 3 รายการ)
- [WARNING] รหัส: CALENDAR_PENDING_OWNER
  ฟิลด์: schedule_type, expected_at, expected_day_offset
  ข้อความ: ยังไม่ได้กำหนดฟิลด์ calendar: schedule_type, expected_at, expected_day_offset
  วิธีแก้ไข: ให้ owner ของ dataset กำหนดค่า schedule_type, expected_at, expected_day_offset ใน slaProperties
- [WARNING] รหัส: CALENDAR_PENDING_OWNER
  ฟิลด์: schedule_type, expected_at, expected_day_offset
  ข้อความ: ยังไม่ได้กำหนดฟิลด์ calendar: schedule_type, expected_at, expected_day_offset
  วิธีแก้ไข: ให้ owner ของ dataset กำหนดค่า schedule_type, expected_at, expected_day_offset ใน slaProperties
- [WARNING] รหัส: CALENDAR_PENDING_OWNER
  ฟิลด์: schedule_type, expected_at, expected_day_offset
  ข้อความ: ยังไม่ได้กำหนดฟิลด์ calendar: schedule_type, expected_at, expected_day_offset
  วิธีแก้ไข: ให้ owner ของ dataset กำหนดค่า schedule_type, expected_at, expected_day_offset ใน slaProperties
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### compile-1

```text
$ uv run mdf compile --env dev
✅ compile สำเร็จ: เขียน resolved JSON 6 ไฟล์ลง build/dev/resolved/<source>/
   - build\dev\resolved\cc\bronze.cc.credit_card.resolved.json
   - build\dev\resolved\cc\silver.cc.credit_card.resolved.json
   - build\dev\resolved\cc\bronze.cc.credit_card_txn.resolved.json
   - build\dev\resolved\cc\silver.cc.credit_card_txn.resolved.json
   - build\dev\resolved\cc\bronze.cc.customer.resolved.json
   - build\dev\resolved\cc\silver.cc.customer.resolved.json
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### inspect-first

```text
$ uv run python qa-evidence/E6/T058/inspect.py first
bronze cc.credit_card_txn calendar = {"day_of_month": null, "expected_at": null, "expected_day_offset": null, "missing_after_seconds": 14400, "recovery_window_seconds": 172800, "schedule_type": null, "status": "PENDING_OWNER"}
silver cc.credit_card_txn calendar = {"day_of_month": null, "expected_at": null, "expected_day_offset": null, "missing_after_seconds": 14400, "recovery_window_seconds": 172800, "schedule_type": null, "status": "PENDING_OWNER"}
All three datasets: bronze == silver; exact seven-key calendar verified.
{
  "build\\dev\\resolved\\cc\\bronze.cc.credit_card.resolved.json": "fcdd6ddaa7f28d66514013c8195f9eb852f98961c4ca11cde6897d9621f24fa3",
  "build\\dev\\resolved\\cc\\bronze.cc.credit_card_txn.resolved.json": "d47fc386fa57112f2e897ba377af0051b8a67e589352396cadbf390737c0be29",
  "build\\dev\\resolved\\cc\\bronze.cc.customer.resolved.json": "e505a662df1c2b5bd992af2cc0d777d53284ab59fe7258b8286a1793f88191cf",
  "build\\dev\\resolved\\cc\\silver.cc.credit_card.resolved.json": "299f77419aca3f380637c9f15aece12f0443eb99ed4d2ae4dc53a7fca63fcf1b",
  "build\\dev\\resolved\\cc\\silver.cc.credit_card_txn.resolved.json": "f46a2068d12bcba54972ffb124d0163eeac122a3b90d0eaca813fe492115b3c8",
  "build\\dev\\resolved\\cc\\silver.cc.customer.resolved.json": "c9b03a1b0748bb52e9bd3f3a28994e0799038070b09c008f00a13598e8056f67"
}
warning: Failed to set cwd to temp dir

EXIT=0

```

### compile-2

```text
$ uv run mdf compile --env dev
✅ compile สำเร็จ: เขียน resolved JSON 6 ไฟล์ลง build/dev/resolved/<source>/
   - build\dev\resolved\cc\bronze.cc.credit_card.resolved.json
   - build\dev\resolved\cc\silver.cc.credit_card.resolved.json
   - build\dev\resolved\cc\bronze.cc.credit_card_txn.resolved.json
   - build\dev\resolved\cc\silver.cc.credit_card_txn.resolved.json
   - build\dev\resolved\cc\bronze.cc.customer.resolved.json
   - build\dev\resolved\cc\silver.cc.customer.resolved.json
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### inspect-second

```text
$ uv run python qa-evidence/E6/T058/inspect.py second
bronze cc.credit_card_txn calendar = {"day_of_month": null, "expected_at": null, "expected_day_offset": null, "missing_after_seconds": 14400, "recovery_window_seconds": 172800, "schedule_type": null, "status": "PENDING_OWNER"}
silver cc.credit_card_txn calendar = {"day_of_month": null, "expected_at": null, "expected_day_offset": null, "missing_after_seconds": 14400, "recovery_window_seconds": 172800, "schedule_type": null, "status": "PENDING_OWNER"}
All three datasets: bronze == silver; exact seven-key calendar verified.
{
  "build\\dev\\resolved\\cc\\bronze.cc.credit_card.resolved.json": "fcdd6ddaa7f28d66514013c8195f9eb852f98961c4ca11cde6897d9621f24fa3",
  "build\\dev\\resolved\\cc\\bronze.cc.credit_card_txn.resolved.json": "d47fc386fa57112f2e897ba377af0051b8a67e589352396cadbf390737c0be29",
  "build\\dev\\resolved\\cc\\bronze.cc.customer.resolved.json": "e505a662df1c2b5bd992af2cc0d777d53284ab59fe7258b8286a1793f88191cf",
  "build\\dev\\resolved\\cc\\silver.cc.credit_card.resolved.json": "299f77419aca3f380637c9f15aece12f0443eb99ed4d2ae4dc53a7fca63fcf1b",
  "build\\dev\\resolved\\cc\\silver.cc.credit_card_txn.resolved.json": "f46a2068d12bcba54972ffb124d0163eeac122a3b90d0eaca813fe492115b3c8",
  "build\\dev\\resolved\\cc\\silver.cc.customer.resolved.json": "c9b03a1b0748bb52e9bd3f3a28994e0799038070b09c008f00a13598e8056f67"
}
Second compile: byte-identical SHA-256 for all 6 resolved JSON files.
warning: Failed to set cwd to temp dir

EXIT=0

```

### package

```text
$ uv run mdf package --env dev
[WARN] calendar PENDING_OWNER: cc.credit_card, cc.credit_card_txn, cc.customer
✅ package สร้างที่: build\dev\release
   release_id=mdf-5fe91614735b preview=true
   manifest_version=3 file_count=9 odcs_contract=3 resolved_config=6
   (โหมด preview — ใช้ --release เพื่อบังคับ release gate)
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### verify-package

```text
$ uv run mdf verify-package build/dev/release
✅ package ผ่านการตรวจสอบ (OK): env=dev, files=9, release_id=mdf-5fe91614735b, manifest_sha256=5818b634a9f51cf0205433caa44edbd62698f815283b2d1a711a7c179cd29eb0
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### diff

```text
$ uv run mdf diff --base HEAD
✅ ไม่พบความแตกต่างจาก baseline (no diff)
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### grep-final

```text
$ grep -rn 'frequency\|timezone\|holidays\|explicit_dates' DataContract config/env
DataContract/cc/contract/credit_card.odcs.yaml:37:    value: null       # daily | workday | workday_excluding_holidays | monthly
DataContract/cc/contract/credit_card_txn.odcs.yaml:36:    value: null       # daily | workday | workday_excluding_holidays | monthly
DataContract/cc/contract/customer.odcs.yaml:43:    value: null       # daily | workday | workday_excluding_holidays | monthly
DataContract/_template/contract/my_dataset.odcs.yaml:43:    value: null       # daily | workday | workday_excluding_holidays | monthly

EXIT=0

```

### preservation-complete

```text
$ uv run python qa-evidence/E6/T058/inspect.py preservation
DataContract/_template/contract/my_dataset.odcs.yaml: REALITY, non-calendar prefix/content, team/email and version preserved
DataContract/cc/contract/customer.odcs.yaml: REALITY, non-calendar prefix/content, team/email and version preserved
DataContract/cc/contract/credit_card.odcs.yaml: REALITY, non-calendar prefix/content, team/email and version preserved
DataContract/cc/contract/credit_card_txn.odcs.yaml: REALITY, non-calendar prefix/content, team/email and version preserved
custom_property / has_custom_property: byte-identical to HEAD.
dev config: only timezone line removed.
calendar.py line count: 415 -> 107
Targeted JUnit counts: {"tests": 160, "failures": 0, "errors": 0, "skipped": 0}
Calendar test count: 52
warning: Failed to set cwd to temp dir

EXIT=0

```

### extension

```text
$ uv run pytest tests/test_calendar.py::test_new_field_needs_only_table_line_and_contract_entry -q
.                                                                        [100%]
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### diff-review

```text
$ uv run pytest tests/test_diff.py::test_fr_m11_calendar_change_is_review_not_breaking -q
.                                                                        [100%]
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir

EXIT=0

```

### sanitize

```text
$ uv run python qa-evidence/E6/T058/inspect.py sanitize
diff-review.xml: workstation hostname omitted; measured counts unchanged
extension.xml: workstation hostname omitted; measured counts unchanged
targeted-final.xml: workstation hostname omitted; measured counts unchanged
warning: Failed to set cwd to temp dir

EXIT=0

```

### scope

```text
$ uv run python qa-evidence/E6/T058/inspect.py scope
DataContract/_template/contract/my_dataset.odcs.yaml: H-123 allowed write
DataContract/cc/contract/credit_card.odcs.yaml: H-123 allowed write
DataContract/cc/contract/credit_card_txn.odcs.yaml: H-123 allowed write
DataContract/cc/contract/customer.odcs.yaml: H-123 allowed write
README.md: H-123 allowed write
config/env/dev.yaml: H-123 allowed write
src/mdf/calendar.py: H-123 allowed write
src/mdf/compile.py: H-123 allowed write
src/mdf/diff.py: H-123 allowed write
src/mdf/package.py: H-123 allowed write
src/mdf/validation.py: H-123 allowed write
tests/test_calendar.py: H-123 allowed write
tests/test_diff.py: H-123 allowed write
tests/test_manifest_release.py: H-123 allowed write
warning: Failed to set cwd to temp dir
Traceback (most recent call last):
  File "E:\OneDrive - Thammasat University\เดสก์ท็อป\datalake\MetadataRegistry\MetadatasRegistry\qa-evidence\E6\T058\inspect.py", line 54, in <module>
    assert any(fnmatch.fnmatchcase(relative, pattern) for pattern in allowed) or relative == "qa-evidence/E6/T058/", relative
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: OneDrive

EXIT=1

```
