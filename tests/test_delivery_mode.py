"""T-43 · FR-L.12 / AC-43: config/env/<env>.yaml must declare delivery_mode (auto|u2m|manual)."""

import shutil
from pathlib import Path

import pytest
import yaml

from mdf.cli import main
from mdf.validation import DELIVERY_MODES, validate_project

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def project(tmp_path, monkeypatch):
    shutil.copytree(ROOT / "DataContract", tmp_path / "DataContract")
    shutil.copytree(ROOT / "config", tmp_path / "config")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _set_mode(project: Path, value) -> None:
    p = project / "config" / "env" / "dev.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if value is None:
        data.pop("delivery_mode", None)
    else:
        data["delivery_mode"] = value
    p.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_repo_dev_config_declares_a_valid_mode():
    data = yaml.safe_load((ROOT / "config/env/dev.yaml").read_text(encoding="utf-8"))
    assert data["delivery_mode"] in DELIVERY_MODES
    # Free Edition has no federation (R-20): the committed default must not be auto
    assert data["delivery_mode"] == "u2m"


@pytest.mark.parametrize("mode", DELIVERY_MODES)
def test_each_mode_passes_validation(project, mode):
    _set_mode(project, mode)
    assert validate_project().is_valid


@pytest.mark.parametrize("bad", [None, "", "AUTO", "oauth", 1])
def test_missing_or_unknown_mode_fails_with_thai_message(project, bad, capsys):
    _set_mode(project, bad)
    report = validate_project()
    codes = [i.code for i in report.errors]
    assert "DELIVERY_MODE_INVALID" in codes
    issue = next(i for i in report.errors if i.code == "DELIVERY_MODE_INVALID")
    assert issue.field == "delivery_mode"
    assert "auto, u2m หรือ manual" in issue.message
    assert main(["validate"]) == 1
    assert "DELIVERY_MODE_INVALID" in capsys.readouterr().out
