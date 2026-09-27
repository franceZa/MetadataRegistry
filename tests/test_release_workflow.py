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
    wf = _load()
    publish = wf["jobs"]["publish"]
    assert publish["env"]["RELEASE_ID"] == "${{ needs.build-and-verify.outputs.release_id }}"
    assert "release_id" in wf["jobs"]["build-and-verify"]["outputs"]
    joined = "\n".join(_runs("publish"))
    assert 'gh release create "$RELEASE_ID"' in joined
    assert '--target "$GITHUB_SHA"' in joined
    assert "build/dev/release/*" in joined


def test_ac36_existing_release_skip_if_identical_fail_if_different():
    joined = "\n".join(_runs("publish"))
    view = joined.index('gh release view "$RELEASE_ID"')
    create = joined.index("gh release create")
    assert view < create
    existing = joined[view:create]
    assert 'gh release download "$RELEASE_ID"' in existing
    assert "verify-package build/existing" in existing
    assert "diff" in existing and "exit 1" in existing
    assert "exit 0" in existing


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
