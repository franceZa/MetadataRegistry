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


# ---------- T-57 · FR-M.9 · AC-58 — v3 guidance: odcs.yaml, no fixed count, runbook sync ----------

RUNBOOK = ROOT / "runbooks" / "release-delivery.md"
GUIDE = ROOT / "runbooks" / "release-delivery-guide.md"
PLACEHOLDER = "mdf-<sha12>"


def _m_lines(rid: str = RID) -> list[str]:
    lines = [ln for ln in ns._manual(rid, REPO, None) if ln.startswith("- [ ] **M-")]
    assert [ln.split("**")[1] for ln in lines] == [f"M-{i}" for i in range(1, 8)]
    return lines


def test_t57_manual_m3_says_upload_odcs_yaml_and_has_no_fixed_file_count():
    text = ns.render("manual", RID, REPO)
    m3 = next(ln for ln in text.splitlines() if "**M-3**" in ln)
    assert "**และ `*.odcs.yaml`**" in m3 and "*.resolved.json" in m3
    assert "ทุกไฟล์" in m3 and "`<source>/`" in m3
    assert "file_count" in m3  # count comes from the manifest, never hardcoded
    assert "[TAMPERED]" in m3  # what happens if the .odcs.yaml is forgotten
    assert not re.search(r"\d+\s*×|\d+\s*ไฟล์", text), re.search(r"\d+\s*×|\d+\s*ไฟล์", text)


def test_t57_runbook_m1_to_m7_match_next_steps_word_for_word():
    """HRM correction #1 (H-115): runbook M-1…M-7 == next_steps.py (release_id placeholder)."""
    runbook = RUNBOOK.read_text(encoding="utf-8").splitlines()
    for line in _m_lines(PLACEHOLDER):
        assert line in runbook, line.split("**")[1]


def test_t57_guide_m1_to_m7_table_matches_next_steps_word_for_word():
    guide = GUIDE.read_text(encoding="utf-8").splitlines()
    for line in _m_lines(PLACEHOLDER):
        tag, body = re.match(r"- \[ \] (\*\*M-\d\*\*) (.*)$", line).groups()
        rows = [g for g in guide if g.startswith(f"| {tag} | ")]
        assert len(rows) == 1, tag
        assert rows[0].split(" | ")[1] == body, tag


def test_t57_runbooks_have_no_hardcoded_file_counts():
    for path in (RUNBOOK, GUIDE, ROOT / "runbooks" / "release-workflow" / "flow-chart.mmd"):
        text = path.read_text(encoding="utf-8")
        assert "8 ไฟล์" not in text and "6 ×" not in text, path
    rb = RUNBOOK.read_text(encoding="utf-8")
    assert "`file_count` ใน `manifest.json` + 2" in rb
