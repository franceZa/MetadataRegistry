# T-46 evidence — 3 delivery modes on the real workspace (masked)

- วันที่ 2026-09-27 · master = `d3ea0d5` (PR #7 merge) · HG_PROD ✅ (seq 92) · host/email/workspace id ถูก mask
- `config/env/dev.yaml`: `delivery_mode: u2m`

## (1) mode `u2m` — ✅ ผ่าน

**Summary บนหน้า run จริง** — run `36315480466` ของ `Release (push master)`:

| job | ผล |
|---|---|
| Build & verify release package | success |
| Publish GitHub Release | success (สร้าง `mdf-d3ea0d559e04`) |
| Deliver to Databricks (dev) | **skipped** (mode ไม่ใช่ auto — ถูกต้อง) |

step **Next steps (job summary)** แสดง (ตัดมา):
```
## ขั้นต่อไป — `mdf-d3ea0d559e04` · mode **u2m** (คุณ login · สคริปต์ทำที่เหลือ)
1. ... git worktree add ../mdf-mdf-d3ea0d559e04 mdf-d3ea0d559e04
2. ... databricks auth login --host https://<workspace-host> --profile mdf-free
3. ... bash scripts/deliver_release.sh mdf-d3ea0d559e04
4. จบเมื่อเห็น `── ✅ delivered mdf-d3ea0d559e04`
**ถ้าติด** ... ถอยไป mode manual
```
`release_id` ถูกใส่ไว้แล้วทุกคำสั่ง · ไม่มี host/email

**ทำตาม Summary ทีละข้อ** (worktree ที่ tag `mdf-d3ea0d559e04` = `d3ea0d5`, dirty=0 · profile `mdf-free` Valid YES):
```
── CD-1 gh release download mdf-d3ea0d559e04
── CD-2 verify-package  ✅ manifest_sha256=e871519b7400…
── CD-3 sealed check → copy (manifest last)
── CD-4 copy back + verify  ✅ hash ตรง CD-2
── CD-5 bundle deploy -t dev  (1 unchanged)
── CD-6 register job  TERMINATED SUCCESS  ✅ REGISTERED appended
── CD-7 smoke query registry
── CD-8 activate  TERMINATED SUCCESS  ✅ ACTIVATED appended
── ✅ delivered mdf-d3ea0d559e04        DELIVER_EXIT=0
```

**query registry หลังส่ง:**
| release_id | event | manifest_sha256 | actor |
|---|---|---|---|
| mdf-d3ea0d559e04 | REGISTERED | e871519b7400… | manual |
| mdf-d3ea0d559e04 | ACTIVATED | e871519b7400… | manual |

active release = `mdf-d3ea0d559e04` · registry รวม REGISTERED 4 / ACTIVATED 5

> หมายเหตุ: `actor = manual` คือค่าของ mode u2m (คนรันสคริปต์เอง) · mode manual (UI) ใช้ `manual-ui` · mode auto ใช้ `github-oidc`

## (3) mode `auto` — ✅ หยุดที่ preflight ถูกต้อง · ยังไม่ได้พิสูจน์ว่าส่งได้จริง

`workflow_dispatch` ของ **Deploy release to Databricks (dev)** กับ `release_id=mdf-d3ea0d559e04` — run `36315638956` (repo ไม่มี variable ใด ๆ):

| step | ผล |
|---|---|
| Validate release_id | success |
| **Preflight (mode auto needs DEP-3 federation)** | **failure** (ตั้งใจ) |
| Checkout / Install uv / Sync / Install CLI / **Deliver (CD-1…8)** | **skipped** |
| Upload delivery evidence | success (artifact 0 ชิ้น = ไม่มีการส่งอะไร) |

ข้อความใน Summary:
```
## ❌ delivery_mode: auto — ยังตั้ง federation ไม่ครบ (DEP-3)
ต้องมี repo variables DATABRICKS_HOST + DATABRICKS_CLIENT_ID และ federation policy บน workspace ที่ไม่ใช่ Free Edition
ขั้นต่อไป: เปลี่ยน config/env/dev.yaml เป็น delivery_mode: u2m แล้วรัน
bash scripts/deliver_release.sh mdf-d3ea0d559e04
```
- ไม่มีการเขียน workspace (Deliver skipped · ไม่มีแถว `github-oidc` ใน registry)
- ผลข้างเคียง: GitHub สร้าง Environment `dev` ว่างขึ้นเองตอน job อ้าง `environment: dev` → **ลบแล้ว** ตามที่ผู้ใช้สั่ง (`gh api -X DELETE .../environments/dev` · ตอนนี้ `[]`)
- **mode auto ส่งของได้จริงหรือไม่ ยังไม่ได้พิสูจน์** — ต้องมี workspace ที่ไม่ใช่ Free Edition (R-20)

## (2) mode `manual` — ⏳ รอผู้ใช้ทำตาม M-1…M-7

release `mdf-f145479894d6` (ยังไม่เคยส่ง) · ผู้ใช้เลือกทำเองผ่าน UI · จบแล้ว activate `mdf-d3ea0d559e04` กลับ
