# T-41 evidence — first real delivery `mdf-98a182c99186` (Free Edition · **manual U2M**)

> ⚠️ **ป้าย manual (AC-41 And / D-P5-6):** รันด้วย `scripts/deliver_release.sh` จากเครื่องผู้ใช้ผ่าน OAuth U2M profile — **CD อัตโนมัติ (`deploy-dev.yml`) ยังไม่ได้พิสูจน์** (Free Edition ตั้ง federation ไม่ได้, R-20)

- HG_PROD: `APPROVED: PROD` (seq 92) · สั่งรัน: ผู้ใช้ "go T-41" (seq 115)
- Release: https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-98a182c99186 · target `98a182c99186391ad87a7bc53f10b16a96206f4f` · 8 assets
- รันจาก git worktree สะอาดที่ `98a182c` + cherry-pick fix `6f46f2d` (แก้เฉพาะ `scripts/deliver_release.sh` + fake; `src/`, `resources/`, `databricks.yml`, `pyproject.toml` = release byte-for-byte → wheel/job ตรงกับ package)
- host / email / workspace id ถูก mask ทั้งไฟล์

## 0. Run 1 — FAILED ที่ CD-3 (พบ bug จริง)
```
── CD-3 sealed check dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186
Error: no such directory: /Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186
EXIT=1
```
- สาเหตุ (probe ยืนยัน): `databricks fs cp` แบบไฟล์เดียว **ไม่สร้างโฟลเดอร์แม่** บน UC Volume · fake CLI เดิมสร้างให้เงียบ ๆ จึงซ่อน bug
- ผลกระทบ: ไม่มีอะไรถูกคัดลอก (Volume ยังมีแค่ `mdf-747738df7af8`) · ไม่มีแถวใน registry
- แก้: `fs mkdir $DEST` ก่อนคัดลอก + fake ทำตามของจริง → PR #5 (https://github.com/franceZa/MetadataRegistry/pull/5) · test เดิมพังด้วย error เดียวกันก่อนแก้, 13 passed หลังแก้

## 1. Run 2 — CD-1…8 ✅ (AC-37)
### evidence.md (สคริปต์เขียนเอง) — mdf-98a182c99186

- actor: manual · catalog: dev_catalog · target: dev · started: 2026-09-27T07:36:59Z
- ⚠️ manual run (D-P5-6): automated CD (deploy-dev.yml) NOT proven by this run
- CD-1: https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-98a182c99186
- CD-2: verify OK · manifest_sha256 `90d1c7bcc26c9c1c76df46428fd3673fe538c9ff89e12ecfe952cb21b6bd65b8` · file_count 6
- CD-3: copied 8 files · manifest.json last
- CD-4: copy-back verify OK · manifest_sha256 matches CD-2

```
$ databricks fs ls dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186
bronze.cc.credit_card.resolved.json
bronze.cc.credit_card_txn.resolved.json
bronze.cc.customer.resolved.json
manifest.json
silver.cc.credit_card.resolved.json
silver.cc.credit_card_txn.resolved.json
silver.cc.customer.resolved.json
validation-report.json
```
- CD-5: bundle deploy -t dev OK
- CD-6: job run (register) OK · run: https://<host>/jobs/945186884866349/runs/168469045056055?o=<ws>
- CD-7: registry has exactly 1 REGISTERED row · manifest_sha256 + file_count match
- CD-8: job run (activate) OK · run: https://<host>/jobs/945186884866349/runs/688074900013864?o=<ws>
- CD-8: latest ACTIVATED = mdf-98a182c99186 · bundle var active_release_id set

```
registry rows for mdf-98a182c99186: [["REGISTERED", "90d1c7bcc26c9c1c76df46428fd3673fe538c9ff89e12ecfe952cb21b6bd65b8", "6", "/Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186", "manual", "2026-09-27 07:38:57.261654"], ["ACTIVATED", "90d1c7bcc26c9c1c76df46428fd3673fe538c9ff89e12ecfe952cb21b6bd65b8", "6", "/Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186", "manual", "2026-09-27 07:40:26.945165"]]
```
- copied_this_run: 1 · finished: 2026-09-27T07:40:55Z


## 2. Run 3 — รันซ้ำ id เดิม ✅ (AC-38 ข้อ 1)
### evidence.md (rerun) — mdf-98a182c99186

- actor: manual · catalog: dev_catalog · target: dev · started: 2026-09-27T07:41:13Z
- ⚠️ manual run (D-P5-6): automated CD (deploy-dev.yml) NOT proven by this run
- CD-1: https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-98a182c99186
- CD-2: verify OK · manifest_sha256 `90d1c7bcc26c9c1c76df46428fd3673fe538c9ff89e12ecfe952cb21b6bd65b8` · file_count 6
- CD-3: already sealed (same manifest_sha256) → no copy
- CD-4: copy-back verify OK · manifest_sha256 matches CD-2

```
$ databricks fs ls dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186
bronze.cc.credit_card.resolved.json
bronze.cc.credit_card_txn.resolved.json
bronze.cc.customer.resolved.json
manifest.json
silver.cc.credit_card.resolved.json
silver.cc.credit_card_txn.resolved.json
silver.cc.customer.resolved.json
validation-report.json
```
- CD-5: bundle deploy -t dev OK
- CD-6: job run (register) OK · run: https://<host>/jobs/945186884866349/runs/444869118323270?o=<ws>
- CD-7: registry has exactly 1 REGISTERED row · manifest_sha256 + file_count match
- CD-8: job run (activate) OK · run: https://<host>/jobs/945186884866349/runs/889056172040978?o=<ws>
- CD-8: latest ACTIVATED = mdf-98a182c99186 · bundle var active_release_id set

```
registry rows for mdf-98a182c99186: [["REGISTERED", "90d1c7bcc26c9c1c76df46428fd3673fe538c9ff89e12ecfe952cb21b6bd65b8", "6", "/Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186", "manual", "2026-09-27 07:38:57.261654"], ["ACTIVATED", "90d1c7bcc26c9c1c76df46428fd3673fe538c9ff89e12ecfe952cb21b6bd65b8", "6", "/Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186", "manual", "2026-09-27 07:40:26.945165"]]
```
- copied_this_run: 0 · finished: 2026-09-27T07:43:17Z

- ผล job: `REGISTERED skipped` · `ACTIVATED skipped` · `copied_this_run: 0` → ไม่คัดลอก ไม่มีแถวใหม่

## 3. Tamper ✅ (AC-38 ข้อ 2)
แก้ 1 byte ใน `silver.cc.customer.resolved.json` ของ package ที่ดาวน์โหลดมา แล้วส่งด้วย id เดิม (`--from-dir`):
```
[TAMPERED] ไฟล์ 'silver.cc.customer.resolved.json' ถูกดัดแปลง (sha256 ไม่ตรง: expected 9e7c1e30745d…, got e308d38c25e9…)
❌ [CD-2] package failed verification — nothing sent to the workspace
rc=1
```

## 4. Registry append-only บนแถวจริง ✅ (AC-40)
```
UPDATE dev_catalog.ops.release_registry SET actor='tampered' WHERE release_id='mdf-98a182c99186' → FAILED [DELTA_CANNOT_MODIFY_APPEND_ONLY]
DELETE FROM dev_catalog.ops.release_registry WHERE release_id='mdf-98a182c99186'              → FAILED [DELTA_CANNOT_MODIFY_APPEND_ONLY]
SELECT event, actor, count(*) … GROUP BY event, actor → [["ACTIVATED","manual","1"],["REGISTERED","manual","1"]]
```
register ถูกเรียก 2 ครั้ง (run 2 + run 3) → REGISTERED ยังเป็น 1 แถว

## 5. job ต้องได้ release_id ชัดเจน ✅ (AC-42)
| input | ผล job (task log) | rc |
|---|---|---|
| `release_id=` (ว่าง) | `[NO_RELEASE_ID] ต้องระบุ --release-id (mdf-<sha12>) — job ไม่เดา release ล่าสุด (AC-42)` | 1 (run 790213257938523) |
| `release_id=mdf-000000000000` | `[RELEASE_NOT_FOUND] ไม่พบ release ที่ '/Volumes/dev_catalog/ops/files/releases/mdf-000000000000' (หรือยังไม่ sealed: ไม่มี manifest.json)` | 1 (run 404196252834391) |
| `release_id=mdf-98a182c99186` | `REGISTERED appended` → rerun `skipped` | 0 (run 168469045056055) |

- ข้อสังเกต: job ที่ fail แสดงใน UI เป็น `INTERNAL_ERROR … SystemExit: 1` (serverless wheel task) — ข้อความจริงอยู่ใน task log บรรทัดแรก

## 6. Release workflow rerun ✅ (AC-36)
`gh run rerun 36302188207` (attempt 2) → success · log: `release mdf-98a182c99186 already published with identical content - skip` · Release ยังมีตัวเดียว · deliver job = skipped (guard)

## Outputs
| key | value |
|---|---|
| `release_id` | `mdf-98a182c99186` |
| `manifest_sha256` | `90d1c7bcc26c9c1c76df46428fd3673fe538c9ff89e12ecfe952cb21b6bd65b8` |
| `volume_path` | `/Volumes/dev_catalog/ops/files/releases/mdf-98a182c99186` (8 ไฟล์) |
| `active_release_id` | `mdf-98a182c99186` = latest ACTIVATED ใน registry (**แหล่งความจริง**) · bundle var ส่งตอน deploy CD-8 แต่ยังไม่มี resource ใดใช้ (`0 changed`) และไม่ถูกเก็บถาวร → Phase 3 ต้องอ่านจาก registry หรือส่ง `--var` ทุกครั้ง |
| job | `mdf_release_register_dev` (id 945186884866349) |
