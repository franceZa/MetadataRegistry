-- T-44 · FR-L.13 / AC-44 · delivery_mode: manual — step M-4 of runbooks/release-delivery.md
-- Verifies a release folder in the Volume and appends ONE REGISTERED row, with the same checks
-- and the same skip/fail rules as job mdf_release_register_dev (src/mdf/register.py).
--
-- How to use (Databricks SQL editor, any SQL warehouse):
--   1. Paste this whole file. 2. Set the parameter  release_id  (e.g. mdf-ef2f425903b6).
--   3. Run ALL statements. Statements 1–2 raise a Thai error and stop if anything is wrong;
--      statement 3 inserts only when nothing is wrong; statement 4 shows the result.
--      If the folder does not exist at all, statement 2 stops with Databricks' own PATH_NOT_FOUND.
-- Catalog is dev_catalog. For another env, replace dev_catalog in the 3 places below.
-- Idempotent: running it again for an already-registered release inserts nothing.

-- (1) FORMAT CHECK — before any file is read.
SELECT CASE WHEN :release_id RLIKE '^mdf-[0-9a-f]{12}$' THEN 'OK — รูปแบบ release_id ถูกต้อง'
            ELSE raise_error(concat('[BAD_RELEASE_ID] release_id ต้องเป็น mdf-<sha12> (ได้ ''', :release_id, ''')')) END AS format_check;

-- (2) GUARD — raises on the first problem found, inserts nothing.
WITH
rid AS (SELECT :release_id AS release_id),
vol AS (
  SELECT regexp_extract(f.path, '[^/]+$', 0) AS name, sha2(f.content, 256) AS sha256, f.content
  FROM read_files(concat('/Volumes/dev_catalog/ops/files/releases/', :release_id, '/'), format => 'binaryFile') AS f
),
man_raw AS (SELECT content, sha256 AS manifest_sha256 FROM vol WHERE name = 'manifest.json'),
man AS (
  SELECT manifest_sha256,
         from_json(CAST(content AS STRING),
           'release_id STRING, source_commit STRING, file_count INT, preview BOOLEAN, validation_report_sha256 STRING, ci_run_url STRING, files ARRAY<STRUCT<path: STRING, sha256: STRING>>') AS m
  FROM man_raw
),
listed AS (SELECT f.path AS name, f.sha256 FROM man LATERAL VIEW explode(m.files) t AS f),
problems AS (
  SELECT 1 AS ord, '[RELEASE_NOT_FOUND] ไม่พบ manifest.json ในโฟลเดอร์ release (ยังไม่ sealed หรือ release_id ผิด)' AS msg
  WHERE NOT EXISTS (SELECT 1 FROM man_raw)
  UNION ALL
  SELECT 2, concat('[RELEASE_ID_MISMATCH] manifest มี ''', coalesce(m.release_id, '<ไม่มี release_id: manifest รุ่นเก่า>'),
                   ''' แต่ระบุ ''', (SELECT release_id FROM rid), '''')
  FROM man WHERE m.release_id IS NULL OR m.release_id <> (SELECT release_id FROM rid)
  UNION ALL
  SELECT 3, '[PREVIEW_PACKAGE] เป็น preview package (หรือ manifest ไม่มี field preview) — ห้าม register'
  FROM man WHERE coalesce(m.preview, true)
  UNION ALL
  SELECT 4, concat('[TAMPERED] ไฟล์ ''', coalesce(l.name, '?'), ''' หายไปจาก Volume')
  FROM listed l LEFT ANTI JOIN vol v ON v.name = l.name
  UNION ALL
  SELECT 5, concat('[TAMPERED] ไฟล์ ''', coalesce(l.name, '?'), ''' sha256 ไม่ตรง manifest')
  FROM listed l JOIN vol v ON v.name = l.name WHERE v.sha256 <> l.sha256
  UNION ALL
  SELECT 6, concat('[TAMPERED] พบไฟล์ที่ไม่มีใน manifest: ''', v.name, '''')
  FROM vol v WHERE v.name NOT IN ('manifest.json', 'validation-report.json')
    AND NOT EXISTS (SELECT 1 FROM listed l WHERE l.name = v.name)
  UNION ALL
  SELECT 7, '[TAMPERED] validation-report.json หายไปหรือ sha256 ไม่ตรง manifest'
  FROM man WHERE NOT EXISTS (SELECT 1 FROM vol v WHERE v.name = 'validation-report.json' AND v.sha256 = man.m.validation_report_sha256)
  UNION ALL
  SELECT 8, concat('[HASH_CONFLICT] release นี้ถูก register ไว้แล้วด้วย manifest_sha256 อื่น (', substr(r.manifest_sha256, 1, 12), '…) — release ถูกแก้หลัง seal')
  FROM dev_catalog.ops.release_registry r, man
  WHERE r.release_id = (SELECT release_id FROM rid) AND r.event = 'REGISTERED' AND r.manifest_sha256 <> man.manifest_sha256
)
SELECT CASE WHEN count(*) = 0 THEN 'OK — ผ่านทุกข้อ รัน statement ถัดไปได้'
            ELSE raise_error(coalesce(min_by(msg, ord), '[VERIFY_FAILED] ตรวจไม่ผ่าน (ไม่ทราบสาเหตุ)')) END AS guard
FROM problems;

-- (3) INSERT — repeats every check inside the same statement, so it can never insert on its own.
INSERT INTO dev_catalog.ops.release_registry
WITH
rid AS (SELECT :release_id AS release_id WHERE :release_id RLIKE '^mdf-[0-9a-f]{12}$'),
vol AS (
  SELECT regexp_extract(f.path, '[^/]+$', 0) AS name, sha2(f.content, 256) AS sha256, f.content
  FROM read_files(concat('/Volumes/dev_catalog/ops/files/releases/', :release_id, '/'), format => 'binaryFile') AS f
),
man AS (
  SELECT sha256 AS manifest_sha256,
         from_json(CAST(content AS STRING),
           'release_id STRING, source_commit STRING, file_count INT, preview BOOLEAN, validation_report_sha256 STRING, ci_run_url STRING, files ARRAY<STRUCT<path: STRING, sha256: STRING>>') AS m
  FROM vol WHERE name = 'manifest.json'
),
listed AS (SELECT f.path AS name, f.sha256 FROM man LATERAL VIEW explode(m.files) t AS f),
ok AS (
  SELECT man.* FROM man, rid
  WHERE man.m.release_id = rid.release_id AND NOT coalesce(man.m.preview, true)
    AND NOT EXISTS (SELECT 1 FROM listed l LEFT ANTI JOIN vol v ON v.name = l.name)
    AND NOT EXISTS (SELECT 1 FROM listed l JOIN vol v ON v.name = l.name WHERE v.sha256 <> l.sha256)
    AND NOT EXISTS (SELECT 1 FROM vol v WHERE v.name NOT IN ('manifest.json', 'validation-report.json')
                    AND NOT EXISTS (SELECT 1 FROM listed l WHERE l.name = v.name))
    AND EXISTS (SELECT 1 FROM vol v WHERE v.name = 'validation-report.json' AND v.sha256 = man.m.validation_report_sha256)
    AND NOT EXISTS (SELECT 1 FROM dev_catalog.ops.release_registry r
                    WHERE r.release_id = rid.release_id AND r.event = 'REGISTERED')
)
SELECT ok.m.release_id, 'REGISTERED', ok.m.source_commit, ok.manifest_sha256, ok.m.file_count,
       concat('/Volumes/dev_catalog/ops/files/releases/', ok.m.release_id),
       concat('https://github.com/franceZa/MetadataRegistry/releases/tag/', ok.m.release_id),
       ok.m.ci_run_url, 'manual-ui', current_timestamp()
FROM ok;

-- (4) RESULT — expect exactly 1 REGISTERED row; compare manifest_sha256 with the GitHub asset digest.
SELECT release_id, event, manifest_sha256, file_count, actor, event_ts
FROM dev_catalog.ops.release_registry
WHERE release_id = :release_id
ORDER BY event_ts;
