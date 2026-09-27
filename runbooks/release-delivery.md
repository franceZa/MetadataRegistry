# Runbook — ส่ง release ไป Databricks / rollback config (Phase 2 · E6)

> ทุกคำสั่งในไฟล์นี้รันจริงแล้วบน Free Edition (T-41 และ T-42, 2026-09-27) · หลักฐาน: `qa-evidence/E6/T041/run.md`, `qa-evidence/E6/T042/run.md`
> ตัวอย่างใช้ release จริง `mdf-98a182c99186` และ `mdf-ef2f425903b6` · host/email ของ workspace ไม่อยู่ใน repo (repo เป็น public)

## 0. ภาพรวม

```
push master ──► release.yml ──► GitHub Release mdf-<sha12>      (อัตโนมัติ ทุก push)
                                   │
          คุณรัน (manual U2M) ─────┘
          scripts/deliver_release.sh mdf-<sha12>
            CD-1 ดาวน์โหลด asset          CD-5 bundle deploy (job mdf_release_register_dev)
            CD-2 verify + release_id      CD-6 job: ตรวจ hash ใน workspace → REGISTERED
            CD-3 คัดลอก → Volume (manifest ท้ายสุด = sealed)
            CD-4 คัดลอกกลับ + verify      CD-7 query registry  · CD-8 job → ACTIVATED
```

- **ที่เก็บไฟล์:** `/Volumes/dev_catalog/ops/files/releases/<release_id>/` — มี `manifest.json` = sealed = ห้ามแก้
- **แหล่งความจริงว่า release ไหนใช้งานอยู่:** แถว `ACTIVATED` ล่าสุดใน `dev_catalog.ops.release_registry` (append-only)
- **CD อัตโนมัติ (`deploy-dev.yml`) ปิดอยู่** บน Free Edition — ดูข้อ 6

## 1. เตรียมเครื่อง (ครั้งเดียว)

| สิ่งที่ต้องมี | ตรวจด้วย |
|---|---|
| Databricks CLI ≥ 1.17 | `databricks --version` |
| profile U2M ของ workspace | `databricks auth login --host <workspace-url> --profile mdf-free` แล้ว `databricks auth profiles` ต้องขึ้น `YES` |
| GitHub CLI login | `gh auth status` |
| uv | `uv --version` |
| bash (Windows = git-bash) | `bash --version` |

UC objects (ทำไปแล้วใน T-37 · รันซ้ำได้ไม่มีผล):
```bash
python run_sql.py <warehouse_id> sql/bootstrap/ops.sql   # หรือวาง SQL ใน SQL editor แทน ${catalog} ด้วย dev_catalog
```

## 2. ส่ง release ใหม่ (deploy)

1. หา release_id: `gh release list -R franceZa/MetadataRegistry` → เลือก `mdf-<sha12>` (แถว `Latest` = push ล่าสุด)
2. **checkout commit ของ release นั้น** เพื่อให้ job/wheel ที่ deploy ตรงกับ package:
   ```bash
   git fetch origin --tags
   git worktree add --detach ../mdf-rel-<sha12> <sha12>
   cd ../mdf-rel-<sha12> && uv sync --locked
   ```
3. รัน:
   ```bash
   export DATABRICKS_CONFIG_PROFILE=mdf-free MDF_ACTOR=manual
   export MDF_WAREHOUSE_ID=<id จาก `databricks warehouses list`>   # ไม่ตั้ง = ใช้ตัวแรก
   bash scripts/deliver_release.sh mdf-<sha12>
   ```
   จบด้วย `── ✅ delivered mdf-<sha12>` และ exit 0 · ใช้เวลา ~4–5 นาที (serverless job 2 รอบ)
4. หลักฐาน: `build/deliver/mdf-<sha12>/evidence.md` (mask host/email แล้ว) → คัดลอกไป `qa-evidence/` ถ้าต้องเก็บ

ตัวเลือก: `--no-activate` = register อย่างเดียว ไม่เปลี่ยน release ที่ใช้งาน · `--from-dir DIR` = ใช้ package ในเครื่องแทน GitHub (ไม่มี URL ใน registry)

## 3. ตรวจผล

```sql
-- release ที่ใช้งานอยู่
SELECT release_id, event_ts FROM dev_catalog.ops.release_registry
WHERE event = 'ACTIVATED' ORDER BY event_ts DESC LIMIT 1;

-- ประวัติของ release หนึ่ง
SELECT event, manifest_sha256, file_count, actor, event_ts
FROM dev_catalog.ops.release_registry WHERE release_id = 'mdf-<sha12>' ORDER BY event_ts;
```
```bash
databricks fs ls dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-<sha12>   # ต้องมี 8 ไฟล์ รวม manifest.json
```

## 4. Rollback config (กลับไปใช้ release เก่า)

**ไม่ลบ ไม่ทับ ไม่ RESTORE** — แค่ activate release เก่าอีกครั้ง (append แถว `ACTIVATED` ใหม่)

```bash
bash scripts/deliver_release.sh mdf-<sha12-เก่า>
```
- release เก่า sealed อยู่แล้ว → CD-3 `already sealed … skip copy` · CD-6 `REGISTERED skipped` · CD-8 `ACTIVATED appended`
- ตรวจ: query ข้อ 3 ต้องได้ release เก่าเป็น ACTIVATED ล่าสุด
- **ข้อควรระวัง:** รันจาก worktree ของ commit ใหม่ได้ (job logic เหมือนกัน) แต่ถ้า job definition เปลี่ยนระหว่าง release ให้ checkout commit ของ release เก่าตามข้อ 2.2
- roll forward = รันคำสั่งเดิมกับ release ใหม่

## 5. เมื่อไม่ผ่าน

| อาการ | ความหมาย | ทำอะไร |
|---|---|---|
| `❌ [USAGE]` | release_id ไม่ใช่ `mdf-<12 hex>` | แก้ argument |
| `❌ [CD-1]` | ไม่มี GitHub Release นี้ | `gh release list` |
| `❌ [CD-2]` + `[TAMPERED]` / `[RELEASE_ID_MISMATCH]` | package ไม่ตรง manifest · workspace **ไม่ถูกแตะ** | ห้ามส่ง · ตรวจที่มาของ package |
| `❌ [CD-3] … sealed … DIFFERENT manifest … immutable` | id นี้ถูก seal ด้วยเนื้อหาอื่นแล้ว | ห้ามแก้โฟลเดอร์ใน Volume · สร้าง release ใหม่จาก commit ใหม่ |
| หยุดกลางทาง CD-3 (เน็ตหลุด) | โฟลเดอร์ไม่มี `manifest.json` = ยังไม่ sealed | รันคำสั่งเดิมซ้ำ → `partial folder … resumed` |
| `❌ [CD-6]` / `[CD-8]` + UI ขึ้น `INTERNAL_ERROR … SystemExit: 1` | job ปฏิเสธ | ดูข้อความจริงที่บรรทัดแรกของ task log: `databricks jobs get-run-output <task_run_id>` (`[NO_RELEASE_ID]`, `[RELEASE_NOT_FOUND]`, `[HASH_CONFLICT]`, `[VERIFY_FAILED]`, `[NOT_REGISTERED]`) |
| `❌ [CD-7]` | registry ไม่ตรง (แถว/hash/file_count) | หยุด · query ข้อ 3 · ห้าม UPDATE/DELETE (ตารางปฏิเสธอยู่แล้ว) |
| `Error: no such directory` ตอน CD-3 | สคริปต์เก่าก่อน PR #5 | ใช้ commit ≥ `ef2f425` |

รันซ้ำ id เดิมปลอดภัยเสมอ (ไม่คัดลอก ไม่เพิ่มแถว)

## 6. เปิด CD อัตโนมัติ (เมื่อย้ายไป workspace ที่มี account admin)

Free Edition ทำไม่ได้ (ไม่มี account console → ตั้ง federation ไม่ได้) · ขั้นตอนเมื่อมี workspace ที่ทำได้:

1. account console → สร้าง service principal · ให้สิทธิ์ `USE CATALOG`, `USE SCHEMA`, `READ/WRITE VOLUME` (ops.files), `MODIFY` + `SELECT` (ops.release_registry), สิทธิ์ใช้ SQL warehouse
2. federation policy ของ SP: issuer `https://token.actions.githubusercontent.com` · audience = account id · subject `repo:franceZa/MetadataRegistry:environment:dev`
3. GitHub → Settings → Environments → สร้าง `dev` (ใส่ required reviewer ได้)
4. repo variables (ไม่ใช่ secret): `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID` · แล้ว `MDF_CD_ENABLED=true`
5. ทดสอบ: Actions → **Deploy release to Databricks (dev)** → Run workflow → `release_id` → ต้องได้ artifact `mdf-delivery-<id>` ที่ CD-1…8 ครบ และ `actor = github-oidc` ใน registry
6. ก่อนเปิด: pin `databricks/setup-cli@main` เป็น SHA

ถ้าข้อ 5 ยังไม่เคยผ่าน ต้องรายงานว่า **CD อัตโนมัติยังไม่ได้พิสูจน์** ทุกครั้ง
