import json
import re
import subprocess  # nosec B404
import sys
from pathlib import Path

import yaml

RELEASE_YML = Path(".github/workflows/release.yml")


def _load():
    return yaml.safe_load(RELEASE_YML.read_text(encoding="utf-8"))


def _runs(job: str) -> list[str]:
    return [s.get("run", "") for s in _load()["jobs"][job]["steps"]]


def _index(runs: list[str], needle: str) -> int:
    for i, r in enumerate(runs):
        if needle in r:
            return i
    raise AssertionError(f"ไม่พบ step ที่มี '{needle}'")


def test_ac19_trigger_only_push_master():
    wf = _load()
    triggers = wf.get(True, wf.get("on", {}))
    push = triggers.get("push")
    assert push is not None, "ต้องมี trigger push"
    assert push.get("branches") == ["master"], "push ต้องชี้ master เท่านั้น"
    assert "tags" not in push, "A-18: release ทุก push master ไม่ผูก tag"
    assert "workflow_run" not in triggers


def test_ac19_concurrency_present_fr_h2():
    wf = _load()
    assert "concurrency" in wf, "release.yml ต้องมี concurrency group (FR-H.2)"
    assert "group" in wf["concurrency"]
    assert wf["concurrency"].get("cancel-in-progress") is False


def test_ac19_contents_write_only_publish_job():
    """contents: write must appear ONLY in the publish job (FR-H.2)."""
    wf = _load()
    top_perms = wf.get("permissions", {})
    if isinstance(top_perms, dict) and "contents" in top_perms:
        assert top_perms["contents"] != "write"
    for name, job in wf["jobs"].items():
        perms = job.get("permissions", {})
        if isinstance(perms, dict) and perms.get("contents") == "write":
            assert name == "publish", f"contents:write ห้ามอยู่นอก job publish (พบใน {name})"


def test_ac19_no_git_push_or_commit():
    raw = RELEASE_YML.read_text(encoding="utf-8")
    assert "git push" not in raw
    assert "git commit" not in raw


def test_fr_h2_build_steps_complete():
    """Build job: sync, validate, pytest, compile, package --release, verify, upload."""
    runs = "\n".join(_runs("build-and-verify"))
    assert "uv sync --locked" in runs
    assert "mdf validate" in runs
    assert "mdf compile" in runs
    assert "package --env dev --release" in runs
    assert "verify-package" in runs
    assert "pytest" in runs


def test_t36_pytest_runs_before_release_package():
    """Tests rebuild build/dev/release as preview -> must run before package --release."""
    runs = _runs("build-and-verify")
    assert _index(runs, "pytest") < _index(runs, "package --env dev --release")
    assert _index(runs, "package --env dev --release") < _index(runs, "verify-package")


def test_ac35_build_verifies_expected_release_id_and_not_preview():
    runs = "\n".join(_runs("build-and-verify"))
    assert '--expect-release-id "mdf-${GITHUB_SHA::12}"' in runs
    assert "'.preview'" in runs and '"false"' in runs


def test_ac36_publish_not_gated_on_tag():
    publish = _load()["jobs"]["publish"]
    assert "build-and-verify" in publish["needs"]
    cond = publish.get("if", "")
    assert "refs/tags" not in cond
    assert "refs/heads/master" in cond


def test_ac36_publish_installs_uv_before_uv_run():
    steps = _load()["jobs"]["publish"]["steps"]
    uses = [s.get("uses", "") for s in steps]
    runs = [s.get("run", "") for s in steps]
    setup = next(i for i, u in enumerate(uses) if u.startswith("astral-sh/setup-uv"))
    first_uv_run = next(i for i, r in enumerate(runs) if "uv run" in r)
    assert setup < first_uv_run


def test_ac36_publish_verifies_before_release():
    runs = _runs("publish")
    joined = "\n".join(runs)
    assert "--expect-release-id" in joined
    assert _index(runs, "verify-package") < _index(runs, "gh release create")


def test_ac36_release_named_by_release_id_with_all_assets():
    """T-52/AC-51: publish attaches a single zip asset named after the release id."""
    wf = _load()
    publish = wf["jobs"]["publish"]
    assert publish["env"]["RELEASE_ID"] == "${{ needs.build-and-verify.outputs.release_id }}"
    assert "release_id" in wf["jobs"]["build-and-verify"]["outputs"]
    joined = "\n".join(_runs("publish"))
    assert 'gh release create "$RELEASE_ID"' in joined
    assert '--target "$GITHUB_SHA"' in joined
    assert '"build/${RELEASE_ID}.zip"' in joined
    assert "build/dev/release/*" not in joined, "AC-51: no more flat multi-file asset"


def test_ac51_release_zip_built_without_wrapping_folder():
    """T-52/AC-51: zip is built from inside build/dev/release/ (no wrapper dir)."""
    joined = "\n".join(_runs("publish"))
    assert "cd build/dev/release && zip -q -r" in joined
    assert '"../../../build/${RELEASE_ID}.zip" .' in joined


def test_ac36_existing_release_skip_if_identical_fail_if_different():
    """T-52/AC-51: idempotency downloads the zip, extracts via safe_unzip.py, then compares."""
    joined = "\n".join(_runs("publish"))
    view = joined.index('gh release view "$RELEASE_ID"')
    create = joined.index("gh release create")
    assert view < create
    existing = joined[view:create]
    assert 'gh release download "$RELEASE_ID"' in existing
    assert "--pattern" in existing and "${RELEASE_ID}.zip" in existing
    assert "scripts/safe_unzip.py" in existing
    assert "verify-package build/existing" in existing
    assert "diff" in existing and "exit 1" in existing
    assert "exit 0" in existing


def test_ac51_manifest_sha256_in_notes_and_job_summary():
    """T-52/AC-51 (รอบ 6, OQ-P5-9): manifest_sha256 in both release notes and job summary."""
    steps = _load()["jobs"]["publish"]["steps"]
    names = [s.get("name", "") for s in steps]
    digest_i = names.index("Compute manifest digest")
    assert steps[digest_i]["id"] == "digest"
    assert "manifest_sha256=" in steps[digest_i]["run"]
    publish_i = names.index("Publish or skip if identical release exists")
    publish_step = steps[publish_i]
    assert (
        publish_step["env"]["MANIFEST_SHA256"] == "${{ steps.digest.outputs.manifest_sha256 }}"
    )
    assert 'manifest_sha256: %s\\n\' "$GITHUB_SHA" "$MANIFEST_SHA256"' in publish_step["run"]
    assert 'echo "manifest_sha256: \\`${MANIFEST_SHA256}\\`" >> "$GITHUB_STEP_SUMMARY"' in (
        publish_step["run"]
    )
    next_steps_i = names.index("Next steps (job summary)")
    next_steps_step = steps[next_steps_i]
    assert (
        next_steps_step["env"]["MANIFEST_SHA256"]
        == "${{ steps.digest.outputs.manifest_sha256 }}"
    )
    assert 'manifest_sha256: \\`${MANIFEST_SHA256}\\`" >> "$GITHUB_STEP_SUMMARY"' in (
        next_steps_step["run"]
    )
    assert digest_i < publish_i < next_steps_i


def test_t45_publish_writes_next_steps_summary_for_configured_mode():
    """FR-L.14 (ก): after publish/skip, the job summary shows next steps for delivery_mode."""
    steps = _load()["jobs"]["publish"]["steps"]
    names = [s.get("name", "") for s in steps]
    i = names.index("Next steps (job summary)")
    assert i > names.index("Publish or skip if identical release exists")
    step = steps[i]
    assert step["env"]["DELIVERY_MODE"] == "${{ needs.build-and-verify.outputs.delivery_mode }}"
    assert "scripts/next_steps.py" in step["run"] and "$RELEASE_ID" in step["run"]
    assert "GITHUB_STEP_SUMMARY" in step["run"]


# ---------- T-57 · FR-M.4 / FR-M.9 — calendar PENDING_OWNER in summary + release notes ----------

PENDING_LINE = "calendar PENDING_OWNER:"
EMPTY_GUARD = 'if [ -n "$PENDING_OWNER" ]; then'
PENDING_ENV = "${{ steps.pending.outputs.pending_owner }}"


def _publish_steps() -> tuple[list[dict], list[str]]:
    steps = _load()["jobs"]["publish"]["steps"]
    return steps, [s.get("name", "") for s in steps]


def _pending_step() -> dict:
    steps, names = _publish_steps()
    return steps[names.index("Collect calendar PENDING_OWNER datasets")]


def test_t57_pending_owner_line_in_both_notes_and_summary_only_when_non_empty():
    steps, names = _publish_steps()
    pending_i = names.index("Collect calendar PENDING_OWNER datasets")
    publish_i = names.index("Publish or skip if identical release exists")
    summary_i = names.index("Next steps (job summary)")
    assert pending_i < publish_i < summary_i
    for i in (publish_i, summary_i):
        step = steps[i]
        assert step["env"]["PENDING_OWNER"] == PENDING_ENV
        run = step["run"]
        assert PENDING_LINE in run and '"$PENDING_OWNER"' in run
        guard = run.index(EMPTY_GUARD)
        line = run.index(PENDING_LINE)
        assert guard < line < run.index("fi", line), "line must sit inside the non-empty guard"
    notes_run = steps[publish_i]["run"]
    assert '--notes "$NOTES"' in notes_run
    assert notes_run.index(PENDING_LINE) < notes_run.index("gh release create")
    assert '>> "$GITHUB_STEP_SUMMARY"' in steps[summary_i]["run"].split(PENDING_LINE)[1]


def test_t57_pending_owner_reads_resolved_json_not_contracts():
    """HRM correction #2 (H-115): list = compiled `calendar.status`, contracts NOT re-parsed."""
    run = _pending_step()["run"]
    assert 'Path("build/dev/release").rglob("*.resolved.json")' in run
    assert '"status") == "PENDING_OWNER"' in run
    for banned in ("DataContract", "odcs", "yaml", "read_calendar", "mdf.calendar"):
        assert banned not in run, banned


def test_t57_zip_transport_and_two_digests_unchanged():
    """FR-L.1a + FR-L.14 must not move: single zip asset, one digest reused in 2 places."""
    joined = "\n".join(_runs("publish"))
    assert joined.count("zip -q -r") == 1 and '"build/${RELEASE_ID}.zip"' in joined
    assert joined.count("sha256sum build/dev/release/manifest.json") == 1
    assert "manifest_sha256: %s" in joined
    assert joined.count('echo "manifest_sha256: \\`${MANIFEST_SHA256}\\`"') == 2


def _embedded_python() -> str:
    m = re.search(r"<<'PY'[^\n]*\n(.*?)\n\s*PY\n", _pending_step()["run"], re.S)
    assert m, "pending step must embed a python heredoc"
    lines = m.group(1).splitlines()
    indent = min(len(ln) - len(ln.lstrip()) for ln in lines if ln.strip())
    return "\n".join(ln[indent:] for ln in lines)


def _resolved(root: Path, source: str, dataset: str, layer: str, status: str) -> None:
    d = root / "build" / "dev" / "release" / source
    d.mkdir(parents=True, exist_ok=True)
    cfg = {
        "contract_id": f"{source}.{dataset}",
        "source": source,
        "dataset": dataset,
        "calendar": {"status": status},
    }
    (d / f"{layer}.{source}.{dataset}.resolved.json").write_text(json.dumps(cfg), encoding="utf-8")
    (d / f"{dataset}.odcs.yaml").write_text("id: should-not-be-read\n", encoding="utf-8")


def _run_embedded(cwd: Path) -> str:
    r = subprocess.run(  # nosec B603
        [sys.executable, "-c", _embedded_python()],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return r.stdout


def test_t57_pending_owner_step_lists_sorted_unique_datasets(tmp_path):
    for layer in ("bronze", "silver"):
        _resolved(tmp_path, "cc", "customer", layer, "PENDING_OWNER")
        _resolved(tmp_path, "cc", "credit_card", layer, "PENDING_OWNER")
        _resolved(tmp_path, "cc", "credit_card_txn", layer, "COMPLETE")
    assert _run_embedded(tmp_path).strip() == "pending_owner=cc.credit_card, cc.customer"


def test_t57_pending_owner_step_empty_when_all_complete(tmp_path):
    for layer in ("bronze", "silver"):
        _resolved(tmp_path, "cc", "customer", layer, "COMPLETE")
    assert _run_embedded(tmp_path).strip() == "pending_owner="
