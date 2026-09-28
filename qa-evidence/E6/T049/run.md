# T-49 — Evidence run

## 1. Full test suite

Command:
```
uv run pytest -q
```

Output (stdout, `-q` progress dots):
```
........................................................................ [ 36%]
........................................................................ [ 72%]
......................................................                   [100%]
```
Exit code: `0`

Dot count = 198 tests, all passed (no `F`/`E` markers), exit 0. This includes 11 new tests
added for T-49 in `tests/test_package.py`:
- `test_verify_v1_flat_package_ok_with_legacy_warning`
- `test_verify_v2_package_ok_no_warning`
- `test_verify_v2_rejects_dotdot_traversal`
- `test_verify_v2_rejects_backslash`
- `test_verify_v2_rejects_absolute_path`
- `test_verify_v2_rejects_too_deep_path`
- `test_verify_v2_rejects_source_mismatch`
- `test_verify_v2_rejects_extra_file_in_subfolder`
- `test_verify_v2_rejects_empty_extra_folder`
- `test_verify_unknown_manifest_version`

plus regression checks that pre-existing tests
(`test_verify_intact_package_passes`, `test_verify_detects_one_byte_tampering`,
`test_verify_detects_missing_file`, `test_verify_detects_extra_file`, and
`tests/test_manifest_release.py`, `tests/test_register.py`) still pass unchanged.

## 2. Real CLI run (build/dev/release, v1 flat — current repo build)

Note: repo git tree is dirty (uncommitted work from other tickets), but `mdf package` runs
in **preview mode** by default (no `--release` flag), which does not gate on git dirty state.
So no tmp-dir fixture substitution was needed — the real CLI path was exercised directly.

Commands:
```
uv run mdf compile --env dev
uv run mdf package --env dev
uv run mdf verify-package build/dev/release
```

Output:
```
✅ compile สำเร็จ: เขียน resolved JSON 6 ไฟล์ลง build/dev/resolved/
   - build\dev\resolved\bronze.cc.credit_card.resolved.json
   - build\dev\resolved\silver.cc.credit_card.resolved.json
   - build\dev\resolved\bronze.cc.credit_card_txn.resolved.json
   - build\dev\resolved\silver.cc.credit_card_txn.resolved.json
   - build\dev\resolved\bronze.cc.customer.resolved.json
   - build\dev\resolved\silver.cc.customer.resolved.json
---PACKAGE---
✅ package สร้างที่: build\dev\release
   release_id=mdf-d3ea0d559e04 preview=true
   (โหมด preview — ใช้ --release เพื่อบังคับ release gate)
---VERIFY---
✅ package ผ่านการตรวจสอบ (OK): env=dev, files=6, release_id=mdf-d3ea0d559e04, manifest_sha256=7a4f245c5b72d1214f31ea11c507888cab179de97a356580d738fb03a03d9638
   [WARN] legacy flat layout (manifest_version 1)
```

Confirms: v1 flat package (current `build_package`, `MANIFEST_VERSION = 1`, unchanged per
constraint #5 in H-097) verifies OK and CLI prints `[WARN] legacy flat layout` — regression
+ AC-48(And) satisfied against a real, freshly built package (not a mocked fixture).

## 3. v2 layout, traversal, and recursive-extra-file coverage

v2 manifest layout (`<source>/<file>`), traversal rejection (`..`, backslash, absolute,
too-deep, source-mismatch), recursive extra-file/empty-dir detection, and unknown
`manifest_version` rejection are covered by unit tests in `tests/test_package.py` using
hand-written fixtures (per ticket's own "ไม่ต้องพึ่ง mdf package จริง" instruction — v2
layout isn't produced by `mdf package` yet since T-48 is a separate, not-yet-done ticket).
All 9 such tests pass — see pytest output above (§1).

## AC mapping

| AC | Evidence | Result |
|---|---|---|
| AC-46 (verifier side: subfolder sha256) | `test_verify_v2_package_ok_no_warning` | PASS |
| AC-47 (traversal: `..`, backslash, absolute, before file read) | `test_verify_v2_rejects_dotdot_traversal`, `_backslash`, `_absolute_path` | PASS |
| AC-47 (SSOT-corrected: exactly 2 segments, `cc/sub/x.json` → TAMPERED) | `test_verify_v2_rejects_too_deep_path` | PASS |
| AC-47 (And: recursive extra file / empty dir) | `test_verify_v2_rejects_extra_file_in_subfolder`, `_empty_extra_folder` | PASS |
| AC-48 (v1 and v2 both pass; v3 unknown fails) | `test_verify_v1_flat_package_ok_with_legacy_warning`, `test_verify_v2_package_ok_no_warning`, `test_verify_unknown_manifest_version`; real CLI run above | PASS |
| AC-48 (And: `[WARN] legacy flat layout` on v1 only, not v2) | same as above + CLI stdout | PASS |
| FR-F.8(4) source-segment match | `test_verify_v2_rejects_source_mismatch` | PASS |
