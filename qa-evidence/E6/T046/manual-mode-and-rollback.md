# T-46 evidence — mode manual (M-1…M-7, real UI) + rollback

- ผู้ใช้ทำ M-1…M-7 เองผ่าน Databricks UI สำหรับ `mdf-f145479894d6` (ยังไม่เคยส่งมาก่อน)
- Volume: 8 ไฟล์ครบ, `manifest.json` เป็นไฟล์สุดท้าย (`18:54:10` vs ไฟล์อื่น `18:53:19`)
- Registry:

| release_id | event | manifest_sha256 (16 ตัวแรก) | actor |
|---|---|---|---|
| mdf-f145479894d6 | REGISTERED | `e4ffbfc823aeb0b1` | manual-ui |
| mdf-f145479894d6 | ACTIVATED | `e4ffbfc823aeb0b1` | manual-ui |

hash ตรงกับ GitHub Release asset digest `e4ffbfc823aeb0b1e49fdcaa63a7c997e977ad4466db8afe5deaa0530925f335` ทุกตัว

## Rollback

รัน `sql/manual/activate_release.sql` (ไฟล์เดียวกับ M-6) ด้วย `release_id = mdf-d3ea0d559e04`:
```
guard: OK — รัน statement ถัดไปได้
insert: 1 row
active_release_id = mdf-d3ea0d559e04 · manifest_sha256 e871519b740074fd... · activated_at 2026-09-27T12:10:24.544Z
```

Active release กลับไปเป็น `mdf-d3ea0d559e04` ตามเดิม

## T-46 สรุปทั้ง 3 mode

| mode | ผล |
|---|---|
| u2m | ✅ real CD-1…8 ผ่าน (mdf-d3ea0d559e04) |
| auto | ✅ หยุดที่ preflight ตามที่ออกแบบ ไม่มีการเขียน workspace |
| manual | ✅ M-1…M-7 ผ่านหน้าเว็บจริง (mdf-f145479894d6), rollback กลับสำเร็จ |
