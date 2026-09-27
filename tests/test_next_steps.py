"""T-45 · FR-L.14: scripts/next_steps.py prints per-mode next steps with the real release_id."""

import importlib.util
import re
import subprocess  # nosec B404
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "next_steps.py"
_spec = importlib.util.spec_from_file_location("next_steps", SCRIPT)
ns = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ns)

RID = "mdf-ef2f425903b6"
REPO = "franceZa/MetadataRegistry"
RUN = "https://github.com/franceZa/MetadataRegistry/actions/runs/1"
LEAKS = re.compile(r"dbc-[0-9a-f]|@gmail|@[a-z0-9-]+\.[a-z]{2,}|dapi[0-9a-f]|ghp_|token=", re.I)


@pytest.mark.parametrize("mode", ["auto", "u2m", "manual"])
def test_every_mode_names_the_release_and_leaks_nothing(mode):
    text = ns.render(mode, RID, REPO, RUN)
    assert f"`{RID}`" in text and f"mode **{mode}**" in text
    assert "ขั้นต่อไป" in text
    assert not LEAKS.search(text), LEAKS.search(text)


def test_auto_links_run_and_explains_environment_approval_and_fallback():
    text = ns.render("auto", RID, REPO, RUN)
    assert f"]({RUN})" in text
    assert "Review deployments" in text and "`dev`" in text
    assert "Preflight" in text and "delivery_mode: u2m" in text


def test_u2m_gives_login_then_the_exact_script_command():
    text = ns.render("u2m", RID, REPO)
    assert "databricks auth login" in text
    assert f"bash scripts/deliver_release.sh {RID}" in text
    assert f"git worktree add ../mdf-{RID} {RID}" in text
    assert text.index("databricks auth login") < text.index("bash scripts/deliver_release.sh")
    assert f"next_steps.py manual {RID}" in text  # fallback to mode 3


def test_manual_is_the_m1_to_m7_checklist_with_release_link():
    text = ns.render("manual", RID, REPO)
    for i in range(1, 8):
        assert f"**M-{i}**" in text
    assert f"https://github.com/{REPO}/releases/tag/{RID}" in text
    assert f"/Volumes/dev_catalog/ops/files/releases/{RID}" in text
    assert "sql/manual/register_release.sql" in text and "sql/manual/activate_release.sql" in text
    assert "manifest.json` เป็นไฟล์สุดท้าย" in text
    assert text.index("**M-4**") < text.index("**M-6**")


@pytest.mark.parametrize(
    ("mode", "rid"), [("xyz", RID), ("u2m", "mdf-XYZ"), ("u2m", "mdf-1234; rm -rf /")]
)
def test_bad_input_is_rejected(mode, rid):
    with pytest.raises(ValueError):
        ns.render(mode, rid, REPO)
    r = subprocess.run(  # nosec B603
        [sys.executable, str(SCRIPT), mode, rid], capture_output=True, text=True, encoding="utf-8"
    )
    assert r.returncode == 2 and "[NEXT_STEPS]" in r.stderr and r.stdout == ""


def test_cli_prints_markdown():
    r = subprocess.run(  # nosec B603
        [sys.executable, str(SCRIPT), "manual", RID],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0 and r.stdout.startswith("## ขั้นต่อไป")
