-- T-44 · FR-L.13 / AC-44 · delivery_mode: manual — step M-6 of runbooks/release-delivery.md
-- Makes a REGISTERED release the active one by appending an ACTIVATED row (never updates/deletes).
-- Same rules as job mdf_release_register_dev mode=activate: must already be REGISTERED; skip if it
-- is already the latest ACTIVATED. Rollback = run this with an older release_id.
--
-- How to use: paste, set parameter  release_id , run ALL statements.
-- Catalog is dev_catalog. For another env, replace dev_catalog below.

-- (1) GUARD
SELECT CASE
  WHEN NOT (:release_id RLIKE '^mdf-[0-9a-f]{12}$')
    THEN raise_error(concat('[BAD_RELEASE_ID] release_id ต้องเป็น mdf-<sha12> (ได้ ''', :release_id, ''')'))
  WHEN NOT EXISTS (SELECT 1 FROM dev_catalog.ops.release_registry
                   WHERE release_id = :release_id AND event = 'REGISTERED')
    THEN raise_error(concat('[NOT_REGISTERED] ''', :release_id, ''' ยังไม่มีแถว REGISTERED — รัน register_release.sql ก่อน'))
  WHEN (SELECT max_by(release_id, event_ts) FROM dev_catalog.ops.release_registry WHERE event = 'ACTIVATED') = :release_id
    THEN 'SKIP — release นี้เป็น active อยู่แล้ว statement ถัดไปจะไม่เพิ่มแถว'
  ELSE 'OK — รัน statement ถัดไปได้'
END AS guard;

-- (2) INSERT ACTIVATED (conditions repeated: inserts nothing unless the guard would say OK)
INSERT INTO dev_catalog.ops.release_registry
SELECT r.release_id, 'ACTIVATED', r.source_commit, r.manifest_sha256, r.file_count, r.volume_path,
       r.github_release_url, r.ci_run_url, 'manual-ui', current_timestamp()
FROM dev_catalog.ops.release_registry r
WHERE r.release_id = :release_id AND :release_id RLIKE '^mdf-[0-9a-f]{12}$'
  AND r.event = 'REGISTERED'
  AND coalesce((SELECT max_by(release_id, event_ts) FROM dev_catalog.ops.release_registry WHERE event = 'ACTIVATED'), '') <> :release_id
LIMIT 1;

-- (3) RESULT — the active release is the latest ACTIVATED row
SELECT max_by(release_id, event_ts) AS active_release_id,
       max_by(manifest_sha256, event_ts) AS manifest_sha256,
       max(event_ts) AS activated_at
FROM dev_catalog.ops.release_registry
WHERE event = 'ACTIVATED';
