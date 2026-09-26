import pytest
import yaml
from pathlib import Path

RELEASE_YML = Path(".github/workflows/release.yml")


def _load():
    return yaml.safe_load(RELEASE_YML.read_text(encoding="utf-8"))


def test_ac19_trigger_only_push_master():
    wf = _load()
    triggers = wf.get(True, wf.get("on", {}))
    push = triggers.get("push")
    assert push is not None, "ต้องมี trigger push"
    assert "master" in push.get("branches", []), "push ต้องชี้ master"
    # ไม่มี trigger อื่นที่ push กลับ (เช่น schedule ที่ commit)
    assert "workflow_run" not in triggers


def test_ac19_concurrency_present_fr_h2():
    wf = _load()
    assert "concurrency" in wf, "release.yml ต้องมี concurrency group (FR-H.2)"
    assert "group" in wf["concurrency"]


def test_ac19_contents_write_only_publish_job():
    """contents: write must appear ONLY in the publish job (FR-H.2)."""
    wf = _load()
    jobs = wf["jobs"]

    # Top-level (if present) must not be write
    top_perms = wf.get("permissions", {})
    if isinstance(top_perms, dict) and "contents" in top_perms:
        assert top_perms["contents"] != "write"

    for name, job in jobs.items():
        perms = job.get("permissions", {})
        if isinstance(perms, dict) and perms.get("contents") == "write":
            assert name == "publish", f"contents:write ห้ามอยู่นอก job publish (พบใน {name})"


def test_ac19_no_git_push_or_commit():
    raw = RELEASE_YML.read_text(encoding="utf-8")
    assert "git push" not in raw
    assert "git commit" not in raw


def test_fr_h2_build_steps_complete():
    """Build job: checkout SHA, sync, validate, compile, package --release, verify, pytest."""
    wf = _load()
    steps = wf["jobs"]["build-and-verify"]["steps"]
    runs = "\n".join(s.get("run", "") for s in steps)
    assert "uv sync --locked" in runs
    assert "mdf validate" in runs
    assert "mdf compile" in runs
    assert "package --env dev --release" in runs
    assert "verify-package" in runs
    assert "pytest" in runs


def test_fr_h2_publish_gated_on_tag():
    """Publish job only runs for tags (v*)."""
    wf = _load()
    publish = wf["jobs"]["publish"]
    assert "needs" in publish and "build-and-verify" in publish["needs"]
    assert "startsWith(github.ref, 'refs/tags/v')" in publish.get("if", "")


def test_fr_h2_publish_verifies_before_release():
    """Publish job re-verifies the downloaded package before gh release create."""
    wf = _load()
    steps = wf["jobs"]["publish"]["steps"]
    runs = "\n".join(s.get("run", "") for s in steps)
    assert "verify-package" in runs
    assert "gh release create" in runs
