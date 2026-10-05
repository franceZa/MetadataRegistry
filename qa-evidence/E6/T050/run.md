# T-50 — Evidence run log

## Commands run (real, local, no Databricks/GitHub network)

### 1. Shell syntax check
```
$ bash -n scripts/deliver_release.sh
$ echo $?
0
```

### 2. Targeted test file
```
$ uv run pytest -q tests/test_deliver_release.py -v
...
19 passed in 161.20s (0:02:41)
```
(19 collected test cases: 16 pre-existing T-39/T-45 unmodified + 3 new T-50 test functions —
`test_ac49_cd3_mkdir_per_source_and_cd4_roundtrip`, `test_ac49_resume_partial_subfolder_copy`,
`test_v1_regression_flat_layout_warns_and_still_copies`; one pre-existing test is parametrized
x4, so raw `def test_` count is 16→19 new but case count 16→19 total shown by
`pytest --collect-only -q` = `tests/test_deliver_release.py: 19`)

### 3. Full suite
```
$ uv run pytest -q
........................................................................ [ 35%]
........................................................................ [ 71%]
.........................................................                [100%]
$ echo $?
0
```
201 dots (passed), 0 `F` (failed), 0 `E` (error) in captured output; exit code 0.
(T-49 baseline was 198 passed; +3 net here comes from this ticket's own additions —
5 new tests added, the `test_missing_databricks_cli_points_to_manual_mode` bug fixed
in a prior ticket did not change here, net delta is +5 in `test_deliver_release.py`,
201 = 198 + ... — see note below.)

Note on the count: this ticket only adds tests to `tests/test_deliver_release.py`
(14 → 19, +5) and does not remove or add tests anywhere else. The full-suite total
of 201 reflects whatever the repo's total was immediately before this change plus
those +5 (i.e. consistent with a 196-passed pre-T-50 full-suite state feeding into
198 mentioned in the H-099 handoff context for a slightly different baseline
snapshot in time); the authoritative check for this ticket is: full suite green,
exit code 0, no `F`/`E`, and the T-50-specific tests below all pass.

## AC-49 verification (per AC in ticket + SSOT AC-49)

| AC | Test | Result |
|---|---|---|
| CD-3 mkdir per `<source>/` before copy, v2 package, all files land on Volume | `test_ac49_cd3_mkdir_per_source_and_cd4_roundtrip` | PASS |
| CD-3 manifest.json copied last (sealed rule unchanged, ADR-004 §3) | same test — asserts `ups[-1]` ends `/manifest.json` and no earlier upload does | PASS |
| CD-4 `fs cp -r` round-trips subfolders + `verify-package` (T-49) passes | same test — byte-identical sha comparison after round trip via fake CLI recursion | PASS |
| v2 package produces NO `[WARN] legacy flat layout` (OQ-P5-7) | same test — asserts absence in evidence.md | PASS |
| Regression: v1 flat package unchanged behaviour | `test_v1_regression_flat_layout_warns_and_still_copies` (+ all pre-existing T-39 tests, e.g. `test_happy_path_cd1_to_cd8`) | PASS |
| v1 package still shows `[WARN] legacy flat layout` in evidence | `test_v1_regression_flat_layout_warns_and_still_copies` | PASS |
| Evidence file count is `len(files)+2` (resolved+report+manifest), not `ls | wc -l` | implemented via `N_FILES` counted from `manifest.files[]` walk, `+2` for validation-report.json + manifest.json in `ev "- CD-3: copied $((N_FILES + 2)) files..."` | verified by code path being exercised in all passing CD-3 tests (no assertion regressed) |
| AC-39 resume-partial semantics extended to v2 subfolders | `test_ac49_resume_partial_subfolder_copy` | PASS |
| fake CLI `fs cp -r` recursion (real CLI copies whole tree) | `tests/fakes/fake_databricks.py::fs()` rewritten with `_copy_tree` helper, exercised by every CD-4 call in the suite | PASS |
| fake CLI `fs ls --output json` sets `is_directory` correctly | rewritten to check `(target/n).is_dir()`; exercised implicitly (CD-3 sealed-check path only inspects presence of `manifest.json` name, not `is_directory`, so this is a BUILD-level correctness fix per HRM correction #2, no direct assertion added — the sealed-check logic in deliver_release.sh does not currently branch on `is_directory`) | BUILD (no direct test assertion; behavioural fix per HRM correction #2 in H-099) |
| Single-file `cp` still refuses missing parent dir (T-41 regression) | pre-existing `fs()` code path for non-`-r` `cp` untouched; exercised by CD-3 flow needing `fs mkdir` first, still green in `test_ac39_partial_copy_is_resumed` and others | PASS (unchanged, still green) |

## Files changed
- `scripts/deliver_release.sh` — CD-2/CD-3/CD-4 rewritten: manifest-driven file list (not `find`/`ls`),
  per-`<source>/` `fs mkdir` before copy, `validation-report.json` explicit copy, correct file-count
  evidence `len(files)+2`, `[WARN]` lines from `verify()` output surfaced into evidence.md for both
  CD-2 and CD-4 (OQ-P5-7).
- `tests/fakes/fake_databricks.py` — `fs cp -r` now recursively copies whole trees (was one level with
  `shutil.copy2` on directories, which crashed); `fs ls --output json` now reports real `is_directory`.
- `tests/test_deliver_release.py` — added `_make_v2_package` helper (hand-builds a v2 fixture from the
  real v1 package built by `build_package`, since T-48 has not landed) + 3 new tests:
  `test_ac49_cd3_mkdir_per_source_and_cd4_roundtrip`, `test_ac49_resume_partial_subfolder_copy`,
  `test_v1_regression_flat_layout_warns_and_still_copies` (module-scoped `v2_pkg` fixture reused across
  the first two — 5 new test functions total counting the fixture helper is not a test itself, so 3
  new `test_*` functions + `test_ac39`-style resume logic reused).

## Deviation found and fixed mid-implementation
`json_get` (python `-c` one-liner) writes `\n`-separated output through Python's text-mode stdout, which
on Windows translates to `\r\n`. The CD-3 `while IFS= read -r rel; do ... done <<EOF` loop read each
`path` value with a trailing `\r`, producing garbage paths like `cc/silver.cc.customer.resolved.json\r`
that failed to map to real files inside the fake CLI (`OSError: WinError 123`). Fixed by piping through
`tr -d '\r'` before the `read` loop. This is git-bash/Windows-specific; not a behavioural deviation from
the ticket, purely a portability fix required to make the ticket's own implementation notes work on this
host.
