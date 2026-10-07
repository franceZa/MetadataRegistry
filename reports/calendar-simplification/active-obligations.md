# Active obligations — ID-addressable detail

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

<a id="ac-01"></a>

### AC-01
Source backup lines 516–520; apply effective precedence above.

#### AC-01: Contract ที่กรอกไม่ครบ ต้องได้ error ที่ BA อ่านแล้วแก้เองได้ (FR-B.9, FR-A.7)
- **Given:** copy `_template` ไปเป็น `DataContract/xx/contract/foo.odcs.yaml` โดยไม่แก้อะไร
- **When:** `uv run mdf validate`
- **Then:** exit 1 และทุก error มีไฟล์, field, สาเหตุ, วิธีแก้เป็นภาษาไทย รวมถึงบอกว่าขาดไฟล์ pipeline คู่กัน

<a id="ac-02"></a>

### AC-02
Source backup lines 521–525; apply effective precedence above.

#### AC-02: Duplicate YAML key ถูกปฏิเสธ (FR-B.1)
- **Given:** contract ที่มี key `version` สองครั้ง
- **When:** validate
- **Then:** exit 1 และบอกบรรทัดของ key ที่ซ้ำ

<a id="ac-03"></a>

### AC-03
Source backup lines 526–530; apply effective precedence above.

#### AC-03: Unknown key ถูกปฏิเสธ ยกเว้นใน `extensions` (FR-B.3)
- **Given:** pipeline มี key `dedupe:` (สะกดผิด) และมี `extensions.foo: 1`
- **When:** validate
- **Then:** error ที่ `dedupe` และไม่มี error ที่ `extensions.foo`

<a id="ac-04"></a>

### AC-04
Source backup lines 531–535; apply effective precedence above.

#### AC-04: Reference ที่ขาด (FR-B.4, FR-G.2) · ◐ Phase 1 (กรณี gold input → Phase 3)
- **Given:** แต่ละกรณีต่อไปนี้ทำใน tmp copy: `actions` อ้าง `<rule>@<col>` ที่ไม่มี / `dq:` tag ที่ไม่มีใน library / BU rule อ้างคอลัมน์ที่ไม่มี / dedup key ไม่มีใน contract / FK ชี้ไปหา dataset ที่ไม่มี (`FK_TARGET_NOT_FOUND` · ดู AC-33) / gold input ไม่มี / contract ไม่มี pipeline
- **When:** validate
- **Then:** แต่ละกรณี exit 1 และ error code ถูกต้อง

<a id="ac-05"></a>

### AC-05
Source backup lines 536–540; apply effective precedence above.

#### AC-05: Unsupported ต้องไม่ถูกปล่อยผ่านเงียบ ๆ (FR-B.7, FR-B.8)
- **Given:** contract ที่มี `quality[]` / library rule `kind: function` ที่ไม่มีฟังก์ชันใน registry / `storage: external`
- **When:** validate
- **Then:** exit 1 ด้วย code `USE_TAG` / `UNSUPPORTED` / `UNSUPPORTED` ตามลำดับ

<a id="ac-06"></a>

### AC-06
Source backup lines 541–547; apply effective precedence above.

#### AC-06: Landing path มาจาก control file (FR-A.5, FR-D.2, D-P1-1)
- **Given:** `config/env/dev.yaml` ตั้ง `catalog: dev_catalog`
- **When:** compile
- **Then:** resolved bronze ของ credit_card มี landing `/Volumes/dev_catalog/landing_cc/files/credit_card/`
- **And:** เปลี่ยนเป็น `catalog: foo` แล้ว compile ใหม่ → path เปลี่ยนตาม **โดยไม่ต้องแก้ contract**
- **And:** contract ที่ hardcode `dev_catalog` → validate error

<a id="ac-07"></a>

### AC-07
Source backup lines 548–553; apply effective precedence above.

#### AC-07: กฎมีที่อยู่เดียว และไม่มีกฎหายเงียบ ๆ (FR-A.3, BR-18, DQ-2)
- **Given:** repo หลัง migrate
- **When:** validate
- **Then:** ไม่มี `quality[]` หรือ SQL ใน contract · ทุก `dq:` tag มีใน library · ทุกค่า pattern/valid_values/foreign_key มี tag คู่กัน
- **And:** (tmp copy) ลบ tag `dq:pattern` ของ national_id แต่ยังมี pattern อยู่ → `PARAM_WITHOUT_TAG` · แปะ `dq:foo` → `UNKNOWN_TAG`

<a id="ac-08"></a>

### AC-08
Source backup lines 1181–1185; apply effective precedence above.

#### AC-08: Migration รักษาความหมาย (FR-A.3, DC-1…8) · ⏭️ **Phase 3**
- **Given:** ชุดแถวตัวอย่างจาก REALITY ทุกกรณี (national_id `"123"`, PAN ที่มีช่องว่าง, `'UNLIMITED'`, amount ติดลบ ฯลฯ)
- **When:** ประเมินกฎเดิม (จาก commit `88b982d`) เทียบกับ checks ที่ขยายจาก model ใหม่ (library + BU) ด้วย executor ของ runtime
- **Then:** ผล pass/fail เหมือนกันทุกแถว **ยกเว้น** จุดที่ตั้งใจเปลี่ยนและมีบันทึกไว้ (DC-1 Luhn, DC-5 business_date) ซึ่งมี test ยืนยันผลที่เปลี่ยนแบบ explicit

<a id="ac-09"></a>

### AC-09
Source backup lines 1186–1192; apply effective precedence above.

#### AC-09: Library rule รันกับข้อมูลจริง + auto not_null (FR-C.3, FR-I.5, D-P2-3) · ⏭️ **Phase 3**
- **Given:** DataFrame ที่ `customer_id` (required, ไม่มี tag) เป็น NULL 1 แถว และ `national_id = "123"` 1 แถว
- **When:** รัน silver ของ customer
- **Then:** ทั้ง 2 แถวไปอยู่ใน quarantine ด้วย `_rule_id = not_null@customer_id` และ `pattern@national_id` ตามลำดับ
- **And:** run_log `rows_quarantined = 2`
- **And:** (tmp copy) `actions: {pattern@national_id: flag}` → แถว national_id ไม่เข้า quarantine แต่ถูกนับเป็น flag (D-P2-4)

<a id="ac-10"></a>

### AC-10
Source backup lines 554–559; apply effective precedence above.

#### AC-10: เพิ่มกฎได้โดยไม่แก้ Python (FR-C.4, FR-C.5) · ◐ Phase 1 (ส่วน "รัน silver" → Phase 3)
- **Given:** tmp copy ที่ (1) เพิ่มกฎ `kind: sql` ใหม่ใน `config/dq_library.yaml` แล้วแปะ tag ใน contract และ (2) เพิ่ม validator rule ใหม่ที่ใช้ operator ที่มีอยู่แล้วใน `contract.rules.json`
- **When:** validate / compile / รัน silver
- **Then:** กฎทั้งสองทำงานโดยไม่มีการแก้ไฟล์ `.py` (test ตรวจว่า `git diff --stat -- src` ว่าง)
- **And:** ตั้ง `enabled: false` → กฎไม่ทำงาน และ diff รายงานว่ามีการปิดกฎ

<a id="ac-11"></a>

### AC-11
Source backup lines 560–564; apply effective precedence above.

#### AC-11: Compile deterministic (FR-D.5, NFR-2, NFR-3)
- **Given:** repo สะอาด
- **When:** compile 2 ครั้ง และ checkout ด้วย CRLF
- **Then:** sha256 ของทุกไฟล์เท่ากัน

<a id="ac-12"></a>

### AC-12
Source backup lines 565–569; apply effective precedence above.

#### AC-12: ไม่มี intermediate spec และไม่มีการ commit output (FR-D.1, FR-H.2)
- **Given:** หลัง compile
- **When:** `git status`
- **Then:** ไม่มีไฟล์ใหม่นอก `build/` (gitignored) และไม่มี `metadata/specs`

<a id="ac-13"></a>

### AC-13
Source backup lines 570–575; apply effective precedence above.

#### AC-13: Breaking change ถูกตรวจพบ (FR-E.1, FR-E.2)
- **Given:** ลบคอลัมน์ `merchant_name` แต่ไม่ bump major
- **When:** `mdf diff --base 88b982d`
- **Then:** exit 1 และรายงาน breaking change + target ที่ได้รับผลกระทบ (silver.cc.credit_card_txn · gold → Phase 3)
- **And:** bump เป็น 2.0.0 + แก้ `contract_ref` → exit 0 แต่ยังรายงาน impact

<a id="ac-14"></a>

### AC-14
Source backup lines 576–580; apply effective precedence above.

#### AC-14: Initial release (FR-E.3)
- **Given:** ยังไม่มี release
- **When:** `mdf diff --initial-release`
- **Then:** report ระบุ "ไม่ได้ตรวจเทียบรุ่นก่อน" และไม่มีคำว่า compatible

<a id="ac-15"></a>

### AC-15
Source backup lines 581–585; apply effective precedence above.

#### AC-15: Package ที่ถูกแก้ต้องถูกจับได้ (FR-F.5)
- **Given:** package ที่ verify ผ่าน
- **When:** แก้ 1 byte / ลบ 1 ไฟล์ / เพิ่ม 1 ไฟล์ แล้ว `mdf verify-package` (ใน directory ที่ไม่มี source)
- **Then:** fail ทั้ง 3 กรณีพร้อมบอกไฟล์

<a id="ac-16"></a>

### AC-16
Source backup lines 586–590; apply effective precedence above.

#### AC-16: Release gate (FR-F.3, FR-F.4)
- **Given:** `dummy: true` หรือ `secret_scope: <TODO:…>` หรือ working tree dirty
- **When:** `mdf package --release`
- **Then:** exit 1 · ส่วนแบบไม่ใช้ `--release` ได้ package ที่มี `preview: true`

<a id="ac-17"></a>

### AC-17
Source backup lines 591–595; apply effective precedence above.

#### AC-17: REALITY oracle (FR-A.6, D-P0-13)
- **Given:** repo หลัง migrate
- **When:** pytest
- **Then:** ชุดบรรทัด `# REALITY:` ของแต่ละ contract เท่ากับของ commit `88b982d` แบบ byte-for-byte

<a id="ac-18"></a>

### AC-18
Source backup lines 596–600; apply effective precedence above.

#### AC-18: Trace (FR-G.1) · Phase 1 (ตัวอย่างเป็น silver · D-P4-3)
- **Given:** release package
- **When:** `mdf trace silver.cc.credit_card_txn --package <dir>`
- **Then:** แสดง bronze input → contract id / version / sha256 → source_commit / release_id

<a id="ac-19"></a>

### AC-19
Source backup lines 601–605; apply effective precedence above.

#### AC-19: CI / release workflow ไม่ commit กลับ (FR-H.2, FR-H.3) · Phase 1 (static + local · D-P4-5)
- **Given:** `.github/workflows/*.yml`
- **When:** pytest อ่าน YAML
- **Then:** ไม่มี `git push`, `git commit`, `contents: write` นอก job publish และทุก trigger ชี้ `master`

<a id="ac-20"></a>

### AC-20
Source backup lines 1193–1197; apply effective precedence above.

#### AC-20: Tokenise + vault (FR-I.4, BR-20) · ⏭️ **Phase 3**
- **Given:** PAN `"5555 5500 …"` และ `"55555500…"` วันเดียวกัน
- **When:** รัน silver credit_card
- **Then:** ได้ token เดียวกัน, silver มี 1 แถว, vault มี 1 mapping และ quarantine/silver ไม่มี cleartext PAN

<a id="ac-21"></a>

### AC-21
Source backup lines 1198–1207; apply effective precedence above.

#### AC-21: Silver ตาม REALITY (FR-I.2–I.7) · ⏭️ **Phase 3**
- **Given:** ไฟล์ตัวอย่างครบทุก REALITY case (DEP-8)
- **When:** รัน bronze → silver ของ 2026-09-10 และ 2026-09-11
- **Then:**
  - credit_card 2026-09-10 = `missing` (ไม่ใช่ 0 แถว)
  - txn 2026-09-11 = `late` โดยไม่ alert
  - `CUST999999` ยังอยู่ใน silver + flag `fk@customer_id` (การจัดการค่า FK ตาม OQ-P1-23)
  - `'UNLIMITED'` อยู่ใน quarantine
  - quality_first ที่ pass rate < 0.99 → ไม่ publish

<a id="ac-22"></a>

### AC-22
Source backup lines 1208–1212; apply effective precedence above.

#### AC-22: Idempotent run (NFR-10, FR-I.3, FR-I.12) · ⏭️ **Phase 3**
- **Given:** รัน bronze → silver → gold ของ business_date เดิม 2 ครั้ง
- **When:** นับแถวและเทียบ hash ของคอลัมน์ธุรกิจใน bronze / silver / quarantine / gold
- **Then:** จำนวนและ hash เท่าเดิม (ไม่มีแถวซ้ำใน bronze ที่เคยเป็น append) · ข้อมูลของวันอื่นไม่เปลี่ยน

<a id="ac-23"></a>

### AC-23
Source backup lines 1213–1221; apply effective precedence above.

#### AC-23: Deploy medallion job + smoke (FR-J.2–J.4) — **ต้องได้ HG_PROD ก่อน** · ⏭️ **Phase 3** (การส่ง release ถึง workspace = AC-35…42 ใน Phase 2)
- **Given:** External Setup Checklist ครบ และผู้ใช้อนุญาต
- **When:** `deploy-dev.yml`
- **Then:**
  - `bundle validate` / `bundle deploy -t dev` ผ่าน
  - smoke run สำเร็จ
  - `SELECT * FROM dev_catalog.ops.run_log WHERE run_id = …` แสดง `release_id` ตรงกับ release ที่ deploy
  - หลักฐานที่เก็บคือ run URL + ผล query (ไม่รวม secret)

<a id="ac-24"></a>

### AC-24
Source backup lines 606–610; apply effective precedence above.

#### AC-24: Blast radius ของการแก้ library (FR-E.5, DQ-6)
- **Given:** แก้ `default_action` ของ `valid_values` จาก reject เป็น flag ใน tmp copy
- **When:** `mdf diff --base 88b982d` (หรือ release ก่อนหน้า)
- **Then:** report แสดงรายชื่อทุกคอลัมน์ที่ใช้กฎนี้ (customer.customer_status, credit_card.card_type, credit_card.card_status, txn.currency, txn.txn_status) และจัดเป็น change ที่ต้อง review

<a id="ac-25"></a>

### AC-25
Source backup lines 611–615; apply effective precedence above.

#### AC-25: `description` บังคับ (FR-B.11, DQ-7, D-P2-8)
- **Given:** tmp copy ที่ลบ `description` ออกจาก library rule 1 ข้อ / BU rule 1 ข้อ / derived 1 ตัว / คอลัมน์ใน contract ที่**ไม่มี** `dq:` tag 1 ตัว / และตั้ง description ของอีกคอลัมน์เป็น `""`
- **When:** validate
- **Then:** ได้ `MISSING_DESCRIPTION` ครบทั้ง 5 จุด พร้อมไฟล์และ field · ส่วน repo จริงหลัง migrate ต้องไม่มี error นี้ (ทุกคอลัมน์ของ 3 contract มี description)

<a id="ac-26"></a>

### AC-26
Source backup lines 1222–1226; apply effective precedence above.

#### AC-26: Backfill ได้ผลเท่ากับรันตามเวลาปกติ (NFR-11) · ⏭️ **Phase 3**
- **Given:** รัน scheduled วันที่ 09-10, 09-11, 09-12 ตามลำดับ แล้วเก็บ hash ของคอลัมน์ธุรกิจทุกตาราง
- **When:** ลบผลของวันที่ 09-11 แล้ว `--mode backfill --from 2026-09-11` (bronze ของ 09-11 ถูกลบด้วยเพื่อให้สร้างใหม่จาก landing)
- **Then:** hash ทุกตารางเท่าเดิม · run_log `run_type=backfill` มี input sha256 เท่ากับรอบเดิม · `arrival_status=backfill` และสถานะเดิม (`late`) ยังอยู่

<a id="ac-27"></a>

### AC-27
Source backup lines 1227–1231; apply effective precedence above.

#### AC-27: SCD2 รันไม่เรียงวันแล้วได้ผลเท่ากัน (FR-I.11, FR-I.14) · ⏭️ **Phase 3**
- **Given:** ไฟล์ credit_card 3 วันที่ PK เดียวกันมีค่าต่างกัน
- **When:** รันลำดับ 09-10 → 09-11 → 09-12 และในชุดที่สองรัน 09-12 → 09-10 → 09-11
- **Then:** ตาราง SCD2 ทั้งสองชุดเหมือนกันทุกแถว · FK ของ txn วันที่ 09-11 อ่าน version ที่มีผล ณ 09-11

<a id="ac-28"></a>

### AC-28
Source backup lines 1232–1236; apply effective precedence above.

#### AC-28: Cascade + gold as-of (FR-I.13, FR-B.13) · ⏭️ **Phase 3**
- **Given:** credit_card 2026-09-10 เป็น `missing` (REALITY) แล้วภายหลังไฟล์มาถึง
- **When:** `--mode backfill --from 2026-09-10` ของ credit_card
- **Then:** txn และ gold ของวันที่ได้รับผลรันใหม่อัตโนมัติ (มี `parent_run_id`) · gold SQL ที่ใช้ `{{input:credit_card}}` แทน `{{input_asof:…}}` ต้อง validate ไม่ผ่าน

<a id="ac-29"></a>

### AC-29
Source backup lines 1237–1241; apply effective precedence above.

#### AC-29: Backfill ด้วย release เก่า (FR-I.18, FR-J.6) · ⏭️ **Phase 3**
- **Given:** release A และ B deploy แล้วทั้งคู่ (B เปลี่ยน action ของกฎ 1 ข้อ)
- **When:** backfill ด้วย `--release-id A` และแบบไม่ระบุ
- **Then:** ได้ผลตาม A และ B ตามลำดับ · run_log บันทึก release_id ถูกต้อง · ถ้าแก้ไฟล์ใน release A 1 byte → block (verify-package)

<a id="ac-30"></a>

### AC-30
Source backup lines 1242–1246; apply effective precedence above.

#### AC-30: Erasure ชนะ backfill (FR-I.15) · ⏭️ **Phase 3**
- **Given:** token ของ national_id ลูกค้า 1 คนอยู่ใน erasure list และ cleartext ถูกลบจาก vault แล้ว
- **When:** backfill วันที่ที่มีลูกค้าคนนี้ (ไฟล์ใน landing ยังมี cleartext)
- **Then:** vault ไม่มี cleartext กลับมา · email/phone/birth_date ของแถวนั้นใน silver เป็น NULL

<a id="ac-31"></a>

### AC-31
Source backup lines 616–620; apply effective precedence above.

#### AC-31: ห้ามใช้ฟังก์ชันเวลา (FR-B.12) · ◐ Phase 1 (gold SQL → Phase 3)
- **Given:** tmp copy ที่มี BU rule `birth_date <= current_date()` / derived ที่ใช้ `now()` / gold SQL ที่ใช้ `rand()`
- **When:** validate
- **Then:** `NON_DETERMINISTIC_EXPR` ครบ 3 จุด พร้อมไฟล์ field และวิธีแก้ ("ใช้ business_date")

<a id="ac-32"></a>

### AC-32
Source backup lines 1247–1251; apply effective precedence above.

#### AC-32: Replay มีรั้วกั้น (FR-I.16) · ⏭️ **Phase 3**
- **Given:** run ของวัน D ที่ version ยังอยู่ใน retention และอีก run ที่เกิน retention
- **When:** `mdf_replay_dev` แบบไม่ใส่ `--confirm RESTORE` / ใส่ / สั่งกับ vault / สั่งกับ run ที่เกิน retention
- **Then:** ปฏิเสธ / RESTORE แล้ว rerun ถึงวันล่าสุดได้ผลเท่า AC-26 / ปฏิเสธ / ปฏิเสธพร้อมบอกให้ใช้ backfill

<a id="ac-33"></a>

### AC-33
Source backup lines 621–626; apply effective precedence above.

#### AC-33: FK config reference ที่หาไม่เจอ = defect ตอน generate config (FR-B.14, D-P4-7)
- **Given:** tmp copy ที่แก้ `credit_card.customer_id` ให้ `foreign_key: cc.customerX.customer_id` / `cc.customer.no_such_col` / ชี้ไปคอลัมน์ที่ `logicalType` ไม่ตรง
- **When:** `mdf validate` แล้ว `mdf compile`
- **Then:** validate exit 1 ด้วย `FK_TARGET_NOT_FOUND` / `FK_TARGET_NOT_FOUND` / `FK_TYPE_MISMATCH` พร้อมไฟล์ + field + วิธีแก้ภาษาไทย · compile ไม่เขียนไฟล์ใน `build/`
- **And:** คอลัมน์ที่ไม่มี `foreign_key` ไม่ถูกตรวจ FK · repo จริงหลัง migrate validate ผ่าน

<a id="ac-34"></a>

### AC-34
Source backup lines 627–632; apply effective precedence above.

#### AC-34: CI step รันบนเครื่องได้ผลเดียวกับที่ workflow จะรัน (FR-H.1, D-P4-5)
- **Given:** `.github/workflows/ci.yml`
- **When:** รันทุก `run:` step ของ job PR ตามลำดับบนเครื่อง (เช่น `uv sync` → `mdf validate` → `mdf compile` → `mdf package` → `mdf verify-package` → `ruff` → `pytest`)
- **Then:** ทุก step exit 0 และมี test ยืนยันว่ารายการคำสั่งที่รันบนเครื่องตรงกับ `run:` ใน YAML (ไม่ drift)
- **And:** CI run จริงบน GitHub ไม่ใช่เกณฑ์ปิด Phase 1 (ทำเมื่อมี DEP-1)

<a id="ac-35"></a>

### AC-35
Source backup lines 811–815; apply effective precedence above.

#### AC-35: Manifest ระบุ release ได้ (FR-F.2, FR-F.6) · 🚚 **Phase 2**
- **Given:** `mdf package --release` บน commit สะอาดของ `master`
- **When:** `mdf verify-package build/dev/release --expect-release-id mdf-<sha12>` และอีกครั้งด้วย id อื่น
- **Then:** ครั้งแรกผ่าน · manifest มี `release_id`, `source_commit` (เต็ม), `compiler_revision`, `uv_lock_sha256`, `ci_run_url`, `validation_report_sha256`, `preview=false` · ครั้งที่สอง exit 1 พร้อมข้อความไทยว่า release_id ไม่ตรง

<a id="ac-36"></a>

### AC-36
Source backup lines 816–820; apply effective precedence above.

#### AC-36: GitHub Release จริง (FR-L.1) · 🚚 **Phase 2**
- **Given:** push `master` บน repo จริง (DEP-1)
- **When:** `release.yml` รัน
- **Then:** มี GitHub Release `mdf-<sha12>` ที่ asset ตรงกับ manifest · รันซ้ำ = ข้าม · asset ต่างจากเดิม = fail · ไม่มี `git push`/`git commit` (AC-19)

<a id="ac-37"></a>

### AC-37
Source backup lines 821–826; apply effective precedence above.

#### AC-37: CD ส่ง release ถึง Databricks ได้จริง (FR-L.2–L.7, FR-L.11) — **ต้องได้ HG_PROD ก่อน** · 🚚 **Phase 2**
- **Given:** DEP-1…3 พร้อม และผู้ใช้อนุญาต HG_PROD
- **When:** `deploy-dev.yml` (หรือ manual ตาม AC-41) กับ `release_id` จาก AC-36
- **Then:** CD-1…8 ผ่านทุกขั้น · `databricks fs ls dbfs:/Volumes/dev_catalog/ops/files/releases/<release_id>` แสดงไฟล์ครบตาม manifest · verify รอบ CD-4 ผ่าน · `SELECT * FROM dev_catalog.ops.release_registry WHERE release_id = '<id>'` ได้ `REGISTERED` 1 แถว + `ACTIVATED` 1 แถว ที่ `manifest_sha256` ตรง
- **And:** หลักฐาน = release URL + run URL + ผล `fs ls` + ผล query (ไม่มี token)

<a id="ac-38"></a>

### AC-38
Source backup lines 827–831; apply effective precedence above.

#### AC-38: Immutable (FR-L.4, FR-J.6) · 🚚 **Phase 2**
- **Given:** release `<id>` sealed ใน Volume แล้ว
- **When:** (1) รัน CD ซ้ำด้วย `<id>` เดิม (2) แก้ไฟล์ใน package ที่ดาวน์โหลดมา 1 byte แล้วส่งด้วย `<id>` เดิม
- **Then:** (1) ไม่มีการคัดลอก ไม่มีแถว `REGISTERED` ใหม่ · (2) fail ที่ CD-2 · ไฟล์ใน Volume และ registry ไม่เปลี่ยน

<a id="ac-39"></a>

### AC-39
Source backup lines 832–836; apply effective precedence above.

#### AC-39: คัดลอกค้างแล้วต่อได้ (FR-L.4) · 🚚 **Phase 2**
- **Given:** โฟลเดอร์ `<id>` ใน Volume มีไฟล์ resolved บางส่วนแต่ไม่มี `manifest.json`
- **When:** รัน CD ใหม่
- **Then:** คัดลอกจนครบ แล้ว CD-4 ผ่าน (test ด้วย CLI จำลองได้ใน unit test · ของจริงบันทึกถ้าเกิดขึ้น)

<a id="ac-40"></a>

### AC-40
Source backup lines 837–841; apply effective precedence above.

#### AC-40: Registry append-only (FR-L.7) · 🚚 **Phase 2**
- **Given:** `ops.release_registry` ที่สร้างด้วย `delta.appendOnly=true`
- **When:** `UPDATE` / `DELETE` แถวใด ๆ และรัน `mdf_release_register_dev` ซ้ำ 2 ครั้ง
- **Then:** UPDATE/DELETE ถูกปฏิเสธ · มี `REGISTERED` 1 แถวต่อ release_id

<a id="ac-41"></a>

### AC-41
Source backup lines 842–847; apply effective precedence above.

#### AC-41: Auth ไม่มี secret และทางสำรองซื่อตรง (FR-L.9, FR-L.10) · 🚚 **Phase 2**
- **Given:** `.github/workflows/deploy-dev.yml`
- **When:** pytest อ่าน YAML
- **Then:** มี `id-token: write` + `DATABRICKS_AUTH_TYPE: github-oidc` · ไม่มี `DATABRICKS_TOKEN` / `DATABRICKS_CLIENT_SECRET` · ทุก step ของ CD เรียก `scripts/deliver_release.sh` ตัวเดียว
- **And:** ถ้าใช้ manual copy แทน หลักฐานของ AC-37 ติดป้าย "manual" และระบุว่า CD อัตโนมัติยังไม่ได้พิสูจน์

<a id="ac-42"></a>

### AC-42
Source backup lines 848–852; apply effective precedence above.

#### AC-42: runtime ได้ release_id ที่ระบุชัดเท่านั้น (FR-L.7, FR-I.18, D-P5-7) · 🚚 **Phase 2**
- **Given:** job `mdf_release_register_dev`
- **When:** รันโดยไม่ส่ง `release_id` / ส่ง id ที่ไม่มีใน Volume / ส่ง id ที่มี
- **Then:** fail (ไม่เดาล่าสุด) / fail พร้อมบอก path / ผ่าน

<a id="ac-43"></a>

### AC-43
Source backup lines 853–858; apply effective precedence above.

#### AC-43: ตั้ง delivery mode ได้ 3 แบบ (FR-L.12, FR-L.2) · 🚚 **Phase 2 · รอบ 10**
- **Given:** `config/env/dev.yaml`
- **When:** ตั้ง `delivery_mode` เป็น `auto` / `u2m` / `manual` / `xyz` / ไม่มี key แล้วรัน `mdf validate`
- **Then:** 3 ค่าแรกผ่าน · `xyz` และไม่มี key → exit 1 พร้อมข้อความไทย · static test ยืนยันว่า job ส่งของใน `release.yml` รันเฉพาะ `auto` (อ่านจากไฟล์ config ไม่ใช่ repo variable)
- **And:** push `master` จริงด้วย `u2m` → job ส่งของถูกข้าม · Job Summary แสดงขั้นต่อไปของ `u2m` พร้อม `release_id`

<a id="ac-45"></a>

### AC-45
Source backup lines 865–869; apply effective precedence above.

#### AC-45: บอกขั้นต่อไปครบทุก mode (FR-L.14) · 🚚 **Phase 2 · รอบ 10**
- **Given:** release ใหม่บน `master`
- **When:** เปิดหน้า run ของ `release.yml` / เปิด runbook / ทำให้ `deliver_release.sh` fail ที่ auth
- **Then:** เห็นขั้นต่อไปของ mode ที่ตั้งไว้ พร้อม `release_id` จริง · runbook มีครบ 3 mode และทุกคำสั่ง/SQL ในนั้นเคยรันจริง · script บอกคำสั่ง login หรือให้ไป mode `manual`

<a id="ac-46"></a>

### AC-46
Source backup lines 870–874; apply effective precedence above.

#### AC-46: compile/package ผลิต layout v2 per-source (FR-D.8, FR-F.7) · 🚚 **Phase 2 · รอบ 11**
- **Given:** `DataContract/` มีมากกว่า 1 source (เช่น `cc`, `xyz`)
- **When:** `mdf compile --env dev` แล้ว `mdf package --release`
- **Then:** `build/dev/resolved/<source>/{layer}.<source>.<dataset>.resolved.json` ต่อ source · `build/dev/release/<source>/…` เหมือนกัน · `manifest.json` มี `manifest_version: 2` และ `files[].path` เป็น `<source>/<file>` (POSIX `/`) เรียงตาม path

<a id="ac-47"></a>

### AC-47
Source backup lines 875–880; apply effective precedence above.

#### AC-47: verify-package ปฏิเสธ traversal และไฟล์แปลกปลอมใน subfolder (FR-F.8) · 🚚 **Phase 2 · รอบ 11**
- **Given:** package v2 ที่ path ใน manifest ถูกแก้เป็น `../evil.json`, `cc\\x.json`, `/etc/passwd`, หรือ path ลึก 2 ระดับ (`cc/sub/x.json`)
- **When:** `mdf verify-package <dir>`
- **Then:** fail ด้วย `[TAMPERED]` ทุกกรณี ก่อนอ่านเนื้อไฟล์
- **And:** มีไฟล์ที่ไม่อยู่ใน manifest วางไว้ใน `cc/extra.json` หรือมีโฟลเดอร์ว่าง `xyz/` ที่ไม่มีใน manifest → fail ด้วย `[TAMPERED]` เช่นกัน (ตรวจ recursive ไม่ใช่แค่ราก)

<a id="ac-48"></a>

### AC-48
Source backup lines 881–886; apply effective precedence above.

#### AC-48: verify-package อ่านได้ทั้ง v1 และ v2 (FR-F.8, D-P5-11 Q4) · 🚚 **Phase 2 · รอบ 11 · แก้รอบ 6**
- **Given:** (1) release v1 flat ที่มีอยู่จริงใน Volume (เช่น `mdf-ef2f425903b6`) (2) release v2 ใหม่จาก AC-46
- **When:** `mdf verify-package <dir>` กับทั้งสอง
- **Then:** ทั้งคู่ผ่าน โดย verifier อ่าน layout จาก `manifest_version` เท่านั้น · ส่ง manifest ที่มี `manifest_version: 3` (ไม่รู้จัก) → fail · **[รอบ 12] แทนที่ด้วย…:** v3 กลายเป็นเวอร์ชันที่รู้จัก (FR-M.8) → ใช้ `manifest_version: 4` เป็นกรณี "ไม่รู้จัก" แทน (AC-57 ข้อ 7)
- **And (รอบ 6, OQ-P5-7 = เตือน):** ผลลัพธ์ของ v1 มีข้อความคำเตือน `[WARN] legacy flat layout` ปรากฏ (ไม่ fail) · ผลลัพธ์ของ v2 **ไม่มี** คำเตือนนี้

<a id="ac-49"></a>

### AC-49
Source backup lines 887–891; apply effective precedence above.

#### AC-49: CD-3/CD-4 recursive round-trip คง subfolder (FR-L.4, FR-L.4a, FR-L.5, FR-J.6) · 🚚 **Phase 2 · รอบ 11**
- **Given:** release v2 จาก AC-46 ที่ยังไม่เคยส่ง
- **When:** รัน `scripts/deliver_release.sh <release_id>` (mode `u2m`)
- **Then:** `databricks fs ls -r dbfs:/Volumes/dev_catalog/ops/files/releases/<release_id>` เห็น subfolder `<source>/` ครบทุกไฟล์ · CD-4 คัดลอกกลับแล้ว `verify-package` ผ่าน (AC-46/47 ต้องผ่านด้วย) · `manifest.json` ยังเป็นไฟล์สุดท้ายที่ copy (sealed rule เดิมไม่เปลี่ยน)

<a id="ac-51"></a>

### AC-51
Source backup lines 898–906; apply effective precedence above.

#### AC-51: zip เป็น asset เดียว รอด transport + กัน zip-slip + v1 legacy ยังดาวน์โหลดได้ (FR-L.1a, FR-L.1b, FR-L.3a) · 🚚 **Phase 2 · รอบ 11 · รอบ 5 · แก้รอบ 6**
- **Given:** release v2 ใหม่ (จาก AC-46) ที่ publish ผ่าน `release.yml`
- **When:** ดู asset ของ GitHub Release นั้น
- **Then:** มี asset เดียวชื่อ `<release_id>.zip` (ไม่มี asset แยกไฟล์แบบเดิม) · แตก zip แล้วโครงสร้างตรงราก release (`manifest.json`, `validation-report.json`, `<source>/…`) ไม่มีโฟลเดอร์ครอบ
- **And (รอบ 6, OQ-P5-9 = เพิ่ม):** ทั้ง **Job Summary ของ run `release.yml`** และ **release notes ของ GitHub Release นั้น** มีข้อความ `manifest_sha256` ของ `manifest.json` ปรากฏตรงกัน
- **And:** push commit เดิมซ้ำ (identical content) → ขั้น idempotency ของ `release.yml` ดาวน์โหลด zip เดิม แตก เทียบ `manifest.json` (ไม่ใช่ hash ของ zip) → skip ไม่สร้างซ้ำ
- **And:** `deliver_release.sh <release_id>` (CD-1) ดาวน์โหลด zip แล้วแตก → ใส่ path ที่มี `../../etc/passwd` หรือ absolute path ปลอมไว้ใน zip ทดสอบ (mock) → CD-1 fail ก่อนเข้า CD-2 ห้ามเขียนไฟล์นอก working dir
- **And (v1 legacy):** `deliver_release.sh mdf-ef2f425903b6` (release เดิมก่อนรอบ 5, asset flat หลายไฟล์ ไม่มี `.zip`) → CD-1 ยังดาวน์โหลดและ deliver ได้ตามพฤติกรรมเดิม (ไม่ต้องมี zip)

<a id="ac-52"></a>

### AC-52
Source backup lines 907–911; apply effective precedence above.

#### AC-52: compile ได้ `calendar` ที่ครบ (FR-M.1, FR-M.3) · 🚚 **Phase 2 · รอบ 12**
- **Given:** สำเนา contract ใน `tmp_path` ที่ใส่ค่า calendar ครบ (ค่าทดสอบ ไม่ใช่ค่าจริง) สำหรับ `daily`, `workday_excluding_holidays` (มี holidays), `day_of_month` และ `explicit_dates`
- **When:** `mdf compile --env dev`
- **Then:** `calendar.status = COMPLETE` · bronze และ silver ของ dataset เดียวกันมี `calendar` เหมือนกันทุก byte · `missing_after_seconds = 14400`, `recovery_window_seconds = 172800` · list เรียงแล้ว · compile ซ้ำได้ bytes เดิม (AC-11)

<a id="ac-53"></a>

### AC-53
Source backup lines 912–916; apply effective precedence above.

#### AC-53: calendar ที่ผิดรูปแบบถูกปฏิเสธ (FR-M.2) · 🚚 **Phase 2 · รอบ 12**
- **Given:** contract ที่มีอย่างใดอย่างหนึ่ง: ~~timezone `Asia/Bangkokk`~~ (ตัดออก · OQ-TRI-12a) timezone เป็นตัวเลขหรือ string ว่าง, `expected_at: 25:00`, `expected_day_offset: -1`, holiday ซ้ำ, `day_of_month: 32`, `type: explicit_dates` แต่ list ว่าง, `effective_to < effective_from`, `recovery_window` 2 h < latency 4 h
- **When:** `mdf validate`
- **Then:** exit 1 ทุกกรณี · ข้อความไทยบอกไฟล์ + field + วิธีแก้ · compile ไม่เขียนไฟล์

<a id="ac-54"></a>

### AC-54
Source backup lines 917–922; apply effective precedence above.

#### AC-54: ยังไม่มีค่าจากเจ้าของ = `PENDING_OWNER` ไม่เดาค่า (FR-M.4) · 🚚 **Phase 2 · รอบ 12**
- **Given:** contract `cc` จริงใน repo (ยังไม่มี `expected_at`/offset/timezone/schedule)
- **When:** `mdf validate` → `mdf compile --env dev` → `mdf package --release` (บน tree สะอาด)
- **Then:** validate exit 0 พร้อม warning `[CALENDAR_PENDING_OWNER]` ครบ 3 dataset · `calendar.status = PENDING_OWNER` และ `expected_at`/`expected_day_offset`/`timezone`/`schedule_type` = `null` (ไม่ใช่ค่าที่เดา) แต่ `missing_after_seconds = 14400` · gate ผ่านพร้อม `[WARN] calendar PENDING_OWNER`
- **And:** `expected_at: "25:00"` (มีค่าแต่ผิด) → exit 1 ไม่ใช่ warning

<a id="ac-55"></a>

### AC-55
Source backup lines 923–929; apply effective precedence above.

#### AC-55: `reader` และธง privacy อยู่ใน resolved JSON (FR-M.5, FR-M.6) · 🚚 **Phase 2 · รอบ 12**
- **Given:** contract `cc` จริง
- **When:** `mdf compile --env dev`
- **Then:** `reader.file_pattern` ของ 3 dataset = `customer_{{business_date}}.csv`, `credit_card_{{business_date}}.csv`, `credit_card_txn_{{business_date}}*.csv` · `reader.format = csv`, `header = true`, `encoding = utf-8` · `card_pan` ของ credit_card และ credit_card_txn มี `pii: true, pci: true` · `national_id` มี `pii: true, pci: false` และ `tags` มี `dq:pattern` · bronze = silver
- **And:** ลบ `pii` ออกจากคอลัมน์หนึ่ง (tmp copy) → validate exit 1 · ตั้ง `pci: true` บนคอลัมน์ที่ pipeline ไม่ tokenise (tmp copy) → exit 1 (P1)
- **And:** pipeline ของ customer ไม่ถูกแก้ (`national_id`/`full_name` ยัง `tokenise: true` · Q5)

<a id="ac-56"></a>

### AC-56
Source backup lines 930–934; apply effective precedence above.

#### AC-56: package v3 แนบ contract (FR-M.7) · 🚚 **Phase 2 · รอบ 12**
- **Given:** compile ของ `cc` ผ่าน
- **When:** `mdf package --env dev` แล้ว `mdf verify-package build/dev/release`
- **Then:** `manifest_version: 3` · `files[]` 9 entry ทุก entry มี `kind`/`source`/`dataset` (+`layer` ของ resolved) · `cc/customer.odcs.yaml` ฯลฯ มี bytes = ไฟล์ใน git · sha256 ของมัน = `lineage.contract_sha256` ของ resolved 2 ไฟล์ · `lineage.contract_bundle_path = cc/<dataset>.odcs.yaml` · verify ผ่านโดยไม่มี `[WARN] legacy`

<a id="ac-57"></a>

### AC-57
Source backup lines 935–940; apply effective precedence above.

#### AC-57: verify-package v3 จับการแก้/ขาด contract (FR-M.8) · 🚚 **Phase 2 · รอบ 12**
- **Given:** package v3 จาก AC-56
- **When:** (1) แก้ `cc/customer.odcs.yaml` 1 byte (2) ลบไฟล์นั้นและ entry ใน manifest (3) เปลี่ยน `kind` เป็น `other` (4) เปลี่ยน `dataset` ของ entry ให้ไม่ตรงชื่อไฟล์ (5) วาง `cc/extra.odcs.yaml` ที่ไม่อยู่ใน manifest (6) แก้ `lineage.contract_sha256` ใน resolved ไฟล์หนึ่งพร้อมแก้ hash ใน manifest ให้ตรง (7) `manifest_version: 4`
- **Then:** fail `[TAMPERED]` ทุกกรณี (7 = unknown manifest_version)
- **And:** package v1 (`mdf-ef2f425903b6`) ยังผ่านพร้อม `[WARN] legacy flat layout` · package v2 ยังผ่านโดยไม่มีคำเตือน

<a id="ac-58"></a>

### AC-58
Source backup lines 941–946; apply effective precedence above.

#### AC-58: ส่ง release v3 ถึง Volume และ registry ได้จริง (FR-M.9) · 🚚 **Phase 2 · รอบ 12** — **HG_PROD** (รวมใน T-53)
- **Given:** release v3 ใหม่จาก `release.yml` (zip asset)
- **When:** ส่งด้วย mode `u2m` และ mode `manual` (M-1…M-7 ที่อัปโหลด `.odcs.yaml` เข้า `<source>/` ด้วย)
- **Then:** `databricks fs ls -r` เห็น 9 ไฟล์ใต้ `cc/` + 2 ไฟล์ราก · CD-4 verify ผ่าน · registry `REGISTERED` + `ACTIVATED` ที่ `file_count = 9` และ `manifest_sha256` ตรงกับ Job Summary/release notes
- **And (negative manual):** ไม่อัปโหลด `.odcs.yaml` → `register_release.sql` error ไม่มีแถวใหม่

<a id="as-11"></a>

### AS-11
Source backup lines 1305–1305; apply effective precedence above.

AS-11 | **⏭️ [Phase 3]** Bronze เก็บทุกคอลัมน์เป็น string · cast ที่ silver | `_rescued_data` เป็นฟีเจอร์ของ Databricks ทำให้ทดสอบ local ไม่ได้ · เก็บค่า raw ได้ครบ | ถ้าต้องการ typed bronze ต้องใช้ rescued data + test บน workspace | OQ-P1-14

<a id="as-12"></a>

### AS-12
Source backup lines 704–704; apply effective precedence above.

AS-12 | ถ้าไม่มี CSV ตัวอย่าง agent จะสร้าง synthetic ตาม REALITY | DEP-8 | Synthetic อาจไม่ครอบคลุมทุกกรณีจริง | DEP-8

<a id="as-14"></a>

### AS-14
Source backup lines 1306–1306; apply effective precedence above.

AS-14 | **⏭️ [Phase 3]** ไฟล์ master เป็น snapshot หรือ delta ก็ได้ · PK ที่ไม่อยู่ในไฟล์ของ D **ไม่ถือว่าถูกลบ** | contract ไม่ได้บอก | ถ้าต้นทางส่ง full snapshot และต้องการจับการลบ ต้องเพิ่ม `_is_deleted` | OQ-P1-17

<a id="as-15"></a>

### AS-15
Source backup lines 1307–1307; apply effective precedence above.

AS-15 | **⏭️ [Phase 3]** SCD2 เก็บ 1 version ต่อ (PK, วันที่ได้รับ) โดยไม่บีบ version ที่ค่าเหมือนเดิม | การบีบทำให้ผลขึ้นกับลำดับที่รัน | storage โต (R-16) | OQ-P1-18

<a id="as-16"></a>

### AS-16
Source backup lines 1308–1308; apply effective precedence above.

AS-16 | **⏭️ [Phase 3]** txn_id ที่ซ้ำข้ามวัน → flag `dup_across_dates` ไม่ drop | merge ข้ามวันขัดกับ BF-2 | ถ้าต้องการเก็บแค่แถวเดียวต้องมีขั้นตอนข้ามวัน | OQ-P1-19

<a id="as-17"></a>

### AS-17
Source backup lines 1309–1309; apply effective precedence above.

AS-17 | **⏭️ [Phase 3]** Delta retention = 30 วัน (`deletedFileRetentionDuration` และ `logRetentionDuration`) → replay ย้อนได้ 30 วัน · รอบนี้ไม่มี retention job | ค่าตั้งต้น 7 วันสั้นเกินไปสำหรับกู้คืน | storage | OQ-P1-20

<a id="as-18"></a>

### AS-18
Source backup lines 1310–1310; apply effective precedence above.

AS-18 | **⏭️ [Phase 3]** HMAC key rotation = rebuild ทั้งหมด ไม่ทำในรอบนี้ · run_log เก็บ key version | token ต้องคงที่เพื่อ join ข้ามวัน | – | –

<a id="as-19"></a>

### AS-19
Source backup lines 1311–1311; apply effective precedence above.

AS-19 | **⏭️ [Phase 3]** Erasure: ไม่เขียน vault + NULL คอลัมน์ PII ที่ไม่ tokenise (email, phone, birth_date) · แถวยังอยู่ (token เป็น pseudonym) | D-P3-8 ไม่ได้ระบุผลต่อแถว | ถ้าต้องลบทั้งแถว AC-30 จะเปลี่ยน | OQ-P1-21

<a id="as-20"></a>

### AS-20
Source backup lines 1312–1312; apply effective precedence above.

AS-20 | **⏭️ [Phase 3]** Runtime code ไม่ถูกเก็บแยกตาม release · runtime ต้องอ่าน resolved config ทุก `schema_version` ที่ยังรองรับได้ · run_log บันทึก `runtime_version` | การ deploy code หลายรุ่นใน DAB ซับซ้อนเกิน | ผลของ release เก่าอาจต่างเล็กน้อยถ้า logic runtime เปลี่ยน | –

<a id="as-21"></a>

### AS-21
Source backup lines 705–705; apply effective precedence above.

AS-21 | Library rule `kind: function` (luhn, fk_exists, cast_ok) ใน Phase 1 = ประกาศชื่อใน function registry + validator ตรวจว่ามีชื่ออยู่จริง · โค้ด Spark ของฟังก์ชัน → Phase 3 | D-P4-1 ไม่รันกับข้อมูล | Phase 3 อาจต้องเปลี่ยน signature ของฟังก์ชัน → bump library | Phase 3

<a id="as-22"></a>

### AS-22
Source backup lines 1011–1011; apply effective precedence above.

AS-22 | 🚚 **[Phase 2]** Publish release ทุก push `master` (1 commit = 1 release) · `workflow_dispatch` ใช้ส่ง release เดิมซ้ำ/ย้อน | FR-H.2 เดิม + D-P5-6 · ผู้ใช้ไม่ได้ระบุ trigger | ถ้าต้องการปล่อยเฉพาะตอน tag ต้องเปลี่ยน FR-L.1 | OQ-P5-3

<a id="as-23"></a>

### AS-23
Source backup lines 1012–1012; apply effective precedence above.

AS-23 | 🚚 **[Phase 2]** "append แบบ manage delta path" = ตาราง managed Delta `{catalog}.ops.release_registry` (append-only, 1 แถวต่อ event) · ไม่เก็บ JSON ทั้งก้อนลงตาราง (JSON อยู่ใน Volume ที่เดียว) | ⚠️ Agent Interpretation ของ D-P5-2 · ผู้ใช้ไม่ได้ตอบคำถามเรื่องนี้ | ถ้าต้องการให้ medallion อ่าน config จากตารางแทนไฟล์ ต้องเพิ่ม `ops.resolved_config` | OQ-P5-4

<a id="as-24"></a>

### AS-24
Source backup lines 1013–1013; apply effective precedence above.

AS-24 | 🚚 **[Phase 2]** CD-8 "เปิด schedule" ใน Phase 2 = append `ACTIVATED` + ตั้ง bundle variable `active_release_id` เท่านั้น เพราะยังไม่มี job ที่มี schedule · schedule จริงเกิดใน Phase 3 (`mdf_cc_dev`) | D-P5-8 ข้อ 8 + D-P5-3 | – | –

<a id="as-25"></a>

### AS-25
Source backup lines 1014–1014; apply effective precedence above.

AS-25 | 🚚 **[Phase 2]** Job `mdf_release_register_dev` (serverless, ไม่มี schedule) คือ "Databricks Job" ของ CD-5…7 · ใช้ wheel `mdf` เดียวกับ CI | D-P5-8 ข้อ 5–7 ต้องมี job ให้ส่ง release_id และ smoke | – | –

<a id="as-26"></a>

### AS-26
Source backup lines 1015–1015; apply effective precedence above.

AS-26 | 🚚 **[Phase 2 · รอบ 10]** mode เก็บใน `config/env/<env>.yaml` (control file เดียว D-P0-9) ไม่ใช่ GitHub variable · ค่าตั้งต้น `dev` = `u2m` เพราะ workspace ปัจจุบันเป็น Free Edition | ⚠️ Agent Interpretation ของ "user config mode ดังกล่าวได้ 3 แบบ" | ถ้าอยากตั้งใน GitHub UI ต้องย้ายไป repo variable | OQ-P5-5

<a id="as-27"></a>

### AS-27
Source backup lines 1016–1016; apply effective precedence above.

AS-27 | 🚚 **[Phase 2 · รอบ 10]** "human ทำทั้งหมด" (mode 3) = ไม่ใช้ CLI ไม่รันอะไรบนเครื่อง · ใช้แค่เบราว์เซอร์ (GitHub + Databricks UI) · bundle deploy/job แทนด้วย SQL ใน SQL editor ที่ตรวจเท่ากับ job | ⚠️ Agent Interpretation | ถ้า "human" = ตรวจด้วยตาอย่างเดียวไม่มี SQL → ต้องเขียน M-5 ใหม่ | OQ-P5-5

<a id="as-28"></a>

### AS-28
Source backup lines 1017–1017; apply effective precedence above.

AS-28 | 🚚 **[Phase 2 · รอบ 10]** Phase 2 ปิดได้โดย mode `auto` = BUILD + preflight ที่ fail พร้อมข้อความ (ไม่ใช่ส่งสำเร็จ) เพราะผู้ใช้กำหนดว่า mode 1 ใช้ "กรณีที่ไม่ใช้ Free Edition" | D-P5-10 + R-20 | ถ้าต้องเห็น mode 1 ส่งสำเร็จก่อนปิด → ต้องมี workspace แบบเสียเงิน (งบ ≠ ฿0) | OQ-P5-6

<a id="as-29"></a>

### AS-29
Source backup lines 1018–1018; apply effective precedence above.

AS-29 | 🚚 **[Phase 2 · รอบ 11]** `<source>` ที่ใช้เป็นชื่อโฟลเดอร์ = ชื่อโฟลเดอร์จริงใต้ `DataContract/` (ผ่าน `discover_datasets` อยู่แล้ว) — ไม่มี source ไหนชื่อขึ้นต้นด้วย `_` (สงวนให้ gold) หรือมีอักขระที่ทำให้ path หลุด เพราะ `discover_datasets`/FR-B.6 คุมอยู่แล้ว | โค้ดปัจจุบัน (`src/mdf/loading.py:135`) ข้าม `_*`/`.` อยู่แล้ว · ยังไม่เคยมี source ชื่อแปลก | ถ้ามี source ชื่อมีจุด/สแลชในอนาคต ต้องเพิ่ม validation ที่ discovery ก่อน compile | –

<a id="as-3"></a>

### AS-3
Source backup lines 168–168; apply effective precedence above.

Repo layout (**Proposed**, AS-3) | **◐ [🚚 Phase 2: `databricks.yml`, `resources/release.job.yml`, `scripts/deliver_release.sh`, `.github/workflows/deploy-dev.yml` · ⏭️ Phase 3: `src/mdf/runtime/`, `resources/cc.job.yml`]** `DataContract/{<src>/contract, <src>/pipeline, _gold/<domain>, _template}` · `config/{env/, naming.yaml, dq_library.yaml, rules/, schemas/}` · `src/mdf/{loading, validation, rules, dq, compile, diff, package, trace, cli}.py` + `src/mdf/runtime/` · `tests/` · `databricks.yml` + `resources/` · `build/` (gitignore) | – | –

Source backup lines 698–698; apply effective precedence above.

AS-3 | Layout `config/{env, naming.yaml, dq_library.yaml, rules, schemas}` | OQ-P1-2/3 ไม่มีคำตอบ | ย้าย path (เปลี่ยนน้อย) | OQ-P1-2, OQ-P1-3

<a id="as-30"></a>

### AS-30
Source backup lines 1019–1019; apply effective precedence above.

AS-30 | 🚚 **[Phase 2 · รอบ 12]** Q2 = (b): calendar ที่ยังไม่มีค่าจากเจ้าของ = warning + `PENDING_OWNER` ไม่ block release · ค่าที่มีแต่ผิด = error | ผู้ใช้เลือกตามคำแนะนำ (D-P5-12) | ถ้าต้องการ block release จนกว่าค่าครบ → เปลี่ยน FR-M.4 เป็น error | OQ-P5-10

<a id="as-31"></a>

### AS-31
Source backup lines 1020–1020; apply effective precedence above.

AS-31 | 🚚 **[Phase 2 · รอบ 12]** `recovery_window` = 2 วัน (172800 วินาที) สำหรับ 3 dataset ของ `cc` | ⚠️ ค่ามาจาก `../Medallion/config_requirements.md` CR-01 ("chosen 2 d retry window") ผู้ใช้อนุมัติขอบเขต CR-01 แล้ว แต่ไม่ได้พูดถึงเลขนี้โดยตรง | ถ้าไม่ใช่ 2 วัน ต้องแก้ contract (ไม่ต้องแก้โค้ด) | OQ-P5-10

<a id="as-32"></a>

### AS-32
Source backup lines 1021–1021; apply effective precedence above.

AS-32 | 🚚 **[Phase 2 · รอบ 12]** bytes ของ contract ที่แนบใน release = bytes ใน git (LF ตาม `.gitattributes`) จึงใช้ `lineage.contract_sha256` เดิมเทียบได้ตรง | `.gitattributes` บังคับ `eol=lf` อยู่แล้ว · FR-D.5 normalise CRLF ก่อน hash | ถ้า hash ไม่ตรงบน Windows → T-56 ต้อง normalise ก่อนคัดลอก | AC-56 บน Windows + Linux CI

<a id="as-33"></a>

### AS-33
Source backup lines 1022–1022; apply effective precedence above.

AS-33 | 🚚 **[Phase 2 · รอบ 12]** release v2 ไม่มีคำเตือนใหม่ (ต่างจาก v1 ที่เตือน legacy) แม้จะไม่มี `calendar` | ⚠️ Agent Interpretation: คำเตือนของ v1 มาจากคำตอบ OQ-P5-7 เรื่อง layout เท่านั้น · การที่ release ไม่มี calendar เป็นเรื่องของ runtime (FR-M.10) | ถ้าต้องการเตือนด้วย → เพิ่มใน FR-M.8 | –

<a id="as-4"></a>

### AS-4
Source backup lines 169–169; apply effective precedence above.

Control file (AS-4) | `config/env/dev.yaml`: `env, dummy, catalog: dev_catalog, secret_scope, workspace_host, timezone: Asia/Bangkok, schedules` · `config/naming.yaml`: `table, landing, quarantine, vault, checkpoint, run_log, config_id, contract_id` | – | OQ-P1-2 (ผู้ใช้ยังไม่ยืนยันรูปแบบ)

Source backup lines 699–699; apply effective precedence above.

AS-4 | Control file = `config/env/<env>.yaml` 1 ไฟล์ต่อ env + `config/naming.yaml` ใช้ร่วมกัน | ผู้ใช้พูดว่า "file หนึ่งตัว" | ถ้าต้องการไฟล์เดียวจริง ๆ ก็รวมสองไฟล์ได้ | OQ-P1-2

<a id="as-5"></a>

### AS-5
Source backup lines 700–700; apply effective precedence above.

AS-5 | Cross-file rule ใช้ operator `ref_exists` / `column_in_contract` ใน JSON · operator ใหม่ต้องแก้ Python | OQ-P1-5 ไม่มีคำตอบ | ถ้าต้องไม่มี Python เลย DSL จะซับซ้อนมาก (R-1) | OQ-P1-5

<a id="as-7"></a>

### AS-7
Source backup lines 701–701; apply effective precedence above.

AS-7 | CODEOWNERS เป็นไฟล์ตัวอย่างที่ยังไม่ใส่ชื่อจริง | OQ-P1-8 ไม่มีคำตอบ | – | DEP-5

<a id="as-8"></a>

### AS-8
Source backup lines 702–702; apply effective precedence above.

AS-8 | ไม่มีตัวเลขเรื่องปริมาณ · NFR-8 = ≤10 วินาที | OQ-P1-9 ไม่มีคำตอบ | ต้องปรับ design ถ้ามีหลายร้อย dataset | OQ-P1-9

<a id="as-9"></a>

### AS-9
Source backup lines 703–703; apply effective precedence above.

AS-9 | Original Draft ฝังเฉพาะไฟล์สั้น ไฟล์ยาวอ้างผ่าน snapshot + sha256 | ~100 KB จะทำให้เอกสารอ่านไม่ได้ (Q-20 ไม่มีคำตอบ) | ถ้าต้องการฝังทั้งหมด จะเพิ่มเป็นภาคผนวกด้วย script | Q-20

<a id="bf-1"></a>

### BF-1
Source backup lines 1352–1352; apply effective precedence above.

- **BF-1 ไม่มีนาฬิกา:** ทุก expression (BU rule, derived, gold SQL, library rule) ห้ามใช้ `current_date`, `current_timestamp`, `now`, `rand`, `uuid` และฟังก์ชันที่ผลขึ้นกับเวลาที่รัน ถ้าต้องใช้วันที่ให้ใช้ `business_date` → validator error `NON_DETERMINISTIC_EXPR` (FR-B.12)

<a id="bf-10"></a>

### BF-10
Source backup lines 1361–1361; apply effective precedence above.

- **BF-10 Token คงที่:** HMAC key version ต้องเท่ากับที่ใช้กับข้อมูลเดิม ถ้าไม่ตรงให้ block (FR-I.17) · การ rotate key = rebuild ทั้งหมด ซึ่งไม่อยู่ในรอบนี้ (AS-18)

<a id="bf-2"></a>

### BF-2
Source backup lines 1353–1353; apply effective precedence above.

- **BF-2 เขียนทีละวันเสมอ:** ตารางที่แบ่ง partition ตาม business_date (bronze, silver txn, quarantine, gold) เขียนด้วย Delta `replaceWhere business_date = D` ห้าม append หรือ merge ข้ามวัน (D-P3-7)

<a id="bf-3"></a>

### BF-3
Source backup lines 1354–1354; apply effective precedence above.

- **BF-3 ต้นทางเก็บครบ:** landing volume = raw archive เก็บ 1825 วัน · ถ้า bronze ของ D หมดอายุแล้ว runtime สร้าง bronze D ใหม่จาก landing อัตโนมัติ (D-P3-3) · ไฟล์ใน landing ห้ามถูกเขียนทับ ส่วนไฟล์แก้ไขจากต้นทางต้องมาเป็นชื่อใหม่

<a id="bf-4"></a>

### BF-4
Source backup lines 1355–1355; apply effective precedence above.

- **BF-4 Master เป็น SCD2:** ทำให้ backfill ย้อนหลังหรือรันไม่เรียงวันได้ผลเท่าเดิม (FR-I.11)

<a id="bf-5"></a>

### BF-5
Source backup lines 1356–1356; apply effective precedence above.

- **BF-5 อ่านแบบ as-of:** FK lookup และ gold อ่าน master **ณ วัน D** เสมอ ไม่ใช่สถานะปัจจุบัน (FR-I.14)

<a id="bf-6"></a>

### BF-6
Source backup lines 1357–1357; apply effective precedence above.

- **BF-6 Cascade:** backfill วัน D ของตารางต้นน้ำ ทำให้ downstream ของวันที่ได้รับผลกระทบต้องรันใหม่ runtime คำนวณรายการวันเอง และรันต่อให้เมื่อใช้ `--cascade` (ค่าตั้งต้น) (FR-I.13)

<a id="bf-7"></a>

### BF-7
Source backup lines 1358–1358; apply effective precedence above.

- **BF-7 Config ย้อนได้:** ค่าตั้งต้นคือ release ปัจจุบัน ถ้าต้องการผลเหมือนตอนนั้นให้ระบุ `release_id` · ทุก release ที่เคย deploy ต้องเก็บไว้ใน volume ห้ามลบ (D-P3-5, FR-J.6)

<a id="bf-8"></a>

### BF-8
Source backup lines 1359–1359; apply effective precedence above.

- **BF-8 หลักฐาน input:** run_log เก็บรายการไฟล์ที่อ่าน (path, size, sha256) และ Delta version ก่อน/หลังของทุกตารางที่เขียน จึงพิสูจน์ได้ว่า backfill ใช้ input เดียวกับรอบเดิม (FR-I.9)

<a id="bf-9"></a>

### BF-9
Source backup lines 1360–1360; apply effective precedence above.

- **BF-9 Erasure ชนะ backfill:** ทุก run รวม backfill และ replay กรองด้วย erasure list ก่อนเขียน vault · vault, erasure list และ run_log **ห้าม RESTORE** (FR-I.15, FR-I.16)

<a id="bl-m1"></a>

### BL-M1
Source backup lines 1337–1337; apply effective precedence above.

BL-M1 | **CR-02 ส่วนนโยบาย:** protection action ต่อคอลัมน์ · PII-only (`national_id`, `full_name`) เลิก tokenise เปลี่ยนเป็น mask `*` · governed view ของ `birth_date` (DATE → string `*`) · PCI token namespace ร่วม `cc.card_pan` + versioned `key_ref` · กลุ่มที่ unmask ได้ | **Q5 = เก็บไว้ก่อน** · ตอนนี้คงตาม SSOT (tokenise `national_id`/`full_name`) | §Security "PII ที่ tokenise: national_id, full_name" · BR-20 · DPR-06 · OQ-P1-12

<a id="bl-m2"></a>

### BL-M2
Source backup lines 1338–1338; apply effective precedence above.

BL-M2 | **CR-03:** `pipeline.extensions.medallion` (`silver_date_ordering`, `blocked_date`, `pii_display`, `pci_tokenization`) + validator enum/cross-check | Q6 ตัดสิน**หลักการ**แล้ว (ดู CONFLICT-18) · shape ของ YAML ยังเป็นตัวอย่าง ยังไม่ทำ | NFR-11, BF-6 (cascade อัตโนมัติ)

<a id="bl-m3"></a>

### BL-M3
Source backup lines 1339–1339; apply effective precedence above.

BL-M3 | **CR-04:** `notification_outbox` ใน `config/naming.yaml` · `notification: {recipient_source: job_author, channel: email, delivery_enabled: false}` ใน env · สถานะ `PENDING_EMAIL` · backfill job รับ outbox request ID | ยังไม่ถาม | – (ใหม่ทั้งหมด)

<a id="bl-m4"></a>

### BL-M4
Source backup lines 1340–1340; apply effective precedence above.

BL-M4 | **CR-05:** lineage ระดับคอลัมน์ทุก field (contract column → cast → normalise → DQ rule IDs → tokenise/mask/view → derived) | ยังไม่ถาม | –

<a id="bl-m5"></a>

### BL-M5
Source backup lines 1341–1341; apply effective precedence above.

BL-M5 | **CR-06 ฝั่ง Medallion:** loader ใน `../Medallion/framework/_shared_helpers_bronze.py` อ่าน v3 + fixture ใหม่แทน `releases/mdf-44d14f829e93/` ที่หายไป | repo อื่น · ใช้สัญญาใน FR-M.10 | –

<a id="br-1"></a>

### BR-1
Source backup lines 332–332; apply effective precedence above.

BR-1 | `pattern` | cc.customer.national_id | `logicalTypeOptions.pattern: ^[0-9]{13}$` | reject | `national_id_well_formed` (DC-2)

<a id="br-10"></a>

### BR-10
Source backup lines 346–346; apply effective precedence above.

BR-10 | `birth_date_not_future` | customer | `birth_date <= business_date` (✅ D-P3-1 · เดิม `current_date()`) | reject | pre-tokenise

<a id="br-11"></a>

### BR-11
Source backup lines 347–347; apply effective precedence above.

BR-11 | `registered_after_birth` | customer | `registered_date IS NULL OR registered_date > birth_date` | flag | pre-tokenise

<a id="br-12"></a>

### BR-12
Source backup lines 348–348; apply effective precedence above.

BR-12 | `expiry_after_issue` | credit_card | `expiry_date > issue_date` | reject | pre-tokenise

<a id="br-13"></a>

### BR-13
Source backup lines 349–349; apply effective precedence above.

BR-13 | `credit_limit_positive` | credit_card | `credit_limit > 0` (หลัง cast) | reject | pre-tokenise

<a id="br-14"></a>

### BR-14
Source backup lines 350–350; apply effective precedence above.

BR-14 | `approved_amount_positive` | credit_card_txn | `NOT (txn_status = 'APPROVED' AND amount <= 0)` | reject | pre-tokenise

<a id="br-15"></a>

### BR-15
Source backup lines 351–351; apply effective precedence above.

BR-15 | `txn_timestamp_matches_business_date` | credit_card_txn | `txn_timestamp IS NULL OR to_date(txn_timestamp) = business_date` | flag | pre-tokenise

<a id="br-16"></a>

### BR-16
Source backup lines 352–352; apply effective precedence above.

BR-16 | `amount_within_sane_bound` | credit_card_txn | `amount <= 1000000` | flag | pre-tokenise

<a id="br-17"></a>

### BR-17
Source backup lines 353–353; apply effective precedence above.

BR-17 | derived `txn_card_key` | credit_card_txn | `concat(card_pan, '_', date_format(business_date,'yyyyMMdd'))` (card_pan = token) | – | post-tokenise (DRAFT1 §9.3)

<a id="br-18"></a>

### BR-18
Source backup lines 359–359; apply effective precedence above.

BR-18 | กฎพื้นฐานทุกข้อต้องมาจาก library · ห้ามมี SQL ใน contract · ทุก tag ต้องมีค่าที่ต้องใช้ และทุกค่าต้องมี tag (DQ-2, DQ-3) | validate | error | –

<a id="br-19"></a>

### BR-19
Source backup lines 360–360; apply effective precedence above.

BR-19 | PCI → ต้อง `tokenise: true` · คอลัมน์ที่เป็น dedup key และถูก tokenise ต้องมี normalise | validate | error | –

<a id="br-2"></a>

### BR-2
Source backup lines 333–333; apply effective precedence above.

BR-2 | `not_blank` (library ใหม่: `{col} IS NULL OR trim({col}) <> ''`) + `not_null` (auto) | cc.customer.full_name | – | reject | `full_name_present` (ต้องรันก่อน tokenise · DQ-5)

<a id="br-20"></a>

### BR-20
Source backup lines 361–361; apply effective precedence above.

BR-20 | **⏭️ [Phase 3]** Quarantine เขียนหลัง tokenise ห้ามมี cleartext ของคอลัมน์ที่ tokenise | runtime | – | –

<a id="br-21"></a>

### BR-21
Source backup lines 362–362; apply effective precedence above.

BR-21 | ห้ามแก้ contract ให้ตรงกับข้อมูล · `# REALITY:` ต้องคงไว้แบบ byte-for-byte | PR | test fail | –

<a id="br-22"></a>

### BR-22
Source backup lines 363–363; apply effective precedence above.

BR-22 | Contract major bump ← breaking change | diff | fail ถ้าไม่ได้ bump | `--initial-release`

<a id="br-23"></a>

### BR-23
Source backup lines 364–364; apply effective precedence above.

BR-23 | **⏭️ [Phase 3]** 1 run = 1 business_date · late ภายใน grace ไม่ alert · missing ≠ ไม่มีข้อมูล · backfill ไม่ประเมิน late/missing ใหม่ | runtime | – | –

<a id="br-24"></a>

### BR-24
Source backup lines 365–365; apply effective precedence above.

BR-24 | **⏭️ [Phase 3]** Dedup deterministic (order_by + tie-breaker) | runtime | – | –

<a id="br-25"></a>

### BR-25
Source backup lines 366–366; apply effective precedence above.

BR-25 | **⏭️ [Phase 3]** `quality_first` (customer, credit_card) vs `latency_first` (credit_card_txn) | runtime | ดู FR-I.7 | –

<a id="br-26"></a>

### BR-26
Source backup lines 367–367; apply effective precedence above.

BR-26 | Release ต้องมาจาก clean commit บน `master` · dummy/`<TODO>` ไม่ผ่าน | release | fail | preview ใช้ได้

<a id="br-27"></a>

### BR-27
Source backup lines 368–368; apply effective precedence above.

BR-27 | แก้ library → ต้องได้ review จาก BU + DE และ diff ต้องแสดง blast radius (DQ-6) | PR | – | –

<a id="br-28"></a>

### BR-28
Source backup lines 369–369; apply effective precedence above.

BR-28 | ห้ามใช้ฟังก์ชันเวลาหรือสุ่มใน expression ทุกชนิด (BF-1) | validate | error `NON_DETERMINISTIC_EXPR` | –

<a id="br-29"></a>

### BR-29
Source backup lines 370–370; apply effective precedence above.

BR-29 | **⏭️ [Phase 3]** vault, erasure_list และ run_log ห้าม RESTORE · replay ใช้ได้เฉพาะในช่วง retention | runtime | error | –

<a id="br-3"></a>

### BR-3
Source backup lines 334–334; apply effective precedence above.

BR-3 | `valid_values` | customer.customer_status, credit_card.card_type, credit_card.card_status, txn.currency, txn.txn_status | `customProperties.valid_values` (✅ D-P2-9 · ย้ายมาจาก `quality: library validValues`) | reject (Proposed · OQ-P2-9) | `quality[library validValues]`

<a id="br-4"></a>

### BR-4
Source backup lines 335–335; apply effective precedence above.

BR-4 | `pattern` | cc.credit_card.card_pan | `^[0-9]{15,16}$` | reject | – (หลัง normalise จึงผ่านค่า PAN ที่มีช่องว่าง)

<a id="br-5"></a>

### BR-5
Source backup lines 336–336; apply effective precedence above.

BR-5 | `luhn` (function) | cc.credit_card.card_pan | – | reject | `pan_luhn_valid` + `quality custom luhn_valid` (DC-1)

<a id="br-6"></a>

### BR-6
Source backup lines 337–337; apply effective precedence above.

BR-6 | `fk` (function) | credit_card.customer_id → cc.customer | `customProperties.foreign_key` | ⏭️ [Phase 3] **flag** + ส่ง defect ให้ BA (OQ-P1-23) · Phase 1 ตรวจแค่ config (FR-B.14) | `customer_exists` (DC-4)

<a id="br-7"></a>

### BR-7
Source backup lines 338–338; apply effective precedence above.

BR-7 | `fk` (function) | txn.card_pan → cc.credit_card (เทียบกันด้วย token) | `customProperties.foreign_key` | ⏭️ [Phase 3] flag + ส่ง defect ให้ BA (OQ-P1-23) · Phase 1 ตรวจแค่ config (FR-B.14) | – · วันที่ master **missing** (2026-09-10) ให้ join กับ master snapshot ล่าสุด (Proposed) · **ขัดกับ DPR-01 → CONFLICT-17 (Phase 3)**

<a id="br-8"></a>

### BR-8
Source backup lines 339–339; apply effective precedence above.

BR-8 | `not_null` (auto) | ทุกคอลัมน์ที่ `required: true` | – | reject | `txn_timestamp_present` (CL-9)

<a id="br-9"></a>

### BR-9
Source backup lines 340–340; apply effective precedence above.

BR-9 | `cast_ok` (auto) | ทุกคอลัมน์ | physicalType | reject | – · `'UNLIMITED'` ใน credit_limit โดน reject ตรงนี้ (DC-8)

<a id="cd-1"></a>

### CD-1
Source backup lines 1059–1059; apply effective precedence above.

CD-1 | ดาวน์โหลด asset ของ GitHub Release `<release_id>` ลงโฟลเดอร์ชั่วคราว | ได้ `manifest.json` + ไฟล์ครบตาม manifest | fail (ไม่แตะ workspace) | FR-L.3

<a id="cd-2"></a>

### CD-2
Source backup lines 1060–1060; apply effective precedence above.

CD-2 | `mdf verify-package <dir> --expect-release-id <release_id>` | hash ครบ, ไม่มีไฟล์เกิน, `manifest.release_id` = input | fail | FR-F.5, FR-F.6, AC-35

<a id="cd-3"></a>

### CD-3
Source backup lines 1061–1061; apply effective precedence above.

CD-3 | `databricks fs cp <dir> dbfs:/Volumes/{catalog}/ops/files/releases/<release_id> --recursive` · **คัดลอกไฟล์ resolved ก่อน `manifest.json` เป็นไฟล์สุดท้าย** (โฟลเดอร์ที่มี `manifest.json` = sealed) | โฟลเดอร์ปลายทางยังไม่มี `manifest.json` → คัดลอกได้ · มีแล้วและ `manifest_sha256` ตรง → ข้าม (idempotent) | มีแล้วแต่ hash ไม่ตรง → fail · **ห้ามเขียนทับหรือลบ** | FR-L.4, FR-J.6, AC-38, AC-39

<a id="cd-4"></a>

### CD-4
Source backup lines 1062–1062; apply effective precedence above.

CD-4 | คัดลอกจาก Volume กลับมาที่โฟลเดอร์ชั่วคราวอีกชุด แล้ว verify-package | ผลเหมือน CD-2 | fail | FR-L.5, AC-37

<a id="cd-5"></a>

### CD-5
Source backup lines 1063–1063; apply effective precedence above.

CD-5 | `databricks bundle deploy -t dev` (job `mdf_release_register_dev` + wheel ของ `mdf`) | deploy ผ่าน | fail | FR-L.6, FR-J.1

<a id="cd-6"></a>

### CD-6
Source backup lines 1064–1064; apply effective precedence above.

CD-6 | `databricks bundle run mdf_release_register_dev --params release_id=<id>` → job อ่าน `/Volumes/…/<id>/` ตรวจ hash ในฝั่ง workspace แล้ว **INSERT** แถว `REGISTERED` ถ้ายังไม่มี | มีแถว `REGISTERED` 1 แถวต่อ release_id · รันซ้ำไม่เพิ่มแถว | release_id ไม่มีใน Volume / hash ไม่ตรง / มีแถวเดิมที่ `manifest_sha256` ต่างกัน → job fail | FR-L.7, AC-40, AC-42

<a id="cd-7"></a>

### CD-7
Source backup lines 1065–1065; apply effective precedence above.

CD-7 | smoke: อ่าน registry ของ `<release_id>` | 1 แถว `REGISTERED` ที่ `manifest_sha256` ตรงกับ CD-2 · `file_count` ตรง | fail | FR-L.7, AC-37

<a id="cd-8"></a>

### CD-8
Source backup lines 1066–1066; apply effective precedence above.

CD-8 | append แถว `ACTIVATED` + ตั้ง bundle variable `active_release_id=<id>` (ค่าตั้งต้นของ parameter `release_id` ใน job ที่มี schedule) | แถว ACTIVATED ล่าสุด = release นี้ | – | FR-L.8

<a id="d-p0-1"></a>

### D-P0-1
Source backup lines 1404–1404; apply effective precedence above.

SSOT ชี้ขาด; ขัดกันให้ถามผู้ใช้ ไม่เลือก draft เก่าอัตโนมัติ.

<a id="d-p0-10"></a>

### D-P0-10
Source backup lines 1413–1413; apply effective precedence above.

Gold layout DataContract/_gold/<domain>/<table>.gold.yaml + SQL/DAG อยู่ Phase 3.

<a id="d-p0-11"></a>

### D-P0-11
Source backup lines 1414–1414; apply effective precedence above.

Managed storage only; reserved storage field ไม่อนุญาต unsupported mode.

<a id="d-p0-13"></a>

### D-P0-13
Source backup lines 1416–1416; apply effective precedence above.

REALITY lines เป็น test oracle; ไม่กู้ legacy มาแก้ข้อมูลให้ผ่าน.

<a id="d-p0-14"></a>

### D-P0-14
Source backup lines 1417–1417; apply effective precedence above.

Agent แก้ DataContract ได้ ยกเว้น landing path ต้องตาม confirmed template.

<a id="d-p0-2"></a>

### D-P0-2
Source backup lines 1405–1405; apply effective precedence above.

Metadata อยู่ Git ไม่มี meta.* database.

<a id="d-p0-6"></a>

### D-P0-6
Source backup lines 1409–1409; apply effective precedence above.

Resolved JSON ต่อ table ใต้ build ไม่ commit; CI publish manifest/hash ไม่มี intermediate spec/bot push.

<a id="d-p0-8"></a>

### D-P0-8
Source backup lines 1411–1411; apply effective precedence above.

Contract/pipeline technical validator rules ใน JSON; data DQ อยู่ YAML library.

<a id="d-p0-9"></a>

### D-P0-9
Source backup lines 1412–1412; apply effective precedence above.

dev env เดียว; catalog จาก control file; เพิ่ม env ด้วยไฟล์ ไม่ hardcode.

<a id="d-p1-1"></a>

### D-P1-1
Source backup lines 1423–1423; apply effective precedence above.

Landing prefix /Volumes/{catalog}/landing_{source}/; resolve placeholders + suffix ตาม DC-11r/FR-A.5.

<a id="d-p1-2"></a>

### D-P1-2
Source backup lines 1424–1424; apply effective precedence above.

Data DQ execution อยู่ Phase 3; Phase 1 compile only.

<a id="d-p1-3"></a>

### D-P1-3
Source backup lines 1425–1425; apply effective precedence above.

Catalog dev_catalog ได้; TODO host/secret_scope ต้อง release fail จน configured จริง.

<a id="d-p2-1"></a>

### D-P2-1
Source backup lines 170–1432; apply effective precedence above.

DQ 3 ส่วน: ODCS tags/params, BU+DE library YAML, BU SQL/derived pipeline; contract no SQL.

<a id="d-p2-2"></a>

### D-P2-2
Source backup lines 1433–1433; apply effective precedence above.

ODCS ไม่มี relationships/standard valid-values; customProperties.foreign_key/valid_values; description บังคับ.

<a id="d-p2-3"></a>

### D-P2-3
Source backup lines 1434–1434; apply effective precedence above.

required:true auto not_null.

<a id="d-p2-4"></a>

### D-P2-4
Source backup lines 1435–1435; apply effective precedence above.

Library default_action, per-column pipeline override.

<a id="d-p2-5"></a>

### D-P2-5
Source backup lines 1436–1436; apply effective precedence above.

BU constraints/normalise/tokenise/dedup/load/retention อยู่ pipeline เดียวต่อ dataset.

<a id="d-p2-6"></a>

### D-P2-6
Source backup lines 1437–1437; apply effective precedence above.

Library+non-derived BU หลัง cast ก่อน tokenise; derived BU หลัง derived.

<a id="d-p2-7"></a>

### D-P2-7
Source backup lines 1438–1438; apply effective precedence above.

Library/BU/derived description บังคับ.

<a id="d-p2-8"></a>

### D-P2-8
Source backup lines 1439–1439; apply effective precedence above.

ทุก contract column description nonempty.

<a id="d-p2-9"></a>

### D-P2-9
Source backup lines 1440–1440; apply effective precedence above.

valid_values / foreign_key ใช้ customProperties.

<a id="d-p3-1"></a>

### D-P3-1
Source backup lines 1446–1446; apply effective precedence above.

BR-10 birth_date <= business_date ไม่ใช้ current_date.

<a id="d-p3-2"></a>

### D-P3-2
Source backup lines 1447–1447; apply effective precedence above.

Backfill ได้ทุก stage ตาม explicit human flow; ห้าม ordinary retry เริ่ม older-date backfill (confirmed later Q6).

<a id="d-p3-3"></a>

### D-P3-3
Source backup lines 1448–1448; apply effective precedence above.

Raw landing 1825 วัน; bronze30/90วัน; rebuild bronze จาก rawเมื่อ expired.

<a id="d-p3-4"></a>

### D-P3-4
Source backup lines 1449–1449; apply effective precedence above.

Human replay recovery RESTORE+rerun เฉพาะ retention window; primary partition replaceWhere.

<a id="d-p3-5"></a>

### D-P3-5
Source backup lines 1450–1450; apply effective precedence above.

Backfill default current release, explicit old release allowed; log release_id.

<a id="d-p3-6"></a>

### D-P3-6
Source backup lines 1451–1451; apply effective precedence above.

customer/credit_card SCD2 business-date valid_from/to, as-of1825วัน; time travel short recovery only.

<a id="d-p3-7"></a>

### D-P3-7
Source backup lines 1452–1452; apply effective precedence above.

Partition replaceWhere primary; human RESTORE/replay within retention, no vault/erasure_list/run_log RESTORE.

<a id="d-p3-8"></a>

### D-P3-8
Source backup lines 1453–1453; apply effective precedence above.

Erasure token list filters every run incl backfill; raw archive runtime SP only.

<a id="d-p4-2"></a>

### D-P4-2
Source backup lines 1460–1460; apply effective precedence above.

Master-missing fact/gold policy OQ-P1-22 deferred Phase3.

<a id="d-p4-3"></a>

### D-P4-3
Source backup lines 1461–1461; apply effective precedence above.

Gold compile/DAG/input_asof/SCD2 trace อยู่ Phase3.

<a id="d-p4-4"></a>

### D-P4-4
Source backup lines 1462–1462; apply effective precedence above.

Phase1 CLI validate/compile/trace-orphan/diff/package/verify.

<a id="d-p4-5"></a>

### D-P4-5
Source backup lines 1463–1463; apply effective precedence above.

Phase1 static/local proof distinct from Phase2 actual delivery; no URL fabrication.

<a id="d-p4-7"></a>

### D-P4-7
Source backup lines 1465–1465; apply effective precedence above.

Missing config FK target compile defect; data FK defect sends BA/source; no invented unknown member, OQ-P1-23.

<a id="d-p5-10"></a>

### D-P5-10
Source backup lines 1485–1485; apply effective precedence above.

auto/u2m/manual modes remain; actual registry delivery proved; manual acceptance cancelled H-119 not PASS.

<a id="d-p5-11"></a>

### D-P5-11
Source backup lines 1491–1498; apply effective precedence above.

Per-source localbuild→recursivecopy; manifest explicit POSIXpaths, newv3 after round12, oldv1/v2 untouched; v1warn; gold2directorylevels interpret/clarify beforeenable; zipassetone, zip-slipcheck, manifestdigestsummary+notes.

<a id="d-p5-12"></a>

### D-P5-12
Source backup lines 1504–1511; apply effective precedence above.

Calendar/reader/privacyflags/ODCSbundle selected only; unknownownerpending; resolvedauthority; PIImaskdefer; ordinaryolderdateblock/humanbackfill; timezone static stringonly no tzdata.

<a id="d-p5-2"></a>

### D-P5-2
Source backup lines 1472–1472; apply effective precedence above.

Phase2 actual release delivery to Volume + managedDelta registry; not data runtime.

<a id="d-p5-3"></a>

### D-P5-3
Source backup lines 1473–1473; apply effective precedence above.

PySpark runtime/DQ/backfill/gold/ABAC tagging Phase3.

<a id="d-p5-4"></a>

### D-P5-4
Source backup lines 1474–1474; apply effective precedence above.

AI semantic/PII/classification/auto-suggest ABAC Phase4.

<a id="d-p5-5"></a>

### D-P5-5
Source backup lines 1475–1475; apply effective precedence above.

github-oidc federation auth; no PAT/clientsecret in GitHub/artifacts.

<a id="d-p5-6"></a>

### D-P5-6
Source backup lines 1476–1476; apply effective precedence above.

Recursive copy to release_id Volume; fallback honest U2M/manual when auto unavailable.

<a id="d-p5-7"></a>

### D-P5-7
Source backup lines 1477–1477; apply effective precedence above.

Explicit runtime release_id input, not inferred latest.

<a id="d-p5-8"></a>

### D-P5-8
Source backup lines 1478–1478; apply effective precedence above.

download→verify→immutable copy→remoteverify→deploy/update→explicitrelease→smoke→activate schedule.

<a id="d-p5-9"></a>

### D-P5-9
Source backup lines 1479–1479; apply effective precedence above.

Actual evidence required before delivery PASS; HG_PROD before first workspace write.

<a id="dc-11r"></a>

### DC-11r
Source backup lines 154–163; apply effective precedence above.

### DC-11r — Landing path ฉบับแก้ (แทน DC-11)

- ✅ Prefix ตามที่ผู้ใช้กำหนด: `/Volumes/{catalog}/landing_{source}/`
- ⚠️ **Agent Interpretation (Proposed):** path เต็มคือ `/Volumes/{catalog}/landing_{source}/files/{dataset}/`
  เหตุผลคือ UC Volume path ต้องเป็น `/Volumes/<catalog>/<schema>/<volume>/…` ถ้ามีแค่ prefix จะยังไม่มีชื่อ volume
  ส่วนต่อท้าย `files/{dataset}/` เอามาจาก DRAFT1 §8 `landing_volume` → To be confirmed (OQ-P1-11)
- Template ของ path นี้อยู่ใน **control file ไฟล์เดียว** `config/naming.yaml` (key `landing`) ส่วน contract `servers[].location` เก็บ template เดียวกัน (มี placeholder)
  และ validator ตรวจว่าสองที่ตรงกัน ถ้าไม่ตรงหรือมี placeholder ที่ไม่รู้จักให้ error
- ค่าของ `{catalog}` มาจาก `config/env/<env>.yaml` (dev = `dev_catalog`), `{source}` มาจาก contract `customProperties.source_system`, `{dataset}` มาจาก contract `name`

<a id="dep-1"></a>

### DEP-1
Source backup lines 986–986; apply effective precedence above.

DEP-1 | **◐ [Phase 1 ไม่ block · 🚚 Phase 2 = blocking]** GitHub repo + remote + branch protection ของ `master` | External | **ผู้ใช้** | AC-36/37 ทำไม่ได้ · Phase 2 ปิดไม่ได้

Source backup lines 1028–1028; apply effective precedence above.

DEP-1…3 | 🚚 P0 สำหรับ Phase 2 | ดู External Setup Checklist | ผู้ใช้ | **Yes สำหรับ E6 (Phase 2)**

<a id="dep-2"></a>

### DEP-2
Source backup lines 987–987; apply effective precedence above.

DEP-2 | 🚚 **[Phase 2]** Databricks Free Edition workspace host + ยืนยันว่าสร้าง catalog `dev_catalog` ได้ | External | ผู้ใช้ | E6 (Phase 2) ติด · ถ้าสร้างไม่ได้ต้องเปลี่ยน control file เป็น `workspace` (R-4)

<a id="dep-3"></a>

### DEP-3
Source backup lines 988–988; apply effective precedence above.

DEP-3 | 🚚 **[Phase 2]** Service principal ใน workspace + **federation policy** (account admin) ที่ issuer `https://token.actions.githubusercontent.com`, subject `repo:<org>/<repo>:environment:dev` · ใส่ `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID` เป็น variable ของ GitHub Environment `dev` · สิทธิ์ SP: USE CATALOG, CREATE SCHEMA (ครั้งแรก), WRITE VOLUME `ops.files`, MODIFY `ops.release_registry`, สร้าง job | External | ผู้ใช้ | **จำเป็นเฉพาะ mode `auto`** (รอบ 10) · ไม่มี → ใช้ `u2m` หรือ `manual` (FR-L.12)

<a id="dep-4"></a>

### DEP-4
Source backup lines 1282–1282; apply effective precedence above.

DEP-4 | **⏭️ [Phase 3]** (ไม่ต้องใช้ใน Phase 2) Databricks secret scope + HMAC key | External | ผู้ใช้ | Tokenise บน workspace จริงไม่ได้ · release gate จะไม่ผ่าน

<a id="dep-5"></a>

### DEP-5
Source backup lines 678–678; apply effective precedence above.

DEP-5 | ชื่อ group / SP สำหรับ grants, ชื่อ GitHub team สำหรับ CODEOWNERS | External | ผู้ใช้ | ใช้ได้แค่ `.example` / เอกสาร

<a id="dep-6"></a>

### DEP-6
Source backup lines 679–679; apply effective precedence above.

DEP-6 | ODCS v3.0.2 schema (pin) | Technical | Agent | FR-B.2

<a id="dep-7"></a>

### DEP-7
Source backup lines 1283–1283; apply effective precedence above.

DEP-7 | **⏭️ [Phase 3]** JDK 17 + winutils (สำหรับ local Spark บน Windows) | Technical | ผู้ใช้ / เครื่อง dev | Runtime test จะ skip (หลักฐานอ่อนลง)

<a id="dep-8"></a>

### DEP-8
Source backup lines 1284–1284; apply effective precedence above.

DEP-8 | **⏭️ [Phase 3]** ไฟล์ CSV ตัวอย่างที่มี REALITY cases | Data | ผู้ใช้ (หรือให้ agent สร้างจากคำอธิบาย REALITY → AS-12) | AC-21 / AC-23

<a id="dep-9"></a>

### DEP-9
Source backup lines 680–680; apply effective precedence above.

DEP-9 | E0 (layout + migration) | Internal | – | ทุก Epic ถัดไป

<a id="dpr-01"></a>

### DPR-01
Source backup lines 278–278; apply effective precedence above.

DPR-01 | **⏭️ [Phase 3]** Arrival | landing path (DC-11r) + file pattern + SLA | หาไฟล์ของ business_date · เก็บ path/size/sha256 | `arrival_status` on_time/late/missing (scheduled) หรือ `backfill` | missing → run_log + ข้าม dataset และ downstream · late ไม่ alert · backfill ไม่ประเมินความตรงเวลา

<a id="dpr-02"></a>

### DPR-02
Source backup lines 279–279; apply effective precedence above.

DPR-02 | **⏭️ [Phase 3]** Bronze load | CSV จาก landing archive | อ่านทุกคอลัมน์เป็น string + audit columns | `bronze_{source}.{dataset}` (**replaceWhere `_business_date = D`**) | อ่านไฟล์ไม่ได้ → block

<a id="dpr-03"></a>

### DPR-03
Source backup lines 280–280; apply effective precedence above.

DPR-03 | **⏭️ [Phase 3]** Normalise | bronze | เช่น `strip_whitespace` ตามที่ pipeline กำหนด | ค่าที่ normalise แล้ว | –

<a id="dpr-04"></a>

### DPR-04
Source backup lines 281–281; apply effective precedence above.

DPR-04 | **⏭️ [Phase 3]** Cast | ค่าที่ normalise แล้ว | `try_cast` ตาม physicalType | คอลัมน์ที่มีชนิดถูกต้อง | cast แล้วได้ NULL ทั้งที่ค่าเดิมไม่ NULL → กฎ `cast_ok` (auto rule ใน DQ library · DQ-1) → reject

<a id="dpr-05"></a>

### DPR-05
Source backup lines 282–282; apply effective precedence above.

DPR-05 | **⏭️ [Phase 3]** Basic DQ | ข้อมูลที่ cast แล้ว (cleartext) | library rules ต่อคอลัมน์ (auto + `dq:` tags) + BU rules ที่ไม่อ้าง derived | pass / reject / flag / block | reject → quarantine (หลัง tokenise PCI) · block → หยุด run

<a id="dpr-06"></a>

### DPR-06
Source backup lines 283–283; apply effective precedence above.

DPR-06 | **⏭️ [Phase 3]** Tokenise | คอลัมน์ `tokenise: true` | ตรวจ key version (FR-I.17) → HMAC-SHA256 (key จาก secret scope) → กรอง erasure list (FR-I.15) → MERGE vault ตาม token | token | ไม่มี key หรือ key version ไม่ตรง → block

<a id="dpr-07"></a>

### DPR-07
Source backup lines 284–284; apply effective precedence above.

DPR-07 | **⏭️ [Phase 3]** Derived | ข้อมูลหลัง tokenise | expression ใน pipeline `derived[]` | คอลัมน์ใหม่ | ตรวจตอน validate (FR-B.5)

<a id="dpr-08"></a>

### DPR-08
Source backup lines 285–285; apply effective precedence above.

DPR-08 | **⏭️ [Phase 3]** Post-derived DQ | ข้อมูลหลัง derived | BU rules ที่อ้าง derived column (DQ-5) | flag/reject | –

<a id="dpr-09"></a>

### DPR-09
Source backup lines 286–286; apply effective precedence above.

DPR-09 | **⏭️ [Phase 3]** Dedup | ข้อมูลหลัง DQ | `row_number()` ตาม keys, order_by desc, tie-breaker `_ingest_file_name, _ingest_row_number` | 1 แถวต่อ key | –

<a id="dpr-10"></a>

### DPR-10
Source backup lines 287–287; apply effective precedence above.

DPR-10 | **⏭️ [Phase 3]** Write silver | ข้อมูลหลัง dedup | master → SCD2 (FR-I.11) · fact → replaceWhere D (FR-I.12) | `silver_{source}.{dataset}` | –

<a id="dpr-11"></a>

### DPR-11
Source backup lines 288–288; apply effective precedence above.

DPR-11 | **⏭️ [Phase 3]** FK | silver | left join ไปหา parent แบบ **as-of D** (FR-I.14) | flag `fk@<col>` + ส่ง defect ให้ BA (D-P4-7 · OQ-P1-23) | ห้าม drop

<a id="dpr-12"></a>

### DPR-12
Source backup lines 289–289; apply effective precedence above.

DPR-12 | **⏭️ [Phase 3]** Pass-rate gate | จำนวนแถวที่ผ่าน / ทั้งหมด | เทียบกับ `min_dq_pass_rate` | publish หรือ stop, `is_trusted` | quality_first ไม่ผ่าน → ไม่ publish

<a id="dpr-13"></a>

### DPR-13
Source backup lines 290–290; apply effective precedence above.

DPR-13 | **⏭️ [Phase 3]** Gold | silver 3 ตาราง (master ผ่าน `{{input_asof}}`) | SQL ที่ resolve แล้ว | `gold_card.fct_daily_spend_by_segment` (replaceWhere D) | input ใดเป็น missing → ข้าม gold ของวันนั้น (Proposed) และ backfill ภายหลังเมื่อไฟล์มา

<a id="dpr-14"></a>

### DPR-14
Source backup lines 291–291; apply effective precedence above.

DPR-14 | **⏭️ [Phase 3]** Run log | ทุก step | append | `ops.run_log` | เขียน log ไม่ได้ → task fail

<a id="dpr-15"></a>

### DPR-15
Source backup lines 292–292; apply effective precedence above.

DPR-15 | **⏭️ [Phase 3]** Cascade | dataset + วันที่ backfill | FR-I.13 | รายการวันที่ downstream ต้องรันใหม่ + child runs (`parent_run_id`) | `--no-cascade` → แค่บันทึกรายการ

<a id="dpr-16"></a>

### DPR-16
Source backup lines 293–293; apply effective precedence above.

DPR-16 | **⏭️ [Phase 3]** Replay | run_log `table_versions` | FR-I.16 RESTORE แล้ว rerun | ตารางกลับมาอยู่ในสภาพที่ถูกต้อง | เกิน retention → error ให้ใช้ backfill

<a id="dq-1"></a>

### DQ-1
Source backup lines 89–89; apply effective precedence above.

- **DQ-1 Auto rules:** `required: true` → `not_null` (D-P2-3) · ทุกคอลัมน์ → `cast_ok` (ตรวจว่าค่า cast ได้ตาม physicalType ถือเป็นกฎ "type" ที่ผู้ใช้ระบุ) · ไม่ต้องแปะ tag · ถ้าแปะ tag ซ้ำ → warning

<a id="dq-2"></a>

### DQ-2
Source backup lines 90–90; apply effective precedence above.

- **DQ-2 ห้ามทิ้งเงียบ ๆ:** tag ที่ไม่มีใน library → error `UNKNOWN_TAG` · tag ที่ต้องการค่าแต่ไม่มี (เช่น `dq:pattern` แต่ไม่มี `logicalTypeOptions.pattern`) → error `TAG_WITHOUT_PARAM` · มีค่าแต่ไม่มี tag (เช่นมี pattern แต่ไม่แปะ `dq:pattern`) → error `PARAM_WITHOUT_TAG`

<a id="dq-3"></a>

### DQ-3
Source backup lines 91–91; apply effective precedence above.

- **DQ-3 Contract ไม่มี SQL:** มี `quality[]` ใน contract → error `USE_TAG` พร้อมบอกว่า tag ไหนใช้แทนได้

<a id="dq-4"></a>

### DQ-4
Source backup lines 92–92; apply effective precedence above.

- **DQ-4 NULL:** กฎใน library ยกเว้น `not_null` ต้องให้ NULL ผ่าน (เช่น `{col} IS NULL OR {col} RLIKE …`) เพื่อไม่ให้แถวเดียวถูกนับซ้ำ · สำหรับ BU rule ถ้าผลเป็น NULL = **ไม่ผ่าน** (DC-8)

<a id="dq-5"></a>

### DQ-5
Source backup lines 93–93; apply effective precedence above.

- **DQ-5 Stage ที่รัน (✅ D-P2-6):** กฎใน library และ BU rule ที่ไม่อ้าง derived column จะรัน **หลัง cast และก่อน tokenise** · BU rule ที่อ้าง derived column รันหลัง derived โดย compiler ตัดสินจาก field `columns` · ถ้า BU rule ที่รันหลัง tokenise อ้างคอลัมน์ที่ tokenise แล้ว → error

<a id="dq-6"></a>

### DQ-6
Source backup lines 94–94; apply effective precedence above.

- **DQ-6 Blast radius:** แก้กฎใน library ข้อเดียว → `mdf diff` ต้องรายงานรายชื่อ dataset/คอลัมน์ทั้งหมดที่ใช้กฎนั้น (AC-24) · CODEOWNERS ของ library = BU + DE

<a id="dq-7"></a>

### DQ-7
Source backup lines 95–95; apply effective precedence above.

- **DQ-7 `description` บังคับ (✅ D-P2-2, D-P2-7, D-P2-8):** ต้องมีที่ (a) ทุกกฎใน library (b) ทุก BU rule (c) ทุก derived column (d) **ทุกคอลัมน์ใน contract** · ถ้าไม่มีหรือเป็นค่าว่าง → error `MISSING_DESCRIPTION`

<a id="dq-8"></a>

### DQ-8
Source backup lines 96–96; apply effective precedence above.

- **DQ-8 Tag namespace:** tag ของ DQ ขึ้นต้นด้วย `dq:` เพื่อแยกจาก tag อื่น (เช่น tag ของ UC ABAC ในอนาคต) · tag ที่ไม่มี prefix นี้ไม่ถูกนับเป็นกฎ

<a id="fr-a-1"></a>

### FR-A.1
Source backup lines 416–416; apply effective precedence above.

FR-A.1 | **◐ [Phase 1 · `_gold` → Phase 3]** Discovery รองรับแค่รูปแบบเดียว: `DataContract/<source>/contract/<dataset>.odcs.yaml` คู่กับ `DataContract/<source>/pipeline/<dataset>.pipeline.yaml` และ `DataContract/_gold/<domain>/<table>.gold.yaml` + `<table>.sql` | P0 | DRAFT2 §3, D-P0-5, D-P0-10 | ถ้าเจอ `dq/*.dq.yaml` แบบเก่า → error `LEGACY_LAYOUT` พร้อมบอกวิธีย้าย · ข้าม `_template` · ถ้ามีไฟล์ผิดที่ → `FILE_LAYOUT`

<a id="fr-a-2"></a>

### FR-A.2
Source backup lines 417–417; apply effective precedence above.

FR-A.2 | Rename `dq/` → `pipeline/` ของทั้ง 3 dataset และ template | P0 | DRAFT2:73-78, DC-12 | ใช้ `git mv` บน branch ที่แตกจาก master

<a id="fr-a-3"></a>

### FR-A.3
Source backup lines 418–418; apply effective precedence above.

FR-A.3 | Migrate กฎเดิมตาม DQ model (D-P2-1): กฎพื้นฐาน → `dq:` tag ใน contract (ค่าอยู่ใน field ของ ODCS / customProperties) · กฎเฉพาะ dataset → pipeline `rules[]` · ลบ `quality[]` และ `business_rules[]` ทั้งหมด | P0 | D-P2-1…5 | Mapping ครบทุกข้อดูใน Business Rules · ห้ามมี expression ซ้ำ

<a id="fr-a-4"></a>

### FR-A.4
Source backup lines 1135–1135; apply effective precedence above.

FR-A.4 | **⏭️ [Phase 3]** สร้าง gold ตัวอย่าง 1 ตาราง: `DataContract/_gold/card/fct_daily_spend_by_segment.gold.yaml` + `.sql` | P0 | D-P0-3, D-P0-10, DRAFT1 §9.4 | measure ของตารางยังเป็น Proposed (OQ-P2-6) · **[รอบ 11]** ในสเปก release จองชื่อโฟลเดอร์ `_gold/<domain>/` ไว้แล้ว (D-P5-11 Q5 · ดู FR-F.7 notes) — compile/package ของ gold **ยังไม่ implement** รอบนี้ ต้องรอ FR-A.4/D-P4-3 ก่อน · **[รอบ 6, OQ-P5-8 = 2 ชั้น]** ⚠️ Agent Interpretation: path ลึก 2 ชั้น = `_gold/<domain>/<file>` (ไม่มี sub-domain) — ยัง ⏭️ Phase 3

<a id="fr-a-5"></a>

### FR-A.5
Source backup lines 419–419; apply effective precedence above.

FR-A.5 | `servers[].location` ของทุก contract ใช้ template ตาม DC-11r | P0 | D-P1-1 | –

<a id="fr-a-6"></a>

### FR-A.6
Source backup lines 420–420; apply effective precedence above.

FR-A.6 | บรรทัด `# REALITY:` ทุกบรรทัดใน contract ต้องเหมือนเดิมแบบ byte-for-byte หลัง migrate | P0 | D-P0-13, DRAFT1 §7:375 | มี test เทียบกับ commit `88b982d`

<a id="fr-a-7"></a>

### FR-A.7
Source backup lines 421–421; apply effective precedence above.

FR-A.7 | Template ใหม่ (`_template/contract`, `_template/pipeline`) ที่ถ้า copy ไปใช้โดยไม่แก้เลย validator ต้อง fail พร้อมบอกว่าต้องแก้อะไร | P1 | PROMPT_01 DoD | –

<a id="fr-b-1"></a>

### FR-B.1
Source backup lines 427–427; apply effective precedence above.

FR-B.1 | YAML loader ต้องปฏิเสธ **duplicate mapping key** และบอกเลขบรรทัด | P0 | DRAFT2:145 | `yaml.safe_load` ไม่ตรวจเรื่องนี้

<a id="fr-b-10"></a>

### FR-B.10
Source backup lines 436–436; apply effective precedence above.

FR-B.10 | Status ของ contract ที่เข้า release ได้คือ `active` เท่านั้น (Proposed) · `draft` ใช้ทำ preview ได้ | P1 | DRAFT2:165 | OQ-P2-7

<a id="fr-b-11"></a>

### FR-B.11
Source backup lines 437–437; apply effective precedence above.

FR-B.11 | `description` บังคับตาม DQ-7 (library rule, BU rule, derived, **ทุกคอลัมน์ใน contract**) → `MISSING_DESCRIPTION` | P0 | D-P2-7, D-P2-8 | –

<a id="fr-b-12"></a>

### FR-B.12
Source backup lines 438–438; apply effective precedence above.

FR-B.12 | **◐ [Phase 1: library rule, BU rule, derived · gold SQL → Phase 3]** ห้ามใช้ฟังก์ชันที่ผลขึ้นกับเวลาที่รันหรือสุ่ม (`current_date`, `current_timestamp`, `now`, `rand`, `uuid`, `unix_timestamp()` แบบไม่มี argument ฯลฯ) ใน library rule, BU rule, derived และ gold SQL → `NON_DETERMINISTIC_EXPR` · รายการฟังก์ชันอยู่ใน rule JSON แก้ได้โดยไม่แก้ Python | P0 | D-P3-2, BF-1 | –

<a id="fr-b-13"></a>

### FR-B.13
Source backup lines 1141–1141; apply effective precedence above.

FR-B.13 | **⏭️ [Phase 3]** Gold SQL ที่อ้าง input ที่เป็น SCD2 ต้องใช้ `{{input_asof:<id>}}` ถ้าใช้ `{{input:<id>}}` กับตาราง SCD2 → error `SCD2_NEEDS_ASOF` | P0 | D-P3-6, BF-5 | –

<a id="fr-b-14"></a>

### FR-B.14
Source backup lines 439–439; apply effective precedence above.

FR-B.14 | **FK config reference (D-P4-7 ก):** ค่า `customProperties.foreign_key` ต้องอยู่ในรูป `<source>.<dataset>.<column>` · dataset ต้องมี contract · คอลัมน์ต้องมีอยู่ใน contract นั้น · `logicalType` ต้องเข้ากันได้ (Proposed) · ไม่ผ่าน → `FK_TARGET_NOT_FOUND` / `FK_TYPE_MISMATCH` exit 1 และ compile ไม่ออก config · คอลัมน์ที่ไม่มี `foreign_key` = ไม่ relate → ไม่ตรวจ | P0 | D-P4-7 | ตรวจ config เท่านั้น ไม่แตะข้อมูล

<a id="fr-b-2"></a>

### FR-B.2
Source backup lines 428–428; apply effective precedence above.

FR-B.2 | ตรวจ contract ด้วย ODCS v3.0.2 official JSON Schema ที่ pin ไว้ (+ `SOURCE.md` ระบุ URL + sha256) | P0 | DRAFT1 §0 #3, DC-9 | Draft 2019-09

<a id="fr-b-3"></a>

### FR-B.3
Source backup lines 429–429; apply effective precedence above.

FR-B.3 | ปฏิเสธ unknown key ในไฟล์ที่เราเป็นเจ้าของ (pipeline, gold, env, naming) ยกเว้นใน `extensions:` | P0 | DRAFT2:143 | ทำผ่าน rule operator `allowed_keys` (FR-C)

<a id="fr-b-4"></a>

### FR-B.4
Source backup lines 430–430; apply effective precedence above.

FR-B.4 | **◐ [Phase 1 · gold `inputs`/`{{input:…}}` → Phase 3 · FK = FR-B.14]** ตรวจ reference: contract ↔ pipeline (`contract_ref` + major), `dq:` tag ↔ library (DQ-2), key ของ `actions` (`<rule>@<column>` หรือ BU rule id) ต้องมีอยู่จริง, `columns` ของ BU rule, คอลัมน์ของ normalise/tokenise/derived/dedup/merge/FK, gold `inputs` และ `{{input:…}}` ใน SQL | P0 | DRAFT2:156-165, D-P2-4 | –

<a id="fr-b-5"></a>

### FR-B.5
Source backup lines 431–431; apply effective precedence above.

FR-B.5 | **◐ [Phase 1 · gold DAG → Phase 3]** ตรวจการชนกัน: derived ชื่อซ้ำหรือชนกับคอลัมน์ต้นทาง, derived วน (cycle), target table/config id ซ้ำ, env ซ้ำ, gold DAG วน | P0 | DRAFT2:160-163, D-P0-10 | –

<a id="fr-b-6"></a>

### FR-B.6
Source backup lines 432–432; apply effective precedence above.

FR-B.6 | ป้องกัน path traversal: id หรือชื่อที่มาจาก input ต้องไม่ทำให้เขียนไฟล์ออกนอก `build/` | P0 | DRAFT2:164 | **[รอบ 11]** ครอบคลุมชื่อ `<source>` ที่ใช้เป็นโฟลเดอร์ย่อยของ `build/<env>/{resolved,release}/` ด้วย (FR-D.8, FR-F.7) — `source` มาจาก `discover_datasets` (ชื่อโฟลเดอร์จริงใน `DataContract/`) ไม่ใช่ input อิสระ จึงไม่เกิด traversal ใหม่

<a id="fr-b-7"></a>

### FR-B.7
Source backup lines 433–433; apply effective precedence above.

FR-B.7 | กฎหรือ field ที่มีผลต่อ execution แต่ยังไม่รองรับ → error ห้ามปล่อยผ่านเงียบ ๆ: contract มี `quality[]` → `USE_TAG` (DQ-3) · `kind: function` ที่ไม่มีฟังก์ชันใน registry → `UNSUPPORTED` · BU rule ที่เป็น aggregate → `UNSUPPORTED` | P0 | DRAFT2:167-171, D-P2-1 | –

<a id="fr-b-8"></a>

### FR-B.8
Source backup lines 434–434; apply effective precedence above.

FR-B.8 | `storage: external` → error `UNSUPPORTED` (ในรอบนี้) | P1 | D-P0-11 | –

<a id="fr-b-9"></a>

### FR-B.9
Source backup lines 435–435; apply effective precedence above.

FR-B.9 | Error ทุกข้อต้องบอก **ไฟล์ / field / สาเหตุ / วิธีแก้** เป็นภาษาไทย และจัดกลุ่มตามไฟล์ · ถ้าไม่ผ่าน exit 1 · ถ้า config ของ rule เองผิด exit 2 | P0 | PROMPT_01:17-18, DRAFT2:146 | –

<a id="fr-c-1"></a>

### FR-C.1
Source backup lines 445–445; apply effective precedence above.

FR-C.1 | **DQ rule library** `config/dq_library.yaml` ไฟล์เดียว เป็น SSOT ของกฎพื้นฐาน รูปแบบตาม DQ model | P0 | D-P2-1, D-P2-5 | YAML + คอมเมนต์ไทย

<a id="fr-c-2"></a>

### FR-C.2
Source backup lines 446–446; apply effective precedence above.

FR-C.2 | 1 กฎใน library = `description` (บังคับ), `kind: sql\|function`, `sql` (มี placeholder `{col}` + params) หรือ `function` (ชื่อใน registry), `params` (map ไปหา field ของ contract), `default_action: reject\|flag\|block`, `auto?`, `enabled` | P0 | D-P2-1…4 | –

<a id="fr-c-3"></a>

### FR-C.3
Source backup lines 447–447; apply effective precedence above.

FR-C.3 | กฎที่ใช้กับคอลัมน์ = auto rules (DQ-1) ∪ `dq:` tags ของคอลัมน์ · action = `actions[<rule>@<col>]` ใน pipeline ถ้ามี ไม่อย่างนั้นใช้ `default_action` | P0 | D-P2-3, D-P2-4 | –

<a id="fr-c-4"></a>

### FR-C.4
Source backup lines 448–448; apply effective precedence above.

FR-C.4 | **◐ [Phase 1: SQL rule + ชื่อฟังก์ชันที่ประกาศใน registry · logic ของฟังก์ชันบน Spark → Phase 3 (AS-21)]** กฎพื้นฐานใหม่แบบ SQL = **แก้ library YAML อย่างเดียว** แล้วแปะ tag ใน contract ได้ทันที · `kind: function` ต้องเขียนฟังก์ชัน Python 1 ตัวลงทะเบียนด้วย decorator (ไฟล์เดียว) | P0 | D-P2-1 ("dev ต้องเขียน logic ให้") | AC-10

<a id="fr-c-5"></a>

### FR-C.5
Source backup lines 449–449; apply effective precedence above.

FR-C.5 | **Validator rules** `config/rules/contract.rules.json` + `config/rules/pipeline.rules.json` (ใช้กับ gold ด้วยใน Phase 3) = กฎ **ตรวจไฟล์** เท่านั้น: `id, description, scope, when?, field, operator, value?, severity, message, fix, enabled` · operator เช่น required, type, regex, in, allowed_keys, unique, ref_exists, column_in_contract · เพิ่มกฎที่ใช้ operator ที่มีอยู่ = แก้ JSON อย่างเดียว | P0 | D-P0-8 | Conditional rule ต้องมี `required: true`

<a id="fr-c-6"></a>

### FR-C.6
Source backup lines 450–450; apply effective precedence above.

FR-C.6 | ตรวจตัว library และ rule JSON ก่อนใช้: kind/operator/scope ที่ไม่รู้จัก, id ซ้ำ, ไฟล์ผิดรูป, placeholder ใน `sql` ที่ไม่มีใน `params`, ไม่มี `description` → exit 2 | P0 | – | –

<a id="fr-c-7"></a>

### FR-C.7
Source backup lines 451–451; apply effective precedence above.

FR-C.7 | `enabled: false` = ปิดกฎได้ทั้งใน library และ validator rules · การปิดกฎใน library ต้องถูกรายงานใน diff (DQ-6) | P1 | – | –

<a id="fr-d-1"></a>

### FR-D.1
Source backup lines 457–457; apply effective precedence above.

FR-D.1 | `mdf compile --env dev` จะ validate ก่อน ถ้ามี error จะไม่เขียนอะไรเลย แล้วสร้าง resolved JSON 1 ไฟล์ต่อ target table ลง `build/dev/resolved/` ~~flat~~ → **แทนที่ด้วย FR-D.8 (รอบ 11):** ลง `build/dev/resolved/<source>/` | P0 | D-P0-6, DRAFT2 §5 | ไม่มี intermediate spec

<a id="fr-d-2"></a>

### FR-D.2
Source backup lines 459–459; apply effective precedence above.

FR-D.2 | Resolve ชื่อและ path จาก `config/naming.yaml` + `config/env/<env>.yaml`: table, quarantine, vault, landing (DC-11r), checkpoint, run_log | P0 | D-P0-9, D-P1-1, DRAFT1 §8 | `meta_schema` ถูกตัดออก

<a id="fr-d-3"></a>

### FR-D.3
Source backup lines 460–460; apply effective precedence above.

FR-D.3 | **◐ [Phase 1 compile checks/load ลง config · การรันจริง → Phase 3]** Resolved config ต้อง self-contained สำหรับ runtime: schema (จาก contract), reader options, **checks ที่ขยายแล้ว** (library rule ต่อคอลัมน์ + BU rules พร้อม `rule_id`, `description`, SQL/function ที่แทนค่าแล้ว, `action`, `stage` ตาม DQ-5, `library_version`), normalise/tokenise/derived/dedup/load, retention, lineage (`contract_id, contract_version, contract_file, contract_sha256, pipeline_file, pipeline_sha256, dq_library_sha256`) และ `schema_version` | P0 | DRAFT2 §5, PROMPT_01:41-43, D-P2-1 | ⚠️ **gap ที่พบรอบ 12:** "reader options" ไม่ถูก compile (`src/mdf/compile.py:149-197` ไม่อ่าน `servers.format` และ `customProperties` ของ contract) → ปิดด้วย FR-M.5

<a id="fr-d-4"></a>

### FR-D.4
Source backup lines 1147–1147; apply effective precedence above.

FR-D.4 | **⏭️ [Phase 3]** Gold: resolved config มี `inputs` (resolved table names), SQL ที่แทนค่า `{{input:<id>}}` และ `{{input_asof:<id>}}` แล้ว (as-of = `_valid_from <= :business_date AND (_valid_to IS NULL OR _valid_to > :business_date)`) + sha256, grain, unknown_member และ load `replace_partition` (replaceWhere) | P0 | D-P0-3, D-P0-10, DRAFT1 §9.4, D-P3-6 | –

<a id="fr-d-5"></a>

### FR-D.5
Source backup lines 461–461; apply effective precedence above.

FR-D.5 | Deterministic: input เดิม + compiler เดิม = bytes เดิม (sorted keys, LF, ไม่มี timestamp) | P0 | DRAFT2:242-244 | CRLF→LF ก่อน hash

<a id="fr-d-6"></a>

### FR-D.6
Source backup lines 462–462; apply effective precedence above.

FR-D.6 | ตรวจ resolved output ด้วย `config/schemas/resolved.schema.json` | P1 | DRAFT2:125 | –

<a id="fr-d-7"></a>

### FR-D.7
Source backup lines 463–463; apply effective precedence above.

FR-D.7 | มีช่อง `extensions: {semantic, classification_suggestion, uc_tags, uc_abac}` ว่างไว้ทั้งระดับ table และ column | P2 | PROMPT_01:60-66 | ห้าม implement

<a id="fr-d-8"></a>

### FR-D.8
Source backup lines 458–458; apply effective precedence above.

FR-D.8 | 🚚 **[Phase 2 · รอบ 11]** `mdf compile` เขียน resolved JSON ลง `build/<env>/resolved/<source>/{layer}.{source}.{dataset}.resolved.json` (แทนที่ FR-D.1 ส่วน path — ชื่อไฟล์คงเดิม) · `source` มาจาก `discover_datasets` เดิม ห้ามมีค่าที่ทำให้ path หลุดออกนอก `build/` (ครอบด้วย FR-B.6) | P0 | D-P5-11 (Q1 ปิดแล้ว = (b)) | ไม่มี sink แบบ configurable เข้า `/Volumes` โดยตรง

<a id="fr-e-1"></a>

### FR-E.1
Source backup lines 469–469; apply effective precedence above.

FR-E.1 | `mdf diff --base <git-rev\|package-dir>` ตรวจ: คอลัมน์ถูกลบ/เปลี่ยนชื่อ, type, required, PK, load mode/merge keys, DQ rule ถูกลบ/เปลี่ยน, action ถูกเปลี่ยน | P0 | DRAFT2 §7 | –

<a id="fr-e-2"></a>

### FR-E.2
Source backup lines 470–470; apply effective precedence above.

FR-E.2 | Breaking change ที่ contract ไม่ได้ bump major → fail · ถ้า bump แล้วต้องรายงาน impact (รายชื่อ target ที่ได้รับผลกระทบ) | P0 | DRAFT2:202-204, DRAFT1 §5 ④ | Major bump ไม่ได้แปลว่า consumer พร้อมแล้ว

<a id="fr-e-3"></a>

### FR-E.3
Source backup lines 471–471; apply effective precedence above.

FR-E.3 | `--initial-release` ต้องสั่งแบบ explicit และรายงานว่า "ไม่ได้ตรวจเทียบรุ่นก่อน" ห้ามรายงานว่า compatible | P0 | DRAFT2:206-210 | Baseline แรก = `88b982d` มีอยู่แล้ว แต่ยังไม่มี release

<a id="fr-e-4"></a>

### FR-E.4
Source backup lines 472–472; apply effective precedence above.

FR-E.4 | การเพิ่ม nullable column ต้องรายงานเป็น "additive" ห้ามถือว่าปลอดภัยโดยอัตโนมัติ | P1 | DRAFT2:200 | –

<a id="fr-e-5"></a>

### FR-E.5
Source backup lines 473–473; apply effective precedence above.

FR-E.5 | Diff ของ `config/dq_library.yaml`: แสดงกฎที่เปลี่ยน/ลบ/ปิด พร้อม **รายชื่อ dataset + คอลัมน์ทุกตัวที่ใช้กฎนั้น** · action ที่เข้มขึ้น (flag→reject/block) หรือ SQL ที่เปลี่ยน = impact ต้องได้รับการ review | P0 | DQ-6 | AC-24

<a id="fr-f-1"></a>

### FR-F.1
Source backup lines 479–479; apply effective precedence above.

FR-F.1 | `mdf package` สร้าง `resolved/*.json` + `manifest.json` + `validation-report.json` ~~flat~~ → **แทนที่ด้วย FR-F.7 (รอบ 11):** resolved แยกโฟลเดอร์ `<source>/` · `manifest.json`/`validation-report.json` อยู่ราก | P0 | DRAFT2 §8 | –

<a id="fr-f-2"></a>

### FR-F.2
Source backup lines 480–480; apply effective precedence above.

FR-F.2 | Manifest มี `manifest_version, release_id, environment, source_commit (เต็ม), compiler_revision, uv.lock sha256, ci_run_url, files[{path, sha256}], validation_report_sha256, preview` และห้าม hash ตัวเอง | P0 | DRAFT2:224-240 | Build time เก็บใน report ไม่ได้อยู่ใน config · ⚠️ **gap ที่พบใน review รอบ 9:** `src/mdf/package.py:85-90` เขียน manifest แค่ `package, env, file_count, files` (ไม่มี `release_id`, `source_commit` ฯลฯ) → CD ตรวจ release_id ไม่ได้ · แก้ใน 🚚 Phase 2 (T-35) · **[รอบ 11]** `manifest_version` เดิม = 1 → **ดู FR-F.7:** v2 เปลี่ยนความหมายของ `files[].path` เป็น `<source>/<file>` (relative POSIX) แทนชื่อไฟล์เปล่า — v1 คงความหมายเดิม (ไม่แก้ release เก่า)

<a id="fr-f-3"></a>

### FR-F.3
Source backup lines 482–482; apply effective precedence above.

FR-F.3 | Working tree ที่ dirty หรือ build บนเครื่อง local → `preview: true` | P0 | DRAFT2:255-257 | –

<a id="fr-f-4"></a>

### FR-F.4
Source backup lines 483–483; apply effective precedence above.

FR-F.4 | `--release` gate ปฏิเสธ: env `dummy: true`, placeholder `<TODO:…>`, tree dirty, contract status ที่ไม่ใช่ active | P0 | DRAFT2:175-177, D-P1-3 | ⚠️ **gap รอบ 9:** `check_release_gate` (`src/mdf/package.py:30-49`) ตรวจแค่ `dummy` + `<TODO` ของ secret_scope · ยังไม่ตรวจ tree dirty และ contract status → 🚚 Phase 2 (T-35)

<a id="fr-f-5"></a>

### FR-F.5
Source backup lines 484–484; apply effective precedence above.

FR-F.5 | `mdf verify-package <dir>` ตรวจ: ไฟล์ครบและไม่มีไฟล์เกิน, hash ตรง, schema ถูก, reference ภายในครบ **โดยไม่ต้องมี source checkout** | P0 | DRAFT2:246-253 | ~~ตรวจแค่ระดับราก (`pkg.iterdir()`)~~ → **แทนที่ด้วย FR-F.8 (รอบ 11):** ต้องตรวจแบบ recursive

<a id="fr-f-6"></a>

### FR-F.6
Source backup lines 753–753; apply effective precedence above.

FR-F.6 | 🚚 **[Phase 2]** `mdf verify-package <dir> --expect-release-id <id>` → fail ถ้า `manifest.release_id` ≠ `<id>` · ใช้ใน CD-2, CD-4 และ job ฝั่ง workspace (CD-6) | P0 | D-P5-7, D-P5-8 | AC-35

<a id="fr-f-7"></a>

### FR-F.7
Source backup lines 481–481; apply effective precedence above.

FR-F.7 | 🚚 **[Phase 2 · รอบ 11]** `mdf package` เขียน `manifest_version: 2` · layout: `build/<env>/release/{manifest.json, validation-report.json, <source>/<layer>.<source>.<dataset>.resolved.json}` · ชื่อไฟล์ resolved คงเดิม ย้ายเข้าโฟลเดอร์ `<source>/` อย่างเดียว · `files[].path` = relative **POSIX** (ใช้ `/` เท่านั้น ห้าม `\\`) รูป `<source>/<file>` เรียงตาม path · `manifest.json`/`validation-report.json` อยู่ราก ไม่อยู่ใน `files[]` (ตามเดิม) · `file_count` = จำนวน `files[]` (ไม่นับ manifest/report — ความหมายเดิม) | P0 | D-P5-11 (Q3) | แทนที่ FR-F.1 ส่วน layout · gold `_gold/<domain>/` จองชื่อไว้แต่ยัง**ไม่ implement** (⏭️ Phase 3 · ดู FR-A.4/D-P0-10) · **[รอบ 6, OQ-P5-8]** เมื่อ implement gold: path ลึก 2 ชั้น = `_gold/<domain>/<file>` (⚠️ Agent Interpretation ไม่มี sub-domain) | **[รอบ 12]** release ใหม่ใช้ `manifest_version: 3` แทน (FR-M.7) · layout `<source>/` คงเดิม

<a id="fr-f-8"></a>

### FR-F.8
Source backup lines 485–485; apply effective precedence above.

FR-F.8 | 🚚 **[Phase 2 · รอบ 11]** `verify-package` รองรับ `manifest_version` 1 (path = ชื่อไฟล์เปล่า ไม่มี `/`) และ 2 (path = `<source>/<file>`) โดย**อ่านชนิด layout จาก `manifest_version` เท่านั้น ห้ามเดาจากโครงสร้างโฟลเดอร์** · เวอร์ชันอื่นที่ไม่รู้จัก → fail `[TAMPERED] unknown manifest_version` · กติกาเพิ่มสำหรับ v2: (1) ปฏิเสธ path ที่ absolute, มี `..`, มี `\\`, ขึ้นต้นด้วย `/`, หรือลึกเกิน 1 ระดับ (segment ต้องมีเป๊ะ 2 ส่วน `<source>/<file>`) → `[TAMPERED]` (ต่อยอด FR-B.6) (2) ตรวจไฟล์แปลกปลอมแบบ **recursive** ทุก subfolder ไม่ใช่แค่ราก (3) โฟลเดอร์ว่างหรือโฟลเดอร์ที่ไม่มีไฟล์ใน manifest = แปลกปลอม → fail (4) segment แรกของ path ต้องตรงกับชื่อ source ที่เข้ารหัสอยู่ในชื่อไฟล์ (`{layer}.{source}.{dataset}.resolved.json`) · **[รอบ 6]** เมื่อพบ `manifest_version: 1` (v1 flat) — verify ผ่านได้เหมือนเดิม (**ไม่ fail**) แต่ต้องพิมพ์คำเตือน `[WARN] legacy flat layout (manifest_version 1)` ในผลลัพธ์ของ `verify-package` (แทนที่คำตอบเดิม No ของ OQ-P5-7 รอบ 11 ด้วย **เตือน** รอบ 6) · v2 ไม่มีคำเตือนนี้ | P0 | D-P5-11 (Q3, Q4); OQ-P5-7 (รอบ 6) | มี fixture v1 flat จริง (เช่น `mdf-ef2f425903b6`) ใช้ยืนยันว่า verify-package ยังอ่าน v1 ได้ทั้งพฤติกรรม (ผ่าน) และคำเตือนใหม่ (AC-46, AC-48)

<a id="fr-g-1"></a>

### FR-G.1
Source backup lines 491–491; apply effective precedence above.

FR-G.1 | **◐ [Phase 1 target = bronze/silver · gold → Phase 3]** `mdf trace <table\|config_id\|contract_id> [--package <dir>]` แสดง chain: target → inputs → contract file + version + sha256 → source_commit / release_id | P0 | PROMPT_01:41-43, :50, DRAFT2:339 | –

<a id="fr-g-2"></a>

### FR-G.2
Source backup lines 492–492; apply effective precedence above.

FR-G.2 | **◐ [Phase 1 · gold input → Phase 3 · FK = config reference (D-P4-7)]** Orphan check: contract ที่ไม่มี pipeline, pipeline ที่ไม่มี contract, gold input ที่ไม่มีอยู่จริง, FK ที่ชี้ไปหา dataset ที่ไม่มี | P0 | PROMPT_01:43 | เป็นส่วนหนึ่งของ validate

<a id="fr-g-3"></a>

### FR-G.3
Source backup lines 493–493; apply effective precedence above.

FR-G.3 | Python API `load_dataset(source, dataset, env) -> Dataset` สำหรับรวม contract + pipeline ไว้ review และมี getter เช่น `bronze_table()`, `silver_table()`, `landing_path()`, `quarantine_table()` | P1 | DRAFT1:66 (ประโยคไม่จบ) | ⚠️ Agent Interpretation → OQ-P2-3

<a id="fr-h-1"></a>

### FR-H.1
Source backup lines 499–499; apply effective precedence above.

FR-H.1 | **◐ [Phase 1 หลักฐาน = static test + รัน step เดียวกันบนเครื่อง จนกว่าจะมี repo (D-P4-5)]** `ci.yml` (PR → `master`): `uv sync --locked` → validate → diff กับ base ของ PR → compile preview → verify-package → ruff → pytest → upload artifact (preview + report) | P0 | DRAFT2 §9, D-P0-12 | –

<a id="fr-h-2"></a>

### FR-H.2
Source backup lines 500–500; apply effective precedence above.

FR-H.2 | **◐ [Phase 1 หลักฐาน = static test + รัน step เดียวกันบนเครื่อง (D-P4-5)]** `release.yml` (push `master`): checkout exact SHA → build ซ้ำ → `package --release` → verify → `gh release create <release_id>` (`release_id = mdf-<sha12>` · D-P5-6) ถ้า tag มีอยู่แล้วให้เทียบ hash หรือ fail · ⚠️ gap รอบ 9: `release.yml` ปัจจุบัน publish เฉพาะ push tag `v*` และตั้งชื่อตาม tag → 🚚 Phase 2 (T-36) · ต่อด้วย `deploy-dev.yml` ผ่าน `workflow_call` (R-22) · มี `concurrency` · ให้ `contents: write` เฉพาะ job ที่ publish · **ไม่มี `git push`/`git commit`** | P0 | DRAFT2 §9, D-P0-6 | –

<a id="fr-h-3"></a>

### FR-H.3
Source backup lines 501–501; apply effective precedence above.

FR-H.3 | ลบ `cd.yml` เดิม (bot commit) และ `ci.yml` เดิม (`generate --check`, trigger `main`) | P0 | D-P0-6, D-P0-12 | –

<a id="fr-h-4"></a>

### FR-H.4
Source backup lines 502–502; apply effective precedence above.

FR-H.4 | `.github/CODEOWNERS.example` + ownership mapping โดยไม่เดาชื่อ team · ใน docs ต้องระบุ branch protection / required checks / required reviews ที่ผู้ใช้ต้องตั้งเอง | P1 | DRAFT2:80-88, :296-298 | AS-7

<a id="fr-i-1"></a>

### FR-I.1
Source backup lines 1153–1153; apply effective precedence above.

FR-I.1 | **⏭️ [Phase 3]** Entry point: `python -m mdf.runtime.run --config-dir <resolved dir> --run-group cc --layer bronze\|silver\|gold --mode scheduled\|backfill --from YYYY-MM-DD [--to YYYY-MM-DD] [--release-id <id>] [--cascade/--no-cascade]` อ่านแค่ resolved JSON ไม่อ่านตาราง metadata · ช่วงวันรันเรียงจากเก่าไปใหม่ | P0 | D-P0-4, D-P3-2 | –

<a id="fr-i-10"></a>

### FR-I.10
Source backup lines 1162–1162; apply effective precedence above.

FR-I.10 | **⏭️ [Phase 3]** ทดสอบ runtime บนเครื่องด้วย local Spark ได้ ถ้าไม่มี JDK ให้ **skip พร้อมเหตุผล** ห้ามรายงานว่าผ่าน | P1 | backup (อ้างอิง), DRAFT1 §0 | –

<a id="fr-i-11"></a>

### FR-I.11
Source backup lines 1163–1163; apply effective precedence above.

FR-I.11 | **⏭️ [Phase 3]** **SCD2** สำหรับ master (customer, credit_card): คอลัมน์ `_valid_from` (= business_date ของแถว), `_valid_to` (exclusive, NULL = ปัจจุบัน), `_is_current`, `_row_hash` · เขียนวัน D โดย (1) แทนที่ version ที่ `_valid_from = D` (2) คำนวณ `_valid_to`/`_is_current` ใหม่ด้วย `lead(_valid_from)` เฉพาะ PK ที่ถูกแตะ · ผลต้องเท่ากันไม่ว่าวันจะรันเรียงลำดับไหน · PK ที่ไม่อยู่ในไฟล์ D ≠ ถูกลบ (AS-14) · ไม่บีบ version ที่ค่าซ้ำ (AS-15) | P0 | D-P3-6, BF-4 | –

<a id="fr-i-12"></a>

### FR-I.12
Source backup lines 1164–1164; apply effective precedence above.

FR-I.12 | **⏭️ [Phase 3]** ตารางที่แบ่ง partition ตาม business_date (silver txn, quarantine, gold) เขียนด้วย `replaceWhere business_date = D` · PK ต้องไม่ซ้ำภายในวัน · txn_id ที่ซ้ำข้ามวันจะถูก flag `dup_across_dates` ห้าม drop (AS-16) | P0 | D-P3-7, BF-2 | –

<a id="fr-i-13"></a>

### FR-I.13
Source backup lines 1165–1165; apply effective precedence above.

FR-I.13 | **⏭️ [Phase 3]** **Cascade:** backfill dataset X วัน D → runtime คำนวณ downstream ที่ได้รับผล: fact ที่ FK ไป X และ gold ที่ใช้ X ตั้งแต่วัน D ถึงวันก่อน version ถัดไปของ PK ที่เปลี่ยน (ถ้าหาไม่ได้ ให้ถึงวันล่าสุดที่เคยรัน) แล้วรันต่อตามลำดับ · `--no-cascade` = แค่รายงานรายการวันใน run_log | P0 | D-P3-2, BF-6 | ขอบเขตวัน = Agent Interpretation

<a id="fr-i-14"></a>

### FR-I.14
Source backup lines 1166–1166; apply effective precedence above.

FR-I.14 | **⏭️ [Phase 3]** FK lookup และ gold อ่าน master แบบ as-of D (ดู FR-D.4) ห้ามใช้ `_is_current` ใน pipeline · view `<table>_current` มีไว้ให้ผู้ใช้ทั่วไปเท่านั้น | P0 | D-P3-6, BF-5 | –

<a id="fr-i-15"></a>

### FR-I.15
Source backup lines 1167–1167; apply effective precedence above.

FR-I.15 | **⏭️ [Phase 3]** **Erasure list** `{catalog}.ops.erasure_list (dataset, key_column, token, erased_at, request_ref)` เก็บ token เท่านั้น · ทุก run (scheduled/backfill/replay) ถ้าแถวมี token อยู่ใน list: ไม่เขียน cleartext ลง vault และตั้งคอลัมน์ PII ที่ไม่ tokenise ของแถวนั้นเป็น NULL (AS-19) · ห้าม RESTORE | P0 | D-P3-8, BF-9 | –

<a id="fr-i-16"></a>

### FR-I.16
Source backup lines 1168–1168; apply effective precedence above.

FR-I.16 | **⏭️ [Phase 3]** **โหมด `replay`** (กู้คืน · คนสั่งเท่านั้น): `RESTORE` ตารางที่ระบุไปยัง `version_before` ของ run แรกของวัน D จาก run_log แล้วรันใหม่ D → วันล่าสุดตามลำดับ · ต้องใส่ `--confirm RESTORE` · ถ้า version เก่ากว่า Delta retention (AS-17) → error ที่บอกให้ใช้ backfill แทน · ห้ามใช้กับ vault, erasure_list และ run_log | P1 | D-P3-4, D-P3-7 | –

<a id="fr-i-17"></a>

### FR-I.17
Source backup lines 1169–1169; apply effective precedence above.

FR-I.17 | **⏭️ [Phase 3]** Tokenise ตรวจ `hmac_key_version` ของ secret ปัจจุบันเทียบกับของข้อมูลเดิม (จาก run_log) ถ้าไม่ตรง → block · ห้ามมี token จาก key คนละ version ปนกันในตารางเดียว | P0 | BF-10, AS-18 | –

<a id="fr-i-18"></a>

### FR-I.18
Source backup lines 1170–1170; apply effective precedence above.

FR-I.18 | **⏭️ [Phase 3]** `--release-id` โหลด resolved config จาก `/Volumes/{catalog}/ops/files/releases/<release_id>/` แล้วตรวจ `verify-package --expect-release-id` ก่อนใช้ · `release_id` ต้องมีแถว `REGISTERED` ใน `ops.release_registry` ที่ `manifest_sha256` ตรง (D-P5-7) · ไม่ส่ง `release_id` มา = error ห้ามเดา release ล่าสุดเอง · ถ้า schema ของตารางปลายทางไม่เข้ากับ config ของ release นั้น → block พร้อมบอกว่าคอลัมน์ไหน · runtime code ไม่ย้อน version (AS-20) · **[รอบ 11]** runtime ต้องอ่าน path ของไฟล์ resolved **จาก `manifest.files[].path` เท่านั้น** ห้ามเดา layout จากโครงสร้างโฟลเดอร์ · ต้องรองรับทั้ง `manifest_version` 1 (flat) และ 2 (`<source>/<file>`) เพราะ release เก่าที่ flat ไม่ migrate (D-P5-11 Q4) · **[รอบ 6, OQ-P5-8 = 2 ชั้น]** ⚠️ Agent Interpretation: เมื่อ gold เริ่ม implement (Phase 3) path ของไฟล์ gold = `_gold/<domain>/<file>` (2 ส่วน เหมือน source ปกติ ไม่มี sub-domain) — ใช้กฎ depth เดียวกับ FR-F.8 (segment ต้องมีเป๊ะ 2 ส่วน) ยัง **⏭️ Phase 3** ไม่ block รอบนี้ | P0 | D-P3-5, BF-7; D-P5-11 (Q4); OQ-P5-8 (รอบ 6) | –

<a id="fr-i-2"></a>

### FR-I.2
Source backup lines 1154–1154; apply effective precedence above.

FR-I.2 | **⏭️ [Phase 3]** Arrival check ตาม SLA **เฉพาะ `--mode scheduled`**: on_time / late (อยู่ใน grace ไม่ alert) / missing (ห้ามตีความว่าไม่มีข้อมูล และข้าม downstream) · `--mode backfill` บันทึก `arrival_status=backfill` ไม่ alert และไม่แก้สถานะของ run เดิม · ถ้าไม่มีไฟล์ของ D → `missing` + ข้าม | P0 | DRAFT1 §5 ①, §5:316-319, BF table | **[รอบ 12]** อ่าน SLA จาก `calendar` ใน resolved JSON ของ release (FR-M.3, FR-M.10) ไม่อ่าน contract จาก git · dataset ที่ `calendar.status = PENDING_OWNER` → ห้ามคำนวณ late/missing (บันทึกเป็น pending owner ไม่เดาค่า · R-27) · หยุด poll อัตโนมัติที่ expected instant + `recovery_window_seconds` · retry ปกติห้ามเริ่ม backfill (D-P5-12 Q6)

<a id="fr-i-3"></a>

### FR-I.3
Source backup lines 1155–1155; apply effective precedence above.

FR-I.3 | **⏭️ [Phase 3]** Bronze: อ่าน CSV **ทุกคอลัมน์เป็น string** + audit columns (`_ingest_file_name, _ingest_row_number, _ingest_ts, _business_date, _run_id`) → **`replaceWhere _business_date = D`** (ไม่ใช่ append) · ถ้า partition ของ D หมดอายุแล้ว สร้างใหม่จาก landing archive (D-P3-3) | P0 | DRAFT1 §9.2, D-P3-3, BF-2 | ⚠️ ต่างจาก DRAFT1 ② (StructType + `_rescued_data`) → CL-12, AS-11 · append เดิม → CL-27

<a id="fr-i-4"></a>

### FR-I.4
Source backup lines 1156–1156; apply effective precedence above.

FR-I.4 | **⏭️ [Phase 3]** Silver ตามลำดับ **normalise → cast (`cast_ok`) → library rules + BU rules ที่ไม่อ้าง derived (บน cleartext) → tokenise (HMAC-SHA256 + vault) → derived → BU rules ที่อ้าง derived → dedup (deterministic) → merge** | P0 | DC-7, ✅ D-P2-6, DRAFT1 §5:322-324 | reject → quarantine พร้อม `rule_id, reason` · block → หยุด run · flag → นับเป็น metric

<a id="fr-i-5"></a>

### FR-I.5
Source backup lines 1157–1157; apply effective precedence above.

FR-I.5 | **⏭️ [Phase 3]** DQ executor รัน checks จาก resolved config: `kind: sql` → Spark SQL expression · `kind: function` → ฟังก์ชันใน registry (luhn, fk_exists, cast_ok) · NULL ตาม DQ-4 | P0 | D-P1-2, D-P2-1, DC-8 | –

<a id="fr-i-6"></a>

### FR-I.6
Source backup lines 1158–1158; apply effective precedence above.

FR-I.6 | **⏭️ [Phase 3]** FK ในข้อมูลที่หา parent ไม่เจอ = **data defect** → ส่ง BA คุยกับ source (D-P4-7 ข) · ระหว่างรอ: ⚠️ Agent Interpretation left join + flag `fk@<col>` + ค่า FK = NULL ("เก็บ None") ห้าม drop · ~~unknown member `-1`/`'UNKNOWN'`~~ ถอนแล้ว · รายละเอียด → OQ-P1-23 | P0 | DRAFT1 §5:323, DC-4 | –

<a id="fr-i-7"></a>

### FR-I.7
Source backup lines 1159–1159; apply effective precedence above.

FR-I.7 | **⏭️ [Phase 3]** dq_policy: `quality_first` + pass rate < `min_dq_pass_rate` → ไม่ publish · `latency_first` → publish โดยตั้ง `is_trusted=false` | P0 | DRAFT1 §5:325 | –

<a id="fr-i-8"></a>

### FR-I.8
Source backup lines 1160–1160; apply effective precedence above.

FR-I.8 | **⏭️ [Phase 3]** Gold: รัน SQL ที่ resolve แล้ว → `replace_partition` (Delta replaceWhere `business_date = D`) · master อ่านผ่าน `{{input_asof}}` | P0 | D-P0-3, D-P3-7 | –

<a id="fr-i-9"></a>

### FR-I.9
Source backup lines 1161–1161; apply effective precedence above.

FR-I.9 | **⏭️ [Phase 3]** `run_log` (Delta managed, `{catalog}.ops.run_log`, append-only, **ห้าม RESTORE**) บันทึก `run_id, run_type (scheduled/backfill/replay), parent_run_id (cascade), release_id, config_id, config_sha256, runtime_version, hmac_key_version, business_date, layer, arrival_status, input_files[] (path, size, sha256), table_versions[] (table, version_before, version_after), rows_in, rows_out, rows_quarantined, dq_pass_rate, is_trusted, status, started_at, ended_at` · ผลปัจจุบันของ (config_id, business_date) = run สุดท้ายที่ `status=success` | P0 | D-P0-4, DRAFT2 §10:319-320, DRAFT1 §4, D-P3-5, BF-8 | ชื่อ schema = OQ-P2-2

<a id="fr-j-1"></a>

### FR-J.1
Source backup lines 759–759; apply effective precedence above.

FR-J.1 | 🚚 **[Phase 2]** `databricks.yml` มี target `dev` เดียว (serverless) ใช้ variables จาก control file และห้ามมี secret ในไฟล์ | P0 | D-P0-9, PROMPT_02 §1 | –

<a id="fr-j-2"></a>

### FR-J.2
Source backup lines 1176–1176; apply effective precedence above.

FR-J.2 | **⏭️ [Phase 3]** Job `mdf_cc_dev` **job เดียว** ใช้ทั้ง scheduled และ backfill: task bronze → silver → gold (depends_on) · parameters `mode`, `from`, `to`, `release_id`, `cascade` (ค่าตั้งต้น scheduled = เมื่อวานตาม Asia/Bangkok) · `max_concurrent_runs: 1` + queue เพื่อไม่ให้ backfill กับ scheduled เขียนวันเดียวกันพร้อมกัน · มี job แยก `mdf_replay_dev` สำหรับ FR-I.16 (ไม่มี schedule) | P0 | D-P0-4, PROMPT_02:47, D-P3-2 | ไม่มี onboarding job

<a id="fr-j-3"></a>

### FR-J.3
Source backup lines 760–760; apply effective precedence above.

FR-J.3 | **◐ [🚚 Phase 2: schema `ops` + volume `files` + `ops.release_registry` · ⏭️ Phase 3: schema อื่นทั้งหมด]** สร้าง UC objects ที่จำเป็นแบบ idempotent (`CREATE … IF NOT EXISTS`): schemas `bronze_cc, silver_cc, quarantine_cc, vault_cc, gold_card, ops, landing_cc` + volume `files` | P0 | PROMPT_02:49-50 | ⚠️ Free Edition อาจสร้าง catalog ใหม่ไม่ได้ (R-4)

<a id="fr-j-4"></a>

### FR-J.4
Source backup lines 761–761; apply effective precedence above.

FR-J.4 | **◐ [🚚 Phase 2 = FR-L (CD-1…8) · ⏭️ Phase 3 = smoke run medallion 1 business_date → query `run_log`]** Workflow `deploy-dev.yml`: ดาวน์โหลด release → verify-package → `bundle validate` → `bundle deploy -t dev` → smoke | P0 | PROMPT_02 §2 | **ต้องได้ HG_PROD ก่อนรันจริงครั้งแรก**

<a id="fr-j-5"></a>

### FR-J.5
Source backup lines 762–762; apply effective precedence above.

FR-J.5 | **◐ [🚚 Phase 2: deploy, rollback config (= CD-8 ด้วย release เก่า), manual copy · ⏭️ Phase 3: backfill, replay, erasure, HMAC rotation]** Runbook: deploy, rollback config (redeploy release เดิม = rollback config **ไม่ใช่ rollback ข้อมูล**), backfill (ตัวอย่างคำสั่งช่วงวัน + release_id), replay/RESTORE (เงื่อนไขและตารางที่ห้ามแตะ), erasure request, HMAC key rotation (= rebuild ทั้งหมด · AS-18) | P1 | PROMPT_02 §3, DRAFT2:322, D-P3-2 | –

<a id="fr-j-6"></a>

### FR-J.6
Source backup lines 763–763; apply effective precedence above.

FR-J.6 | 🚚 **[Phase 2]** Deploy คัดลอก release package ไปที่ `/Volumes/{catalog}/ops/files/releases/<release_id>/` แบบ **ไม่เขียนทับและไม่ลบ** release เดิม · ถ้ามี release_id นี้อยู่แล้ว hash ต้องตรง ไม่ตรง → fail · **[รอบ 11]** สำหรับ release v2 คัดลอกแบบ **recursive** ให้คง subfolder `<source>/` (ดู FR-L.4) | P0 | D-P3-5, BF-7 | –

<a id="fr-j-7"></a>

### FR-J.7
Source backup lines 1177–1177; apply effective precedence above.

FR-J.7 | **⏭️ [Phase 3]** Grants (สคริปต์/เอกสาร): landing volume และ `bronze_*` อ่านได้เฉพาะ SP ของ runtime (+ break-glass group) · `vault_*` และ `ops.erasure_list` จำกัดกลุ่มเดียว · ตั้ง table property `delta.deletedFileRetentionDuration`/`delta.logRetentionDuration` ตาม AS-17 | P0 | D-P3-8, AS-17 | ชื่อ SP/group = DEP-5

<a id="fr-k-1"></a>

### FR-K.1
Source backup lines 508–508; apply effective precedence above.

FR-K.1 | README ภาษาไทย: ติดตั้ง, workflow ของ BA/DE/Platform ทีละขั้น, วิธีเพิ่มหรือแก้ rule JSON, วิธีอ่าน error | P0 | PROMPT_01 (backup), DRAFT2 §13 | –

<a id="fr-k-2"></a>

### FR-K.2
Source backup lines 509–509; apply effective precedence above.

FR-K.2 | **◐ [current = Phase 1 · future = Phase 3 / AI phase]** `docs/architecture/ARCHITECTURE.md` ฉบับใหม่ที่ตรงกับ implementation และแยก current / future ออกจากกัน | P1 | DRAFT2 §13 | DRAFT1/DRAFT2 ต้นฉบับย้ายไปเก็บที่ `docs/archive/` (Proposed)

<a id="fr-k-3"></a>

### FR-K.3
Source backup lines 510–510; apply effective precedence above.

FR-K.3 | รายงานปิดงาน 5 ข้อ (เปลี่ยนอะไร, โครงสร้างก่อน/หลัง, audit ได้ถึงไหน, คำสั่ง + ผลที่รันจริง, สิ่งที่ยังไม่ได้ทดสอบ) | P1 | DRAFT2:390-399 | –

<a id="fr-l-1"></a>

### FR-L.1
Source backup lines 769–769; apply effective precedence above.

FR-L.1 | `release.yml` publish GitHub Release ชื่อ `mdf-<source_commit[:12]>` จาก push `master` · asset = ไฟล์ใน package ทั้งหมด (resolved JSON + `manifest.json` + `validation-report.json`) · id เดิมมีอยู่แล้ว → เทียบ hash ตรง = ข้าม / ไม่ตรง = fail | P0 | D-P5-2, D-P5-6, FR-H.2 | trigger = Proposed (AS-22 · OQ-P5-3) · **[รอบ 11 · รอบ 5]** ส่วน asset ถูก **แทนที่ด้วย…(รอบ 11 · รอบ 5)** — ดู FR-L.1a (asset เดี่ยวเป็น zip แทน flat หลายไฟล์ เพราะ GitHub Release asset เก็บโฟลเดอร์ย่อยไม่ได้)

<a id="fr-l-10"></a>

### FR-L.10
Source backup lines 782–782; apply effective precedence above.

FR-L.10 | CD-1…8 อยู่ในสคริปต์เดียว `scripts/deliver_release.sh <release_id>` ที่ workflow เรียก · manual copy (D-P5-6) = ผู้ใช้รันสคริปต์เดียวกันด้วย OAuth U2M · มี test ยืนยันว่า workflow เรียกสคริปต์นี้ (ไม่ drift · เหมือน AC-34) | P0 | D-P5-6 | หลักฐาน manual ต้องติดป้าย manual

<a id="fr-l-11"></a>

### FR-L.11
Source backup lines 783–783; apply effective precedence above.

FR-L.11 | ทุก run ของ CD เขียนหลักฐาน: release URL, run URL (หรือ "manual" + ผู้รัน), ผล verify 2 รอบ, `databricks fs ls` ของโฟลเดอร์ปลายทาง, ผล query registry | P1 | D-P5-9 | ห้ามมี token ในหลักฐาน

<a id="fr-l-12"></a>

### FR-L.12
Source backup lines 784–784; apply effective precedence above.

FR-L.12 | 🚚 **[Phase 2 · รอบ 10]** ผู้ใช้ตั้ง delivery mode ใน `config/env/<env>.yaml` ด้วย key เดียว `delivery_mode: auto \| u2m \| manual` · `mdf validate` ปฏิเสธค่าอื่นหรือไม่มี key (ข้อความไทย + วิธีแก้) · เปลี่ยน mode = แก้ไฟล์ผ่าน PR (มีร่องรอยใน Git) · ห้ามมี host/secret ในไฟล์นี้ (repo public) | P0 | D-P5-10 | ค่าตั้งต้นของ `dev` = `u2m` (AS-26)

<a id="fr-l-13"></a>

### FR-L.13
Source backup lines 785–785; apply effective precedence above.

FR-L.13 | 🚚 **[Phase 2 · รอบ 10]** mode `manual`: repo มี SQL ที่วางใน SQL editor ได้ทันที (ใส่แค่ `release_id`) · `sql/manual/register_release.sql` ตรวจในฝั่ง workspace **เท่ากับ job** (manifest ครบ, `release_id` ตรง, sha256 ทุกไฟล์ตรง, ไม่มีไฟล์เกิน, validation report ตรง) ไม่ผ่าน = `raise_error` และ **ไม่ INSERT** · ผ่าน = INSERT `REGISTERED` ถ้ายังไม่มี (มีแล้ว hash ตรง = ไม่เพิ่ม · ไม่ตรง = error) · `sql/manual/activate_release.sql` ต้องมี `REGISTERED` ก่อน แล้ว append `ACTIVATED` · ทุก script แสดง `manifest_sha256` ให้เทียบกับ digest ของ `manifest.json` บนหน้า GitHub Release · **[รอบ 11]** ไฟล์ SQL ต้องอ่านไฟล์ resolved ที่อยู่ใน subfolder `<source>/` ได้ด้วย `read_files(...)` แบบ glob ที่ลงลึก 1 ระดับ (ไม่ใช่แค่ไฟล์ระดับราก) และ `regexp_extract` ที่ใช้หา path ต้องคืนค่า relative path เต็ม (`<source>/<file>`) ไม่ใช่แค่ basename · **[รอบ 11 · รอบ 5] แทนที่ด้วย…(รอบ 11 · รอบ 5):** clause \"เทียบกับ digest ของ `manifest.json` บนหน้า GitHub Release\" ใช้ไม่ได้แล้ว เพราะหน้า Release แสดง digest ของไฟล์ `<release_id>.zip` (ไม่ใช่ของ `manifest.json` โดยตรง) — ให้เทียบกับ `manifest_sha256` ที่พิมพ์ใน **Job Summary** ของ run `release.yml` แทน (FR-L.14) | P0 | D-P5-10; D-P5-11 (Q3); D-P5-11 (รอบ 5) | `read_files(... format => 'binaryFile')` + `sha2` + `raise_error` + path ที่มี `:release_id` ใช้ได้บน Free Edition (probe รอบ 10) · SQL จริงยังเขียนแบบเดิม (ไม่ใช่งาน BA) — TRI จะแตก ticket ให้ SWE แก้ `sql/manual/*.sql`

<a id="fr-l-14"></a>

### FR-L.14
Source backup lines 786–786; apply effective precedence above.

FR-L.14 | 🚚 **[Phase 2 · รอบ 10]** ระบบบอกผู้ใช้ทีละขั้นว่าต้องทำอะไรต่อ ตาม mode ที่ตั้ง และใส่ `release_id` จริงให้: (ก) ทุก push `master` → หน้า run ของ `release.yml` มี **Job Summary "ขั้นต่อไป"** · `auto` = ลิงก์ approve Environment `dev` · `u2m` = คำสั่งที่ copy ไปรันได้เลย · `manual` = checklist M-1…M-7 (ข) `runbooks/release-delivery.md` ครบ 3 mode (ค) `scripts/deliver_release.sh` เมื่อ fail บอกสาเหตุ + ขั้นต่อไป (login หมดอายุ → คำสั่ง login · u2m ทำไม่ได้ → ไป `manual`) · **[รอบ 11]** ข้อความของ `src/mdf/next_steps.py` (mode `manual` M-2/M-3) ต้องพูดถึงการสร้างโฟลเดอร์ย่อย `<source>/` ก่อนอัปโหลด ไม่ใช่อัปโหลดแบบ flat · **[รอบ 11 · รอบ 5]** Job Summary (ก) ต้องพิมพ์ `manifest_sha256` ของ `manifest.json` ด้วย (ทุก mode) เพราะ digest ที่หน้า Release เป็นของไฟล์ zip แล้ว ใช้เทียบไม่ได้อีกต่อไป (ดู FR-L.13) — mode `manual` (M-2) ข้อความต้องบอกให้ดาวน์โหลด `<release_id>.zip` แล้วแตกเอง ไม่ใช่ดาวน์โหลดทีละไฟล์ 8 ไฟล์แบบเดิม · **[รอบ 6]** Job Summary (ก) และ**หลักฐาน CD/next steps ที่เกี่ยวข้อง** ต้องแสดงคำเตือน `legacy flat layout (v1)` เมื่อ release ที่เกี่ยวข้องเป็น v1 flat (ต่อยอด FR-F.8, AC-48, OQ-P5-7) · **[รอบ 6]** `manifest_sha256` **แทนที่คำตอบเดิม** (เดิม: Job Summary อย่างเดียว) ด้วยต้องพิมพ์ทั้งใน **Job Summary และ release notes** ของ GitHub Release (OQ-P5-9) | P0 | D-P5-10 "อยากให้บอกด้วยว่าฉันต้องทำยังไงต่อ step by step"; D-P5-11 (Q6); D-P5-11 (รอบ 5); D-P5-11 (รอบ 6) | ตำแหน่งที่แสดง `manifest_sha256` (Job Summary + release notes) เดิมเป็น Agent Interpretation · **ปิดแล้ว รอบ 6 (OQ-P5-9 = เพิ่ม)** — ต้องมีทั้งสองที่

<a id="fr-l-15"></a>

### FR-L.15
Source backup lines 787–787; apply effective precedence above.

FR-L.15 | 🚚 **[Phase 2 · รอบ 10]** คอลัมน์ `actor` บอก mode: `github-oidc` (auto) · `manual` (u2m — ค่าเดิม ไม่เปลี่ยน เพราะแก้แถวเก่าใน append-only ไม่ได้) · `manual-ui` (manual) | P1 | D-P5-10 | แถวเดิม 7 แถว = `manual` = u2m ถูกต้องแล้ว

<a id="fr-l-1a"></a>

### FR-L.1a
Source backup lines 770–770; apply effective precedence above.

FR-L.1a | 🚚 **[Phase 2 · รอบ 11 · รอบ 5]** `release.yml` publish step แนบไฟล์เดียว `<release_id>.zip` เป็น asset (แทนที่ `build/dev/release/*` แบบ flat ของ FR-L.1 — เหตุผล: GitHub Release asset เก็บโฟลเดอร์ย่อยไม่ได้) · โครงสร้างใน zip = ราก release ตรง ๆ (`manifest.json`, `validation-report.json`, `<source>/…`) **ไม่มีโฟลเดอร์ครอบชั้นนอก** (ไม่ใช่ `<release_id>/manifest.json`) · zip สร้างจาก `build/dev/release/` ก่อนขั้น publish · zip ไม่ deterministic (มี timestamp ในตัว) → **ห้ามใช้ hash ของ zip ตัดสิน idempotency** ขั้น \"Publish or skip if identical release exists\" (`release.yml:101-117`) ต้องดาวน์โหลด zip ของ release เดิม แตกก่อน แล้วเทียบ `manifest.json` ที่แตกได้เหมือนเดิม (ไม่เปลี่ยน logic diff เดิม แค่เพิ่มขั้นแตก zip ก่อน `jq`) | P0 | D-P5-11 (รอบ 5) | ผู้ใช้: \"แนบไฟล์ .zip ของทั้ง package เป็น asset เดียว\"

<a id="fr-l-1b"></a>

### FR-L.1b
Source backup lines 771–771; apply effective precedence above.

FR-L.1b | 🚚 **[Phase 2 · รอบ 11 · รอบ 5]** `verify-package` ที่รันกับ zip ที่แตกแล้ว (ทั้งใน CI สำหรับ idempotency check และใน CD-1) ใช้กฎเดียวกับ FR-F.8 ทุกประการ (v1/v2, traversal, sealed) — zip เป็นแค่ transport ไม่ใช่ layout ใหม่ | P0 | FR-F.8 | ไม่เพิ่ม manifest_version ใหม่สำหรับ zip

<a id="fr-l-2"></a>

### FR-L.2
Source backup lines 772–772; apply effective precedence above.

FR-L.2 | `deploy-dev.yml`: `on: workflow_call` (เรียกต่อจาก release.yml หลัง publish) + `workflow_dispatch` (input `release_id` บังคับ) · `environment: dev` (required reviewer = HG_PROD) · `permissions: id-token: write, contents: read` · `concurrency: deploy-dev` ไม่ cancel · **รอบ 10:** job ส่งของใน `release.yml` รันเฉพาะเมื่อ `delivery_mode: auto` (FR-L.12) · mode อื่น = job ถูกข้ามพร้อมบอกขั้นต่อไป (FR-L.14) | P0 | D-P5-5, D-P5-8, D-P5-10 | R-22: release ที่สร้างด้วย `GITHUB_TOKEN` ไม่ trigger workflow อื่น จึงใช้ `workflow_call`

<a id="fr-l-3"></a>

### FR-L.3
Source backup lines 773–773; apply effective precedence above.

FR-L.3 | CD-1 ดาวน์โหลด asset ของ release ที่ระบุ · CD-2 `verify-package --expect-release-id` ก่อนแตะ workspace | P0 | D-P5-8 ข้อ 1–2 | – · **[รอบ 11 · รอบ 5]** ดูวิธีเลือก asset ที่ดาวน์โหลดใน FR-L.3a

<a id="fr-l-3a"></a>

### FR-L.3a
Source backup lines 774–774; apply effective precedence above.

FR-L.3a | 🚚 **[Phase 2 · รอบ 11 · รอบ 5]** CD-1 ของ `deliver_release.sh` เลือกวิธีดาวน์โหลดตาม**การมี/ไม่มี asset ชื่อ `<release_id>.zip`** เท่านั้น (ยังไม่ verify-package ตอนนี้ ห้ามเดาจาก `manifest_version`): (1) **มี** `<release_id>.zip` (release ใหม่ตาม FR-L.1a) → ดาวน์โหลดเฉพาะไฟล์นั้น แล้วแตกด้วยกฎกัน zip-slip เดียวกับ FR-F.8 (ปฏิเสธ absolute path, `..`, `\\`, ขึ้นต้นด้วย `/`) ก่อนเข้า CD-2 — path ที่ไม่ผ่าน → fail CD-1 ห้ามแตะ workspace (2) **ไม่มี** asset นั้น (release เดิมก่อนรอบ 5 ที่เป็น asset flat หลายไฟล์ เช่น `mdf-ef2f425903b6`) → ดาวน์โหลดทุกไฟล์แบบเดิม (พฤติกรรมก่อนรอบ 5) เพื่อให้ rollback/re-deliver release เก่ายังทำได้ | P0 | D-P5-11 (รอบ 5) | ต่อยอด FR-L.3 (CD-1) — แก้ที่ `scripts/deliver_release.sh` (TRI แตก ticket ให้ SWE ทำ ไม่ใช่งาน BA รอบนี้)

<a id="fr-l-4"></a>

### FR-L.4
Source backup lines 775–775; apply effective precedence above.

FR-L.4 | CD-3 `databricks fs cp <dir> dbfs:/Volumes/{catalog}/ops/files/releases/<release_id> --recursive` · resolved ก่อน `manifest.json` สุดท้าย · โฟลเดอร์ที่มี `manifest.json` = sealed → hash ตรง = ข้าม · ไม่ตรง = fail · **ห้ามเขียนทับ ห้ามลบ** · โฟลเดอร์ที่ยังไม่มี `manifest.json` (คัดลอกค้าง) คัดลอกต่อได้ · **[รอบ 11]** release v2 มี subfolder `<source>/` — `--recursive` ของ `fs cp` คง subfolder โดยธรรมชาติ · `deliver_release.sh` CD-3 ห้ามพึ่ง `ls $PKG` แบบ flat ต้องวน sub­folder ด้วย (ดู FR-L.4a) | P0 | D-P5-6, D-P5-8 ข้อ 3, FR-J.6 | catalog มาจาก control file (D-P0-9)

<a id="fr-l-4a"></a>

### FR-L.4a
Source backup lines 776–776; apply effective precedence above.

FR-L.4a | 🚚 **[Phase 2 · รอบ 11]** `scripts/deliver_release.sh` CD-3: คัดลอกไฟล์ resolved **ทุก subfolder ของทุก source** ก่อน แล้ว `manifest.json` เป็นไฟล์สุดท้าย (sealed rule เดิมไม่เปลี่ยน) · ต้องใช้ `find`/`glob` แบบ recursive แทนการวน `ls $PKG` ระดับเดียว | P0 | D-P5-11 (Q3) | แก้ตรง `scripts/deliver_release.sh` — TRI จะแตก ticket ให้ SWE ทำ (ไม่ใช่งานของ BA รอบนี้)

<a id="fr-l-5"></a>

### FR-L.5
Source backup lines 777–777; apply effective precedence above.

FR-L.5 | CD-4 คัดลอก `/Volumes/…/<release_id>/` กลับมา แล้ว `verify-package --expect-release-id` ต้องผ่าน | P0 | D-P5-8 ข้อ 4 | พิสูจน์ "คัดลอกครบ" ด้วย hash ไม่ใช่แค่นับไฟล์ · **[รอบ 11]** `fs cp -r` คัดลอกกลับต้องคง subfolder แล้ว verify-package (FR-F.8) อ่าน v2 ได้

<a id="fr-l-6"></a>

### FR-L.6
Source backup lines 778–778; apply effective precedence above.

FR-L.6 | CD-5 `databricks bundle validate -t dev` → `bundle deploy -t dev` · bundle มี wheel ของ `mdf` (artifacts) + job `mdf_release_register_dev` (serverless · ไม่มี schedule) | P0 | D-P5-5, D-P5-8 ข้อ 5 | ไม่มี secret ในไฟล์ (FR-J.1)

<a id="fr-l-7"></a>

### FR-L.7
Source backup lines 779–779; apply effective precedence above.

FR-L.7 | CD-6 `bundle run mdf_release_register_dev --params release_id=<id>` · job อ่าน `/Volumes/{catalog}/ops/files/releases/<id>/` → verify ใน workspace → INSERT `REGISTERED` ลง `{catalog}.ops.release_registry` ถ้ายังไม่มี (มีแล้ว hash ตรง = ไม่เพิ่มแถว · ไม่ตรง = fail) · CD-7 smoke = query registry ของ `<id>` ได้ 1 แถว `REGISTERED` ที่ hash ตรง | P0 | D-P5-2 ("append แบบ manage delta"), D-P5-8 ข้อ 6–7 | AS-23

<a id="fr-l-8"></a>

### FR-L.8
Source backup lines 780–780; apply effective precedence above.

FR-L.8 | CD-8 append `ACTIVATED` + ตั้ง bundle variable `active_release_id` = ค่าตั้งต้นของ parameter `release_id` ของ job ที่มี schedule · Phase 2 ยังไม่มี job ที่มี schedule → ค่านี้ถูกใช้ครั้งแรกโดย `mdf_cc_dev` ใน Phase 3 (AS-24) | P1 | D-P5-7, D-P5-8 ข้อ 8 | rollback config = CD-8 ด้วย release เก่า

<a id="fr-l-9"></a>

### FR-L.9
Source backup lines 781–781; apply effective precedence above.

FR-L.9 | Auth = workload identity federation (`DATABRICKS_AUTH_TYPE=github-oidc`, `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`) + service principal federation policy ที่ subject ผูกกับ `environment:dev` · ห้ามมี `DATABRICKS_TOKEN` / client secret ใน GitHub | P0 | D-P5-5 | DEP-3 · R-20

<a id="fr-m-1"></a>

### FR-M.1
Source backup lines 795–795; apply effective precedence above.

FR-M.1 | 🚚 **[รอบ 12 · CR-01]** ODCS contract ของทุก dataset รองรับ field calendar: `slaProperties` คง `frequency` + `latency` (4 h) เดิม และเพิ่ม `expected_at` (`HH:MM` เวลาท้องถิ่น) + `recovery_window` (`value: 2, unit: d`) · `customProperties` เพิ่ม `timezone` (ชื่อ IANA), `expected_day_offset` (int ≥ 0 นับจาก `business_date`), `business_schedule` (object: `type` ∈ `daily \| workday \| workday_excluding_holidays \| day_of_month \| explicit_dates`, `effective_from`, `effective_to?`, `holidays[]`, `explicit_dates[]`, `exceptions[]`, `day_of_month?`, `day_of_month_policy?`) · ใช้ `customProperties` เดิมของ ODCS (schema v3.0.2 รับ `value` เป็น object ได้ · `config/schemas/odcs_v3.0.2.json` `CustomProperty.value = AnyType`) ไม่เพิ่ม top-level key ใหม่ | P0 | D-P5-12; CR-01 | ค่าจริงต้องมาจากเจ้าของข้อมูล (OQ-P5-10) · ห้ามใส่ค่าที่เดาลง contract · `Asia/Bangkok` ใน `config/env/dev.yaml` เป็นแค่ตัวเลือก ไม่ใช่ค่าของ contract

<a id="fr-m-10"></a>

### FR-M.10
Source backup lines 804–804; apply effective precedence above.

FR-M.10 | 🚚 **[รอบ 12 · Q4 = (a)]** สัญญาระหว่าง release กับ runtime: runtime อ่าน `calendar`, `reader`, `schema[].pii/pci/tags` จาก **resolved JSON เป็นหลัก** · ODCS YAML ที่แนบมาใช้ตรวจ hash และดูย้อนหลังเท่านั้น (runtime ไม่ parse ODCS เพื่อหา policy) · release v3 ที่ YAML หายหรือ hash ไม่ตรง = verify ไม่ผ่าน → runtime ห้ามใช้ · ห้ามอ่าน `DataContract/` จาก git checkout ใน run จริง · fixture ในเครื่องใช้ได้เฉพาะ run ที่ติดป้าย sample | P0 | D-P5-12 Q4 | ฝั่ง Medallion (`../Medallion/framework/_shared_helpers_bronze.py:243` loader) เป็น repo อื่น → ⏭️ Phase 3 / เจ้าของ Medallion · release v1/v2 ไม่มี `calendar` → runtime ต้อง fail พร้อมบอกให้ใช้ release v3 (ไม่ fallback ไป git)

<a id="fr-m-11"></a>

### FR-M.11
Source backup lines 805–805; apply effective precedence above.

FR-M.11 | 🚚 **[รอบ 12 · P1]** `mdf diff` รายงานการเปลี่ยน `calendar` และ `pii`/`pci` ของคอลัมน์เป็นรายการ "ต้อง review" (ไม่ใช่ breaking อัตโนมัติ · แนวเดียวกับ FR-E.4) | P1 | Agent Interpretation (CR-05 ส่วนตรวจ) | `pci: true → false` เปลี่ยนวิธีคุ้มครองข้อมูล จึงไม่ควรผ่านเงียบ ๆ

<a id="fr-m-2"></a>

### FR-M.2
Source backup lines 796–796; apply effective precedence above.

FR-M.2 | 🚚 **[รอบ 12 · CR-01]** `mdf validate` ตรวจ calendar (ข้อความไทย + วิธีแก้ ตาม NFR-7): ~~timezone ไม่ใช่ IANA ที่รู้จัก~~ **(รอบ 12 · OQ-TRI-12a: ไม่ตรวจ IANA — ตรวจแค่เป็น string ไม่ว่าง)** · `expected_at` ไม่ใช่ `HH:MM` 00:00–23:59 · `expected_day_offset` ติดลบหรือไม่ใช่ int · วันที่ไม่ใช่ ISO `YYYY-MM-DD` · `holidays`/`explicit_dates` ซ้ำ · `effective_to < effective_from` · `day_of_month` นอก 1–31 หรือไม่มี `day_of_month_policy` · `explicit_dates` ว่างเมื่อ `type: explicit_dates` · field ที่ type นั้นบังคับขาด · `recovery_window` < `latency` · `latency`/`recovery_window` ที่ unit ไม่ใช่ `h`/`d` | P0 | CR-01 §validation | กติกาเหล่านี้ตรวจรูปแบบ ไม่ได้ตรวจว่าค่าถูกตามธุรกิจ

<a id="fr-m-3"></a>

### FR-M.3
Source backup lines 797–797; apply effective precedence above.

FR-M.3 | 🚚 **[รอบ 12 · CR-01]** `mdf compile` เขียน object `calendar` **รูปเดียว** ลงทั้ง bronze และ silver resolved JSON ของ dataset เดียวกัน (ค่าเหมือนกันทุก byte): `status` (`COMPLETE \| PENDING_OWNER`), `schedule_type`, `timezone`, `expected_at`, `expected_day_offset`, `effective_from`, `effective_to`, `holidays`, `explicit_dates`, `exceptions`, `day_of_month`, `day_of_month_policy`, `missing_after_seconds`, `recovery_window_seconds`, `frequency` · ค่าที่ไม่มีเป็น `null` (ไม่ตัด key ทิ้ง) · list เรียงจากน้อยไปมาก · `missing_after_seconds` = latency เป็นวินาที (ปัจจุบัน 14400) · `recovery_window_seconds` = 172800 · runtime ไม่ต้อง parse ODCS เอง | P0 | CR-01 | deterministic ตาม FR-D.5 · นิยามเวลา: missing = expected instant + `missing_after_seconds` · หยุด poll อัตโนมัติ = expected instant + `recovery_window_seconds` (ใช้ใน Phase 3 FR-I.2)

<a id="fr-m-4"></a>

### FR-M.4
Source backup lines 798–798; apply effective precedence above.

FR-M.4 | 🚚 **[รอบ 12 · Q2 = (b)]** ถ้า contract ยังไม่มีค่าจากเจ้าของข้อมูล (`expected_at`, `expected_day_offset`, `timezone` หรือ `business_schedule` ขาด**ทั้งชุดหรือบางตัว**) → `mdf validate` เป็น **warning** `[CALENDAR_PENDING_OWNER]` (ไม่ fail) · compile เขียน `calendar.status: PENDING_OWNER` พร้อมค่าที่ขาดเป็น `null` (ค่าที่มีอยู่จริง เช่น latency/recovery ยังคำนวณ) · `--release` gate ผ่านได้แต่ต้องพิมพ์ `[WARN] calendar PENDING_OWNER: <dataset,…>` · Job Summary + release notes ของ `release.yml` แสดงรายชื่อ dataset ที่ยัง pending · ค่าที่มี**แต่ผิดรูปแบบ** (FR-M.2) = error เสมอ ไม่ใช่ warning | P0 | D-P5-12 Q2; AS-30 | runtime Phase 3 ต้องปฏิเสธ arrival/pending logic ของ dataset ที่ `PENDING_OWNER` (FR-I.2 · R-27) · ห้าม compiler หรือ runtime เติมค่าเอง

<a id="fr-m-5"></a>

### FR-M.5
Source backup lines 799–799; apply effective precedence above.

FR-M.5 | 🚚 **[รอบ 12 · CR-01 ส่วนเพิ่มเติม]** `mdf compile` เขียน object `reader` ลงทั้ง bronze และ silver: `format` (จาก `servers[]` ตัวที่ `environment` = env ที่ compile), `file_pattern`, `partition_pattern`, `header`, `encoding`, `run_grain`, `source_type` (จาก `customProperties` ของ contract) · `file_pattern` คง template `{{business_date}}` และ `*` ตามต้นฉบับ (เช่น `credit_card_txn_{{business_date}}*.csv` ที่ตั้งใจรับ `.late.csv`) · ไม่มี server ของ env นั้น หรือไม่มี `file_pattern` → validate error | P0 | D-P5-12; FR-D.3 (reader options ที่ยังไม่ถูก compile) | `landing` (path) คงเดิม · `erasure_target` ไม่อยู่ในรอบนี้

<a id="fr-m-6"></a>

### FR-M.6
Source backup lines 800–800; apply effective precedence above.

FR-M.6 | 🚚 **[รอบ 12 · CR-02 ส่วน compile ธง]** `schema[]` ใน resolved JSON (ทั้ง bronze/silver) เพิ่ม `pii` (bool), `pci` (bool) จาก `customProperties` ของคอลัมน์ และ `tags` (list ตามลำดับใน contract · ไม่มี = `[]`) · `classification` คงเดิม · คอลัมน์ที่ไม่มี `pii` หรือ `pci` เป็น boolean → validate error (ทุกคอลัมน์ `cc` มีครบอยู่แล้ว) · **P1:** `pci: true` แต่ pipeline ไม่ได้ตั้ง `columns.<col>.tokenise: true` → error (กฎ `C-PCI-TOKENISE` ที่เสนอไว้ใน §3 Validator rule JSON) | P0 (P1 สำหรับ C-PCI-TOKENISE) | D-P5-12; CR-02 | **ไม่อยู่ในรอบนี้ (Q5 = เก็บไว้ก่อน):** protection action, การเลิก tokenise `national_id`/`full_name`, mask `*`, governed view ของ `birth_date`, token namespace/key_ref → ⏭️ Phase 3 (OQ-P1-12) · pipeline ของ customer **ไม่เปลี่ยน**

<a id="fr-m-7"></a>

### FR-M.7
Source backup lines 801–801; apply effective precedence above.

FR-M.7 | 🚚 **[รอบ 12 · CR-06]** `mdf package` เขียน **`manifest_version: 3`** · ทุก entry ใน `files[]` มี `path`, `sha256`, `kind` (`resolved_config \| odcs_contract`), `source`, `dataset` และ `layer` (เฉพาะ `resolved_config`) · contract ของแต่ละ dataset ถูกคัดลอกเข้า package ที่ `<source>/<dataset>.odcs.yaml` (bytes เดียวกับไฟล์ใน git ที่ checkout ด้วย `eol=lf`) · package `cc` = 9 entry (resolved 6 + contract 3) · `file_count` = จำนวน `files[]` · resolved JSON ทุกไฟล์เพิ่ม `lineage.contract_bundle_path` (เช่น `cc/customer.odcs.yaml`) · `files[]` เรียงตาม path · `manifest.json`/`validation-report.json` อยู่รากเหมือนเดิม | P0 | D-P5-12; CR-06 | แทนที่ FR-F.7 ส่วน `manifest_version: 2` สำหรับ release ใหม่ (layout `<source>/` คงเดิม) · `kind` ระบุชัด ห้ามเดาจากนามสกุลไฟล์

<a id="fr-m-8"></a>

### FR-M.8
Source backup lines 802–802; apply effective precedence above.

FR-M.8 | 🚚 **[รอบ 12 · CR-06]** `verify-package` รองรับ v3 โดยใช้กติกา v2 ทั้งหมด (traversal, ลึกเป๊ะ 2 segment, recursive extra-file/โฟลเดอร์ว่าง, segment แรก = source) **และเพิ่ม:** (1) `kind` ต้องอยู่ใน whitelist · (2) ชื่อไฟล์ต้องตรงกับ `kind` (`{layer}.{source}.{dataset}.resolved.json` หรือ `{dataset}.odcs.yaml`) และตรงกับ field `source`/`dataset`/`layer` · (3) ทุก dataset ต้องมี contract 1 + bronze 1 + silver 1 พอดี · (4) `lineage.contract_sha256` ของ resolved ทุกไฟล์ = sha256 ของ contract ที่แนบมา และ `lineage.contract_bundle_path` = path ของมัน · ผิดข้อใด → `[TAMPERED]` · v1 (เตือน legacy) และ v2 ยังผ่านตามเดิม · `manifest_version` อื่น (เช่น 4) → fail | P0 | D-P5-12; CR-06 | แทนที่ AC-48 ส่วน "`manifest_version: 3` (ไม่รู้จัก) → fail" (3 กลายเป็นเวอร์ชันที่รู้จักแล้ว ใช้ 4 แทน) · **v2 ไม่มีคำเตือนใหม่** (AS-33)

<a id="fr-m-9"></a>

### FR-M.9
Source backup lines 803–803; apply effective precedence above.

FR-M.9 | 🚚 **[รอบ 12]** ทางส่งของทุก mode ใช้กับ v3 ได้: `scripts/deliver_release.sh` CD-3 คัดลอกทุก path ใน `files[]` (รวม `.yaml`) ก่อน `manifest.json` · job `mdf_release_register_dev` ใช้ `verify_package` ตัวเดียวกัน · `sql/manual/register_release.sql` ตรวจไฟล์ `.yaml` ใน subfolder ได้ (path เต็มเทียบ manifest · ทำต่อจาก T-51) · `scripts/next_steps.py` + runbook M-3 อ้างจำนวนไฟล์จาก manifest ไม่ hardcode "6 × `*.resolved.json`" (`scripts/next_steps.py:80`) และบอกให้อัปโหลด `.odcs.yaml` เข้า `<source>/` ด้วย · zip asset (FR-L.1a) ไม่เปลี่ยนกติกา | P0 | D-P5-12; FR-L.4a, FR-L.13, FR-L.14 | ไม่แก้ release เดิม (v1/v2 ไม่ migrate · D-P5-11 Q4)

<a id="nfr-1"></a>

### NFR-1
Source backup lines 209–209; apply effective precedence above.

NFR-1 | Maintainability | Python 3.11, ฟังก์ชันสั้น, มี type hint, ไม่มี metaclass / DI / abstraction หลายชั้น | Junior อ่านโมดูลหลักแล้วเข้าใจภายใน 1 ชั่วโมง · ไม่มีฟังก์ชันใดยาวเกิน ~40 บรรทัด (Proposed)

<a id="nfr-10"></a>

### NFR-10
Source backup lines 218–218; apply effective precedence above.

NFR-10 | **⏭️ [Phase 3]** Idempotency | รัน job ซ้ำด้วย business_date เดิมแล้วผลไม่ซ้ำ (replaceWhere รายวัน / SCD2 แทนที่ version ของวันนั้น) · deploy ซ้ำไม่สร้าง object ซ้ำ | AC-22

<a id="nfr-11"></a>

### NFR-11
Source backup lines 219–219; apply effective precedence above.

NFR-11 | **⏭️ [Phase 3]** Backfillability | ทุกขั้นตอน backfill ได้ทุกวันภายใน 1825 วัน ลำดับไหนก็ได้ ได้ผลเท่ากับรันตามเวลาปกติ (นิยามใน §Backfill model) · **[รอบ 12 · D-P5-12 Q6] แทนที่บางส่วน:** run ตามรอบ (scheduled/retry) ที่เจอวันเก่ากว่าวันที่ commit แล้วใน silver = **block + quarantine `BLOCKED_DATE`** แล้วให้ **คนสั่ง backfill เป็นช่วงวัน** (ไม่เริ่มเอง) · "ลำดับไหนก็ได้" เหลือเฉพาะ backfill ที่คนสั่ง · ผลต้องเท่ากับรันตามเวลาปกติเหมือนเดิม → CONFLICT-18 | AC-26…30

<a id="nfr-2"></a>

### NFR-2
Source backup lines 210–210; apply effective precedence above.

NFR-2 | Determinism | Compile ซ้ำได้ bytes เดิม | AC-11

<a id="nfr-3"></a>

### NFR-3
Source backup lines 211–211; apply effective precedence above.

NFR-3 | Portability | Windows 10 (git-bash) และ Linux CI ได้ hash เดียวกัน | `.gitattributes eol=lf` + normalise CRLF ก่อน hash · AC-11 รันบนทั้งสองระบบ

<a id="nfr-4"></a>

### NFR-4
Source backup lines 212–212; apply effective precedence above.

NFR-4 | **◐ [Phase 1 ไม่มี pyspark · group `runtime` → Phase 3]** Dependencies | Core มีแค่ `pyyaml`, `jsonschema` · `pyspark`/`delta-spark` เป็น optional group `runtime` เท่านั้น | `uv sync --locked` ผ่าน · wheel ของ core ไม่ดึง pyspark

<a id="nfr-5"></a>

### NFR-5
Source backup lines 213–213; apply effective precedence above.

NFR-5 | Security | ไม่มี secret หรือ token ในไฟล์ใด ๆ · เก็บแค่ secret reference | CI มี secret scan แบบง่าย (grep pattern) + review

<a id="nfr-6"></a>

### NFR-6
Source backup lines 214–214; apply effective precedence above.

NFR-6 | **◐ [Phase 1 = static เท่านั้น]** Honesty of evidence | Static validation ห้ามอ้างว่าพิสูจน์ DQ ของข้อมูลจริงได้ · runtime test ที่ skip ต้องแสดงว่า skip | Report แยก "static" / "runtime"

<a id="nfr-7"></a>

### NFR-7
Source backup lines 215–215; apply effective precedence above.

NFR-7 | Usability (BA) | Error มีไฟล์ / field / สาเหตุ / วิธีแก้ เป็นภาษาไทย | AC-01

<a id="nfr-8"></a>

### NFR-8
Source backup lines 216–216; apply effective precedence above.

NFR-8 | Performance | validate + compile ของ 3 dataset (gold → Phase 3) | ≤ 10 วินาทีบนเครื่อง dev (AS-8)

<a id="nfr-9"></a>

### NFR-9
Source backup lines 217–217; apply effective precedence above.

NFR-9 | Language | สื่อสารเป็นภาษาไทย · code / comment / ชื่อไฟล์เป็นภาษาอังกฤษ · `message`/`fix` ของ rule เป็นภาษาไทย | –

<a id="oq-p1-11"></a>

### OQ-P1-11
Source backup lines 716–716; apply effective precedence above.

OQ-P1-11 | P1 | ส่วนต่อท้าย landing `files/{dataset}/` (DC-11r) | ผู้ใช้ | No

<a id="oq-p1-12"></a>

### OQ-P1-12
Source backup lines 1318–1318; apply effective precedence above.

OQ-P1-12 | **⏭️ [Phase 3]** P1 | PII ที่ไม่ tokenise (email, phone, birth_date) จะจัดการอย่างไร | ผู้ใช้ / DPO | No (ส่วน ABAC ของโปรเจกต์ Phase 3)

<a id="oq-p1-14"></a>

### OQ-P1-14
Source backup lines 1319–1319; apply effective precedence above.

OQ-P1-14 | **⏭️ [Phase 3]** P1 | Bronze เก็บเป็น string (AS-11) โอเคไหม | ผู้ใช้ | No

<a id="oq-p1-17"></a>

### OQ-P1-17
Source backup lines 1320–1320; apply effective precedence above.

OQ-P1-17 | **⏭️ [Phase 3]** P1 | ไฟล์ master เป็น full snapshot หรือส่งแค่ที่เปลี่ยน · ต้องจับการลบไหม (AS-14) | ผู้ใช้ / ต้นทาง | No

<a id="oq-p1-18"></a>

### OQ-P1-18
Source backup lines 1321–1321; apply effective precedence above.

OQ-P1-18 | **⏭️ [Phase 3]** P1 | SCD2 ไม่บีบ version (AS-15) โอเคไหม | ผู้ใช้ / DE | No

<a id="oq-p1-19"></a>

### OQ-P1-19
Source backup lines 1322–1322; apply effective precedence above.

OQ-P1-19 | **⏭️ [Phase 3]** P1 | txn_id ซ้ำข้ามวัน = flag (AS-16) | ผู้ใช้ / DE | No

<a id="oq-p1-2"></a>

### OQ-P1-2
Source backup lines 711–711; apply effective precedence above.

OQ-P1-2 | P1 | Control file แบบ AS-4 โอเคไหม | ผู้ใช้ | No

<a id="oq-p1-20"></a>

### OQ-P1-20
Source backup lines 1323–1323; apply effective precedence above.

OQ-P1-20 | **⏭️ [Phase 3]** P1 | Delta retention 30 วัน (AS-17) | ผู้ใช้ / Platform | No

<a id="oq-p1-21"></a>

### OQ-P1-21
Source backup lines 1324–1324; apply effective precedence above.

OQ-P1-21 | **⏭️ [Phase 3]** P1 | ผลของ erasure ต่อแถว (AS-19) | ผู้ใช้ / DPO | No

<a id="oq-p1-22"></a>

### OQ-P1-22
Source backup lines 1325–1325; apply effective precedence above.

OQ-P1-22 | **⏭️ [Phase 3]** P1 | CONFLICT-17: master missing วัน D → fact/gold วัน D รันต่อด้วย master as-of D หรือข้ามทั้งสาย | ผู้ใช้ | ต้องตอบก่อนเริ่ม Phase 3

<a id="oq-p1-23"></a>

### OQ-P1-23
Source backup lines 1326–1326; apply effective precedence above.

OQ-P1-23 | **⏭️ [Phase 3]** P1 | แถวที่ FK หา parent ไม่เจอ (data defect · D-P4-7 ข): ระหว่างรอ source แก้ → quarantine หรือ flag + FK = NULL · เก็บค่าเดิมไว้ไล่ย้อนไหม · ใครแจ้ง BA และอย่างไร | ผู้ใช้ / BA | ต้องตอบก่อนเริ่ม Phase 3

<a id="oq-p1-3"></a>

### OQ-P1-3
Source backup lines 712–712; apply effective precedence above.

OQ-P1-3 | P1 | ตำแหน่ง `config/rules/*.json` | ผู้ใช้ | No

<a id="oq-p1-5"></a>

### OQ-P1-5
Source backup lines 713–713; apply effective precedence above.

OQ-P1-5 | P1 | Cross-file rule แบบ AS-5 | ผู้ใช้ | No

<a id="oq-p1-8"></a>

### OQ-P1-8
Source backup lines 714–714; apply effective precedence above.

OQ-P1-8 | P1 | ชื่อ GitHub team | ผู้ใช้ | No (E4 ใช้ example)

<a id="oq-p1-9"></a>

### OQ-P1-9
Source backup lines 715–715; apply effective precedence above.

OQ-P1-9 | P1 | จำนวน source/dataset ที่คาดไว้ | ผู้ใช้ | No

<a id="oq-p2-2"></a>

### OQ-P2-2
Source backup lines 717–717; apply effective precedence above.

OQ-P2-2 | P2 | Schema ของ run_log (`ops`) | – | No

<a id="oq-p2-3"></a>

### OQ-P2-3
Source backup lines 718–718; apply effective precedence above.

OQ-P2-3 | P2 | API `load_dataset()` + getter (DRAFT1:66) | – | No

<a id="oq-p2-4"></a>

### OQ-P2-4
Source backup lines 719–719; apply effective precedence above.

OQ-P2-4 | P2 | Extension fields สำหรับ AI ในโปรเจกต์ Phase 3 | – | No

<a id="oq-p2-5"></a>

### OQ-P2-5
Source backup lines 720–720; apply effective precedence above.

OQ-P2-5 | P2 | DRAFT1 §1 "ปัญหาที่ต้องการแก้" ที่ว่างอยู่ (เนื้อหาเดิมอยู่ใน backup) | ผู้ใช้ | No

<a id="oq-p2-6"></a>

### OQ-P2-6
Source backup lines 1327–1327; apply effective precedence above.

OQ-P2-6 | **⏭️ [Phase 3]** P2 | Measures ของ gold (Proposed: `txn_count`, `approved_amount`) | ผู้ใช้ / DE | No

<a id="oq-p2-7"></a>

### OQ-P2-7
Source backup lines 721–721; apply effective precedence above.

OQ-P2-7 | P2 | Status ที่อนุญาตให้ release | – | No

<a id="oq-p2-8"></a>

### OQ-P2-8
Source backup lines 1328–1328; apply effective precedence above.

OQ-P2-8 | **⏭️ [Phase 3]** P2 | Gold อ่านแถว `is_trusted=false` ด้วยไหม | ผู้ใช้ / DE | No

<a id="oq-p2-9"></a>

### OQ-P2-9
Source backup lines 722–722; apply effective precedence above.

OQ-P2-9 | P2 | Action ของ validValues (Proposed: reject) | ผู้ใช้ / DE | No

<a id="oq-p5-1"></a>

### OQ-P5-1
Source backup lines 1029–1029; apply effective precedence above.

OQ-P5-1 | 🚚 **P0 ของ Phase 2** | workspace ที่จะใช้เป็นแบบไหน (Free Edition / Databricks แบบเสียเงินบน Azure หรือ AWS) และ host จริงคืออะไร · คุณเป็น account admin ที่สร้าง federation policy ได้ไหม (`config/env/dev.yaml` ตอนนี้เป็น `https://adb-dev.azuredatabricks.net`) | ผู้ใช้ | **Yes สำหรับ T-40/T-41** (ไม่ block T-35…T-39)

<a id="oq-p5-10"></a>

### OQ-P5-10
Source backup lines 1038–1038; apply effective precedence above.

OQ-P5-10 | 🚚 P1 · รอบ 12 | ค่า calendar จริงของ `customer`, `credit_card`, `credit_card_txn`: `expected_at` (HH:MM), `expected_day_offset`, timezone, ประเภท schedule (+ holidays / explicit dates ถ้ามี) และยืนยัน `recovery_window` 2 วัน (AS-31) | ผู้ใช้ / เจ้าของข้อมูล | **No สำหรับรอบ 12** (ใช้ `PENDING_OWNER` · AS-30) · **Yes สำหรับ Phase 3** arrival/pending logic (FR-I.2)

<a id="oq-p5-2"></a>

### OQ-P5-2
Source backup lines 1030–1030; apply effective precedence above.

OQ-P5-2 | 🚚 P1 | ถ้า WIF ไม่ได้: ใช้ manual copy อย่างเดียว (ตาม D-P5-6) หรืออนุญาต PAT อายุสั้นใน GitHub Environment เป็นทางสำรองที่สอง | ผู้ใช้ | No (ค่าตั้งต้น = manual)

<a id="oq-p5-3"></a>

### OQ-P5-3
Source backup lines 1031–1031; apply effective precedence above.

OQ-P5-3 | 🚚 P1 | Trigger ของ release: ทุก push `master` (AS-22) หรือเฉพาะ tag | ผู้ใช้ | No

<a id="oq-p5-4"></a>

### OQ-P5-4
Source backup lines 1032–1032; apply effective precedence above.

OQ-P5-4 | 🚚 P1 | ตาราง Delta ที่ "append": registry อย่างเดียว (AS-23) หรือเก็บ resolved config ทั้งก้อนลงตารางด้วย | ผู้ใช้ | No

<a id="oq-p5-5"></a>

### OQ-P5-5
Source backup lines 1033–1033; apply effective precedence above.

OQ-P5-5 | 🚚 P1 · รอบ 10 | (ก) ตั้ง mode ในไฟล์ `config/env/dev.yaml` ผ่าน PR (AS-26) ใช้ได้ไหม (ข) mode 3 = เบราว์เซอร์ + SQL สำเร็จรูป (AS-27) ใช่ไหม | ผู้ใช้ | No (ใช้ค่าตั้งต้นไปก่อน)

<a id="r-1"></a>

### R-1
Source backup lines 686–686; apply effective precedence above.

R-1 | Library / validator DSL ใหญ่ขึ้นจนดูแลยาก (DRAFT2 เตือนไว้) | M | M | จำกัด `kind` (sql/function) และ operator set, ไม่มี eval, self-check (FR-C.6), มี test ต่อกฎ

<a id="r-10"></a>

### R-10
Source backup lines 1292–1292; apply effective precedence above.

R-10 | **⏭️ [Phase 3]** ไม่มีข้อมูลตัวอย่างจริง ทำให้ AC-21 ต้องใช้ synthetic | M | H | DEP-8, AS-12

<a id="r-11"></a>

### R-11
Source backup lines 1293–1293; apply effective precedence above.

R-11 | **⏭️ [Phase 3]** DQ บน cleartext ก่อน tokenise (DC-7) ทำให้ต้องถือ cleartext ในหน่วยความจำนานขึ้น | L | M | Cleartext ไม่ถูกเขียนลงตารางใดนอกจาก bronze (ต้นทางอยู่แล้ว) และ vault

<a id="r-12"></a>

### R-12
Source backup lines 1294–1294; apply effective precedence above.

R-12 | **⏭️ [Phase 3]** Bronze เก็บทุกคอลัมน์เป็น string (FR-I.3) ต่างจาก DRAFT1 | L | L | CL-12 · ผู้ใช้ override ได้

<a id="r-13"></a>

### R-13
Source backup lines 691–691; apply effective precedence above.

R-13 | แก้ library ข้อเดียวกระทบหลาย dataset พร้อมกัน | H | M | DQ-6 + AC-24 + CODEOWNERS BU+DE + `library_version` และ `dq_library_sha256` ใน resolved config

<a id="r-14"></a>

### R-14
Source backup lines 1295–1295; apply effective precedence above.

R-14 | **⏭️ [Phase 3]** Rotate HMAC key แล้ว token เปลี่ยน ทำให้ join ข้ามวันและ backfill พัง | H | L | FR-I.17 block · runbook: rotate = rebuild ทั้งหมด (AS-18)

<a id="r-15"></a>

### R-15
Source backup lines 1296–1296; apply effective precedence above.

R-15 | **⏭️ [Phase 3]** Landing archive เก็บ cleartext PCI/PII 5 ปี และ erasure ไม่ลบไฟล์ใน archive | H | M | FR-J.7 จำกัดสิทธิ์ · FR-I.15 กันไม่ให้กลับเข้า vault/silver · ผู้ใช้ยอมรับ (D-P3-8) · DPO ต้องรับทราบ

<a id="r-16"></a>

### R-16
Source backup lines 1297–1297; apply effective precedence above.

R-16 | **⏭️ [Phase 3]** SCD2 ที่ไม่บีบ version (AS-15) + archive 1825 วันทำให้ storage โต (Free Edition มี quota) | M | M | วัด storage หลัง smoke test · เปลี่ยนเป็นบีบ version ได้ภายหลังแต่ต้อง rebuild SCD2

<a id="r-17"></a>

### R-17
Source backup lines 1298–1298; apply effective precedence above.

R-17 | **⏭️ [Phase 3]** Backfill ด้วย release เก่าไปเขียนตารางที่ schema เปลี่ยนแล้ว | M | M | FR-I.18 block พร้อมบอกคอลัมน์

<a id="r-18"></a>

### R-18
Source backup lines 1299–1299; apply effective precedence above.

R-18 | **⏭️ [Phase 3]** Cascade ของ master 1 วันอาจรัน downstream หลายร้อยวัน | M | L | `--no-cascade` + รายงานจำนวนวันก่อนรัน · FR-I.13 จำกัดช่วงวันตาม version ถัดไป

<a id="r-19"></a>

### R-19
Source backup lines 692–692; apply effective precedence above.

R-19 | Phase 1 ส่งมอบ resolved config ที่ยังไม่เคยถูก runtime อ่านจริง → Phase 3 อาจพบว่า config ขาด field | M | M | resolved JSON Schema + `schema_version` (FR-D) · Phase 3 เพิ่ม field ได้ด้วยการ bump `schema_version` · ห้ามอ้างว่า Phase 1 "รันบน Databricks ได้"

<a id="r-2"></a>

### R-2
Source backup lines 687–687; apply effective precedence above.

R-2 | Scope รอบนี้ใหญ่ (validator + compiler + package + CI + runtime + deploy) | H | H | แตก Epic ตามลำดับ dependency · E0–E4 ไม่ต้องใช้ Spark/cloud · E5/E6 ทำทีหลัง (ดู Readiness)

<a id="r-20"></a>

### R-20
Source backup lines 996–996; apply effective precedence above.

R-20 | 🚚 **[Phase 2]** Databricks Free Edition "No access to the account console or account-level APIs" (docs.databricks.com/aws/en/getting-started/free-edition-limitations) แต่ federation policy ต้องสร้างโดย account admin → WIF อาจทำไม่ได้บน Free Edition · `config/env/dev.yaml` ตอนนี้ชี้ `https://adb-dev.azuredatabricks.net` (ยังไม่รู้ว่าเป็น workspace จริงหรือ placeholder) | H | H (ถ้าเป็น Free Edition) | OQ-P5-1 ก่อนเริ่ม T-40 · ทางสำรอง FR-L.10 (D-P5-6) · ห้ามแอบใช้ PAT โดยผู้ใช้ไม่อนุญาต (OQ-P5-2)

<a id="r-21"></a>

### R-21
Source backup lines 997–997; apply effective precedence above.

R-21 | 🚚 **[Phase 2]** UC Volume ไม่ใช่ WORM ผู้มีสิทธิ์ WRITE VOLUME ลบ/แก้ไฟล์ได้ | M | L | สิทธิ์เขียนเฉพาะ SP ของ CD · runtime ตรวจ hash เทียบ registry ทุกครั้ง (FR-I.18) · registry append-only · **[รอบ 11]** ครอบคลุม subfolder `<source>/` ด้วย — verify-package แบบ recursive (FR-F.8) ตรวจได้ทั้งไฟล์ระดับรากและใน subfolder

<a id="r-22"></a>

### R-22
Source backup lines 998–998; apply effective precedence above.

R-22 | 🚚 **[Phase 2]** release ที่สร้างด้วย `GITHUB_TOKEN` ไม่ trigger workflow อื่น (`on: release`) → CD ไม่รันเอง | M | H | `deploy-dev.yml` เป็น `workflow_call` จาก release.yml + `workflow_dispatch` (FR-L.2)

<a id="r-23"></a>

### R-23
Source backup lines 999–999; apply effective precedence above.

R-23 | 🚚 **[Phase 2]** gap ของ Phase 1 ใน code: manifest ไม่มี `release_id`/`source_commit` (FR-F.2) และ gate ไม่ตรวจ dirty/status (FR-F.4) ทั้งที่ QA sign-off แล้ว | M | เกิดแล้ว | T-35 เป็นงานแรกของ Phase 2 · AC-35

<a id="r-24"></a>

### R-24
Source backup lines 1000–1000; apply effective precedence above.

R-24 | 🚚 **[Phase 2 · รอบ 10]** mode `manual`: อัปโหลดผ่าน Catalog Explorer อาจ **เขียนทับไฟล์เดิมโดยไม่ถาม** (ต่างจาก `fs cp`) · คนอาจลืมอัปโหลด manifest เป็นไฟล์สุดท้าย | H | M | M-1 เปิดโฟลเดอร์ก่อน: มี `manifest.json` แล้ว = **ห้ามอัปโหลด** ข้ามไป M-5 · `register_release.sql` ตรวจ hash ทุกไฟล์ในฝั่ง workspace จึงจับไฟล์ผิด/ขาดได้ก่อน INSERT · **[รอบ 11]** เพิ่มความเสี่ยง: คนอาจอัปโหลดไฟล์ `.json` ไว้ที่ราก (flat) แทนที่จะสร้างโฟลเดอร์ `<source>/` ก่อน → M-3 (รอบ 11) บังคับสร้างโฟลเดอร์ย่อย · **[รอบ 11 · รอบ 5]** เพิ่มความเสี่ยงใหม่: ผู้ใช้ manual แตก zip เองอาจแตกผิด (มีโฟลเดอร์ครอบชั้นนอกเพิ่ม เช่น เครื่องมือแตก zip บางตัวสร้างโฟลเดอร์ชื่อ zip ให้อัตโนมัติ) แล้วอัปโหลด path ผิดชั้น → mitigation: `register_release.sql` ตรวจ path เต็ม (`<source>/<file>`) เทียบ manifest ไม่ใช่แค่ basename จึงจับ flat-upload/ครอบซ้อนผิดที่ได้ (เหมือนเดิม) · runbook ต้องเตือนเรื่องโฟลเดอร์ครอบซ้อน

<a id="r-25"></a>

### R-25
Source backup lines 1001–1001; apply effective precedence above.

R-25 | 🚚 **[Phase 2 · รอบ 10]** mode `auto` พิสูจน์รันส่งจริงบน Free Edition ไม่ได้ (R-20) | M | เกิดแน่ | ปิดด้วย BUILD + preflight ที่ fail อย่างมีข้อความ (AS-28) · พิสูจน์จริงเมื่อมี workspace แบบเสียเงิน (OQ-P5-6)

<a id="r-26"></a>

### R-26
Source backup lines 1002–1002; apply effective precedence above.

R-26 | 🚚 **[Phase 2 · รอบ 12]** manifest v3 เปลี่ยนทางส่งของทุกจุดพร้อมกัน (package, verify, deliver, SQL manual, next_steps) — ถ้าแก้ไม่ครบ release ใหม่จะส่งไม่ได้ในบาง mode | H | M | T-56/T-57 ต้องมี test matrix v1/v2/v3 · รันจริงครั้งเดียวบน v3 ใน T-53 (Q3 = (a))

<a id="r-27"></a>

### R-27
Source backup lines 1003–1003; apply effective precedence above.

R-27 | 🚚 **[Phase 2 · รอบ 12]** release ออกไปพร้อม `calendar.status: PENDING_OWNER` นาน ๆ แล้ว runtime Phase 3 เผลอใช้ค่าตั้งต้นแทน | H | M | FR-M.4 ให้ค่าเป็น `null` + `status` ชัดเจน · Job Summary/release notes แสดงรายชื่อ pending · Phase 3 FR-I.2 ต้องปฏิเสธ dataset ที่ pending (ห้ามเดา)

<a id="r-28"></a>

### R-28
Source backup lines 1004–1004; apply effective precedence above.

R-28 | 🚚 **[Phase 2 · รอบ 12]** contract ที่แนบใน release มีชื่อ steward/email (ข้อมูลส่วนบุคคล) และ repo เป็น public | M | เกิดอยู่แล้วใน git | release ไม่เพิ่มข้อมูลที่ไม่อยู่ใน git อยู่แล้ว · การย้าย email ออกจาก contract = นอกขอบเขตรอบนี้ (บันทึกไว้ให้ผู้ใช้ตัดสินภายหลัง)

<a id="r-29"></a>

### R-29
Source backup lines 1005–1005; apply effective precedence above.

R-29 | 🚚 **[Phase 2 · รอบ 12 · OQ-TRI-12a]** ไม่ตรวจชื่อ IANA timezone → พิมพ์ผิด (เช่น `Asia/Bangkokk`) ผ่าน validate/release ได้ แล้วไปพังตอน runtime | M | L | ผู้ใช้ยอมรับ: ผู้เขียน contract ต้องใส่ให้ถูก · Phase 3 runtime ต้อง fail ทันทีพร้อมบอกชื่อ field เมื่อแปลง timezone ไม่ได้ (ห้าม fallback เป็น UTC)

<a id="r-3"></a>

### R-3
Source backup lines 1290–1290; apply effective precedence above.

R-3 | **⏭️ [Phase 3]** Local Spark บน Windows ต้องใช้ JDK/winutils | M | M | Test skip พร้อมเหตุผล + ใช้ CI (Linux) รัน runtime test (FR-I.10)

<a id="r-4"></a>

### R-4
Source backup lines 994–994; apply effective precedence above.

R-4 | 🚚 **[Phase 2]** Free Edition สร้าง catalog `dev_catalog` ไม่ได้ (default คือ `workspace`) | M | M | Catalog มาจาก control file (D-P0-9) เปลี่ยนที่เดียวจบ · DEP-2

<a id="r-5"></a>

### R-5
Source backup lines 995–995; apply effective precedence above.

R-5 | 🚚 **[Phase 2]** ตั้ง workload identity federation ไม่ได้ | M | M | FR-L.10 manual copy ด้วยสคริปต์เดียวกัน · ดู R-20

<a id="r-6"></a>

### R-6
Source backup lines 688–688; apply effective precedence above.

R-6 | กฎที่เปลี่ยนความหมาย (DC-1, DC-5) ทำให้ผลต่างจากเดิม | M | L | AC-08 ทดสอบผลที่เปลี่ยนแบบ explicit · ผู้ใช้ override ได้

<a id="r-7"></a>

### R-7
Source backup lines 689–689; apply effective precedence above.

R-7 | GitHub Release ถูกลบหรือแก้ได้โดยผู้มีสิทธิ์ | M | L | manifest sha256 + verify-package + จำกัดสิทธิ์ release · เขียนข้อจำกัดไว้ในเอกสาร

<a id="r-8"></a>

### R-8
Source backup lines 1291–1291; apply effective precedence above.

R-8 | **⏭️ [Phase 3]** Cleartext PII หลุดไปใน quarantine หรือ log | H | M | BR-20 + AC-20

<a id="r-9"></a>

### R-9
Source backup lines 690–690; apply effective precedence above.

R-9 | Branch protection / CODEOWNERS ยังไม่ได้ตั้ง แต่ถูกเข้าใจว่าบังคับใช้แล้ว | M | M | ใช้ไฟล์ `.example` + ระบุในเอกสารว่า "ยังไม่ได้บังคับใช้"

<a id="t-04"></a>

### T-04
Source backup lines 1264–1264; apply effective precedence above.

T-04 | **⏭️ [Phase 3]** Gold ตัวอย่าง `_gold/card/fct_daily_spend_by_segment.{gold.yaml,sql}` | Data | T-03 | validate ผ่าน

<a id="t-18"></a>

### T-18
Source backup lines 1265–1265; apply effective precedence above.

T-18 | **⏭️ [Phase 3]** Runtime: config reader (+ `--release-id`) + arrival (scheduled/backfill) + bronze replaceWhere + rebuild จาก landing | Code | T-10 | test local หรือ skip พร้อมเหตุผล · AC-22 (bronze)

<a id="t-19"></a>

### T-19
Source backup lines 1266–1266; apply effective precedence above.

T-19 | **⏭️ [Phase 3]** Runtime: DQ executor (`kind: sql` + function registry: luhn, fk_exists, cast_ok) | Code | T-18 | AC-08, AC-09

<a id="t-20"></a>

### T-20
Source backup lines 1267–1267; apply effective precedence above.

T-20 | **⏭️ [Phase 3]** Runtime: tokenise + vault (HMAC) + quarantine | Code | T-19 | AC-20

<a id="t-21"></a>

### T-21
Source backup lines 1268–1268; apply effective precedence above.

T-21 | **⏭️ [Phase 3]** Runtime: derived, dedup, SCD2 master, replaceWhere fact, FK as-of + defect flag (OQ-P1-23), pass-rate gate | Code | T-20 | AC-21, AC-22, AC-27

<a id="t-22"></a>

### T-22
Source backup lines 1269–1269; apply effective precedence above.

T-22 | **⏭️ [Phase 3]** Runtime: gold SQL + run_log | Code | T-21 | AC-21 (gold), FR-I.9

<a id="t-23"></a>

### T-23
Source backup lines 1270–1270; apply effective precedence above.

T-23 | **⏭️ [Phase 3]** Synthetic CSV ตาม REALITY (ถ้าผู้ใช้ไม่ส่งมา) | Data | T-03 | ครอบคลุม REALITY ทุกบรรทัด

<a id="t-24"></a>

### T-24
Source backup lines 1271–1271; apply effective precedence above.

T-24 | **⏭️ [Phase 3]** (`databricks.yml` สร้างใน T-38) `resources/cc.job.yml` (params mode/from/to/release_id/cascade, max_concurrent 1) + `mdf_replay_dev` + UC setup SQL (idempotent, table properties, grants) | Deploy | T-14, T-22 | `databricks bundle validate -t dev` ผ่าน (ไม่ต้อง deploy)

<a id="t-25"></a>

### T-25
Source backup lines 1272–1272; apply effective precedence above.

T-25 | **⏭️ [Phase 3]** ขยาย `deploy-dev.yml` ให้ deploy `mdf_cc_dev` + smoke medallion query `run_log` | Deploy | T-40, T-24, DEP-4 | **HG_PROD** → AC-23

<a id="t-30"></a>

### T-30
Source backup lines 1273–1273; apply effective precedence above.

T-30 | **⏭️ [Phase 3]** Runtime: backfill range + cascade + run_log fields (input sha256, table versions, parent_run_id) | Code | T-22 | AC-26, AC-28

<a id="t-31"></a>

### T-31
Source backup lines 1274–1274; apply effective precedence above.

T-31 | **⏭️ [Phase 3]** Runtime: erasure list + HMAC key version guard | Code | T-20 | AC-30, FR-I.17

<a id="t-32"></a>

### T-32
Source backup lines 1275–1275; apply effective precedence above.

T-32 | **⏭️ [Phase 3]** Runtime: replay (RESTORE) + guards | Code | T-30 | AC-32

<a id="t-33"></a>

### T-33
Source backup lines 1276–1276; apply effective precedence above.

T-33 | ~~Deploy: release volume (ไม่ทับ/ไม่ลบ)~~ → รวมเข้า T-39 (🚚 Phase 2) · backfill runbook → ⏭️ Phase 3 | Docs | T-30 | AC-29

<a id="x-1"></a>

### X-1
Source backup lines 1092–1092; apply effective precedence above.

X-1 | release ถูก deploy ถึง `{catalog}.ops.release_registry` **ได้จริง** | query registry: `REGISTERED` + `ACTIVATED` ที่ `manifest_sha256` ตรงกับ GitHub Release (มีแล้วจาก T-41/T-42 ด้วย `u2m`)

<a id="x-2"></a>

### X-2
Source backup lines 1093–1093; apply effective precedence above.

X-2 | ผู้ใช้ตั้ง mode ได้ 3 แบบ | AC-43

<a id="x-3"></a>

### X-3
Source backup lines 1094–1094; apply effective precedence above.

X-3 | mode `u2m` ส่งได้จริง | AC-37 (มีแล้ว) + AC-43 ข้อ And

<a id="x-4"></a>

### X-4
Source backup lines 1095–1095; apply effective precedence above.

X-4 | mode `manual` ส่งได้จริงโดยไม่มี CLI | AC-44

<a id="x-5"></a>

### X-5
Source backup lines 1096–1096; apply effective precedence above.

X-5 | mode `auto` พร้อมใช้เมื่อมี workspace ที่ไม่ใช่ Free Edition | AC-41 + preflight ของ T-46 (3) · ส่งสำเร็จจริง = ตาม OQ-P5-6

<a id="x-6"></a>

### X-6
Source backup lines 1097–1097; apply effective precedence above.

X-6 | ผู้ใช้รู้ขั้นต่อไปทุก mode | AC-45

<a id="x-7"></a>

### X-7
Source backup lines 1098–1098; apply effective precedence above.

X-7 | **[รอบ 11 · เติมแถวที่ §1 อ้างแต่ตารางนี้ยังไม่มี · พบรอบ 12]** release ใหม่เป็น layout v2 per-source และส่งถึง registry ได้จริง | AC-46…51 + T-53

<a id="x-8"></a>

### X-8
Source backup lines 1099–1099; apply effective precedence above.

X-8 | **[รอบ 12]** release ใหม่เป็น manifest v3 ที่มี ODCS YAML + `calendar`/`reader`/ธง privacy ใน resolved JSON และส่งถึง registry ได้จริง | AC-52…57 + AC-58 (รันจริงรวมใน T-53)

## Data entities / security boundary (no standalone requirement IDs)

Source backup lines 223–273 (source/entity definitions), 307–323 (security); apply precedence above.

#### Data Sources

| Source | Owner | Access Method | Refresh Frequency | Reliability/Notes |
|---|---|---|---|---|
| `cc` — customer | steward `<steward>` · owner `source-system-owner` (placeholder) | CSV (header, utf-8) วางลง UC Volume `/Volumes/{catalog}/landing_cc/files/customer/` · `customer_{{business_date}}.csv` | daily · grace 4h | REALITY: national_id `"123"`, full_name ว่าง, birth_date อยู่ในอนาคต, customer_id ซ้ำในไฟล์เดียวกัน |
| `cc` — credit_card | เหมือนข้างบน | `.../credit_card/` · `credit_card_{{business_date}}.csv` | daily · grace 4h | REALITY: PAN มีช่องว่าง, `CUST999999` (FK ไม่มีอยู่จริง), `'UNLIMITED'`, ไฟล์ของ 2026-09-10 **ไม่มา** |
| `cc` — credit_card_txn | เหมือนข้างบน | `.../credit_card_txn/` · `credit_card_txn_{{business_date}}*.csv` (glob รับไฟล์ `.late.csv` ด้วย) | daily · grace 4h | REALITY: PAN ไม่มีใน master, txn_timestamp ว่าง, APPROVED ที่ amount ≤ 0, ไฟล์ของ 2026-09-11 **มาช้า** (ภายใน grace) |
| Gold `card` | **⏭️ [Phase 3]** DE (Proposed) | อ่านจาก silver 3 ตาราง | ตาม run ของ cc | อ่านแค่แถวที่ trusted? → OQ-P2-8 |

⚠️ ไฟล์ข้อมูลตัวอย่าง (CSV) **ไม่มีใน repo** → Dependency DEP-8 (ต้องใช้สำหรับ smoke test / runtime test)

#### Data Entities and Fields

| Entity/Table | Field | Description | Data Type (logical / physical) | Required | PII/Sensitive | Source |
|---|---|---|---|---|---|---|
| cc.customer | customer_id | PK | string / string | ✓ | – | contract |
| cc.customer | national_id | เลขบัตรประชาชน (tokenise) | string / string | ✓ | PII · sensitive | contract |
| cc.customer | full_name | ชื่อเต็ม (tokenise) | string / string | ✓ | PII · sensitive | contract |
| cc.customer | birth_date | วันเกิด | date / date | ✓ | PII · sensitive (**ไม่ tokenise** → OQ-P1-12) | contract |
| cc.customer | email | – | string / string | – | PII · personal (**ไม่ tokenise**) | contract |
| cc.customer | phone | – | string / string | – | PII · personal (**ไม่ tokenise**) | contract |
| cc.customer | registered_date | – | date / date | – | – | contract |
| cc.customer | customer_status | ACTIVE/DORMANT/CLOSED | string / string | ✓ | – | contract |
| cc.customer | business_date | partition 1 | date / date | ✓ | – | contract |
| cc.credit_card | card_pan | PK + business key (normalise + tokenise) | string / string | ✓ | PII + **PCI** | contract |
| cc.credit_card | customer_id | FK → cc.customer | string / string | ✓ | – | contract |
| cc.credit_card | card_type | VISA/MASTERCARD/AMEX | string / string | ✓ | – | contract |
| cc.credit_card | issue_date, expiry_date | – | date / date | ✓ | – | contract |
| cc.credit_card | credit_limit | – | number / decimal(18,2) | ✓ | – | contract |
| cc.credit_card | card_status | ACTIVE/BLOCKED/EXPIRED | string / string | ✓ | – | contract |
| cc.credit_card | business_date | partition 1 | date / date | ✓ | – | contract |
| cc.credit_card_txn | txn_id | PK | string / string | ✓ | – | contract |
| cc.credit_card_txn | card_pan | FK → cc.credit_card (normalise + tokenise) | string / string | ✓ | PII + **PCI** | contract |
| cc.credit_card_txn | txn_timestamp | – | **date / timestamp** (DC-6: ODCS ไม่มี logicalType timestamp) | ✓ | – | contract |
| cc.credit_card_txn | amount | – | number / decimal(18,2) | ✓ | – | contract |
| cc.credit_card_txn | currency | THB | string / string | ✓ | – | contract |
| cc.credit_card_txn | merchant_name, merchant_category | – | string / string | – | – | contract |
| cc.credit_card_txn | txn_status | APPROVED/DECLINED/REVERSED | string / string | ✓ | – | contract |
| cc.credit_card_txn | business_date | partition 1 | date / date | ✓ | – | contract |
| bronze.* | **⏭️ [Phase 3]** `_ingest_file_name, _ingest_row_number, _ingest_ts, _business_date, _run_id` | audit columns | string/long/timestamp/date/string | ✓ | – | DRAFT1 §9.2 |
| silver.* | **⏭️ [Phase 3]** `_is_trusted, _dq_flags` | flag ที่มาจาก DQ (**Proposed**) | boolean / array<string> | – | – | DRAFT1 §5:325 |
| quarantine.* | **⏭️ [Phase 3]** ทุกคอลัมน์ของ silver (ก่อน tokenise **ห้ามเก็บ cleartext PCI**) + `_rule_id, _reason, _run_id` | แถวที่ถูก reject | – | – | ⚠️ ต้อง tokenise ก่อนเขียน quarantine → BR-20 | Proposed |
| vault_cc.credit_card / customer | **⏭️ [Phase 3]** `token, cleartext, created_at` | mapping ของ HMAC | string | ✓ | **PCI / PII** | DRAFT1 §0 tokenise |
| gold_card.fct_daily_spend_by_segment | **⏭️ [Phase 3]** business_date, card_type, customer_status + measures | grain ตาม DRAFT1 §9.4 · **measures: Proposed `txn_count`, `approved_amount`** | date/string/string/long/decimal(18,2) | ✓ | – | OQ-P2-6 |
| ops.run_log | **⏭️ [Phase 3]** ดู FR-I.9 | log ของทุก step | – | ✓ | – | D-P0-4 |
| silver_cc.customer / credit_card (SCD2) | **⏭️ [Phase 3]** `_valid_from, _valid_to, _is_current, _row_hash` | ช่วงเวลาที่ version มีผล (FR-I.11) | date/date/boolean/string | ✓ | – | D-P3-6 |
| silver_cc.<master>_current (view) | **⏭️ [Phase 3]** ทุกคอลัมน์ ที่ `_is_current` | ไว้ให้ผู้ใช้ทั่วไป ห้ามใช้ใน pipeline | – | – | ตามตารางหลัก | FR-I.14 |
| ops.erasure_list | **⏭️ [Phase 3]** `dataset, key_column, token, erased_at, request_ref` | รายการที่ต้องลบ (เก็บเป็น token เท่านั้น) | string/string/string/timestamp/string | ✓ | ไม่มี cleartext | D-P3-8 |
| ops volume `files/releases/<release_id>/` | 🚚 **[Phase 2]** release package ทุกตัวที่เคยส่งถึง workspace · sealed เมื่อมี `manifest.json` · ห้ามทับ/ลบ | runtime อ่านตาม `--release-id` (Phase 3) | files | ✓ | – | D-P3-5, D-P5-6 |
| ops.release_registry | 🚚 **[Phase 2]** `release_id, event (REGISTERED\|ACTIVATED), source_commit, manifest_sha256, file_count, volume_path, github_release_url, ci_run_url, actor, event_ts` | บันทึก append-only ว่า release ไหนถูกส่งถึง/เปิดใช้ (managed Delta · `delta.appendOnly=true`) | string/string/string/string/int/string/string/string/string/timestamp | ✓ | – | D-P5-2 · Proposed (AS-23) |


### Security, Privacy & Access Control

| Area | Requirement | Risk Level | Owner / Decision Needed |
|---|---|---|---|
| PCI (card_pan) | **⏭️ [Phase 3]** normalise → HMAC-SHA256 tokenise → เก็บ cleartext ใน vault เท่านั้น · silver/gold/quarantine เก็บแค่ token | High | ชื่อ secret scope / key (DEP-4) |
| PII ที่ tokenise | **⏭️ [Phase 3]** national_id, full_name | High | – |
| PII ที่ **ไม่** tokenise | **⏭️ [Phase 3]** email, phone, birth_date | Medium | **OQ-P1-12** ใช้ column mask / ABAC หรือยอมรับความเสี่ยง? |
| Vault ownership | **⏭️ [Phase 3]** `credit_card` เป็นเจ้าของ vault ของ PAN · txn ใช้ key เดียวกัน (DC-10) | Medium | DPO (erasure) |
| Erasure | **⏭️ [Phase 3]** `erasure_target: vault` · ลบ cleartext ใน vault แล้ว token จะอ่านย้อนกลับไม่ได้ · **erasure list (token) กรองทุก run รวม backfill/replay** (FR-I.15) · vault/erasure_list ห้าม RESTORE | High | DPO — DRAFT1 §7:373, D-P3-8 |
| Landing raw archive (1825 วัน) | **⏭️ [Phase 3]** มี PAN / เลขบัตรประชาชน / PII แบบ cleartext 5 ปี (ผลของ D-P3-3) · อ่านได้แค่ SP ของ runtime + break-glass · write-once · bronze (cleartext 30/90 วัน) ใช้สิทธิ์เดียวกัน | High | ผู้ใช้/DPO ยอมรับ (D-P3-8) · ⚠️ erasure ไม่ลบไฟล์ใน archive (R-15) |
| Quarantine | **⏭️ [Phase 3]** ห้ามเก็บ cleartext PCI/PII ที่ต้อง tokenise (BR-20) | High | – |
| UC grants (Proposed) | **⏭️ [Phase 3]** runtime SP: เขียน bronze/silver/gold/quarantine/ops · `vault_*` จำกัดให้กลุ่มเดียว · humans: SELECT silver/gold | Medium | ชื่อ group / SP จริง (DEP-5) — **ห้ามเดา** |
| Secrets | ห้ามมี secret ในไฟล์ · GitHub Environment secrets + Databricks secret scope | High | ผู้ใช้ตั้งค่า |
| Repo governance | branch protection `master`, required checks (ci), required review, CODEOWNERS ป้องกัน `.github/`, `config/rules/`, `CODEOWNERS` เอง · ไม่มี bot bypass | Medium | ผู้ใช้ตั้งค่า (DEP-1) — ห้ามอ้างว่าบังคับใช้แล้วถ้ายังไม่ได้ตั้ง |
| Release integrity | sha256 ใน manifest + verify-package · hash ไม่ได้พิสูจน์ว่าใครเป็นคนสร้าง (attestation เป็น optional) | Low | – |
| Release volume + registry | 🚚 **[Phase 2]** SP ของ CD เท่านั้นที่ WRITE VOLUME `ops.files` และ MODIFY `ops.release_registry` · runtime / คน: READ · Volume ไม่ใช่ WORM → immutability มาจากกติกา CD-3 + สิทธิ์ (R-21) | Medium | ชื่อ SP (DEP-3 / DEP-5) |


## Phase 4 boundary

AI semantic layer/PII detection/classification/auto-suggest UC ABAC: backlog only; real UC ABAC attachment is Phase 3. No Phase 4 implementation ticket is authorized.
