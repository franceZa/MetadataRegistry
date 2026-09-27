-- T-37 · FR-J.3 (Phase 2 part) · ADR-004 · A-21
-- UC bootstrap for release delivery. Idempotent: every statement is IF NOT EXISTS.
-- Catalog is a parameter: replace ${catalog} (validated ^[a-z_][a-z0-9_]*$) before running.
-- One statement per `;` (SQL Statement Execution API runs one statement per call).
-- Grants for a CD service principal are deferred to Phase 3 (Free Edition has one user, no SP/WIF).

CREATE SCHEMA IF NOT EXISTS ${catalog}.ops
  COMMENT 'mdf ops: release delivery (Phase 2)';

CREATE VOLUME IF NOT EXISTS ${catalog}.ops.files
  COMMENT 'mdf release packages: releases/<release_id>/ (immutable by CD-3 rule)';

CREATE TABLE IF NOT EXISTS ${catalog}.ops.release_registry (
  release_id          STRING    NOT NULL COMMENT 'mdf-<sha12>',
  event               STRING    NOT NULL COMMENT 'REGISTERED | ACTIVATED',
  source_commit       STRING    NOT NULL COMMENT 'full 40-char git sha',
  manifest_sha256     STRING    NOT NULL COMMENT 'sha256 of manifest.json in the Volume',
  file_count          INT       NOT NULL,
  volume_path         STRING    NOT NULL,
  github_release_url  STRING,
  ci_run_url          STRING,
  actor               STRING    NOT NULL COMMENT 'who ran CD (manual | github-oidc)',
  event_ts            TIMESTAMP NOT NULL
)
USING DELTA
COMMENT 'Append-only log of releases delivered (REGISTERED) and activated (ACTIVATED). AS-23'
TBLPROPERTIES ('delta.appendOnly' = 'true');
