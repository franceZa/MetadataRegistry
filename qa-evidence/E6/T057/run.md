# T-57 — QA evidence (SWE run) · ทางส่งของรองรับ v3 + `calendar PENDING_OWNER`

- เครื่อง: Windows 10 (dev) · git-bash · `uv run` (venv ของโปรเจกต์)
- working tree มีงาน T-48…T-56 ที่ยังไม่ commit (ตั้งใจ) + T-57 (ใบนี้) · **ไม่มี git write** · ไม่ต่อ Databricks/GitHub
- **ไม่ได้รัน full suite** (คำสั่งผู้ใช้ / H-115 ข้อ 7) → HRM รัน batch หลัง T-57 (baseline หลัง T-55 = 231 passed)
- log ดิบ: `pytest_targeted.txt` (โฟลเดอร์เดียวกัน)
- ทุกข้อด้านล่างรันกับไฟล์สุดท้าย

## 1. Targeted pytest (H-115 Verify ข้อ 1)

```
$ uv run pytest tests/test_next_steps.py tests/test_manual_sql.py tests/test_release_workflow.py tests/test_deliver_release.py -q
........................................................................ [ 98%]
.                                                                        [100%]
exit=0
```
collect = **73 tests** (test_deliver_release 25 · test_manual_sql 14 · test_next_steps 14 · test_release_workflow 20) → 73 passed
· `test_deliver_release.py` รันเบื้องหลัง (~5 นาที) โดยไม่แก้ไฟล์ใดระหว่างรัน

test ใหม่ของใบนี้ = 14 ตัว:

| ไฟล์ | test | ตรวจอะไร |
|---|---|---|
| test_next_steps.py | `test_t57_manual_m3_says_upload_odcs_yaml_and_has_no_fixed_file_count` | M-3 มี `*.resolved.json` **และ `*.odcs.yaml`** · อ้าง `file_count` · บอก `[TAMPERED]` ถ้าลืม · ไม่มี `<เลข> ×` / `<เลข> ไฟล์` |
| | `test_t57_runbook_m1_to_m7_match_next_steps_word_for_word` | 7 บรรทัด M-1…M-7 ใน `release-delivery.md` = output `next_steps.py` (rid = `mdf-<sha12>`) ทุกตัวอักษร |
| | `test_t57_guide_m1_to_m7_table_matches_next_steps_word_for_word` | คอลัมน์ "ทำอะไร" ของตาราง M-1…M-7 ใน `release-delivery-guide.md` = ข้อความเดียวกัน |
| | `test_t57_runbooks_have_no_hardcoded_file_counts` | ไม่มี "8 ไฟล์"/"6 ×" ใน runbook, guide, flow-chart.mmd · runbook ข้อ 6 = `file_count` + 2 |
| test_release_workflow.py | `test_t57_pending_owner_line_in_both_notes_and_summary_only_when_non_empty` | step ลำดับ pending → publish → summary · ทั้ง 2 step มี env `PENDING_OWNER` และบรรทัด `calendar PENDING_OWNER:` อยู่ใน `if [ -n "$PENDING_OWNER" ]; then … fi` |
| | `test_t57_pending_owner_reads_resolved_json_not_contracts` | อ่าน `*.resolved.json` + `"status") == "PENDING_OWNER"` · ไม่มี `DataContract`/`odcs`/`yaml`/`read_calendar` |
| | `test_t57_zip_transport_and_two_digests_unchanged` | zip 1 ครั้ง · `sha256sum manifest.json` 1 ครั้ง · digest ใน notes + summary 2 ที่ (FR-L.1a/FR-L.14) |
| | `test_t57_pending_owner_step_lists_sorted_unique_datasets` | **รัน python ที่ฝังใน step จริง** กับ fixture: PENDING 2 dataset (bronze+silver) + COMPLETE 1 → `pending_owner=cc.credit_card, cc.customer` (เรียง/ไม่ซ้ำ · ไม่อ่าน `.odcs.yaml` ที่วางล่อไว้) |
| | `test_t57_pending_owner_step_empty_when_all_complete` | ทุกตัว COMPLETE → `pending_owner=` (ว่าง) |
| test_manual_sql.py | `test_t57_vol_cte_does_not_filter_by_file_extension` | CTE `vol` ทั้ง 2 ที่ (guard/INSERT) ไม่มี `WHERE`/`LIKE`/`RLIKE`/`.json`/`.yaml`/`pathGlobFilter` |
| | `test_t57_manifest_schema_reads_path_and_sha256_only` | `from_json` schema = `path, sha256` ทั้ง 2 ที่ (v3 `kind`/`source`/`dataset` ถูกข้าม · ตรวจ `kind` = P2) |
| | `test_t57_v3_odcs_yaml_in_source_folder_counts_as_a_manifest_file` | twin ของ `regexp_extract(... '/(.*)$')` + กฎ 4/6: Volume ครบ 9+2 = ไม่มีปัญหา · `…/<rid>/cc/customer.odcs.yaml` → `cc/customer.odcs.yaml` |
| | `test_t57_forgetting_odcs_yaml_is_tampered_and_flat_yaml_is_extra` | ลืม 3 `.odcs.yaml` → `[TAMPERED]` หายไป 3 ไฟล์ · `.odcs.yaml` ที่ราก (flat) → `[TAMPERED]` ไฟล์เกิน |
| test_deliver_release.py | `test_t57_v3_zip_cd3_copies_file_count_plus_2_including_odcs_yaml` | fake CLI ผ่าน **zip asset** (ทาง auto/u2m): CD-3 upload = `file_count + 2` (= 11) · `.odcs.yaml` ไปที่ `<rid>/cc/` · manifest ท้ายสุด · Volume มี 11 ไฟล์ · evidence `file_count 9` + `- CD-3: copied 11 files · manifest.json last` · registry `file_count = 9` |

### Mutation check (test จับของเสียจริง · ไฟล์คืนค่า byte-for-byte หลังแต่ละรอบ — assert แล้ว)

| แก้เสีย | ผล |
|---|---|
| summary: `if [ -n "$PENDING_OWNER" ]` → `if true` | FAILED `test_t57_pending_owner_line_in_both_notes_and_summary_only_when_non_empty` |
| step pending อ่าน `DataContract/**/*.odcs.yaml` แทน resolved | FAILED `…reads_resolved_json_not_contracts`, `…lists_sorted_unique_datasets` |
| notes: ลบบรรทัดเติม `calendar PENDING_OWNER` | FAILED `…in_both_notes_and_summary_only_when_non_empty` |
| `next_steps.py` M-3 ลบ "**และ `*.odcs.yaml`**" | FAILED `…runbook_m1_to_m7_match…`, `…guide_m1_to_m7_table_matches…` (+ ภายหลังเพิ่ม assert ตรงใน `…m3_says_upload_odcs_yaml…`) |
| runbook M-3 เปลี่ยนตัวหนา 1 จุด | FAILED `…runbook_m1_to_m7_match_next_steps_word_for_word` |
| SQL `vol` เพิ่ม `WHERE f.path LIKE '%.json'` | FAILED `test_t57_vol_cte_does_not_filter_by_file_extension` |

## 2. `next_steps.py manual` (Verify ข้อ 2)

```
$ uv run python scripts/next_steps.py manual mdf-000000000000
## ขั้นต่อไป — `mdf-000000000000` · mode **manual** (ทำเองในเบราว์เซอร์ ไม่ต้องมี CLI)

- [ ] **M-1** Catalog Explorer → `dev_catalog` → `ops` → Volume `files` → `releases/` → ถ้ามีโฟลเดอร์ `mdf-000000000000` ที่มี `manifest.json` แล้ว **ห้ามอัปโหลด** ข้ามไป M-5
- [ ] **M-2** เปิด [หน้า GitHub Release](https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-000000000000) → ดาวน์โหลด asset เดียว `mdf-000000000000.zip` → แตก zip ในเครื่องตัวเอง → จด `manifest_sha256` จาก release notes ของหน้านี้ **หรือ** Job Summary ของ run `release.yml` (เลือกที่ใดก็ได้ — ไม่ใช่ digest ของไฟล์ zip ที่หน้า Release แสดง เพราะเลขนั้นเป็นของ zip ไม่ใช่ของ `manifest.json`)
- [ ] **M-3** สร้างโฟลเดอร์ `/Volumes/dev_catalog/ops/files/releases/mdf-000000000000` แล้วสร้างโฟลเดอร์ย่อย `<source>/` ทีละ source (ดูจากโฟลเดอร์ที่แตก zip ได้ใน M-2 ว่ามีกี่ source) → อัปโหลด**ทุกไฟล์**ในโฟลเดอร์ `<source>/` ที่แตกจาก zip เข้าโฟลเดอร์ `<source>/` เดียวกัน — ทั้ง `*.resolved.json` **และ `*.odcs.yaml`** (ลืม `*.odcs.yaml` = M-5 หยุดด้วย `[TAMPERED]`) · จำนวนไฟล์ทั้งหมดใน `<source>/` = `file_count` ใน `manifest.json` (**ห้ามอัปโหลดไว้ที่ราก/แบบ flat**) แล้วค่อยอัปโหลด `validation-report.json` ที่ราก `/Volumes/dev_catalog/ops/files/releases/mdf-000000000000`
- [ ] **M-4** อัปโหลด `manifest.json` เป็นไฟล์สุดท้าย ที่ราก `/Volumes/dev_catalog/ops/files/releases/mdf-000000000000` (ไม่ใช่ในโฟลเดอร์ `<source>/`)
- [ ] **M-5** **SQL Editor** → วางไฟล์ `sql/manual/register_release.sql` → ตั้ง parameter `release_id = mdf-000000000000` → **Run all** → ต้องได้ `REGISTERED` และ `manifest_sha256` ตรงกับที่จดใน M-2 (จาก Job Summary ของ `release.yml` ไม่ใช่หน้า Release) · error (รวมถึงกรณีอัปโหลดผิดโฟลเดอร์/flat) = หยุด ห้ามแก้ไฟล์ใน Volume เอง
- [ ] **M-6** วาง `sql/manual/activate_release.sql` → `release_id = mdf-000000000000` → **Run all**
- [ ] **M-7** query ตรวจ: แถว `ACTIVATED` ล่าสุด = `mdf-000000000000` · เก็บผล query เป็นหลักฐาน (ป้าย `manual-ui`) · ผลสุดท้ายต้องขึ้น `active_release_id = mdf-000000000000`

รายละเอียดพร้อมภาพหน้าจอ: `runbooks/release-delivery.md` · rollback = ทำ M-6 ด้วย release เก่า
```
→ M-3 เห็น `*.odcs.yaml` · ไม่มีจำนวนไฟล์ตายตัว (อ้าง `file_count` ใน manifest)

## 3. grep จำนวนตายตัว (Verify ข้อ 3)

```
$ grep -n "8 ไฟล์\|6 ×" scripts runbooks -r
grep_exit=1          # ไม่พบ
```
ก่อนแก้พบ 2 จุด: `runbooks/release-workflow/flow-chart.mmd:31` และ `flow-chart.html:89` ("ดาวน์โหลด 8 ไฟล์")
→ แก้ `.mmd` เป็น `M-1 ถึง M-3: ดาวน์โหลด zip เดียวแล้วแตก<br/>อัปโหลดทุกไฟล์ใน source รวม *.odcs.yaml<br/>manifest.json สุดท้าย`
แล้ว regenerate ด้วย `uv run python runbooks/release-workflow/render_diagrams.py` (ใช้ได้ ไม่ต้องแก้ html มือ)
· `diff` ก่อน/หลัง `flow-chart.html` = บรรทัด 89 บรรทัดเดียว · `decision-tree.html` ที่สคริปต์เขียนทับด้วย = `cmp` เท่าเดิม byte-for-byte

## 4. release.yml static + simulate (Verify ข้อ 4)

static: ดู test ข้อ 1 (`test_t57_*` ใน test_release_workflow.py)

simulate — ดึง `run:` ของ 3 step จาก release.yml (yaml.safe_load) แล้วรันด้วย bash ใน `%LOCALAPPDATA%\Temp` (ไม่แตะ repo):
```
== step pending (real build/dev/release) →
pending_owner=cc.credit_card, cc.credit_card_txn, cc.customer
== PENDING_OWNER='cc.credit_card, cc.credit_card_txn, cc.customer' → release notes:
mdf release package for 0123456789abcdef

manifest_sha256: deadbeef

calendar PENDING_OWNER: cc.credit_card, cc.credit_card_txn, cc.customer
== PENDING_OWNER='cc.credit_card, cc.credit_card_txn, cc.customer' → job summary (head):
manifest_sha256: `deadbeef`

calendar PENDING_OWNER: cc.credit_card, cc.credit_card_txn, cc.customer

## ขั้นต่อไป — `mdf-000000000000` · mode **u2m** (คุณ login · สคริปต์ทำที่เหลือ)
== PENDING_OWNER='' → release notes:
mdf release package for 0123456789abcdef

manifest_sha256: deadbeef
== PENDING_OWNER='' → job summary (head):
manifest_sha256: `deadbeef`
## ขั้นต่อไป — `mdf-000000000000` · mode u2m …
```
- รายชื่อตรงกับบรรทัดของ `mdf package` (T-56 `verify-cli.log:9`: `[WARN] calendar PENDING_OWNER: cc.credit_card, cc.credit_card_txn, cc.customer`)
- ว่าง → ไม่มีบรรทัด `calendar PENDING_OWNER` ทั้ง notes และ summary
- ไม่ parse contract: อ่าน `calendar.status` (ผลของ `compiled_calendar()` ที่ compile ใส่ไว้แล้ว) จาก `build/dev/release/**/*.resolved.json`
- ไม่เปลี่ยน: step `Build release zip asset`, `Compute manifest digest`, ส่วน idempotency (`gh release view/download/safe_unzip/diff`) · asset ยังเป็น `"build/${RELEASE_ID}.zip"` · digest ยังใช้ `steps.digest` 2 ที่

## 5. `register_release.sql` / `deliver_release.sh` (Verify ข้อ 5–6)

**ไม่แก้ทั้ง 2 ไฟล์** (H-115 ข้อ 3) — test พิสูจน์ว่าไม่ต้องแก้:
- SQL: `test_t57_vol_cte_does_not_filter_by_file_extension`, `test_t57_v3_odcs_yaml_in_source_folder_counts_as_a_manifest_file`, `test_t57_forgetting_odcs_yaml_is_tampered_and_flat_yaml_is_extra` (static/unit; live ของจริงอยู่ที่ T-53)
- sh: `test_t57_v3_zip_cd3_copies_file_count_plus_2_including_odcs_yaml` (+ ของเดิม T-56 `test_t56_v3_from_dir_…registers_9` ทาง `--from-dir`) · ข้อความ evidence `copied $((N_FILES + 2)) files` ถูกอยู่แล้ว
- sha256 ปัจจุบัน (ไม่มี diff จากใบนี้): `register_release.sql` `3287552b15a7…` · `deliver_release.sh` `a7f57f856bc5…`
- หมายเหตุ: mutation check ข้อ 1 เขียน `register_release.sql` ชั่วคราวแล้วคืนค่า byte-for-byte (assert ในสคริปต์) → mtime เปลี่ยนแต่เนื้อหาเท่าเดิม

## 6. ruff (Verify ข้อ 7)

ก่อน (T-56 `qa-evidence/E6/T056/ruff-after.log`) และหลัง (ใบนี้) เหมือนกัน:
```
$ uv run ruff check src tests
E501 Line too long (101 > 100)
   --> tests\test_deliver_release.py:467:101
Found 1 error.
```
→ ไม่มี error ใหม่ (ระหว่างทางมี E501 ใน test ใหม่ 4 บรรทัด — แก้แล้วก่อนรันรอบสุดท้าย)

## 7. อื่น ๆ
- leak check บน diff ของ `scripts/next_steps.py`, `runbooks/**`, `release.yml`: ไม่พบ `dbc-` / `@gmail` / host workspace / `dapi` / `ghp_` · URL ใหม่ใน guide = repo สาธารณะเดิม (`github.com/franceZa/MetadataRegistry/releases/tag/mdf-<sha12>`) ซึ่งมีอยู่แล้วใน runbook M-2
- ไฟล์ต้องห้าม (`src/**`, `DataContract/**`, `tests/fakes/**`, `config/**`) ไม่ได้แตะ
