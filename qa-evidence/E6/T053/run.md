# T-53 live acceptance — BLOCKED (manual UI portion outstanding)

## Scope and authorization

Executed H-117 under the user's APPROVED: PROD and explicit commit/push/PR/merge authorization. Data-plane access stayed within `dev_catalog.ops`; used existing profile `mdf-free`, Free Edition, existing SQL warehouse and existing register job. No paid resources were requested. Bundle deployment reported **0 resources created, 0 changed, 1 unchanged**. No HRM logs changed; no QA signoff asserted.

No local full-suite rerun. Parent-provided batch result: 267 passed, exit 0. The permitted change to `tests/test_deliver_release.py:467` shortened its E501 comment only. `uv run ruff check src tests` and `git diff --check` passed. The earlier broader `ruff check .` failed on out-of-scope script/evidence lint; those files were not refactored.

## Published artifact and CI

- Feature commit: `5fe91614735bc65e78cd3a4acf4ad4470a7b029b` (51 files of approved round11+12 work).
- PR: https://github.com/franceZa/MetadataRegistry/pull/8
- CI: https://github.com/franceZa/MetadataRegistry/actions/runs/37332685864 — **success**.
- `gh pr checks 8`: Validate/compile/test, Bandit and Gitleaks all **pass**; verified before merge.
- Merge commit: `b255065b505d7babe95b5af2a4a6869f4d45cf81`; remote state **MERGED**, `mergedAt=2026-10-05T15:30:50Z`.
- Release workflow: https://github.com/franceZa/MetadataRegistry/actions/runs/37333436149 — **success**.
- Release: https://github.com/franceZa/MetadataRegistry/releases/tag/mdf-b255065b505d
- Exactly one asset: `mdf-b255065b505d.zip`, 21723 bytes.
- Zip SHA-256: `6b5ec9d560790cc1242b4d792fa03dd9511cec388e7ce6882c1b9d06324f7cf8` (matches GitHub asset digest).
- Manifest SHA-256: `4704afd38d1fd99e110c2a99af25275e32cf724ee0cac617da1f5f320a809e7f`.

Real downloaded zip was checked against the real CD-4 Volume read-back: all eleven files match byte-for-byte. Manifest is v3, non-preview, source commit equals the merge commit, `file_count=9`. Manifest digest matches release notes, registry, and the live workflow's Job Summary environment/output commands. The successful `Next steps (job summary)` step writes this digest and `calendar PENDING_OWNER: cc.credit_card, cc.credit_card_txn, cc.customer` to `$GITHUB_STEP_SUMMARY`; see `release.log`. This is workflow execution evidence, **not a claim of browser inspection of the rendered summary**.

## Acceptance matrix

| Ticket criterion | Result | Grounding / outstanding work |
|---|---|---|
| (1) Approved publication, real zip, digest/summary | PASS via live workflow logs | PR and release links above; `ci.log`, `release.log`, `release-metadata.json`, `artifact-verification.json` |
| (2) U2M CD-1…8 | PASS | Real script exit 0, Volume read-back verification, `REGISTERED actor=u2m`, activation; `u2m.log`, `delivery-evidence.md`, `registry-observation.json` |
| (3) Distinct release, manual UI M-1…M-7 | **BLOCKED** | Local browser invocation timed out before page inspection; no distinct manual v3 release published/delivered and no manual rows inserted |
| (4) v1 rollback + warning | PARTIAL / exact SQL UI step **BLOCKED** | Real rollback via existing U2M register job, v1 active read-back and `[WARN] legacy flat layout` verified. Did **not** execute `sql/manual/activate_release.sql` through UI; its hard-coded `manual-ui` actor was not falsely emitted through API |
| (5) v3 9+2, file_count 9, calendar/reader/pii/pci | PASS via live CLI/workflow logs | `volume-listing.json`, `manifest-volume.json`, `resolved-sample.json`, registry and artifact assertions; rendered Job Summary not independently opened |
| (6) Missing ODCS rejection through manual UI; zero insert | **BLOCKED / NOT RUN** | No incomplete manual upload and no negative SQL invocation. No fabricated `[TAMPERED]` result or zero-insert claim |

## Real U2M execution

Executed in a detached worktree at the published tag, preserving the original feature branch and work. Windows scratch setup initially failed because nested subprocess selected the wrong Bash and inherited a nonexistent temporary directory; a fresh uv environment and explicit Git Bash executable resolved it. These failures occurred **before delivery began**.

Reproducible commands, from a fresh worktree at `mdf-b255065b505d`:

```bash
git fetch origin master --tags
git worktree add --detach C:/Users/User/AppData/Local/Temp/t053-release mdf-b255065b505d
# In Git Bash: cd /c/Users/User/AppData/Local/Temp/t053-release
export UV_PROJECT_ENVIRONMENT=C:/Users/User/AppData/Local/Temp/t053-venv
export TMPDIR=C:/Users/User/AppData/Local/Temp TEMP=C:/Users/User/AppData/Local/Temp TMP=C:/Users/User/AppData/Local/Temp
export DATABRICKS_CONFIG_PROFILE=mdf-free MDF_CATALOG=dev_catalog MDF_TARGET=dev MDF_ACTOR=u2m
uv sync --locked
bash scripts/deliver_release.sh mdf-b255065b505d
```

Registry UTC observations:

| Event | release_id | file_count | actor | event_ts |
|---|---|---:|---|---|
| REGISTERED | mdf-b255065b505d | 9 | u2m | 2026-10-05 15:36:35.097825 |
| ACTIVATED | mdf-b255065b505d | 9 | u2m | 2026-10-05 15:38:05.184301 |
| ACTIVATED (rollback) | mdf-ef2f425903b6 | 6 | u2m | 2026-10-05 15:41:30.794287 |
| ACTIVATED (restore) | mdf-b255065b505d | 9 | u2m | 2026-10-05 15:43:01.327298 |

Volume listing is the root plus `cc/` listing. CLI v1.17.0 rejects `fs ls --recursive` / the runbook's recursive shorthand, so actual `fs ls` calls enumerated both directories. The resulting nine `cc/` files are six resolved JSON and three ODCS YAML, with `manifest.json` and `validation-report.json` at root. A real `fs cat` of `cc/bronze.cc.customer.resolved.json` shows `calendar.status=PENDING_OWNER`, `reader`, and `pii,pci` on every schema element. Config references to other schemas are inert content; those objects were not accessed.

Read-only reproduction from the original repo root:

```bash
python qa-evidence/E6/T053/observe.py
python qa-evidence/E6/T053/verify_artifacts.py
# Explicit listings with profile mdf-free:
databricks fs ls dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-b255065b505d --profile mdf-free --output json
databricks fs ls dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-b255065b505d/cc --profile mdf-free --output json
databricks fs cat dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-b255065b505d/cc/bronze.cc.customer.resolved.json --profile mdf-free
```

## Real v1 rollback and restoration

Existing `mdf-ef2f425903b6` was confirmed in Volume and REGISTERED in the registry; no v1 fixture was fabricated. From the published worktree:

```bash
databricks bundle run -t dev mdf_release_register_dev --params release_id=mdf-ef2f425903b6,mode=activate,actor=u2m
# Read back latest ACTIVATED: mdf-ef2f425903b6 (rollback-registry.json)
databricks fs cp -r dbfs:/Volumes/dev_catalog/ops/files/releases/mdf-ef2f425903b6 C:/Users/User/AppData/Local/Temp/t053-v1
uv run mdf verify-package C:/Users/User/AppData/Local/Temp/t053-v1 --expect-release-id mdf-ef2f425903b6
# Output: OK, files=6; [WARN] legacy flat layout (manifest_version 1)
databricks bundle run -t dev mdf_release_register_dev --params release_id=mdf-b255065b505d,mode=activate,actor=u2m
```

Both jobs returned SUCCESS and exact targets were read back. **Final active release: `mdf-b255065b505d` (v3), actor `u2m`, UTC `2026-10-05 15:43:01.327298`.** The existing bundle's active_release_id had been set to this v3 by CD-8; the rollback jobs did not redeploy it.

## Manual UI blocker and exact remaining steps

`browser_exec(local=True)` attempted to open the user's Databricks session using the valid profile's host without printing it. It returned `timed out after 420.0s`; there was no screenshot/page/login-wall result. This is a **browser transport/session availability blocker**, not evidence of invalid Databricks OAuth. No retry loop, credential guessing, new browser login, or API substitution for manual acceptance was attempted.

1. Restore a working local browser session (or user performs the UI checklist). Stop for user login if a login wall appears.
2. Publish a **second distinct real v3 release** through an approved source/evidence commit, PR, passing checks and merge. Do not rename/repackage the first release or reuse a legacy release as v3. No second release was created in this attempt because manual UI was unavailable; additional publication scope should be confirmed by HRM/user.
3. For that release follow M-1…M-7 in `runbooks/release-delivery.md` through real UI. Upload root files and resolved JSON **without ODCS YAML** initially.
4. Query/save registry count for that distinct release, run complete `sql/manual/register_release.sql` with that release_id, capture real `[TAMPERED]`, and query/save unchanged count (zero new rows).
5. Upload all actual `.odcs.yaml`, rerun SQL, save REGISTERED/ACTIVATED `actor=manual-ui` and matching Job Summary digest.
6. Execute `sql/manual/activate_release.sql` in the real SQL UI for `mdf-ef2f425903b6`; capture new ACTIVATED and real legacy warning verification. Restore the preferred latest v3 and read back final active state.
7. Open rendered GitHub Job Summary if visual/UI evidence is required in addition to the existing successful execution logs. Append masked evidence, then request QA review. Do not mark COMPLETED before these steps.

## Evidence index

- `ci.log`, `release.log`, `release-metadata.json`: actual remote CI/publication and summary execution.
- `u2m.log`, `delivery-evidence.md`: actual delivery, masked host/email.
- `volume-listing.json`, `manifest-volume.json`, `resolved-sample.json`: live Volume observations.
- `registry-observation.json`: final exact registry query results; `rollback-registry.json`: intermediate v1 active proof.
- `rollback-job.log`, `rollforward-job.log`, `v1-listing.log`, `v1-verify.log`: actual rollback, warning and restoration.
- `artifact-verification.json`: real zip/hash/count/Volume assertions, PASS.
- `observe.py`, `verify_artifacts.py`: reproducible read-only evidence checks; no full suite.

Private Databricks hosts/emails are masked as `<host>`/`<user>`. No credentials are stored. Evidence and H-118 are left in the authorized working tree for HRM review; they are not a second production publication.
