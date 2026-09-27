# T-37 evidence — UC bootstrap on Databricks Free Edition (masked)

- เวลา: 2026-09-27 · HG_PROD: `APPROVED: PROD` (checkpoint seq 92)
- ผู้รัน: ผู้ใช้ผ่าน U2M OAuth profile `mdf-free` (`<user>`, `<host>`) · warehouse: Serverless Starter Warehouse (2X-Small · id masked)
- วิธีรัน: SQL Statement Execution API (`databricks api post /api/2.0/sql/statements`) ทีละ statement จาก `sql/bootstrap/ops.sql` · แทน `${catalog}` = `dev_catalog`
- ไม่มี token/secret ในไฟล์นี้

## RUN 1 (06:05:48Z) และ RUN 2 (06:06:10Z) — idempotent
| statement | RUN 1 | RUN 2 |
|---|---|---|
| `CREATE SCHEMA IF NOT EXISTS dev_catalog.ops` | SUCCEEDED | SUCCEEDED |
| `CREATE VOLUME IF NOT EXISTS dev_catalog.ops.files` | SUCCEEDED | SUCCEEDED |
| `CREATE TABLE IF NOT EXISTS dev_catalog.ops.release_registry (…)` | SUCCEEDED | SUCCEEDED |

## OBSERVE
| query | ผล |
|---|---|
| `SHOW TBLPROPERTIES dev_catalog.ops.release_registry ('delta.appendOnly')` | `delta.appendOnly = true` |
| `SELECT count(*) FROM dev_catalog.ops.release_registry` | `0` (ยังไม่มี release ถูกส่ง) |
| `DESCRIBE TABLE dev_catalog.ops.release_registry` | 10 คอลัมน์ตาม SSOT: release_id, event, source_commit, manifest_sha256, file_count (int), volume_path, github_release_url, ci_run_url, actor, event_ts (timestamp) |
| `SHOW TABLES IN dev_catalog.ops` | `release_registry` เท่านั้น (probe ถูก DROP แล้ว) |

## AC-40 (ส่วน T-37) — UPDATE/DELETE ถูกปฏิเสธ
### บน `release_registry` จริง (ตารางว่าง · predicate `1 = 0` ไม่แตะแถวใด)
| statement | ผล |
|---|---|
| `UPDATE dev_catalog.ops.release_registry SET actor='x' WHERE 1 = 0` | **FAILED** `[DELTA_CANNOT_MODIFY_APPEND_ONLY] This table is configured to only allow appends.` |
| `DELETE FROM dev_catalog.ops.release_registry WHERE 1 = 0` | **FAILED** `[DELTA_CANNOT_MODIFY_APPEND_ONLY]` |

### บน probe ที่มีข้อมูลจริง (`ops._t037_appendonly_probe`, appendOnly เหมือนกัน · ไม่ใส่แถวทดสอบลง registry เพราะจะลบไม่ได้)
| statement | ผล |
|---|---|
| `INSERT … VALUES (1)` | SUCCEEDED (1 แถว) |
| `UPDATE … SET id = 2 WHERE id = 1` | **FAILED** `[DELTA_CANNOT_MODIFY_APPEND_ONLY]` |
| `DELETE … WHERE id = 1` | **FAILED** `[DELTA_CANNOT_MODIFY_APPEND_ONLY]` |
| `SELECT *` | `[1]` — ข้อมูลไม่เปลี่ยน |
| `DROP TABLE …probe` | SUCCEEDED (เก็บกวาด) |

## ข้อสังเกต
- appendOnly **ไม่กัน `DROP TABLE`** หรือ `ALTER TABLE … SET TBLPROPERTIES (delta.appendOnly=false)` โดยเจ้าของตาราง — Free Edition มีผู้ใช้คนเดียว (= owner) จึงกันไม่ได้ด้วย grant → บันทึกเป็น risk R-24 (grant แยก SP/runtime เลื่อนไป Phase 3 ตาม ticket)
- `workspace_host` ไม่ commit host จริง (repo เป็น PUBLIC) → ตั้งเป็น `null` + อ่านจาก CLI profile / `DATABRICKS_HOST` ตอน CD · ไม่มีโค้ดใดอ่านค่านี้ (grep) และ resolved JSON ไม่มีค่านี้
