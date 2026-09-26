import os
import subprocess
from pathlib import Path

import pytest
import yaml

CI_YML = Path(".github/workflows/ci.yml")


def _load_ci():
    return yaml.safe_load(CI_YML.read_text(encoding="utf-8"))


# ---------- AC-19: Static safety checks ----------


def test_ac19_trigger_targets_master():
    ci = _load_ci()
    triggers = ci.get(True, ci.get("on", {}))
    pr = triggers.get("pull_request")
    assert pr is not None, "ต้องมี trigger pull_request"
    branches = pr.get("branches", [])
    assert "master" in branches, "pull_request ต้องชี้ master"


def test_ac19_no_git_push_or_commit():
    """No step may run git push or git commit (AC-19, FR-H.2)."""
    raw = CI_YML.read_text(encoding="utf-8")
    assert "git push" not in raw, "ห้ามมี git push ใน workflow"
    assert "git commit" not in raw, "ห้ามมี git commit ใน workflow"


def test_ac19_no_contents_write():
    """permissions must not grant contents: write (AC-19)."""
    ci = _load_ci()
    perms = ci.get("permissions", {})
    if isinstance(perms, dict):
        assert perms.get("contents") != "write", "contents: write ห้ามปรากฏ"


def test_ac19_ci_steps_complete_fr_h1():
    """FR-H.1 step list: sync, validate, diff, compile, package, verify, ruff, pytest, artifact."""
    ci = _load_ci()
    steps = ci["jobs"]["validate-and-test"]["steps"]
    script_lines = []
    for s in steps:
        if "run" in s:
            script_lines.append(s["run"])
    joined = "\n".join(script_lines)

    assert "uv sync --locked" in joined
    assert "mdf validate" in joined
    assert "mdf diff" in joined
    assert "mdf compile" in joined
    assert "mdf package" in joined
    assert "mdf verify-package" in joined
    assert "ruff" in joined
    assert "pytest" in joined

    # artifact upload present
    uses = [s.get("uses", "") for s in steps]
    assert any("upload-artifact" in u for u in uses)


# ---------- AC-34: Run the same steps locally ----------


def _run(args, env=None):
    # args is a list and shell is not used: no shell injection (bandit B602)
    # and the same call works on Windows and on the Linux CI runner.
    return subprocess.run(  # nosec B603 - fixed argv, no user input
        args, capture_output=True, text=True, encoding="utf-8", env=env
    )


def test_ac34_step_uv_sync_locked():
    result = _run(["uv", "sync", "--locked"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_ac34_step_validate():
    result = _run(["uv", "run", "mdf", "validate"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_ac34_step_compile():
    result = _run(["uv", "run", "mdf", "compile", "--env", "dev"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_ac34_step_package_and_verify():
    result = _run(["uv", "run", "mdf", "package", "--env", "dev"])
    assert result.returncode == 0, result.stdout + result.stderr
    result = _run(["uv", "run", "mdf", "verify-package", "build/dev/release"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_ac34_step_pytest():
    # Guard against self-recursion: the inner `uv run pytest` re-enters this
    # test; set MDF_CI_INNER in the subprocess so the inner copy skips itself.
    if os.environ.get("MDF_CI_INNER") == "1":
        pytest.skip("inner CI run — skip self-referential pytest step")
    env = {**os.environ, "MDF_CI_INNER": "1"}
    result = _run(["uv", "run", "pytest", "-q"], env=env)
    assert result.returncode == 0, result.stdout + result.stderr
