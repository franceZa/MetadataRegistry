# T-42 evidence — runbook dry-run on the real workspace (manual U2M)

- วันที่ 2026-09-27 · worktree สะอาดที่ `ef2f425` (master หลัง merge PR #4 + #5) · profile `mdf-free` · actor `manual`
- ใช้พิสูจน์ runbook `runbooks/release-delivery.md` ข้อ 2 (deploy release ใหม่) และข้อ 4 (rollback / roll forward)

## 1. Deploy release ใหม่ `mdf-ef2f425903b6` (runbook §2) — ครั้งแรกหลังแก้ PR #5
```
CD-3 (โฟลเดอร์ยังไม่มี) → mkdir + คัดลอก 8 ไฟล์ (ไม่มี 'no such directory')
✅ REGISTERED appended: release_id=mdf-ef2f425903b6 manifest_sha256=6bf079b8…
✅ ACTIVATED appended:  release_id=mdf-ef2f425903b6
EXIT_DELIVER=0
```
→ ยืนยันว่า fix PR #5 ใช้ได้กับ release_id ใหม่บนของจริง

## 2. Rollback config → `mdf-98a182c99186` (runbook §4)
```
── CD-3 already sealed with identical manifest → skip copy
✅ REGISTERED skipped: release_id=mdf-98a182c99186
✅ ACTIVATED appended: release_id=mdf-98a182c99186
EXIT_ROLLBACK=0
```

## 3. Roll forward → `mdf-ef2f425903b6`
```
── CD-3 already sealed with identical manifest → skip copy
✅ REGISTERED skipped · ✅ ACTIVATED appended
EXIT_FORWARD=0
```

## 4. Registry หลังทั้งหมด (append-only, ไม่มีแถวถูกลบ/แก้)
| release_id | event | sha256[:8] | actor | event_ts (UTC) |
|---|---|---|---|---|
| mdf-98a182c99186 | REGISTERED | 90d1c7bc | manual | 07:38:57 |
| mdf-98a182c99186 | ACTIVATED | 90d1c7bc | manual | 07:40:26 |
| mdf-ef2f425903b6 | REGISTERED | 6bf079b8 | manual | 08:15:29 |
| mdf-ef2f425903b6 | ACTIVATED | 6bf079b8 | manual | 08:17:01 |
| mdf-98a182c99186 | ACTIVATED | 90d1c7bc | manual | 08:19:32 ← rollback |
| mdf-ef2f425903b6 | ACTIVATED | 6bf079b8 | manual | 08:22:01 ← roll forward |

`SELECT release_id … WHERE event='ACTIVATED' ORDER BY event_ts DESC LIMIT 1` → `mdf-ef2f425903b6`

REGISTERED = 1 แถวต่อ release แม้รันหลายครั้ง · Volume `releases/` = `mdf-747738df7af8` (spike, ไม่แตะ), `mdf-98a182c99186`, `mdf-ef2f425903b6`

## หมายเหตุ
- release `mdf-44d14f829e93` (merge PR #4) มีใน GitHub แต่ **ไม่ได้ส่ง** — ไม่จำเป็น (A-18: ทุก push มี Release, ส่งเฉพาะที่ต้องการ)
- ⚠️ manual run — CD อัตโนมัติยังไม่ได้พิสูจน์
