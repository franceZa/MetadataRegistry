# T-56 — QA evidence (SWE run) · manifest v3 + ODCS contract ใน release

- เครื่อง: Windows 10 (dev) · git-bash · `uv run` · Python 3.13 (venv ของโปรเจกต์)
- HEAD = `5a9126bc35c9` · working tree มีงานที่ยังไม่ commit ของ T-48…T-55 (ตั้งใจ) + T-56 (ใบนี้)
- ไม่มี git write · ไม่ต่อ Databricks/GitHub · **ไม่ได้รัน full suite** (H-113 ข้อ 8 — HRM รัน batch หลัง T-57)
- log ดิบ: `verify-cli.log`, `as32_ac11.log`, `compat.log`, `targeted-pytest.log`, `ruff-after.log` (โฟลเดอร์เดียวกัน)
- script ที่ใช้ซ้ำได้: `as32_ac11_check.py`, `compat_fixtures.py` (อ่านอย่างเดียว · ใช้ scratch dir ใน `%LOCALAPPDATA%\Temp` แล้วลบทิ้ง)

ทุกข้อด้านล่างรันกับโค้ดสุดท้าย (หลัง patch ครั้งสุดท้ายของ `package.py`/`compile.py`)

## 1. Targeted pytest (H-113 Verify ข้อ 1)

```
$ uv run pytest tests/test_package.py tests/test_manifest_release.py tests/test_register.py \
    tests/test_deliver_release.py tests/test_e2e.py tests/test_cli.py -q -p no:cacheprovider
........................................................................ [ 63%]
..........................................                               [100%]
EXIT=0
```
collect = **114 tests** (test_package 36 · test_manifest_release 20 · test_register 17 ·
test_deliver_release 24 · test_e2e 7 · test_cli 10) → 114 passed, exit 0 ·
`test_deliver_release.py` ใช้เวลาหลายนาที (fake CLI ผ่าน bash; ช้าสุด 180 s/test) จึงรันเป็น background

test ใหม่ของใบนี้ = 22 ตัว (`test_package.py` 19 · `test_cli.py` 2 · `test_deliver_release.py` 1)

## 2. compile → package → verify-package (Verify ข้อ 2) · AC-56

```
$ uv run mdf compile --env dev
✅ compile สำเร็จ: เขียน resolved JSON 6 ไฟล์ลง build/dev/resolved/<source>/
EXIT compile=0
$ uv run mdf package --env dev
[WARN] calendar PENDING_OWNER: cc.credit_card, cc.credit_card_txn, cc.customer
✅ package สร้างที่: build\dev\release
   release_id=mdf-5a9126bc35c9 preview=true
   manifest_version=3 file_count=9 odcs_contract=3 resolved_config=6
   (โหมด preview — ใช้ --release เพื่อบังคับ release gate)
EXIT package=0
$ uv run mdf verify-package build/dev/release
✅ package ผ่านการตรวจสอบ (OK): env=dev, files=9, release_id=mdf-5a9126bc35c9, manifest_sha256=8d6b824c1105abec37301e988f1a35624d992b25d9e6cf601d99a0c77e9c4923
EXIT verify=0
```
- verify-package **ไม่มี `[WARN]`** ✅
- `[WARN] calendar PENDING_OWNER` มาจาก `mdf package` (T-54/T-55 · AS-30 · ไม่ block release) ไม่ใช่ verify-package และไม่ใช่ `[WARN] legacy`

## 3. ไฟล์ใน release + manifest.json (Verify ข้อ 3) · AC-56

```
$ find build/dev/release -type f | sort
build/dev/release/cc/bronze.cc.credit_card.resolved.json
build/dev/release/cc/bronze.cc.credit_card_txn.resolved.json
build/dev/release/cc/bronze.cc.customer.resolved.json
build/dev/release/cc/credit_card.odcs.yaml
build/dev/release/cc/credit_card_txn.odcs.yaml
build/dev/release/cc/customer.odcs.yaml
build/dev/release/cc/silver.cc.credit_card.resolved.json
build/dev/release/cc/silver.cc.credit_card_txn.resolved.json
build/dev/release/cc/silver.cc.customer.resolved.json
build/dev/release/manifest.json
build/dev/release/validation-report.json
```
`manifest.json` (ตัดเฉพาะ field ที่ไม่ใช่ files[] บางส่วน · ฉบับเต็มอยู่ใน `verify-cli.log`):
```json
{
  "manifest_version": 3,
  "release_id": "mdf-5a9126bc35c9",
  "environment": "dev",
  "source_commit": "5a9126bc35c9fac28bf7b2a222eb9ac501303924",
  "compiler_revision": "0.1.0+src.106088cbfdd7",
  "ci_run_url": null,
  "file_count": 9,
  "files": [
    {"path": "cc/bronze.cc.credit_card.resolved.json",     "sha256": "4eae6b94…", "kind": "resolved_config", "source": "cc", "dataset": "credit_card",     "layer": "bronze"},
    {"path": "cc/bronze.cc.credit_card_txn.resolved.json", "sha256": "d124e9bf…", "kind": "resolved_config", "source": "cc", "dataset": "credit_card_txn", "layer": "bronze"},
    {"path": "cc/bronze.cc.customer.resolved.json",        "sha256": "3bd41162…", "kind": "resolved_config", "source": "cc", "dataset": "customer",        "layer": "bronze"},
    {"path": "cc/credit_card.odcs.yaml",     "sha256": "1718f4e1edb8428f9131c8ada07b7285f946412e5492b97f254c22edcf1a03f7", "kind": "odcs_contract", "source": "cc", "dataset": "credit_card"},
    {"path": "cc/credit_card_txn.odcs.yaml", "sha256": "145c94d42d8e0e7faea58e940bedfc43210859328506dde81b26c77c419eef3b", "kind": "odcs_contract", "source": "cc", "dataset": "credit_card_txn"},
    {"path": "cc/customer.odcs.yaml",        "sha256": "38813858c933deeb3db47dc87cb0c526a18cc9b3c95d06f3da603089a04bcb0b", "kind": "odcs_contract", "source": "cc", "dataset": "customer"},
    {"path": "cc/silver.cc.credit_card.resolved.json",     "sha256": "9b62b8e7…", "kind": "resolved_config", "source": "cc", "dataset": "credit_card",     "layer": "silver"},
    {"path": "cc/silver.cc.credit_card_txn.resolved.json", "sha256": "af4f43fb…", "kind": "resolved_config", "source": "cc", "dataset": "credit_card_txn", "layer": "silver"},
    {"path": "cc/silver.cc.customer.resolved.json",        "sha256": "c9419fa5…", "kind": "resolved_config", "source": "cc", "dataset": "customer",        "layer": "silver"}
  ],
  "validation_report_sha256": "8e500692…",
  "preview": true
}
```
9 entry · เรียงตาม `path` · `file_count = 9` · `layer` มีเฉพาะ `resolved_config` ·
manifest ไม่ list ตัวเอง (assert ใน `tests/test_manifest_release.py::test_ac35_release_manifest_has_fr_f2_fields`)

## 4. AS-32 — sha256 contract ที่คัดลอก บน Windows (Verify ข้อ 4)

```
$ uv run python qa-evidence/E6/T056/as32_ac11_check.py "$LOCALAPPDATA/Temp/t56_snap"
== AS-32: bundled contract vs working tree vs HEAD vs lineage ==
platform: win32
-- customer
   bundle   38813858c933deeb3db47dc87cb0c526a18cc9b3c95d06f3da603089a04bcb0b  CRLF=False
   worktree 38813858c933deeb3db47dc87cb0c526a18cc9b3c95d06f3da603089a04bcb0b  CRLF=False
   HEAD     2c6a0af2612d5bc8734e3aaaf0efe9eba51ceb1cf27a3b6a6a7b26cc62f1163e  (== worktree: False)
   lineage.bronze.contract_sha256 38813858…bcb0b  bundle_path=cc/customer.odcs.yaml  contract_file=DataContract/cc/contract/customer.odcs.yaml
   lineage.silver.contract_sha256 38813858…bcb0b  bundle_path=cc/customer.odcs.yaml  contract_file=DataContract/cc/contract/customer.odcs.yaml
   bundle==worktree, sha==lineage(x2), bundle_path ok, no CRLF -> [True, True, True, True]
-- credit_card
   bundle   1718f4e1edb8428f9131c8ada07b7285f946412e5492b97f254c22edcf1a03f7  CRLF=False
   worktree 1718f4e1edb8428f9131c8ada07b7285f946412e5492b97f254c22edcf1a03f7  CRLF=False
   HEAD     6be1dc020514e0fb6739578e2ab3ddd4852bb07ff35a906f3d321aa072d3a591  (== worktree: False)
   lineage.bronze/silver.contract_sha256 1718f4e1…03f7 (ทั้งคู่) · bundle_path=cc/credit_card.odcs.yaml
   bundle==worktree, sha==lineage(x2), bundle_path ok, no CRLF -> [True, True, True, True]
-- credit_card_txn
   bundle   145c94d42d8e0e7faea58e940bedfc43210859328506dde81b26c77c419eef3b  CRLF=False
   worktree 145c94d42d8e0e7faea58e940bedfc43210859328506dde81b26c77c419eef3b  CRLF=False
   HEAD     97bdbb222333523e09e72b71f5d1c0b4bf6fa0993396811fbc51090404d746d0  (== worktree: False)
   lineage.bronze/silver.contract_sha256 145c94d4…ef3b (ทั้งคู่) · bundle_path=cc/credit_card_txn.odcs.yaml
   bundle==worktree, sha==lineage(x2), bundle_path ok, no CRLF -> [True, True, True, True]
AS-32 RESULT: PASS
```
- bundle = working tree = `lineage.contract_sha256` ของ bronze **และ** silver ทุก dataset · ไม่มี CRLF → **ไม่ต้อง normalise** (`.gitattributes` `* text=auto eol=lf` ทำงาน)
- **HEAD ≠ working tree ทั้ง 3 ไฟล์** — เพราะ `recovery_window` ของ T-55 ยังไม่ commit:
  ```
  $ git diff --numstat HEAD -- DataContract/cc/contract/
  3  0  DataContract/cc/contract/credit_card.odcs.yaml
  3  0  DataContract/cc/contract/credit_card_txn.odcs.yaml
  3  0  DataContract/cc/contract/customer.odcs.yaml
  $ git diff HEAD -- DataContract/cc/contract/customer.odcs.yaml
  +  - property: recovery_window # AS-31: 2 d retry window before escalation (CR-01)
  +    value: 2
  +    unit: d
  ```
  ต่างกันแค่ 3 บรรทัดที่เพิ่มต่อไฟล์ ไม่มีบรรทัดถูกแก้หรือลบ · หลัง commit T-55 แล้ว ค่า "ไฟล์ใน git" จะ = bundle (HRM รันสคริปต์นี้ซ้ำหลัง commit ได้)
- โค้ด: `build_package` อ่าน `lineage.contract_file` จาก resolved JSON ที่ compile เพิ่งเขียน แล้วคัดลอก **bytes ดิบ** (`read_bytes`/`write_bytes` ไม่ผ่าน YAML load/dump) · ถ้า sha256 ไม่ตรง `lineage.contract_sha256` (ไฟล์ถูกแก้ระหว่าง compile กับ package) → `RuntimeError [PACKAGE_CONTRACT_CHANGED]` ไม่ออก package

## 5. AC-57 — tamper 7 กรณี → `[TAMPERED]` (Verify ข้อ 5)

```
$ uv run pytest tests/test_package.py tests/test_cli.py -rA -p no:cacheprovider \
    -k "ac56 or ac57 or fr_m8 or ac11 or unknown or v1_flat or v2_package or v3 or contract"
PASSED tests/test_package.py::test_verify_v1_flat_package_ok_with_legacy_warning
PASSED tests/test_package.py::test_verify_v2_package_ok_no_warning
PASSED tests/test_package.py::test_verify_unknown_manifest_version
PASSED tests/test_package.py::test_ac56_v3_manifest_entries_kind_source_dataset_layer
PASSED tests/test_package.py::test_ac56_bundled_contract_matches_lineage_and_source_bytes
PASSED tests/test_package.py::test_ac56_v3_verify_ok_without_warning
PASSED tests/test_package.py::test_ac57_case1_contract_one_byte_changed
PASSED tests/test_package.py::test_ac57_case2_contract_and_entry_removed
PASSED tests/test_package.py::test_ac57_case3_kind_other
PASSED tests/test_package.py::test_ac57_case4_dataset_field_does_not_match_filename
PASSED tests/test_package.py::test_ac57_case5_extra_contract_not_in_manifest
PASSED tests/test_package.py::test_ac57_case6_lineage_sha_edited_and_manifest_rehashed
PASSED tests/test_package.py::test_ac57_case7_manifest_version_4_unknown
PASSED tests/test_package.py::test_fr_m8_kind_is_read_from_manifest_not_extension
PASSED tests/test_package.py::test_fr_m8_missing_kind_rejected
PASSED tests/test_package.py::test_fr_m8_contract_bundle_path_mismatch
PASSED tests/test_package.py::test_fr_m8_file_count_mismatch_rejected
PASSED tests/test_package.py::test_fr_m8_missing_silver_layer_rejected
PASSED tests/test_package.py::test_fr_m8_v3_keeps_v2_traversal_rule
PASSED tests/test_package.py::test_ac57_and_as33_real_v2_package_ok_no_warning
PASSED tests/test_package.py::test_ac57_and_real_v1_flat_package_ok_with_legacy_warning
PASSED tests/test_package.py::test_ac11_package_twice_byte_identical
PASSED tests/test_cli.py::test_package_prints_manifest_v3_summary
PASSED tests/test_cli.py::test_verify_package_tampered_contract_exit_one
24 passed, 22 deselected in 3.21s
```
| SSOT AC-57 | test | ข้อความที่ assert (นอกจาก `[TAMPERED]`) |
|---|---|---|
| (1) แก้ `cc/customer.odcs.yaml` 1 byte | `test_ac57_case1_…` + CLI `test_verify_package_tampered_contract_exit_one` (exit 1) | `cc/customer.odcs.yaml` (sha256 ไม่ตรง) |
| (2) ลบไฟล์ + entry | `test_ac57_case2_…` (แก้ `file_count` ให้ตรงด้วย) | `cc.customer` … `odcs_contract` 1 ไฟล์พอดี แต่พบ 0 |
| (3) `kind: other` | `test_ac57_case3_…` | `kind 'other'` ไม่อยู่ใน whitelist |
| (4) `dataset` ไม่ตรงชื่อไฟล์ | `test_ac57_case4_…` | path ไม่ตรง kind/source/dataset (ควรเป็น `cc/credit_card.odcs.yaml`) |
| (5) `cc/extra.odcs.yaml` ไม่อยู่ใน manifest | `test_ac57_case5_…` | ไฟล์แปลกปลอม `cc/extra.odcs.yaml` |
| (6) แก้ `lineage.contract_sha256` + rehash ใน manifest | `test_ac57_case6_…` | `lineage.contract_sha256` ไม่ตรงกับ contract ที่แนบ |
| (7) `manifest_version: 4` | `test_ac57_case7_…` | `unknown manifest_version` |

กรณีเสริม (FR-M.8): `kind` อ่านจาก manifest ไม่ใช่นามสกุล (ตั้ง `.odcs.yaml` เป็น `resolved_config`+`layer` → TAMPERED เพราะชื่อที่สร้างจาก field ≠ path) · ไม่มี `kind` · `contract_bundle_path` ชี้ผิด · `file_count` ≠ `len(files)` · ขาด silver · v3 ยังใช้กติกา traversal ของ v2

## 6. v1 / v2 / v4 compat ผ่าน CLI จริง (Verify ข้อ 6) · AC-57 And · AC-48 · AS-33

```
$ uv run python qa-evidence/E6/T056/compat_fixtures.py "$LOCALAPPDATA/Temp/t56_compat"
--- fixture v1: exit=0
✅ package ผ่านการตรวจสอบ (OK): env=dev, files=6, release_id=mdf-5a9126bc35c9, manifest_sha256=d7ca12f3…
   [WARN] legacy flat layout (manifest_version 1)
--- fixture v2: exit=0
✅ package ผ่านการตรวจสอบ (OK): env=dev, files=6, release_id=mdf-5a9126bc35c9, manifest_sha256=e418b3a3…
--- fixture v4: exit=1
[TAMPERED] unknown manifest_version: 4
```
- fixture สร้างจาก v3 จริง: v2 = ตัด contract + field ของ v3 ออก, `manifest_version 2` · v1 = flatten v2 · v4 = v3 ตั้ง `manifest_version 4`
- v2 **ไม่มีคำเตือนใด ๆ** (AS-33) · v1 มี `[WARN] legacy flat layout` · 4 = unknown
- AC-48: test เดิม `test_verify_unknown_manifest_version` เปลี่ยน `3` → `4` (ไม่ลบ · assertion เท่าเดิม: `"unknown manifest_version"` + `"TAMPERED"`)
- fixture v1 ของ `test_deliver_release.py` (`_flatten_to_v1` เดิม) ยังสร้างจาก package จริง → ตอนนี้ได้ v1 ที่มี 9 ไฟล์ flat (รวม `.odcs.yaml`) และ `test_v1_regression_flat_layout_warns_and_still_copies` ยังผ่าน (v1 verifier ไม่สนใจ field `kind`)

## 7. register.py + deliver_release.sh กับ v3 (fake) · ticket AC ข้อ 4

ไม่ได้แก้ `src/mdf/register.py`, `scripts/deliver_release.sh`, `tests/fakes/**` (mtime: register.py 2026-09-27, deliver_release.sh/fakes 2026-10-04 — ก่อนใบนี้)

- `tests/test_register.py::test_ac42_known_release_id_registers` — package จริง (v3) → register ผ่าน, row `file_count == 9` (เดิม 6)
- `tests/test_deliver_release.py::test_t56_v3_from_dir_cd3_copies_odcs_yaml_into_source_and_registers_9` (ใหม่) —
  `deliver_release.sh <rid> --from-dir <v3 pkg>` ผ่าน CD-1…CD-8 ใน fake: sha256 ของทั้ง 9 entry บน Volume ปลอม = manifest ·
  upload ครบ `cc/{credit_card,credit_card_txn,customer}.odcs.yaml` · upload รวม 11 ไฟล์ (9 + validation-report + manifest) · `manifest.json` เป็นตัวสุดท้าย ·
  evidence ไม่มี `[WARN]` · มี `- CD-4:` · registry = `REGISTERED`,`ACTIVATED` ที่ `file_count = 9` และ `manifest_sha256` ตรง
- test เดิมอื่นของ deliver (v1 legacy, zip, AC-38/39/49) ผ่านทั้งหมดโดยไม่ต้องแก้ (24/24)

## 8. AC-11 — package 2 ครั้ง byte-identical (Verify ข้อ 7)

```
== AC-11: package twice -> byte-identical ==
files compared: 11
differing files: []
file-set difference: []
commit/run-bound fields (same here because same commit): {'release_id': 'mdf-5a9126bc35c9', 'source_commit': '5a9126bc35c9fac28bf7b2a222eb9ac501303924', 'compiler_revision': '0.1.0+src.106088cbfdd7', 'ci_run_url': None}
AC-11 RESULT: PASS
```
+ `tests/test_package.py::test_ac11_package_twice_byte_identical` PASS
- ทั้ง 11 ไฟล์ (รวม `manifest.json`) byte-identical เมื่อรัน 2 ครั้งบน tree เดียวกัน
- field ที่ผูกกับ commit/run (เปลี่ยนเมื่อ commit/run เปลี่ยน — ไม่นับเป็น non-determinism): `release_id`, `source_commit`, `compiler_revision` (`+src.<hash ของ src/mdf>`), `ci_run_url` (`GITHUB_RUN_ID`), `preview` (dirty tree/`--release`) · ค่าในรอบนี้ไม่เปลี่ยนเพราะ commit เดียวกัน
- หมายเหตุ: `compiler_revision` เปลี่ยนจาก `…413f9ffd2c44` (รันแรก) เป็น `…106088cbfdd7` เพราะแก้ `src/mdf/*.py` ระหว่างรอบ — เป็นพฤติกรรมที่ตั้งใจ (hash ของโค้ด compiler)

## 9. ruff (Verify ข้อ 8)

| | ผล |
|---|---|
| baseline (HEAD + T-55, ตาม H-112) | 3 error: `package.py:331`, `package.py:336` (E501), `tests/test_deliver_release.py:430` (E501) |
| ต้นรอบนี้ (มี partial edit ของ seq 171) | 3 error: `package.py:388`, `package.py:393`, `test_deliver_release.py:430` (2 ตัวแรกคือบรรทัดเดิมที่เลื่อน) |
| **หลัง T-56** | **1 error**: `tests/test_deliver_release.py:467` E501 — บรรทัดเดิม (`# ---------- T-52 · AC-51 …`) ที่เลื่อนจาก 430 เพราะเพิ่ม test ข้างบน · เนื้อบรรทัดไม่ถูกแตะ (H-113 ข้อ 6) |

```
$ uv run ruff check src tests
E501 Line too long (101 > 100)
   --> tests\test_deliver_release.py:467:101
Found 1 error.
EXIT=1
```
E501 ทั้ง 2 จุดใน `package.py` หายเพราะส่วน path check ถูกเขียนใหม่เป็น `_check_source_file_path()` และข้อความ v1 แยก 2 บรรทัด · ไม่มี error ใหม่
(`ruff format --check` ไม่ใช่ gate: `package.py` ไม่ format-clean ตั้งแต่ HEAD อยู่แล้ว)

## 10. ไม่ได้รัน
- `uv run pytest -q` (full suite) — **ห้ามตาม H-113 ข้อ 8** · HRM รัน batch หลัง T-56 + T-57 (baseline หลัง T-55 = 231 passed; ใบนี้เพิ่ม test 22 ตัว → คาด 253 ถ้าไม่มีอะไรพังนอกชุด targeted)
- ไม่มีการต่อ Databricks/GitHub (AC-58/HG_PROD อยู่ใน T-53)
