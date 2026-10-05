# T-48 evidence — compile/package layout v2 per-source, manifest_version 2

Repo root: `E:/OneDrive - Thammasat University/เดสก์ท็อป/datalake/MetadataRegistry/MetadatasRegistry`
HEAD at time of work: `5a9126bc35c9fac28bf7b2a222eb9ac501303924` (dirty tree, T-49/T-50/T-52 uncommitted work already present)

## 1. Code changes

| File | Change |
|---|---|
| `src/mdf/compile.py:1-4` | added `import shutil` |
| `src/mdf/compile.py:80-84` | clean stale `build/<env>/resolved/` (flat leftovers) with `shutil.rmtree` **after** validation passes, before any write (FR-B.6, only under `build/`) |
| `src/mdf/compile.py:165-167` | create `output_dir / ds.source` per dataset (`source_dir`), `mkdir(parents=True, exist_ok=True)` |
| `src/mdf/compile.py:199` | write to `source_dir / f"{layer}.{ds.source}.{ds.dataset}.resolved.json"` instead of flat `output_dir` |
| `src/mdf/package.py:14` | `MANIFEST_VERSION = 1` → `MANIFEST_VERSION = 2` (comment retains v1 = legacy, still read by `verify_package` per T-49) |
| `src/mdf/package.py:222-233` | `build_package` now derives `source = src.parent.name` (compile_project already lays out `<source>/<file>`), copies into `package_dir/<source>/`, records `files_meta` path as `f"{source}/{src.name}".replace("\\","/")` |
| `src/mdf/trace.py:13-20` | `load_dataset` reads `build/<env>/resolved/<source>/{layer}.{source}.{dataset}.resolved.json` (was flat) — fixes the sibling reader HRM flagged (H-103 correction #1) |
| `src/mdf/cli.py:24-27,98-99` | help/summary text updated to say `resolved/<source>/` instead of flat `resolved/` |

## 2. Test changes (path-only, HRM correction #4 — no assertions weakened)

| File | Change |
|---|---|
| `tests/test_compile.py` | updated flat-path assertion to `build/dev/resolved/cc`; added `test_ac46_multi_source_creates_per_source_subfolders` — builds a 2nd source `xyz` (copy of real `cc`) inside `tmp_path`, asserts 12 files land under `<source>/<file>` for both `cc` and `xyz`. `DataContract/` itself untouched. |
| `tests/test_package.py` | tampered/missing-file fixture paths updated to `<pkg>/cc/<file>` |
| `tests/test_cli.py` | tampered-file path updated to `<pkg>/cc/<file>` |
| `tests/test_e2e.py` | glob changed from `*.resolved.json` to `*/*.resolved.json` |
| `tests/test_register.py` | tampered-file path updated to `release_dir(...)/cc/<file>` |
| `tests/test_deliver_release.py` | Real `build_package` now emits genuine v2 (`<source>/` subfolders). Added `_flatten_to_v1()` helper + `pkg_v1` fixture value — HRM correction #4: real GitHub Release assets cannot contain folders, so the "legacy flat asset, no `.zip`" download path (`world["gh_rel"]`) must be genuinely flat; it is now built by flattening the real v2 package rather than asserting against the (now-v2) `pkg` directly. Removed the old `_make_v2_package` hand-built-fixture helper (no longer needed — T-48 done, `release["pkg"]` **is** the v2 fixture now); `v2_pkg` fixture returns `release["pkg"]` directly. Updated flat-layout assertions (`test_happy_path_cd1_to_cd8`, `test_ac39_partial_copy_is_resumed`, `test_sealed_with_different_manifest_fails_and_changes_nothing`, `test_v1_regression_flat_layout_warns_and_still_copies`) to compare against `world["pkg_v1"]`. `_add_zip_asset()` now zips the real v2 tree (with `<source>/` subfolders) since zip assets, unlike bare GitHub Release assets, can hold folders. |

## 3. Test run — targeted files (all touched by T-48)

```
$ uv run pytest tests/test_compile.py tests/test_package.py tests/test_trace.py tests/test_cli.py tests/test_e2e.py -q
............................................                             [100%]
44 passed
```

```
$ uv run pytest tests/test_register.py tests/test_deliver_release.py -q
........................................                                 [100%]
40 passed  (17 test_register.py + 23 test_deliver_release.py)
```
(Backgrounded — the deliver_release suite drives real bash + fake `gh`/`databricks` subprocesses per test and takes several minutes; run in background, log polled, per H-103 instruction.)

## 4. Full suite — `uv run pytest -q` (background, ~10 min baseline per H-103)

```
$ uv run pytest -q
.............F.......................................................... [ 34%]
.............................F.......................................... [ 69%]
................................................................         [100%]
2 failed, 206 passed (208 collected)

FAILED tests/test_ci_workflow.py::test_ac34_step_pytest
FAILED tests/test_manifest_release.py::test_ac35_release_manifest_has_fr_f2_fields
```

`test_ac34_step_pytest` fails only because it shells out to `uv run pytest -q` again and asserts `returncode == 0`; its failure is a pure symptom of `test_ac35_release_manifest_has_fr_f2_fields` failing in that inner run — same root cause, not two independent breaks.

`test_manifest_release.py:66` — `assert m["manifest_version"] == 1` — is a **pre-existing hardcoded v1 assertion outside T-48's allowed_writes** (H-103 lists only `src/mdf/compile.py, src/mdf/package.py, src/mdf/trace.py, src/mdf/cli.py, tests/test_compile.py, tests/test_package.py, tests/test_trace.py, tests/test_cli.py, tests/test_e2e.py, tests/test_register.py, tests/test_deliver_release.py`; `tests/test_manifest_release.py` is not in that list). `MANIFEST_VERSION` is now correctly `2` per AC-46/FR-D.8/FR-F.7, so this assertion is now stale by design of the ticket, but SWE has no write authority on this file. **See BLOCKED handoff H-104** — this is a scope gap for HRM to resolve (either grant a one-line write on this file, or dispatch a follow-up ticket).

No regression was introduced beyond this pre-existing test's now-stale hardcoded assertion — every file SWE is authorized to touch is green.

## 5. CLI verify (per H-103 §Verify)

```
$ rm -rf build && uv run mdf compile --env dev
✅ compile สำเร็จ: เขียน resolved JSON 6 ไฟล์ลง build/dev/resolved/<source>/
   - build\dev\resolved\cc\bronze.cc.credit_card.resolved.json
   - build\dev\resolved\cc\silver.cc.credit_card.resolved.json
   - build\dev\resolved\cc\bronze.cc.credit_card_txn.resolved.json
   - build\dev\resolved\cc\silver.cc.credit_card_txn.resolved.json
   - build\dev\resolved\cc\bronze.cc.customer.resolved.json
   - build\dev\resolved\cc\silver.cc.customer.resolved.json

$ uv run mdf package --env dev
✅ package สร้างที่: build\dev\release
   release_id=mdf-5a9126bc35c9 preview=true
   (โหมด preview — ใช้ --release เพื่อบังคับ release gate)

$ find build/dev/release -type f
build/dev/release/cc/bronze.cc.credit_card.resolved.json
build/dev/release/cc/bronze.cc.credit_card_txn.resolved.json
build/dev/release/cc/bronze.cc.customer.resolved.json
build/dev/release/cc/silver.cc.credit_card.resolved.json
build/dev/release/cc/silver.cc.credit_card_txn.resolved.json
build/dev/release/cc/silver.cc.customer.resolved.json
build/dev/release/manifest.json
build/dev/release/validation-report.json

$ python -c "import json; m=json.load(open('build/dev/release/manifest.json',encoding='utf-8')); print('manifest_version:', m['manifest_version']); [print(f['path']) for f in m['files']]"
manifest_version: 2
cc/bronze.cc.credit_card.resolved.json
cc/bronze.cc.credit_card_txn.resolved.json
cc/bronze.cc.customer.resolved.json
cc/silver.cc.credit_card.resolved.json
cc/silver.cc.credit_card_txn.resolved.json
cc/silver.cc.customer.resolved.json

$ uv run mdf verify-package build/dev/release
✅ package ผ่านการตรวจสอบ (OK): env=dev, files=6, release_id=mdf-5a9126bc35c9, manifest_sha256=45976ef07f52740df565b0389ac56b3f120f0c02f6d5a7d25ffc027c727c860e
```
No `[WARN]` line present (manifest_version 2, no legacy fallback warning).

```
$ uv run mdf trace silver.cc.credit_card_txn
📊 Lineage: dev_catalog.silver_cc.credit_card_txn
   Layer: silver · Config ID: silver.cc.credit_card_txn
   Landing: /Volumes/dev_catalog/landing_cc/files/credit_card_txn/
   Bronze input: dev_catalog.bronze_cc.credit_card_txn (contract cc.credit_card_txn, sha256 97bdbb222333…)
   Contract: cc.credit_card_txn v1.0.0
     file: DataContract/cc/contract/credit_card_txn.odcs.yaml
     sha256: 97bdbb222333523e09e72b71f5d1c0b4bf6fa0993396811fbc51090404d746d0
   Pipeline: DataContract/cc/pipeline/credit_card_txn.pipeline.yaml
     sha256: 9f51384306053c92ae5c5314e8be73fb83b7b12c1c339711e313d79e89f0bda4
   DQ library sha256: 1aaea8cf0c2655706b73fd94acf2eb91692f6539735308103b3fd8ea81932204
   Schema version: 1.0.0
```
`mdf trace` works after the compile layout change (trace.py fix confirmed).

`--release` was **not** forced per H-103 (tree is dirty from T-49/T-50/T-52 uncommitted work; would hit the release gate as expected and documented, not a bug).

## 6. Stale-cleanup regression check (HRM correction #2)

```
$ mkdir -p build/dev/resolved && echo STALE > build/dev/resolved/STALE_FLAT_FILE.resolved.json
$ uv run mdf compile --env dev >/dev/null
$ ls build/dev/resolved
cc
```
Stale flat file from a hypothetical pre-v2 compile is removed by the new `shutil.rmtree` cleanup before writing v2 output.

## 7. Determinism (AC-11)

```
$ uv run python -c "... compile twice, sha256 every file under build/dev/resolved ..."
identical: True 6
```

## 8. AC vs result

| AC | Result |
|---|---|
| AC-46 (>1 source → per-source folders both compile & package) | PASS — `tests/test_compile.py::test_ac46_multi_source_creates_per_source_subfolders` (12 files, 2 sources, `cc`/`xyz`); real repo `cc` verified live (§5) |
| manifest_version 2, `files[].path` = `<source>/<file>` POSIX, sorted | PASS — §5 manifest dump: `manifest_version: 2`, paths `cc/...`, alphabetically sorted |
| AC-11 determinism | PASS — §7 |
| `verify_package` passes real `mdf package --release`-equivalent output, no WARN | PASS — §5 (used `--env dev` preview build; `--release` blocked by dirty tree per H-103 note, not exercised here but `verify_package` logic identical either way; T-49's `verify_package` v2 path is exercised end-to-end) |
| Regression: single source (`cc` only) still gets `<source>/` (no flat fallback) | PASS — §5 real-repo compile has 1 source (`cc`), output is `build/dev/resolved/cc/...`, never flat |
| `trace.py` sibling fix (H-103 correction #1) | PASS — §5 `mdf trace silver.cc.credit_card_txn` succeeds |
| Stale flat cleanup (H-103 correction #2) | PASS — §6 |
| No regression on T-49/T-50/T-52 fixtures/behaviour | PASS — `tests/test_register.py` + `tests/test_deliver_release.py` 40/40 green (§3); `_flatten_to_v1` keeps the "legacy flat GitHub asset" scenario genuinely flat as HRM correction #4 requires |

## 9. Known gap — BLOCKED item

`tests/test_manifest_release.py:66` hardcodes `assert m["manifest_version"] == 1`. This file is **outside T-48's allowed_writes** per H-103. With `MANIFEST_VERSION = 2` (required by this ticket), that assertion now fails by design. SWE cannot fix it without exceeding granted write scope. Reported to HRM in `handoffs/104-swe-to-hrm-t048.md` as BLOCKED, pending either (a) HRM granting write on `tests/test_manifest_release.py`, or (b) a follow-up ticket.
