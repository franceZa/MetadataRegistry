# T-44 evidence — mode manual SQL on the real workspace (masked)

- 2026-09-27 · Free Edition · SQL warehouse (serverless) · via Statement Execution API with named parameter `release_id` (the same way the SQL editor binds `:release_id`)
- Scratch schema `dev_catalog.ops_t044` created with **the same table definition** as `ops.release_registry` (`CREATE TABLE … LIKE`, appendOnly = true) · SQL files rewritten only `ops.` → `ops_t044.` (count checked, no leftovers) · schema **dropped** at the end · real `ops` untouched
- Package under test: real GitHub Release `mdf-44d14f829e93` (8 assets)

## Probes (read-only, real `ops`)
| Input | Result |
|---|---|
| `mdf-ef2f425903b6` (registered) | format OK · guard OK |
| `x'; DROP` | stmt 1 `[BAD_RELEASE_ID]` — nothing read |
| `mdf-000000000000` (no folder) | stmt 2 `CF_PATH_DOES_NOT_EXIST_FOR_READ_FILES` (Databricks' own error, before any insert) |
| `mdf-747738df7af8` (spike folder, old manifest without `release_id`) | `[RELEASE_ID_MISMATCH] … <ไม่มี release_id: manifest รุ่นเก่า>` (first run returned `null` message → fixed with `coalesce`) |

## Negative / positive cases (scratch schema)
| # | Case | Guard (stmt 2) | Insert (stmt 3) rows |
|---|---|---|---|
| C1 | 1 byte changed in a resolved file | `[TAMPERED] … sha256 ไม่ตรง manifest` | 0 (insert run anyway) |
| C2 | resolved file missing | `[TAMPERED] … หายไปจาก Volume` | – |
| C3 | extra file | `[TAMPERED] พบไฟล์ที่ไม่มีใน manifest` | – |
| C4 | no manifest.json (partial copy) | `[RELEASE_NOT_FOUND]` | – |
| C5 | validation-report changed | `[TAMPERED] validation-report.json …` | – |
| C6 | good package under another folder name | `[RELEASE_ID_MISMATCH]` | 0 (insert run anyway) |
| C7 | activate before register | `[NOT_REGISTERED]` | 0 |
| | **rows after C1–C7** | | **0** |
| P1 | good package: register → register again → activate → activate again | OK · OK · OK · `SKIP` | 1 · 0 · 1 · 0 |
| P2 | resolved file changed after register | `[TAMPERED]` (caught before hash-conflict) | – |
| P3 | consistent repackage (file + manifest changed together) under the registered id | `[HASH_CONFLICT] … ถูก register ไว้แล้วด้วย manifest_sha256 อื่น` | 0 |

Final scratch registry: REGISTERED 1 + ACTIVATED 1, `actor = manual-ui`, `github_release_url` filled.

## Raw (masked)
```
C:\Users\User\AppData\Local/Temp/t044/reg.sql:7
C:\Users\User\AppData\Local/Temp/t044/act.sql:6
== C1 one byte changed in a resolved file
{"n": 2, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [TAMPERED] ไฟล์ silver.cc.customer.resolved.json sha256 ไม่ตรง manifest SQLSTATE: P0001", "rows": null}
{"n": 3, "state": "SUCCEEDED", "error": "", "rows": [["0", "0"]]}
{"n": 4, "state": "SUCCEEDED", "error": "", "rows": null}
== C2 file missing
{"n": 2, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [TAMPERED] ไฟล์ bronze.cc.customer.resolved.json หายไปจาก Volume SQLSTATE: P0001", "rows": null}
== C3 extra file
{"n": 2, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [TAMPERED] พบไฟล์ที่ไม่มีใน manifest: sneaky.json SQLSTATE: P0001", "rows": null}
== C4 no manifest.json (partial copy)
{"n": 2, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [RELEASE_NOT_FOUND] ไม่พบ manifest.json ในโฟลเดอร์ release (ยังไม่ sealed หรือ release_id ผิด) SQLSTATE: P0001", "rows": null}
== C5 validation-report tampered
{"n": 2, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [TAMPERED] validation-report.json หายไปหรือ sha256 ไม่ตรง manifest SQLSTATE: P0001", "rows": null}
== C6 folder name != manifest.release_id (copied under another id)
{"n": 2, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [RELEASE_ID_MISMATCH] manifest มี mdf-44d14f829e93 แต่ระบุ mdf-aaaaaaaaaaaa SQLSTATE: P0001", "rows": null}
{"n": 3, "state": "SUCCEEDED", "error": "", "rows": [["0", "0"]]}
== C7 activate before register
{"n": 1, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [NOT_REGISTERED] mdf-44d14f829e93 ยังไม่มีแถว REGISTERED — รัน register_release.sql ก่อน SQLSTATE: P0001", "rows": null}
{"n": 2, "state": "SUCCEEDED", "error": "", "rows": [["0", "0"]]}
== rows after all negatives (expect none)
{"stmt": "SELECT count(*) FROM dev_catalog.ops_t044.release_registry", "state": "SUCCEEDED", "error": "", "rows": [["0"]]}
== P1 good package: register, register again, activate, activate again
{"n": 1, "state": "SUCCEEDED", "error": "", "rows": [["OK — รูปแบบ release_id ถูกต้อง"]]}
{"n": 2, "state": "SUCCEEDED", "error": "", "rows": [["OK — ผ่านทุกข้อ รัน statement ถัดไปได้"]]}
{"n": 3, "state": "SUCCEEDED", "error": "", "rows": [["1", "1"]]}
{"n": 4, "state": "SUCCEEDED", "error": "", "rows": [["mdf-44d14f829e93", "REGISTERED", "3cdfa4666022d08da773d096011166057b47e92ca3b36432a6b876d3cf2dc2be", "6", "manual-ui", "2026-09-27T10:39:02.084Z"]]}
{"n": 2, "state": "SUCCEEDED", "error": "", "rows": [["OK — ผ่านทุกข้อ รัน statement ถัดไปได้"]]}
{"n": 3, "state": "SUCCEEDED", "error": "", "rows": [["0", "0"]]}
{"n": 4, "state": "SUCCEEDED", "error": "", "rows": [["mdf-44d14f829e93", "REGISTERED", "3cdfa4666022d08da773d096011166057b47e92ca3b36432a6b876d3cf2dc2be", "6", "manual-ui", "2026-09-27T10:39:02.084Z"]]}
{"n": 1, "state": "SUCCEEDED", "error": "", "rows": [["OK — รัน statement ถัดไปได้"]]}
{"n": 2, "state": "SUCCEEDED", "error": "", "rows": [["1", "1"]]}
{"n": 3, "state": "SUCCEEDED", "error": "", "rows": [["mdf-44d14f829e93", "3cdfa4666022d08da773d096011166057b47e92ca3b36432a6b876d3cf2dc2be", "2026-09-27T10:39:26.392Z"]]}
{"n": 1, "state": "SUCCEEDED", "error": "", "rows": [["SKIP — release นี้เป็น active อยู่แล้ว statement ถัดไปจะไม่เพิ่มแถว"]]}
{"n": 2, "state": "SUCCEEDED", "error": "", "rows": [["0", "0"]]}
== P2 hash conflict: change a file after register
{"n": 2, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [TAMPERED] ไฟล์ silver.cc.customer.resolved.json sha256 ไม่ตรง manifest SQLSTATE: P0001", "rows": null}
== final rows
{"stmt": "SELECT release_id, event, substr(manifest_sha256,1,12), actor, github_release_url FROM dev", "state": "SUCCEEDED", "error": "", "rows": [["mdf-44d14f829e93", "REGISTERED", "3cdfa4666022", "manual-ui", "https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-44d14f829e93"], ["mdf-44d14f829e93", "ACTIVATED", "3cdfa4666022", "manual-ui", "https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-44d14f829e93"]]}
EXIT=0

== P3 consistent repackage under a registered id
{"n": 2, "state": "FAILED", "error": "[USER_RAISED_EXCEPTION] [HASH_CONFLICT] release นี้ถูก register ไว้แล้วด้วย manifest_sha256 อื่น (3cdfa4666022…) — release ถูกแก้หลัง seal SQLSTATE: P0001", "rows": null}
{"n": 3, "state": "SUCCEEDED", "error": "", "rows": [["0", "0"]]}
{"stmt": "SELECT event, count(*) FROM dev_catalog.ops_t044.release_registry GROUP BY event ORDER BY ", "state": "SUCCEEDED", "error": "", "rows": [["ACTIVATED", "1"], ["REGISTERED", "1"]]}
{"stmt": "DROP SCHEMA dev_catalog.ops_t044 CASCADE", "state": "SUCCEEDED", "error": "", "rows": null}
{"stmt": "SHOW SCHEMAS IN dev_catalog", "state": "SUCCEEDED", "error": "", "rows": [["default"], ["information_schema"], ["ops"]]}

```
