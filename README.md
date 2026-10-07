# mdf — Metadata-driven Data Contract Framework (Phase 1)

> ตัวตรวจสอบ Data Contract + ตัวสร้าง config Bronze/Silver จาก metadata ใน Git (ไม่ต้องมี database)
> Python 3.11+ · uv · งบประมาณ Phase 1 = **฿0** (ทำงาน offline ทั้งหมด)

## สารบัญ

1. [ภาพรวม](#ภาพรวม)
2. [การติดตั้ง](#การติดตั้ง)
3. [คำสั่ง CLI](#คำสั่ง-cli)
4. [โครงสร้างโปรเจกต์](#โครงสร้างโปรเจกต์)
5. [การเพิ่มกฎ DQ](#การเพิ่มกฎ-dq)
6. [การทดสอบ](#การทดสอบ)
7. [Workflow ของทีม (swe-delivery-loop)](#workflow-ของทีม)
8. [Phase ถัดไป](#phase-ถัดไป)

## ภาพรวม

`mdf` อ่าน **Data Contract** (ODCS v3.0.2) และ **Pipeline metadata** จาก Git แล้ว:

```
DataContract/<src>/contract/*.odcs.yaml   ─┐
DataContract/<src>/pipeline/*.pipeline.yaml ─┤→ mdf validate → mdf compile → build/<env>/resolved/*.json
config/dq_library.yaml (กฎพื้นฐาน)          ─┤→                                  ↓
config/rules/*.rules.json (กฎเชิงโครงสร้าง)  ─┘                    mdf package → release package + manifest
```

หลักการสำคัญ (ยึดจาก SSOT `DocsForAgent/draft_reviewd_by_agent_v2.md`):

- **Metadata in Git only** — ไม่มี database, ไม่มี intermediate spec
- **Deterministic** — compile กี่ครั้งก็ได้ผล sha256 เดิม (AC-11)
- **REALITY oracle** — บรรทัด `# REALITY:` ใน contract คงเดิม byte-for-byte เพื่อใช้ทดสอบ (AC-17)
- **DQ model 3 ส่วน** — contract (tags) + dq_library (นิยามกฎ) + pipeline (BU rules)

## การติดตั้ง

ต้องมี [uv](https://docs.astral.sh/uv/) ก่อน แล้วรัน:

```bash
uv sync --locked        # ติดตั้ง dependencies ตาม lockfile
uv run mdf --help       # ตรวจว่าใช้งานได้
```

## คำสั่ง CLI

### `mdf validate` — ตรวจสอบทั้งโปรเจกต์

ตรวจ ODCS schema, กฎเชิงโครงสร้าง, DQ tags, FK references แล้วรายงานภาษาไทย

```bash
uv run mdf validate
# ✅ การตรวจสอบความถูกต้องผ่านเรียบร้อย (PASS)
```

### `mdf compile` — สร้าง resolved config

รวม contract + pipeline + dq_library + env/naming เป็น resolved JSON 1 ไฟล์ต่อตาราง

```bash
uv run mdf compile --env dev
# ✅ compile สำเร็จ: เขียน resolved JSON 6 ไฟล์ลง build/dev/resolved/
```

### `mdf diff` — ตรวจ breaking changes

เทียบ metadata ปัจจุบันกับ git baseline

```bash
uv run mdf diff --base 88b982d
# ❌ พบ BREAKING CHANGE 1 รายการ: ลบคอลัมน์ 'merchant_name' โดยไม่ bump major
```

### `mdf package` — สร้าง release package

```bash
uv run mdf package --env dev            # preview (ไม่บังคับ gate)
uv run mdf package --env dev --release  # บังคับ release gate (AC-16)
```

### `mdf verify-package` — ตรวจ tamper

```bash
uv run mdf verify-package build/dev/release
# ✅ package ผ่านการตรวจสอบ (OK): env=dev, files=6
```

### `mdf trace` — ดู lineage

```bash
uv run mdf trace silver.cc.credit_card_txn
# 📊 Lineage: dev_catalog.silver_cc.credit_card_txn
#    Contract: cc.credit_card_txn v1.0.0 (sha256 97bdbb…)
```

## โครงสร้างโปรเจกต์

```
├── DataContract/
│   ├── cc/                    # source: cc (credit card)
│   │   ├── contract/          # *.odcs.yaml — schema, SLA, landing
│   │   └── pipeline/          # *.pipeline.yaml — BU rules, derived, dedup
│   └── _template/             # เทมเพลตสำหรับ dataset ใหม่
├── config/
│   ├── dq_library.yaml        # นิยามกฎ DQ พื้นฐาน (SSOT)
│   ├── rules/                 # กฎ validator เชิงโครงสร้าง (JSON)
│   ├── env/dev.yaml           # ค่า environment (catalog, secret_scope)
│   ├── naming.yaml            # template ชื่อตาราง/path
│   └── schemas/               # ODCS v3.0.2 JSON Schema (pinned)
├── src/mdf/
│   ├── loading.py             # YAML loader + dataset discovery
│   ├── rules.py               # rule engine + self-check
│   ├── dq.py                  # DQ tag resolution
│   ├── validation.py          # static validator + รายงานภาษาไทย
│   ├── compile.py             # deterministic compiler
│   ├── trace.py               # lineage + orphan detector
│   ├── diff.py                # diff + blast radius
│   ├── package.py             # release package + tamper verifier
│   └── cli.py                 # command dispatcher
├── tests/                     # unit + E2E (90 tests)
├── .github/workflows/         # ci.yml (PR) + release.yml (push master)
├── build/                     # output (gitignored)
├── docs/                      # เอกสาร + index.html + archive/
└── README.md                  # ไฟล์นี้
```

## การเพิ่มกฎ DQ

**1. เพิ่มกฎพื้นฐานใน library** (`config/dq_library.yaml`) — แก้ YAML อย่างเดียว ไม่ต้องแก้ Python (AC-10):

```yaml
# config/dq_library.yaml
rules:
  thai_phone:
    description: "เบอร์โทรศัพท์ไทย 9-10 หลัก"
    kind: sql
    sql: "{col} IS NULL OR {col} RLIKE '^[0-9]{9,10}$'"
    default_action: reject
    enabled: true
```

**2. แปะ tag ใน contract:**

```yaml
# DataContract/cc/contract/customer.odcs.yaml
- name: phone
  tags: ["dq:thai_phone"]
```

**3. ตรวจผล:**

```bash
uv run mdf validate && uv run mdf compile
```

หมายเหตุ: กฎที่ต้องการพารามิเตอร์ (เช่น `pattern`) ต้องประกาศใน `params` และ contract ต้องมีค่านั้น — ไม่งั้นจะเจอ `TAG_WITHOUT_PARAM` (DQ-2)

## Calendar authoring

Calendar อยู่ใน ODCS `slaProperties` เท่านั้น: `schedule_type`, `day_of_month`,
`expected_at`, `business_date_lag`, `latency`, `recovery_window`.
ใช้ block พร้อมตัวอย่างใน `DataContract/_template/contract/my_dataset.odcs.yaml`.

- `schedule_type`: daily | workday | workday_excluding_holidays | monthly.
- `day_of_month`: 1–31 สำหรับ monthly; ไม่ใช่ monthly ให้ใส่ null.
- `expected_at`: "HH:MM" เวลาไทย; `business_date_lag`: จำนวนเต็ม <= 0 นับจากวันที่รัน
  (`business_date = วันที่รัน + lag`; 0 = ไฟล์ของวันที่รัน, -1 = ไฟล์ปิดยอดของเมื่อวาน / T-1).
- `latency` / `recovery_window`: ตัวเลข finite >= 0 พร้อม `unit: h` หรือ `d`.
- ไม่รู้ค่าให้ใส่ null: validate เตือน `CALENDAR_PENDING_OWNER` แต่ compile ได้.
  COMPLETE ต้องมี schedule_type, expected_at, business_date_lag, recovery_window
  (และ day_of_month สำหรับ monthly); latency ไม่บังคับสำหรับ COMPLETE.
- ตรวจเฉพาะรูปแบบของค่าที่ไม่ใช่ null; ไม่ตรวจเงื่อนไขข้ามฟิลด์.
  SLA entries ที่ไม่รู้จักถูกละเว้น; calendar key ใน customProperties ต้องย้ายไป slaProperties.
- ไม่มี frequency, timezone หรือรายการวันที่ใน calendar; Medallion คำนวณวันจาก mode
  และปฏิทินวันหยุดของ runtime เอง. เวลาทั้งหมดเป็นเวลาไทย.

`uv run mdf validate` → `uv run mdf compile --env dev` สร้าง calendar เดียวกันทั้ง
bronze/silver: status, schedule_type, day_of_month, expected_at, business_date_lag,
missing_after_seconds, recovery_window_seconds (h × 3600, d × 86400; null → null).
เพิ่มฟิลด์ชนิดที่รองรับ = เพิ่ม contract entry + หนึ่งบรรทัดใน `CALENDAR_FIELDS` เท่านั้น.

## การทดสอบ

```bash
uv run pytest              # ทั้งหมด 90 tests
uv run pytest tests/test_e2e.py   # E2E lifecycle เฉพาะ
uv run ruff check src tests      # lint
```

## Workflow ของทีม

โปรเจกต์นี้ใช้ **swe-delivery-loop** — ทุกการเปลี่ยนแปลงผ่าน HRM → SWE → QA:

- ดูสถานะปัจจุบัน: `logs/STATE.md`, `docs/index.html` (Workflow Live Status)
- ประวัติทุก event: `logs/checkpoint.jsonl` (append-only)
- หลักฐาน QA ต่อ Epic: `qa/E<n>/SIGNOFF.md`
- Governance: `.github/CODEOWNERS.example`, `docs/branch_protection.md`

## Phase ถัดไป

Phase 1 (static: นิยาม + validate + compile + package) ปิดแล้ว · ลำดับถัดไปตาม SSOT v2:

- **Phase 2 — Release delivery:** publish GitHub Release `mdf-<sha12>` → CD ดาวน์โหลด → `verify-package` → `/Volumes/{catalog}/ops/files/releases/<release_id>/` (immutable) → append `{catalog}.ops.release_registry` (SSOT §5)
- **Phase 3 — Medallion runtime:** PySpark bronze → silver → gold, DQ รันจริง, tokenise + vault, backfill (SCD2, replaceWhere, cascade), job `mdf_cc_dev`, UC ABAC tag (SSOT §6)
- **Phase 4 — AI:** semantic layer, PII detection, classification, auto-suggest UC ABAC tag (SSOT §7)

---

*อ้างอิงสเปก: `DocsForAgent/draft_reviewd_by_agent_v2.md` — เอกสารชี้ขาดสูงสุด*
