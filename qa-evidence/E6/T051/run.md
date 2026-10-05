# T-51 — Evidence run (SWE)

Handoff: `handoffs/107-hrm-to-swe-t051.md` → `handoffs/108-swe-to-hrm-t051.md`
Scope: `sql/manual/register_release.sql`, `scripts/next_steps.py`, `runbooks/release-delivery.md`,
`runbooks/release-delivery-guide.md`, `tests/test_next_steps.py`, `tests/test_manual_sql.py`.

**SQL ยังไม่ได้รันจริง** — ไม่ได้ต่อ Databricks workspace ใบนี้ (NFR-6, ตามข้อ 5 ของ H-107). มีเฉพาะ
static test (syntax/structure) ด้านล่าง การพิสูจน์ live behaviour อยู่ที่ T-53.

## 1. Code changes

- `sql/manual/register_release.sql`
  - statement (2) guard และ (3) INSERT: เพิ่ม `recursiveFileLookup => 'true'` ให้ `read_files()`
    ทั้ง 2 จุด (เดิมอ่านชั้นเดียว ไม่เห็นไฟล์ใต้ `<source>/`)
  - เปลี่ยน `regexp_extract(f.path, '[^/]+$', 0) AS name` (basename เท่านั้น) เป็น
    `regexp_extract(f.path, concat(:release_id, '/(.*)$'), 1) AS name` (path สัมพัทธ์เต็มจากราก
    ของ release) ใช้สูตรเดียวกันทั้ง guard และ INSERT ตาม HRM correction #4
  - v1 (flat, ไม่มี subfolder) ยัง backward-compatible: path สัมพัทธ์ของไฟล์ v1 = basename อยู่แล้ว
    เพราะไม่มี `/` ใน path ส่วนที่เหลือ
  - guard "ไฟล์ที่ไม่มีใน manifest" และการเทียบ `manifest.json`/`validation-report.json` เทียบ
    path สัมพัทธ์ที่ได้จาก regex เดียวกัน (= ชื่อไฟล์ตรง ๆ เมื่ออยู่ที่ราก, นับไฟล์ชื่อ `manifest.json`
    ใน subfolder อื่นเป็นไฟล์แปลกปลอมเพราะ path สัมพัทธ์จะไม่ตรงกับ `'manifest.json'` เปล่า ๆ)
  - ไม่กรองตามนามสกุลไฟล์ (คง behaviour เดิม ไม่ได้เพิ่ม filter ใหม่ — รองรับ `.yaml` ของรอบ 12 ได้
    โดยไม่ต้องแก้เพิ่ม)
  - ไม่แตะ `release_id` format check เดิม (`^mdf-[0-9a-f]{12}$`) และไม่แตะ guard/error code อื่น

- `scripts/next_steps.py` (`_manual()`)
  - เขียนใหม่ทั้งหมดให้ตรงกับตาราง M-1…M-7 ของ SSOT
    (`DocsForAgent/draft_reviewd_by_agent_v2.md` บรรทัดประมาณ 1079–1085):
    - M-1 ตรวจว่า sealed แล้วหรือยัง (มี `manifest.json` ใน Volume แล้ว = ข้ามไป M-5)
    - M-2 ดาวน์โหลด zip เดียว แตกเอง แล้วจด `manifest_sha256` จาก release notes **หรือ** Job Summary
    - M-3 สร้าง `releases/<rid>/` + `<source>/` ต่อ source → อัปโหลด**ทุกไฟล์**ในโฟลเดอร์ `<source>/`
      (ไม่นับจำนวนไฟล์ ไม่ระบุว่าเป็น `.json` อย่างเดียว) + `validation-report.json` ที่ราก
    - M-4 อัปโหลด `manifest.json` เป็นไฟล์สุดท้าย
    - M-5 register SQL + เทียบ digest (จาก Job Summary/release notes ไม่ใช่ "digest หน้า Release")
    - M-6 activate
    - M-7 query ตรวจ
  - ลบข้อความ "ดาวน์โหลดไฟล์ทั้ง 8 ไฟล์ (6 × `*.resolved.json`, `manifest.json`,
    `validation-report.json`)" ที่เดิมอยู่บรรทัด 79–80 ออกทั้งหมด

- `runbooks/release-delivery.md` §4 — sync checklist M-1…M-7 คำต่อคำกับ `next_steps.py` ใหม่
  (รวม error table ที่ชี้ไป M-3/M-4/M-5 ใหม่) และลบ "8 ไฟล์" ที่บรรทัด 89, 134 (เดิม)

- `runbooks/release-delivery-guide.md` — sync คำศัพท์ §2 (`package`), diagram §3 (`GitHub Release`
  node), ตัวสร้าง package §3, CD-3 §6, และตาราง M-1…M-7 ↔ CD ที่ §7.3 (บรรทัด 209–219 เดิม) ให้ตรง
  กับ `next_steps.py` ใหม่ · ลบ "8 ไฟล์ / 6 × `*.resolved.json` / 7 ไฟล์" ที่บรรทัด 23, 44, 72, 140,
  213, 215 (เดิม)

- `tests/test_manual_sql.py` — เพิ่ม
  `test_register_reads_the_volume_recursively_and_matches_full_relative_path`: ยืนยันว่า
  `recursiveFileLookup => 'true'` ปรากฏ 2 ครั้ง (ทั้ง guard และ INSERT), ไม่มี `'[^/]+$'`
  (basename-only) เหลืออยู่, guard กับ INSERT ใช้สูตร `regexp_extract(f.path, ...)` เดียวกันตัวต่อตัว,
  และสูตรคือ `concat(:release_id, '/(.*)$')`

- `tests/test_next_steps.py` — **ไม่ต้องแก้** หลังรีวิว: assertion เดิมทั้งหมด (M-1..M-7 ครบ,
  `"manifest.json\` เป็นไฟล์สุดท้าย"`, ลิงก์ Release/Volume, M-4 มาก่อน M-6) ยังเป็นจริงกับ wording
  ใหม่พอดี — ไม่มี assertion ไหนเปลี่ยนความหมาย จึงไม่ต้องรีไรต์

## 2. Verify commands (รันจริงตามที่ H-107 ขอ)

### 2.1 Targeted tests
```
$ uv run pytest tests/test_next_steps.py tests/test_manual_sql.py -q
....................                                                     [100%]
20 passed
```
(10 tests `test_next_steps.py` + 10 tests `test_manual_sql.py`, รวม static test ใหม่ 1 ข้อ)

### 2.2 CLI wording check
```
$ uv run python scripts/next_steps.py manual mdf-000000000000
## ขั้นต่อไป — `mdf-000000000000` · mode **manual** (ทำเองในเบราว์เซอร์ ไม่ต้องมี CLI)

- [ ] **M-1** Catalog Explorer → `dev_catalog` → `ops` → Volume `files` → `releases/` → ถ้ามีโฟลเดอร์ `mdf-000000000000` ที่มี `manifest.json` แล้ว **ห้ามอัปโหลด** ข้ามไป M-5
- [ ] **M-2** เปิด [หน้า GitHub Release](https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-000000000000) → ดาวน์โหลด asset เดียว `mdf-000000000000.zip` → แตก zip ในเครื่องตัวเอง → จด `manifest_sha256` จาก release notes ของหน้านี้ **หรือ** Job Summary ของ run `release.yml` (เลือกที่ใดก็ได้ — ไม่ใช่ digest ของไฟล์ zip ที่หน้า Release แสดง เพราะเลขนั้นเป็นของ zip ไม่ใช่ของ `manifest.json`)
- [ ] **M-3** สร้างโฟลเดอร์ `/Volumes/dev_catalog/ops/files/releases/mdf-000000000000` แล้วสร้างโฟลเดอร์ย่อย `<source>/` ทีละ source ที่มีไฟล์ resolved (ดูจากโฟลเดอร์ที่แตก zip ได้ใน M-2 ว่ามีกี่ source) → อัปโหลด**ทุกไฟล์**ในโฟลเดอร์ `<source>/` ที่แตกจาก zip เข้าโฟลเดอร์ `<source>/` เดียวกัน (**ห้ามอัปโหลดไว้ที่ราก/แบบ flat**) แล้วค่อยอัปโหลด `validation-report.json` ที่ราก `/Volumes/dev_catalog/ops/files/releases/mdf-000000000000`
- [ ] **M-4** อัปโหลด `manifest.json` เป็นไฟล์สุดท้าย ที่ราก `/Volumes/dev_catalog/ops/files/releases/mdf-000000000000` (ไม่ใช่ในโฟลเดอร์ `<source>/`)
- [ ] **M-5** **SQL Editor** → วางไฟล์ `sql/manual/register_release.sql` → ตั้ง parameter `release_id = mdf-000000000000` → **Run all** → ต้องได้ `REGISTERED` และ `manifest_sha256` ตรงกับที่จดใน M-2 (จาก Job Summary ของ `release.yml` ไม่ใช่หน้า Release) · error (รวมถึงกรณีอัปโหลดผิดโฟลเดอร์/flat) = หยุด ห้ามแก้ไฟล์ใน Volume เอง
- [ ] **M-6** วาง `sql/manual/activate_release.sql` → `release_id = mdf-000000000000` → **Run all**
- [ ] **M-7** query ตรวจ: แถว `ACTIVATED` ล่าสุด = `mdf-000000000000` · เก็บผล query เป็นหลักฐาน (ป้าย `manual-ui`) · ผลสุดท้ายต้องขึ้น `active_release_id = mdf-000000000000`

รายละเอียดพร้อมภาพหน้าจอ: `runbooks/release-delivery.md` · rollback = ทำ M-6 ด้วย release เก่า
```
(exit 0, ตรงกับ `next_steps.py:_manual()` และ SSOT M-1…M-7)

### 2.3 Stale-wording grep (ต้องไม่เหลือใน 3 ไฟล์ที่แก้)
```
$ grep -rn "8 ไฟล์\|6 × \|7 ไฟล์" scripts runbooks
runbooks/release-workflow/flow-chart.html:89: ... D4[M-1 ถึง M-3: ดาวน์โหลด 8 ไฟล์<br/>...]
runbooks/release-workflow/flow-chart.mmd:31:  ... D4[M-1 ถึง M-3: ดาวน์โหลด 8 ไฟล์<br/>...]
```
ไม่เหลือใน `scripts/next_steps.py`, `runbooks/release-delivery.md`,
`runbooks/release-delivery-guide.md` (3 ไฟล์ที่ H-107 ขอ) — เหลือเฉพาะ
`runbooks/release-workflow/flow-chart.html` / `.mmd` ซึ่ง**ไม่อยู่ใน allowed_writes ของ H-107**
(ข้อ 3: "runbooks/release-workflow/flow-chart.* ไม่อยู่ใน allowed_writes ถ้าเจอข้อความที่ล้าสมัยให้
รายงานใน H-108") — รายงานไว้ใน H-108 § Open questions and risks, ไม่แก้ในใบนี้

### 2.4 Full test suite (background, ~20 นาที)
รันซ้ำ 3 ครั้งอิสระเพื่อยืนยันผล (ครั้งแรกไม่มี stdout buffer, ครั้งที่ 2–3 ยืนยัน exit code ชัดเจน):

```
$ uv run pytest -q > $LOCALAPPDATA/Temp/t051_full2.log 2>&1   # background, exit 0
........................................................................ [ 34%]
........................................................................ [ 68%]
.................................................................        [100%]

$ uv run pytest -q > $LOCALAPPDATA/Temp/t051_full3.log 2>&1; echo "EXIT_CODE=$?" >> ...
........................................................................ [ 34%]
........................................................................ [ 68%]
.................................................................        [100%]
EXIT_CODE=0

$ uv run pytest -q --no-header 2>&1 | tee $LOCALAPPDATA/Temp/t051_full4.log   # exit 0
........................................................................ [ 34%]
........................................................................ [ 68%]
.................................................................        [100%]
```

`uv run pytest --collect-only -q` → 209 tests รวม (รายไฟล์):
`test_bootstrap_sql.py:5, test_ci_workflow.py:9, test_cli.py:8, test_compile.py:6,
test_deliver_release.py:23, test_delivery_mode.py:9, test_deploy_workflow.py:9, test_diff.py:8,
test_dq_library.py:7, test_e2e.py:7, test_fk_validation.py:4, test_loading.py:6,
test_manifest_release.py:17, test_manual_sql.py:10, test_next_steps.py:10, test_package.py:17,
test_reality.py:4, test_register.py:17, test_release_workflow.py:15, test_rules.py:7,
test_trace.py:6, test_validation.py:5` = **209 tests**

ทั้ง 3 รอบได้ dot pattern เดียวกัน (209 `.`, ไม่มี `F`/`E`) และ exit code 0 ทุกครั้ง →
**209 passed, 0 failed** (baseline T-48 = 208 passed + static test ใหม่ 1 ข้อที่ T-51 เพิ่ม = 209)

## 3. AC-by-AC

| AC | Command | Expected | Actual | PASS/FAIL |
|---|---|---|---|---|
| AC-50 (positive, static) | `uv run pytest tests/test_manual_sql.py -q` | recursive read + full-relative-path regex ใน `register_release.sql` | `test_register_reads_the_volume_recursively_and_matches_full_relative_path` PASS — SQL **ยังไม่ได้รันจริง** กับ release v2 (รอ T-53) | PASS (static only) |
| AC-50 (negative, static) | เดิม `test_register_guards_come_before_insert_and_are_repeated_inside_it` | guard raise error ก่อน INSERT, error code ครบ | PASS (ไม่เปลี่ยนความหมาย) — live negative-case รอ T-53 | PASS (static only) |
| `next_steps.py` M-2/M-3/M-5 wording | `uv run python scripts/next_steps.py manual mdf-000000000000` + `test_next_steps.py` | M-2 zip เดียว, M-3 สร้าง `<source>/`, M-5(digest) อ้าง Job Summary/release notes | ตรงตาม SSOT M-1…M-7 ทุกข้อ (ดู §2.2) · `test_next_steps.py` 10 passed ไม่ต้องแก้ assertion | PASS |
| runbook sync กับ `next_steps.py` | diff อ่านด้วยตา + grep | ตาราง M-1…M-7 ตรงกันทุกคำ, ไม่มี "8 ไฟล์/6×/7 ไฟล์" | `release-delivery.md` §4 + `release-delivery-guide.md` §2/§3/§6/§7.3 sync แล้ว, grep สะอาดใน 3 ไฟล์ที่แก้ | PASS |

evidence_class: **BUILD** (code+test ตรงกับ ticket Evidence Class) — ไม่มี RUN+OBSERVE กับ
Databricks จริงในใบนี้ (ตามข้อ 5 ของ H-107 และงบ ฿0 ของ ticket); live RUN+OBSERVE อยู่ที่ T-53

## 4. ขอบเขตที่ไม่ได้แก้ (นอก allowed_writes)
- `runbooks/release-workflow/flow-chart.html` และ `.mmd` ยังมีข้อความ "ดาวน์โหลด 8 ไฟล์" ที่บรรทัด
  89 และ 31 ตามลำดับ — ไม่อยู่ใน `allowed_writes` ของ H-107 ข้อ 3 ระบุชัดว่าไฟล์นี้ไม่ต้องแก้ ให้
  รายงานใน H-108 เท่านั้น
