# T-52 — Evidence run (SWE)

## Scope
`.github/workflows/release.yml` publish job now attaches a single `<release_id>.zip` asset,
idempotency step is zip-aware (extracts via `scripts/safe_unzip.py` before comparing
`manifest.json`), `manifest_sha256` is computed once and echoed into both the GitHub Release
notes and the `$GITHUB_STEP_SUMMARY`. `scripts/deliver_release.sh` CD-1 picks the download
method from the real asset list of the release (`gh release view --json assets`): a
`<release_id>.zip` asset → download that file only and extract with the new zip-slip-guarded
`scripts/safe_unzip.py`; no such asset (v1 legacy) → old flat multi-file download, unchanged.
`tests/fakes/fake_gh.py` extended to support `release view --json assets -q '.assets[].name'`
and `release download ... -p PATTERN`.

## Files changed
- `.github/workflows/release.yml` — publish job: build zip, compute digest once, idempotency
  step downloads+extracts the zip via `scripts/safe_unzip.py`, `gh release create` attaches the
  single zip with `manifest_sha256` in `--notes`, job summary echoes the same digest.
- `scripts/deliver_release.sh` — CD-1 only: chooses zip vs legacy flat download from
  `gh release view --json assets`; zip path extracted via `scripts/safe_unzip.py`.
- `scripts/safe_unzip.py` (new) — stdlib `zipfile` only; validates every entry (absolute path,
  drive letter, backslash, `..` traversal, symlink `external_attr`) BEFORE writing anything;
  exits 1 with `[ZIP_SLIP] <reason>: <entry>` on the first bad entry; nothing is written on
  rejection. Used by both `release.yml` and `deliver_release.sh` CD-1.
- `tests/fakes/fake_gh.py` — added `release view --json assets -q '.assets[].name'` (lists file
  names under `$FAKE_GH_RELEASES/<id>/`) and `-p PATTERN` on `release download` (fnmatch over
  those file names).
- `tests/test_release_workflow.py` — updated `test_ac36_release_named_by_release_id_with_all_assets`
  and `test_ac36_existing_release_skip_if_identical_fail_if_different` (old flat-asset
  assertions replaced with zip-asset assertions); added
  `test_ac51_release_zip_built_without_wrapping_folder`,
  `test_ac51_manifest_sha256_in_notes_and_job_summary`.
- `tests/test_deliver_release.py` — added `_add_zip_asset` helper +
  `test_cd1_zip_happy_path_downloads_and_extracts`,
  `test_cd1_zip_slip_rejected_before_cd2_no_files_outside_work`,
  `test_cd1_zip_slip_absolute_path_rejected`,
  `test_v1_legacy_release_without_zip_asset_still_downloads_cd1`.

## Commands run (real output)

```
$ bash -n scripts/deliver_release.sh && echo BASH_SYNTAX_OK
BASH_SYNTAX_OK
```

```
$ command -v actionlint; command -v shellcheck
(both empty — neither actionlint nor shellcheck is installed on this machine; NOT run, not
claimed as passing)
```

```
$ uv run pytest -q tests/test_release_workflow.py tests/test_deliver_release.py
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir
......................................                                   [100%]
38 passed
```

```
$ uv run pytest -q   (full suite, background run, exit_code 0)
warning: Failed to set cwd to temp dir
warning: Failed to set cwd to temp dir
........................................................................ [ 34%]
........................................................................ [ 69%]
...............................................................          [100%]
207 passed
```
(baseline before T-52 was 201 passed; +6 net = 2 static tests added to
`tests/test_release_workflow.py` + 4 RUN+OBSERVE tests added to `tests/test_deliver_release.py`;
2 pre-existing static tests were edited in place, not added/removed, so the count nets to +6.
No failures, no errors.)

## AC mapping
- AC-51 (single zip asset, no wrapper folder): `test_ac36_release_named_by_release_id_with_all_assets`,
  `test_ac51_release_zip_built_without_wrapping_folder` — PASS (static).
- AC-51 And (manifest_sha256 in notes + job summary, matching): `test_ac51_manifest_sha256_in_notes_and_job_summary`
  — PASS (static; both use `steps.digest.outputs.manifest_sha256`, the same value).
- AC-51 And (idempotency zip-aware): `test_ac36_existing_release_skip_if_identical_fail_if_different`
  — PASS (static: downloads the zip with `-p ${RELEASE_ID}.zip`, extracts with
  `scripts/safe_unzip.py`, then `verify-package`/`diff` as before).
- AC-51 And (CD-1 zip-slip guard, nothing written outside `$WORK`):
  `test_cd1_zip_slip_rejected_before_cd2_no_files_outside_work`,
  `test_cd1_zip_slip_absolute_path_rejected` — PASS (RUN+OBSERVE: real bash script, real fake
  `gh`, real `scripts/safe_unzip.py`, asserts no Databricks call beyond the read-only preflight
  and no escaped file on disk).
- AC-51 And (v1 legacy still downloads without a `.zip` asset):
  `test_v1_legacy_release_without_zip_asset_still_downloads_cd1` (plus every pre-existing
  `test_deliver_release.py` test, none of which adds a `.zip` asset, exercising the same
  fallback) — PASS (RUN+OBSERVE).
- CD-1 zip happy path: `test_cd1_zip_happy_path_downloads_and_extracts` — PASS (RUN+OBSERVE:
  real `gh release download -p`, real `scripts/safe_unzip.py` extraction, byte-for-byte compare
  against the fixture package).

Steps 1–3 of the "แผนเทียบผลจริง" table (a real `release.yml` run on `master`, a second push
with the same commit, and the real Release page/run URL) cannot be produced from this sandbox —
no git write, no GitHub connection, per H-101 correction #6. Marked "พิสูจน์ใน T-53" in the
ticket, not claimed as passed. Step 4 (CD-1 zip-slip guard + v1 fallback) is proven above by
pytest against the fake `gh`/`databricks` CLIs (RUN+OBSERVE).

## Deviations from H-101 / ticket text
- Ticket's "Implementation notes" example builds the zip as
  `gh release create ... "build/${RELEASE_ID}.zip"` — implemented exactly as written; used the
  `zip` CLI (available on `ubuntu-latest`), not python, per H-101 correction #3 ("เลือกเครื่องมือเองได้").
- `deliver_release.sh` CD-1 downloads the zip to a separate `$WORK/zip-download/` dir first
  (not directly into `$PKG`) so `scripts/safe_unzip.py` can create `$PKG` itself from an empty
  state — matches ticket note "สร้างโฟลเดอร์เปล่าก่อน" while keeping the raw downloaded zip
  out of the extracted tree.
- No other deviations.
