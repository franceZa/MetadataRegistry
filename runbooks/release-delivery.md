# Runbook — ส่ง release ไป Databricks · 3 mode · rollback (Phase 2 · E6)

> 📘 ยังไม่เคยดูแลระบบนี้? อ่าน [`release-delivery-guide.md`](release-delivery-guide.md) ก่อน — อธิบายสถาปัตยกรรม, ขั้น CD-1…8, และวิธี maintain

> คำสั่งและ SQL ทั้งหมดในไฟล์นี้รันจริงแล้วบน Free Edition (T-41, T-42, T-44 · 2026-09-27) · หลักฐาน: `qa-evidence/E6/T041/`, `T042/`, `T044/`
> host/email ของ workspace ไม่อยู่ใน repo (repo เป็น public) · ตัวอย่างใช้ release จริง `mdf-ef2f425903b6`

## 0. เลือก mode

ตั้งใน `config/env/dev.yaml` บรรทัดเดียว แล้วแก้ผ่าน PR (merge แล้วมีผลกับ push ถัดไป):

```yaml
delivery_mode: u2m     # auto | u2m | manual
```

| mode | ใครทำอะไร | ต้องมี | ใช้เมื่อ |
|---|---|---|---|
| `auto` | GitHub Actions ส่งเองหลัง push master · คุณแค่ approve Environment `dev` | workspace ที่ **ไม่ใช่** Free Edition + federation (ข้อ 5) | มี account admin |
| `u2m` **(ค่าตั้งต้น)** | คุณ login ครั้งเดียว · สคริปต์ทำ CD-1…8 ให้ | Databricks CLI, GitHub CLI, uv, bash | ปกติบน Free Edition |
| `manual` | คุณทำทุกขั้นในเบราว์เซอร์ | เบราว์เซอร์อย่างเดียว | ติดตั้ง/login CLI ไม่ได้จริง ๆ |

**ถอยเมื่อไร:**

| เห็นอะไร | แปลว่า | ทำอะไร |
|---|---|---|
| mode `auto` · job หยุดที่ **Preflight (mode auto needs DEP-3 federation)** | ยังไม่มี federation | PR เปลี่ยนเป็น `u2m` → ทำข้อ 3 |
| mode `u2m` · `❌ [PREFLIGHT] ไม่พบคำสั่ง databricks` / `gh` | เครื่องไม่มี CLI | ติดตั้งตามลิงก์ในข้อความ · ติดตั้งไม่ได้ → ข้อ 4 (manual) |
| mode `u2m` · `❌ [PREFLIGHT] login Databricks ไม่ผ่าน` | token หมดอายุ/ไม่มี profile | รัน `databricks auth login …` ตามบรรทัด `ขั้นต่อไป:` · login ไม่ได้ → ข้อ 4 |

ไม่ต้องจำ: หลัง push master เปิดหน้า run **Release (push master)** → job **Publish GitHub Release** → **Summary** จะมี "ขั้นต่อไป" ของ mode ปัจจุบันพร้อม `release_id` ใส่ไว้แล้ว · หรือรันเอง `python scripts/next_steps.py <mode> <release_id>`

## 1. ภาพรวม

```
push master ─► release.yml ─► GitHub Release mdf-<sha12> + Summary "ขั้นต่อไป"
                                 │
      auto:   deploy-dev.yml ────┤  (OIDC · approve Environment dev)
      u2m:    คุณรัน deliver_release.sh ┤  CD-1 ดาวน์โหลด  CD-2 verify  CD-3 คัดลอก (manifest ท้ายสุด)
                                 │    CD-4 คัดลอกกลับ+verify  CD-5 bundle deploy  CD-6 REGISTERED
                                 │    CD-7 query  CD-8 ACTIVATED
      manual: คุณทำ M-1…M-7 ─────┘  อัปโหลดเอง + SQL สำเร็จรูป (ตรวจเท่ากับ job)
                                 ▼
      /Volumes/dev_catalog/ops/files/releases/<release_id>/     มี manifest.json = sealed ห้ามแก้
      dev_catalog.ops.release_registry                          แถว ACTIVATED ล่าสุด = release ที่ใช้งาน
```

ทุก mode ได้ผลเหมือนกัน: REGISTERED 1 + ACTIVATED ≥1 ที่ `manifest_sha256` ตรงกับ `manifest.json` บนหน้า Release · ต่างกันแค่ `actor` (`github-oidc` / `manual` / `manual-ui`)

## 2. mode `auto`

1. หลัง push master เปิด run **Release (push master)** → job **Deliver to Databricks (dev)**
2. ขึ้น *Waiting for review* → **Review deployments** → `dev` → **Approve**
3. job เขียว → artifact `mdf-delivery-<release_id>` = หลักฐาน (masked)
4. ตรวจตามข้อ 6 ต้องได้ `actor = github-oidc`

ตั้งครั้งแรกตามข้อ 5 · ถ้าหยุดที่ Preflight = ยังตั้งไม่ครบ → ถอยไป `u2m`

## 3. mode `u2m` (ค่าตั้งต้น)

**เตรียมครั้งเดียว**

| ต้องมี | ตรวจ |
|---|---|
| Databricks CLI ≥ 1.17 | `databricks --version` |
| profile U2M | `databricks auth login --host <workspace-url> --profile mdf-free` → `databricks auth profiles` ต้องขึ้น `YES` |
| GitHub CLI | `gh auth status` |
| uv | `uv --version` |
| bash (Windows = git-bash) | `bash --version` |

**ส่ง release** (ทุกครั้ง · ~4–5 นาที)

```bash
git fetch origin --tags
git worktree add --detach ../mdf-rel-<sha12> mdf-<sha12>     # bundle ที่ deploy ต้องตรงกับ release
cd ../mdf-rel-<sha12> && uv sync --locked
export DATABRICKS_CONFIG_PROFILE=mdf-free
export MDF_WAREHOUSE_ID=<id จาก `databricks warehouses list`>   # ไม่ตั้ง = ใช้ตัวแรก
bash scripts/deliver_release.sh mdf-<sha12>
```

- จบด้วย `── ✅ delivered mdf-<sha12>` exit 0 · หลักฐาน `build/deliver/mdf-<sha12>/evidence.md`
- `--no-activate` = register อย่างเดียว · `--from-dir DIR` = ใช้ package ในเครื่องแทนการดาวน์โหลด (เช่นเครื่องไม่มี `gh`)
- รันซ้ำ id เดิมปลอดภัยเสมอ (ไม่คัดลอก ไม่เพิ่มแถว) · หยุดกลางทาง CD-3 → รันซ้ำจะคัดลอกต่อจนครบ

## 4. mode `manual` (ไม่มี CLI · เบราว์เซอร์อย่างเดียว)

ตรวจเท่ากับ job ทุกข้อ (hash ทุกไฟล์ · ไฟล์ขาด/เกิน · release_id · preview · hash เดิมที่ register ไว้) โดย SQL ใน `sql/manual/`

- [ ] **M-1** Catalog Explorer → `dev_catalog` → `ops` → Volume `files` → `releases/` → ถ้ามีโฟลเดอร์ `mdf-<sha12>` ที่มี `manifest.json` แล้ว **ห้ามอัปโหลด** ข้ามไป M-5
- [ ] **M-2** เปิด [หน้า GitHub Release](https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-<sha12>) → ดาวน์โหลด asset เดียว `mdf-<sha12>.zip` → แตก zip ในเครื่องตัวเอง → จด `manifest_sha256` จาก release notes ของหน้านี้ **หรือ** Job Summary ของ run `release.yml` (เลือกที่ใดก็ได้ — ไม่ใช่ digest ของไฟล์ zip ที่หน้า Release แสดง เพราะเลขนั้นเป็นของ zip ไม่ใช่ของ `manifest.json`)
- [ ] **M-3** สร้างโฟลเดอร์ `/Volumes/dev_catalog/ops/files/releases/mdf-<sha12>` แล้วสร้างโฟลเดอร์ย่อย `<source>/` ทีละ source (ดูจากโฟลเดอร์ที่แตก zip ได้ใน M-2 ว่ามีกี่ source) → อัปโหลด**ทุกไฟล์**ในโฟลเดอร์ `<source>/` ที่แตกจาก zip เข้าโฟลเดอร์ `<source>/` เดียวกัน — ทั้ง `*.resolved.json` **และ `*.odcs.yaml`** (ลืม `*.odcs.yaml` = M-5 หยุดด้วย `[TAMPERED]`) · จำนวนไฟล์ทั้งหมดใน `<source>/` = `file_count` ใน `manifest.json` (**ห้ามอัปโหลดไว้ที่ราก/แบบ flat**) แล้วค่อยอัปโหลด `validation-report.json` ที่ราก `/Volumes/dev_catalog/ops/files/releases/mdf-<sha12>`
- [ ] **M-4** อัปโหลด `manifest.json` เป็นไฟล์สุดท้าย ที่ราก `/Volumes/dev_catalog/ops/files/releases/mdf-<sha12>` (ไม่ใช่ในโฟลเดอร์ `<source>/`)
- [ ] **M-5** **SQL Editor** → วางไฟล์ `sql/manual/register_release.sql` → ตั้ง parameter `release_id = mdf-<sha12>` → **Run all** → ต้องได้ `REGISTERED` และ `manifest_sha256` ตรงกับที่จดใน M-2 (จาก Job Summary ของ `release.yml` ไม่ใช่หน้า Release) · error (รวมถึงกรณีอัปโหลดผิดโฟลเดอร์/flat) = หยุด ห้ามแก้ไฟล์ใน Volume เอง
- [ ] **M-6** วาง `sql/manual/activate_release.sql` → `release_id = mdf-<sha12>` → **Run all**
- [ ] **M-7** query ตรวจ: แถว `ACTIVATED` ล่าสุด = `mdf-<sha12>` · เก็บผล query เป็นหลักฐาน (ป้าย `manual-ui`) · ผลสุดท้ายต้องขึ้น `active_release_id = mdf-<sha12>`

**error ที่ SQL บอก (ไม่มีแถวใหม่ทุกกรณี · ทดสอบจริงใน T-44):**

| ข้อความ | ทำอะไร |
|---|---|
| `[BAD_RELEASE_ID]` | parameter ต้องเป็น `mdf-` + 12 ตัว hex |
| `CF_PATH_DOES_NOT_EXIST_FOR_READ_FILES` | ยังไม่ได้สร้างโฟลเดอร์ / สะกดชื่อผิด → M-3 |
| `[RELEASE_NOT_FOUND]` | ยังไม่ได้อัปโหลด `manifest.json` → M-4 ไฟล์สุดท้าย |
| `[TAMPERED] … sha256 ไม่ตรง` / `หายไป` / `ไฟล์ที่ไม่มีใน manifest` | ไฟล์เสีย/ขาด/เกิน (รวมถึงอัปโหลดผิดโฟลเดอร์ `<source>/`) → ลบไฟล์นั้นในโฟลเดอร์ (ถ้ายังไม่มีแถว REGISTERED) แล้วอัปโหลดจากหน้า Release ใหม่ |
| `[RELEASE_ID_MISMATCH]` | อัปโหลดผิดโฟลเดอร์ (ชื่อโฟลเดอร์ ≠ release ใน manifest) |
| `[HASH_CONFLICT]` | id นี้ถูก register ด้วยเนื้อหาอื่นแล้ว · **ห้ามแก้** · ใช้ release ใหม่ |
| `[NOT_REGISTERED]` (activate) | ทำ M-5 ก่อน |

## 5. ตั้งค่า mode `auto` ครั้งแรก (ต้องมี account admin · ทำไม่ได้บน Free Edition)

1. account console → สร้าง service principal · สิทธิ์ `USE CATALOG`, `USE SCHEMA`, `READ/WRITE VOLUME` (ops.files), `MODIFY` + `SELECT` (ops.release_registry), ใช้ SQL warehouse, สร้าง job
2. federation policy ของ SP: issuer `https://token.actions.githubusercontent.com` · audience = account id · subject `repo:franceZa/MetadataRegistry:environment:dev`
3. GitHub → Settings → Environments → สร้าง `dev` (ใส่ required reviewer ได้)
4. repo variables (ไม่ใช่ secret): `DATABRICKS_HOST`, `DATABRICKS_CLIENT_ID`
5. pin `databricks/setup-cli@main` ใน `deploy-dev.yml` เป็น SHA
6. ทดสอบก่อน: Actions → **Deploy release to Databricks (dev)** → Run workflow → `release_id` → ต้องได้ CD-1…8 ครบ + `actor = github-oidc`
7. แล้วค่อย PR เปลี่ยน `delivery_mode: auto`

ถ้าข้อ 6 ยังไม่เคยผ่าน ต้องรายงานว่า **mode auto ยังไม่ได้พิสูจน์**

## 6. ตรวจผล (ทุก mode)

```sql
-- release ที่ใช้งานอยู่
SELECT release_id, event_ts FROM dev_catalog.ops.release_registry
WHERE event = 'ACTIVATED' ORDER BY event_ts DESC LIMIT 1;

-- ประวัติของ release หนึ่ง
SELECT event, manifest_sha256, file_count, actor, event_ts
FROM dev_catalog.ops.release_registry WHERE release_id = 'mdf-<sha12>' ORDER BY event_ts;
```
Volume ต้องมีไฟล์ทั้งหมด = `file_count` ใน `manifest.json` + 2 (`manifest.json` + `validation-report.json` ที่ราก) · ไฟล์ตาม `file_count` อยู่ในโฟลเดอร์ย่อย `<source>/` ของมัน ทั้ง `*.resolved.json` และ `*.odcs.yaml` (ไม่นับจำนวนไฟล์ตายตัว เพราะจำนวน source/dataset เปลี่ยนได้ตามรอบ): `databricks fs ls dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-<sha12> --recursive` หรือเปิดใน Catalog Explorer

## 7. Rollback config (ทุก mode)

**ไม่ลบ ไม่ทับ ไม่ RESTORE** — activate release เก่าอีกครั้ง = append แถว `ACTIVATED` ใหม่ (ทดสอบจริงใน T-42: `ef2f425` → `98a182c` → `ef2f425`)

| mode | ทำ |
|---|---|
| `auto` | Actions → **Deploy release to Databricks (dev)** → Run workflow → `release_id` เก่า |
| `u2m` | `bash scripts/deliver_release.sh mdf-<sha12-เก่า>` → `already sealed … skip copy` · `REGISTERED skipped` · `ACTIVATED appended` |
| `manual` | M-6 ด้วย `release_id` เก่า |

roll forward = ทำแบบเดียวกันกับ release ใหม่ · ตรวจด้วยข้อ 6

## 8. `deliver_release.sh` ไม่ผ่าน (mode auto / u2m)

| อาการ | ความหมาย | ทำอะไร |
|---|---|---|
| `❌ [USAGE]` | release_id ไม่ใช่ `mdf-<12 hex>` | แก้ argument |
| `❌ [PREFLIGHT]` | ไม่มี CLI / login ไม่ผ่าน · **ยังไม่แตะอะไร** | ทำตามบรรทัด `ขั้นต่อไป:` · ไม่ได้ → ข้อ 4 |
| `❌ [CD-1]` | ไม่มี GitHub Release นี้ | `gh release list` |
| `❌ [CD-2]` + `[TAMPERED]` / `[RELEASE_ID_MISMATCH]` | package ไม่ตรง manifest · workspace **ไม่ถูกแตะ** | ห้ามส่ง · ตรวจที่มาของ package |
| `❌ [CD-3] … sealed … DIFFERENT manifest` | id นี้ถูก seal ด้วยเนื้อหาอื่นแล้ว | ห้ามแก้โฟลเดอร์ · ใช้ release ใหม่ |
| หยุดกลางทาง CD-3 | โฟลเดอร์ยังไม่มี `manifest.json` | รันซ้ำ → `partial folder … resume` |
| `❌ [CD-6]` / `[CD-8]` · UI ขึ้น `INTERNAL_ERROR … SystemExit: 1` | job ปฏิเสธ | ข้อความจริงอยู่บรรทัดแรกของ task log: `databricks jobs get-run-output <task_run_id>` |
| `❌ [CD-7]` | registry ไม่ตรง | หยุด · query ข้อ 6 · ห้าม UPDATE/DELETE (ตารางปฏิเสธอยู่แล้ว) |

## 9. UC objects (ทำแล้วใน T-37 · รันซ้ำไม่มีผล)

วาง `sql/bootstrap/ops.sql` ใน SQL editor แทน `${catalog}` ด้วย `dev_catalog`
