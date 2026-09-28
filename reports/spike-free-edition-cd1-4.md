# Spike: ส่ง config release จาก GitHub → Databricks Free Edition (CD-1…4) · **manual**

- วันที่: 2026-09-26 · ผู้อนุมัติ HG_PROD: ผู้ใช้ ("APPROVED: PROD") · ขอบเขต: CD-1…4 เท่านั้น (ไม่มี registry / bundle / job)
- ป้าย: **manual (OAuth U2M)** ไม่ได้พิสูจน์ CD อัตโนมัติ (AC-41 And) · ไม่มี token อยู่ใน GitHub หรือ repo

| ขั้น | สิ่งที่ทำ | ผล |
|---|---|---|
| CD-1 | `gh run download 36244174669 -n mdf-release-747738df…` (run `Release (push master)`, conclusion=success, headSha=`747738df7af8597476d87a3e97697280a47e920c` = master) | 6 resolved JSON + manifest.json |
| CD-2 | `uv run mdf verify-package build/spike/<sha>` (src/config/lock ตรงกับ SHA) | ✅ OK files=6 · manifest sha256 `ea23b4cc…786d` |
| auth | `databricks auth login --host https://dbc-59a6ca1a-bbe7.cloud.databricks.com --profile mdf-free` (CLI 1.17.0) | ✅ U2M ใช้ได้บน Free Edition · `current-user me` active |
| setup | `CREATE CATALOG dev_catalog` ผ่าน SQL statement API (Serverless Starter Warehouse) → `schemas create ops` → `volumes create … files MANAGED` | ✅ `dev_catalog.ops.files` (ดูข้อค้นพบ 1) |
| CD-3 | preflight ว่ายังไม่มี `manifest.json` → `fs cp` resolved ทีละไฟล์ → `manifest.json` เป็นไฟล์สุดท้าย | ✅ `releases/mdf-747738df7af8/` 7 ไฟล์ ขนาดตรง |
| CD-4 | `fs cp` กลับมาทั้งโฟลเดอร์ → `mdf verify-package` | ✅ OK files=6 · manifest sha256 ตรงกับ CD-2 (`ea23b4cc…786d`) |

## ข้อค้นพบ (ต้องส่งกลับเข้า SSOT / tickets Phase 2)

1. **DEP-2 / R-4:** `databricks catalogs create` (REST) ใช้ไม่ได้: `Metastore storage root URL does not exist. Default Storage is enabled…`. แต่ `CREATE CATALOG` ผ่าน SQL บน serverless warehouse **สร้างได้** และใช้ Default Storage ไม่ต้อง fallback เป็น `workspace`
2. **AC-38 / FR-L.4:** `databricks fs cp` ที่ไม่มี `--overwrite` เมื่อพบไฟล์ปลายทาง **ข้ามไฟล์และคืนค่า exit 0** (`(skipped; already exists)`) **ไม่ fail**. สคริปต์ CD จึงตัดสินจาก exit code ไม่ได้ ต้องตรวจ `manifest.json` แล้วเทียบ hash เอง (CD-3 rule)
3. **FR-F.6 gap (รู้อยู่แล้ว):** `verify-package` ยังไม่มี `--expect-release-id` และ manifest ยังไม่มี `release_id` / `source_commit` ตอนนี้ release_id ผูกกับ SHA ผ่าน run metadata เท่านั้น
4. **FR-L.1 gap:** ยังไม่มี GitHub Release `mdf-<sha12>` (`gh release list` ว่าง) รอบนี้จึงใช้ Actions artifact แทน · `publish` job ยังไม่ติดตั้ง uv
5. `config/env/dev.yaml` `workspace_host` ยังเป็น placeholder `adb-dev.azuredatabricks.net` ไม่ตรงกับ workspace จริง (ยังไม่แก้ ต้องผ่าน ticket)
6. ยังไม่ได้ทดสอบ: GitHub OIDC (DEP-3 / R-20), registry, job `mdf_release_register_dev`, การอ่าน `/Volumes/...` จาก compute

## สิ่งที่สร้างไว้ใน workspace (ต้องลบเองถ้าจะ rollback)
`dev_catalog` (catalog) · `dev_catalog.ops` · `dev_catalog.ops.files` (managed volume) · `releases/mdf-747738df7af8/` 7 ไฟล์ · CLI profile `mdf-free` ใน `~/.databrickscfg` (OAuth cache ไม่มี secret อยู่ใน repo)
