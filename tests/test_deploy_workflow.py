"""T-40 static checks for .github/workflows/deploy-dev.yml (AC-41, FR-L.2, FR-L.9, FR-L.10)."""

from pathlib import Path

import yaml

DEPLOY = Path(".github/workflows/deploy-dev.yml")
RELEASE = Path(".github/workflows/release.yml")


def _load(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _on(wf: dict) -> dict:
    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True
    return wf.get("on", wf.get(True))


def _job(wf: dict) -> dict:
    return wf["jobs"]["deliver"]


def test_triggers_are_call_and_dispatch_only_with_required_release_id():
    on = _on(_load(DEPLOY))
    assert set(on) == {"workflow_call", "workflow_dispatch"}
    for trig in on.values():
        assert trig["inputs"]["release_id"]["required"] is True


def test_ac41_oidc_permissions_and_auth_type():
    wf = _load(DEPLOY)
    job = _job(wf)
    assert job["permissions"]["id-token"] == "write"
    assert job["permissions"]["contents"] == "read"
    assert wf["permissions"] == {"contents": "read"}
    assert job["env"]["DATABRICKS_AUTH_TYPE"] == "github-oidc"


def test_ac41_no_long_lived_secrets():
    text = DEPLOY.read_text(encoding="utf-8")
    for banned in ("DATABRICKS_TOKEN", "DATABRICKS_CLIENT_SECRET", "secrets."):
        assert banned not in text, banned
    env = _job(_load(DEPLOY))["env"]
    assert env["DATABRICKS_HOST"].startswith("${{ vars.")
    assert env["DATABRICKS_CLIENT_ID"].startswith("${{ vars.")


def test_ac41_single_delivery_script():
    runs = [s.get("run", "") for s in _job(_load(DEPLOY))["steps"]]
    cd = [r for r in runs if "deliver_release.sh" in r]
    assert cd == ['bash scripts/deliver_release.sh "$RELEASE_ID"']
    joined = "\n".join(runs)
    for inline in ("databricks fs", "databricks bundle", "release_registry", "INSERT"):
        assert inline not in joined, f"CD logic must stay in the script, found '{inline}'"


def test_environment_dev_and_no_cancel_concurrency():
    wf = _load(DEPLOY)
    assert _job(wf)["environment"] == "dev"
    assert wf["concurrency"]["cancel-in-progress"] is False


def test_checks_out_release_commit_and_validates_id():
    steps = _job(_load(DEPLOY))["steps"]
    co = next(s for s in steps if str(s.get("uses", "")).startswith("actions/checkout"))
    assert co["with"]["ref"] == "${{ inputs.release_id }}"
    assert "^mdf-[0-9a-f]{12}$" in steps[0]["run"]


def test_evidence_uploaded_even_on_failure():
    steps = _job(_load(DEPLOY))["steps"]
    up = next(s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact"))
    assert up["if"] == "always()"
    assert up["with"]["path"].endswith("/evidence.md")


def test_release_calls_deploy_guarded_after_publish():
    job = _load(RELEASE)["jobs"]["deliver"]
    assert job["uses"] == "./.github/workflows/deploy-dev.yml"
    assert job["if"] == "vars.MDF_CD_ENABLED == 'true'"
    assert set(job["needs"]) == {"build-and-verify", "publish"}
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    assert job["with"]["release_id"] == "${{ needs.build-and-verify.outputs.release_id }}"
