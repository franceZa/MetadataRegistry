"""E2E integration suite — full mdf CLI lifecycle (T-026).

Runs the actual CLI entrypoint through the complete workflow:
validate -> compile -> diff -> package -> verify-package -> trace
"""

import json
import time
from pathlib import Path

import pytest

from mdf.cli import main


@pytest.fixture(scope="module")
def e2e_timing():
    """Track total wall time of the E2E flow; asserted under 10s (AC)."""
    state = {"start": time.monotonic()}
    yield state
    state["elapsed"] = time.monotonic() - state["start"]


def test_e2e_step1_validate(e2e_timing, capsys):
    """validate: full project passes."""
    rc = main(["validate"])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out


def test_e2e_step2_compile(e2e_timing, capsys):
    """compile: 6 resolved JSON files written deterministically."""
    rc = main(["compile", "--env", "dev"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "6" in out
    resolved = sorted(Path("build/dev/resolved").glob("*.resolved.json"))
    assert len(resolved) == 6


def test_e2e_step3_diff(e2e_timing, capsys):
    """diff vs baseline 88b982d: no breaking changes."""
    rc = main(["diff", "--base", "88b982d"])
    assert rc == 0


def test_e2e_step4_package(e2e_timing, capsys):
    """package: release bundle with manifest created."""
    rc = main(["package", "--env", "dev"])
    assert rc == 0
    manifest = Path("build/dev/release/manifest.json")
    assert manifest.exists()
    m = json.loads(manifest.read_text(encoding="utf-8"))
    assert m["file_count"] == 6


def test_e2e_step5_verify(e2e_timing, capsys):
    """verify-package: intact package verifies OK."""
    rc = main(["verify-package", "build/dev/release"])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_e2e_step6_trace(e2e_timing, capsys):
    """trace: full lineage for silver.cc.credit_card_txn."""
    rc = main(["trace", "silver.cc.credit_card_txn", "--env", "dev"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "cc.credit_card_txn" in out
    assert "sha256" in out
    assert "bronze" in out.lower()


def test_e2e_total_runtime_under_10s(e2e_timing):
    """AC: the whole E2E lifecycle completes in < 10 seconds."""
    elapsed = time.monotonic() - e2e_timing["start"]
    # This runs after all steps; add conservative margin for the steps already executed
    # (each step re-derives from the fixture start)
    assert elapsed < 10.0, f"E2E ใช้เวลา {elapsed:.2f}s — เกิน 10 วินาที"
