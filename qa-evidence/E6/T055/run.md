# T-55 Evidence — compile `calendar` + `reader` + `schema[].pii/pci/tags` + `C-PCI-TOKENISE` + diff review items

วันที่รัน: 2026-10-05 (ตามคำสั่ง H-111) — repo: `MetadatasRegistry` (root ตาม pwd ด้านล่าง)

## 1. Targeted pytest (ก่อนแก้ไฟล์เสร็จ และหลังแก้)

```
$ uv run pytest tests/test_compile.py tests/test_validation.py tests/test_diff.py tests/test_e2e.py tests/test_calendar.py -q
.............................................                            [100%]
EXIT=0   (45 passed — เพิ่ม 2 test ของ FR-M.11 ใน tests/test_diff.py + 1 test ของ AC-52
COMPLETE status ใน tests/test_calendar.py)
```

รันเพิ่มเพื่อความมั่นใจ (ไม่ใช่ตัวตัดสิน แต่ยืนยันไม่กระทบ module อื่นที่ใช้ mdf.calendar/mdf.validation):
```
$ uv run pytest tests/test_compile.py tests/test_validation.py tests/test_diff.py tests/test_e2e.py \
  tests/test_calendar.py tests/test_reality.py tests/test_rules.py tests/test_fk_validation.py \
  tests/test_trace.py tests/test_package.py tests/test_cli.py -q
........................................................................ [ 81%]
................                                                         [100%]
EXIT=0
```

## 2. `uv run mdf validate` — exit 0, warning 3 รายการ, ไม่มี `recovery_window` ในรายการ field ที่ขาด

```
$ uv run mdf validate; echo "EXIT=$?"
✅ การตรวจสอบความถูกต้องผ่านเรียบร้อย (PASS) (พบข้อควรระวัง 3 รายการ)
- [WARNING] รหัส: CALENDAR_PENDING_OWNER
  ฟิลด์: timezone, expected_at, expected_day_offset, business_schedule
  ...
- [WARNING] รหัส: CALENDAR_PENDING_OWNER
  ฟิลด์: timezone, expected_at, expected_day_offset, business_schedule
  ...
- [WARNING] รหัส: CALENDAR_PENDING_OWNER
  ฟิลด์: timezone, expected_at, expected_day_offset, business_schedule
  ...
EXIT=0
```

ยืนยัน: มี warning ครบ 3 dataset (`customer`, `credit_card`, `credit_card_txn`) และ field ที่ขาดไม่มี `recovery_window` อยู่ในรายการ (เหลือแค่ `timezone, expected_at, expected_day_offset, business_schedule`) ตามที่ H-111 ข้อ 2 กำหนด เพราะเพิ่ม `slaProperties: {property: recovery_window, value: 2, unit: d}` ในทั้ง 3 contract แล้ว

## 3. `uv run mdf compile --env dev` + พิมพ์ `calendar`, `reader`, `card_pan` จาก bronze resolved JSON

```
$ rm -rf build && uv run mdf compile --env dev
✅ compile สำเร็จ: เขียน resolved JSON 6 ไฟล์ลง build/dev/resolved/<source>/
   - build\dev\resolved\cc\bronze.cc.credit_card.resolved.json
   - build\dev\resolved\cc\silver.cc.credit_card.resolved.json
   - build\dev\resolved\cc\bronze.cc.credit_card_txn.resolved.json
   - build\dev\resolved\cc\silver.cc.credit_card_txn.resolved.json
   - build\dev\resolved\cc\bronze.cc.customer.resolved.json
   - build\dev\resolved\cc\silver.cc.customer.resolved.json
EXIT=0

$ python -c "
import json
d=json.load(open('build/dev/resolved/cc/bronze.cc.credit_card_txn.resolved.json', encoding='utf-8'))
print('calendar=', d['calendar'])
print('reader=', d['reader'])
print('card_pan=', [c for c in d['schema'] if c['name']=='card_pan'])
"
calendar= {'day_of_month': None, 'day_of_month_policy': None, 'effective_from': None,
'effective_to': None, 'exceptions': [], 'expected_at': None, 'expected_day_offset': None,
'explicit_dates': [], 'frequency': 'daily', 'holidays': [], 'missing_after_seconds': 14400,
'recovery_window_seconds': 172800, 'schedule_type': None, 'status': 'PENDING_OWNER', 'timezone': None}
reader= {'encoding': 'utf-8', 'file_pattern': 'credit_card_txn_{{business_date}}*.csv', 'format': 'csv',
'header': True, 'partition_pattern': '', 'run_grain': 'business_date', 'source_type': 'batch_file'}
card_pan= [{'classification': 'sensitive', 'description': "REALITY: one row per file uses a PAN
that appears in no credit_card file (prawden 8). Also: every txn on business_date=2026-09-10
references cards whose master file was never delivered - the join must degrade gracefully rather
than dropping a day of revenue.", 'logicalType': 'string', 'name': 'card_pan', 'pci': True,
'physicalType': 'string', 'pii': True, 'required': True, 'tags': ['dq:fk']}]
```

ยืนยันตาม AC-54/AC-55: `calendar.status = PENDING_OWNER`, `expected_at`/`expected_day_offset`/
`timezone`/`schedule_type` = `null`, `missing_after_seconds = 14400`, `recovery_window_seconds = 172800`
(หลังเพิ่ม `recovery_window` ใน contract) · `reader.file_pattern` คง template `{{business_date}}`/`*`
ตามต้นฉบับ, `format = csv`, `header = true`, `encoding = utf-8`, `run_grain = business_date`,
`source_type = batch_file` · `card_pan` ของ `credit_card_txn` มี `pii: true, pci: true`

## 4. bronze vs silver `calendar`/`reader`/`schema` ต้องเหมือนกันทุก byte (`json.dumps(sort_keys=True)`)

สคริปต์เทียบ: `qa-evidence/E6/T055/compare_bronze_silver.py`

```
$ uv run python qa-evidence/E6/T055/compare_bronze_silver.py; echo "EXIT=$?"
[OK] customer.calendar: bronze == silver (json.dumps sort_keys=True)
[OK] customer.reader: bronze == silver (json.dumps sort_keys=True)
[OK] customer.schema: bronze == silver (json.dumps sort_keys=True)
[OK] credit_card.calendar: bronze == silver (json.dumps sort_keys=True)
[OK] credit_card.reader: bronze == silver (json.dumps sort_keys=True)
[OK] credit_card.schema: bronze == silver (json.dumps sort_keys=True)
[OK] credit_card_txn.calendar: bronze == silver (json.dumps sort_keys=True)
[OK] credit_card_txn.reader: bronze == silver (json.dumps sort_keys=True)
[OK] credit_card_txn.schema: bronze == silver (json.dumps sort_keys=True)
EXIT=0
```

## 5. Compile 2 ครั้ง → byte-identical ทุกไฟล์ (AC-11)

```
$ rm -rf build && uv run mdf compile --env dev >/dev/null && cp -r build "$LOCALAPPDATA/Temp/t55_run1/build"
$ rm -rf build && uv run mdf compile --env dev >/dev/null && cp -r build "$LOCALAPPDATA/Temp/t55_run2/build"
$ python -c "... sha256 ของทุกไฟล์ run1 vs run2 ..."
OK dev\resolved\cc\bronze.cc.credit_card.resolved.json 1bba5a9e50e0 1bba5a9e50e0
OK dev\resolved\cc\bronze.cc.credit_card_txn.resolved.json 2c9bb42e87e4 2c9bb42e87e4
OK dev\resolved\cc\bronze.cc.customer.resolved.json b40df3a81d0d b40df3a81d0d
OK dev\resolved\cc\silver.cc.credit_card.resolved.json 759d35330e93 759d35330e93
OK dev\resolved\cc\silver.cc.credit_card_txn.resolved.json 8c3e3ffa5129 8c3e3ffa5129
OK dev\resolved\cc\silver.cc.customer.resolved.json 9126f4a5cbed 9126f4a5cbed
ALL BYTE-IDENTICAL: True
```

## 6. Negative cases (AC-55 And)

### 6a. ลบ `pii` ออกจากคอลัมน์หนึ่ง (tmp copy ของ `credit_card.odcs.yaml`, ลบ `pii` ของ `card_pan`)
```
is_valid= False
PRIVACY_FLAG_INVALID in codes: True
exit would be 1
```

### 6b. ตั้ง `pci: true` บนคอลัมน์ที่ pipeline ไม่ tokenise (tmp copy, ตั้ง `customer_id.pci = true` — pipeline ของ `credit_card` ไม่ตั้ง tokenise ให้ `customer_id`)
```
is_valid= False
C-PCI-TOKENISE in codes: True
```

### 6c. ไม่มี server ของ env ที่ compile (tmp copy, ลบ `servers:` ทั้ง block ของ `customer.odcs.yaml`)
```
is_valid= False
READER_SERVER_MISSING in codes: True
CTR_SERVERS_REQUIRED in codes: True
```

### 6d. ไม่มี `file_pattern` (tmp copy, ลบ `customProperties.file_pattern` ของ `customer.odcs.yaml`)
```
is_valid= False
READER_FILE_PATTERN_MISSING in codes: True
```

### 6e. (Q5) pipeline ของ `customer` ไม่ถูกแก้
ตรวจด้วย `git diff --stat DataContract/cc/pipeline/customer.pipeline.yaml` → ไม่มี diff (ไฟล์นี้ไม่อยู่ใน
allowed_writes ของ H-111 และ SWE ไม่ได้แก้ไฟล์นี้เลยทั้ง task)

## 7. FR-M.11 — `mdf diff` รายงาน calendar/pii/pci เป็นรายการ "ต้อง review"

Unit test ใหม่ใน `tests/test_diff.py`:
`test_fr_m11_pci_flag_change_is_review_not_breaking`, `test_fr_m11_calendar_change_is_review_not_breaking`
(รวมอยู่ใน pytest run ข้อ 1 ด้านบน — ทั้งคู่ผ่าน)

เพิ่ม unit test ยืนยัน AC-52 `calendar.status = COMPLETE` โดยตรงใน `tests/test_calendar.py`:
`test_ac52_compiled_calendar_complete_status_and_sorted_lists` — ใส่ค่า calendar ครบ (`daily`
+ holidays, timezone, expected_at, expected_day_offset, recovery_window) ใน tmp contract แล้ว
ยืนยัน `compiled_calendar()` คืน `status=COMPLETE`, `missing_after_seconds=14400` (จาก latency
4h ไม่ hardcode), `recovery_window_seconds=172800` (จาก recovery_window 2d), holidays เรียงแล้ว,
และ compile จริงแล้ว bronze==silver ของ `calendar` (ผ่านในรัน pytest ข้อ 1)

รันจริงกับ repo (เทียบ contract ปัจจุบันที่เพิ่ม `recovery_window` กับ baseline `88b982d` ที่ไม่มี):
```
$ uv run mdf diff --base 88b982d; echo "EXIT=$?"
ℹ️ การเปลี่ยนแปลงอื่น ๆ 3 รายการ:
  - [calendar_changed] cc.credit_card: calendar เปลี่ยนจาก {...'recovery_window_seconds': None...}
    เป็น {...'recovery_window_seconds': 172800...} — ต้อง review
  - [calendar_changed] cc.credit_card_txn: calendar เปลี่ยนจาก {...} เป็น {...} — ต้อง review
  - [calendar_changed] cc.customer: calendar เปลี่ยนจาก {...} เป็น {...} — ต้อง review
EXIT=0
```
ยืนยัน: `kind = non_breaking` (ไม่ใช่ `breaking`) → `has_breaking = False` → exit 0 ตามที่ FR-M.11 ต้องการ
(การเปลี่ยน calendar ไม่ทำให้ gate release พัง แค่ขึ้นเป็นรายการให้รีวิว)

## 8. `uv run ruff check src tests`

```
$ uv run ruff check src tests
E501 Line too long (101 > 100)
   --> src\mdf\package.py:331:111          (pre-existing — ห้ามแก้ ตาม H-111 ข้อ 7)
E501 Line too long (106 > 100)
   --> src\mdf\package.py:336:106          (pre-existing — ห้ามแก้)
E501 Line too long (101 > 100)
   --> tests\test_deliver_release.py:430:101  (pre-existing — ห้ามแก้)
Found 3 errors.
EXIT=1
```
ไม่มี error ใหม่จากไฟล์ที่แก้ใน T-55 (`src/mdf/calendar.py`, `src/mdf/compile.py`,
`src/mdf/validation.py`, `src/mdf/diff.py`, `tests/test_diff.py`) — เหลือแค่ 3 จุดเดิมตาม baseline
(exit 1 เป็นค่าปกติของ repo นี้ เพราะมี pre-existing error ที่ตกลงไว้แล้วว่าไม่แก้)

## 9. Full pytest suite (รันครั้งเดียวหลังแก้ไฟล์เสร็จ, background, ไม่แก้ไฟล์ระหว่างรัน)

Log เต็ม: `qa-evidence/E6/T055/full-pytest.log`

```
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
...............                                                         [100%]
EXIT=0
```

**หมายเหตุความสมบูรณ์ของ log:** เมื่อ redirect stdout ของ `uv run pytest -q` ไปไฟล์ด้วย `>` ใน
background process บน git-bash/Windows บรรทัดสรุปท้าย (`N passed in X.XXs`) ไม่ถูกเขียนลง log (แค่
`EXIT=0` ต่อจาก progress bar สุดท้ายทันที) — เป็น buffering artifact ของ `uv run` + redirect แบบนี้
ไม่ใช่ failure (ยืนยันด้วย `EXIT=$?` = 0 ที่จับจาก process เดียวกันจริง) นับจุด (`.`) ในไฟล์ log ได้
231 จุด = 231 tests passed (baseline 228 + 2 test ใหม่ของ FR-M.11 ใน `tests/test_diff.py` + 1 test
ใหม่ของ AC-52 COMPLETE status ใน `tests/test_calendar.py`) ไม่มี `F`/`E`/`x` ปรากฏในไฟล์เลย ยืนยัน
ไม่มี failure/error (ไฟล์นี้คือรันรอบที่ 2 — รอบแรกรันก่อนเพิ่ม test AC-52 ได้ 230; เพิ่ม test แล้ว
รัน full suite ซ้ำตามกติกา H-111 ข้อ 8 "ถ้าต้องแก้หลัง full suite ให้รันใหม่")

## 10. Contract version bump

ไม่มีการ bump version — `mdf diff --base 88b982d` (ข้อ 7) ยืนยันว่าการเพิ่ม `slaProperties.recovery_window`
ไม่ใช่ breaking change (ไม่ลบคอลัมน์ ไม่เปลี่ยน type ไม่เปลี่ยน required) จึงไม่ต้อง bump ตามกติกา diff เดิม
(H-111 ข้อ 2 บรรทัดสุดท้าย) — contract `customer`/`credit_card`/`credit_card_txn` ยังคงที่ `version: 1.0.0`
เหมือนเดิม แต่ `lineage.contract_sha256` ใน resolved JSON เปลี่ยนไปเพราะเนื้อ contract เปลี่ยน (คาดหมายแล้ว
ตาม H-111 ข้อ 2)

## ไฟล์ที่แก้ไข (ทั้งหมดอยู่ใน allowed_writes ของ H-111)

- `src/mdf/calendar.py` — เพิ่ม `custom_property`, `has_custom_property`, `compiled_calendar()`
  (ไม่แก้ `read_calendar()` เดิม)
- `src/mdf/compile.py` — เพิ่ม `build_reader()`, เรียก `compiled_calendar()`/`build_reader()`,
  เพิ่ม `pii`/`pci`/`tags` ในแต่ละ column, เพิ่ม key `calendar`/`reader` ใน resolved dict
- `src/mdf/validation.py` — เพิ่ม `get_pci_columns()`, privacy flag bool check (`PRIVACY_FLAG_INVALID`),
  `C-PCI-TOKENISE` check ใน `validate_pipeline_file`, `validate_reader_fields()`
  (`READER_SERVER_MISSING`/`READER_FILE_PATTERN_MISSING`)
- `src/mdf/diff.py` — เพิ่มการเทียบ `pii`/`pci` (`privacy_flag_changed`) และ `calendar`
  (`calendar_changed`) เป็นรายการ `non_breaking` (FR-M.11)
- `DataContract/cc/contract/customer.odcs.yaml` — เพิ่ม `slaProperties.recovery_window = 2 d`
- `DataContract/cc/contract/credit_card.odcs.yaml` — เพิ่ม `slaProperties.recovery_window = 2 d`
- `DataContract/cc/contract/credit_card_txn.odcs.yaml` — เพิ่ม `slaProperties.recovery_window = 2 d`
- `tests/test_diff.py` — เพิ่ม 2 test ของ FR-M.11
- `tests/test_calendar.py` — เพิ่ม 1 test ของ AC-52 (`compiled_calendar()` COMPLETE status)
- `qa-evidence/E6/T055/run.md` (ไฟล์นี้), `qa-evidence/E6/T055/compare_bronze_silver.py`,
  `qa-evidence/E6/T055/full-pytest.log`
- `tickets/E6/T055-compile-calendar-reader-privacy.md` — อัปเดตสถานะ

ไม่ได้แก้ (ตามที่คาดไว้): `config/rules/contract.rules.json`, `config/rules/pipeline.rules.json`
(`C-PCI-TOKENISE` เขียนเป็น Python แทนตาม H-111 ข้อ 3 เพราะต้องเทียบข้าม contract-pipeline),
`tests/test_compile.py`, `tests/test_validation.py`, `tests/test_e2e.py`, `tests/test_reality.py`
(ของเดิมผ่านหมดอยู่แล้ว ไม่จำเป็นต้องแก้)
