import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
from importlib import metadata
from pathlib import Path
from typing import Any

from mdf.compile import compile_project, load_env_config
from mdf.loading import discover_datasets, load_yaml_file
from mdf.validation import ValidationReport, validate_project

MANIFEST_VERSION = 1
MANIFEST_NAME = "manifest.json"
VALIDATION_REPORT_NAME = "validation-report.json"

# FR-F.2 — keys every v1 manifest must carry (FR-F.5 schema check)
REQUIRED_MANIFEST_KEYS = (
    "manifest_version",
    "release_id",
    "environment",
    "source_commit",
    "compiler_revision",
    "uv_lock_sha256",
    "ci_run_url",
    "files",
    "validation_report_sha256",
    "preview",
)


class ReleaseGateError(RuntimeError):
    """Raised when the release gate refuses packaging (AC-16)."""


class TamperError(RuntimeError):
    """Raised when package verification detects tampering (AC-15)."""


class ReleaseIdMismatchError(RuntimeError):
    """Raised when manifest.release_id differs from the expected id (FR-F.6, AC-35)."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_text_file(path: Path) -> str:
    """sha256 with CRLF normalised to LF so a Windows checkout hashes like the CI runner."""
    return _sha256_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _git(args: list[str], repo_dir: Path) -> str | None:
    try:
        out = subprocess.run(  # nosec B603 B607
            ["git", *args],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout


def git_state(repo_dir: Path | str = ".") -> dict[str, Any]:
    """Return {'commit': full sha | None, 'dirty': bool}. No git = commit None, dirty True."""
    repo = Path(repo_dir)
    head = _git(["rev-parse", "HEAD"], repo)
    if head is None:
        return {"commit": None, "dirty": True}
    status = _git(["status", "--porcelain", "--untracked-files=all"], repo)
    return {"commit": head.strip(), "dirty": status is None or status.strip() != ""}


def compiler_revision() -> str:
    """mdf version + hash of the compiler source (deterministic per commit, EOL-normalised)."""
    try:
        version = metadata.version("mdf")
    except metadata.PackageNotFoundError:
        version = "0+unknown"
    src_dir = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for py in sorted(src_dir.glob("*.py")):
        h.update(py.name.encode("utf-8"))
        h.update(py.read_bytes().replace(b"\r\n", b"\n"))
    return f"{version}+src.{h.hexdigest()[:12]}"


def _ci_run_url() -> str | None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return None
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not (server and repo and run_id):
        return None
    return f"{server}/{repo}/actions/runs/{run_id}"


def _inactive_contracts(base_dir: Path | str) -> list[str]:
    bad = []
    for ds in discover_datasets(base_dir):
        contract = load_yaml_file(ds.contract_path) or {}
        status = contract.get("status")
        if status != "active":
            bad.append(f"{ds.source}.{ds.dataset} (status={status!r})")
    return bad


def check_release_gate(
    env: str,
    config_dir: Path | str = "config",
    base_dir: Path | str | None = None,
    repo_dir: Path | str | None = None,
) -> None:
    """
    Release gate (FR-F.4, AC-16): refuse --release when
    - env config has dummy: true
    - secret_scope is a placeholder (<TODO...)
    - the git working tree is dirty or not a git repo   (checked when repo_dir is given)
    - any contract status is not 'active'                (checked when base_dir is given)
    """
    env_cfg = load_env_config(config_dir, env)

    if env_cfg.get("dummy") is True:
        raise ReleaseGateError(
            f"[RELEASE_GATE] env '{env}' มี dummy: true — ห้ามสร้าง release package จากข้อมูล dummy "
            "(แก้ dummy: false ใน config/env/{env}.yaml ก่อน)"
        )

    secret_scope = env_cfg.get("secret_scope")
    if isinstance(secret_scope, str) and secret_scope.strip().startswith("<TODO"):
        raise ReleaseGateError(
            f"[RELEASE_GATE] secret_scope ยังเป็น placeholder ('{secret_scope}') — "
            "ตั้งค่า secret scope จริงก่อน release"
        )

    if repo_dir is not None:
        state = git_state(repo_dir)
        if state["commit"] is None:
            raise ReleaseGateError(
                "[RELEASE_GATE] ไม่พบ git commit — release ต้องสร้างจาก commit ที่ระบุได้ "
                "(รันใน git repository ที่มี commit แล้ว)"
            )
        if state["dirty"]:
            raise ReleaseGateError(
                "[RELEASE_GATE] working tree มีการแก้ไขที่ยังไม่ commit (dirty) — "
                "commit หรือ stash ก่อน แล้วค่อยรัน --release (ดู `git status`)"
            )

    if base_dir is not None:
        inactive = _inactive_contracts(base_dir)
        if inactive:
            raise ReleaseGateError(
                "[RELEASE_GATE] contract ที่ status ไม่ใช่ 'active' ห้าม release: " + ", ".join(inactive)
            )


def _validation_report_bytes(report: ValidationReport) -> bytes:
    issues = sorted(
        (
            {
                "code": i.code,
                "severity": i.severity,
                "file": Path(i.file_path).as_posix() if i.file_path else None,
                "field": i.field,
            }
            for i in report.issues
        ),
        key=lambda d: (d["file"] or "", d["code"], d["field"] or ""),
    )
    payload = {
        "status": "PASS" if report.is_valid else "FAIL",
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
        "issues": issues,
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def build_package(
    env: str = "dev",
    base_dir: Path | str = "DataContract",
    config_dir: Path | str = "config",
    release: bool = False,
    repo_dir: Path | str = ".",
) -> Path:
    """
    Build a release package in build/<env>/release/ (FR-F.1, FR-F.2):
    resolved/*.json + validation-report.json + manifest.json.
    When release=True the full release gate (FR-F.4) is enforced (AC-16).
    preview=True for any build without --release, or a dirty tree (FR-F.3, AC-16).
    """
    if release:
        check_release_gate(env, config_dir, base_dir=base_dir, repo_dir=repo_dir)

    # Compile (validates first; raises on invalid workspace)
    resolved_files = compile_project(env=env, base_dir=base_dir, config_dir=config_dir)
    report = validate_project(base_dir=base_dir, config_dir=config_dir)

    state = git_state(repo_dir)
    commit = state["commit"]
    preview = state["dirty"] or not release

    package_dir = Path("build") / env / "release"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    files_meta: list[dict[str, str]] = []
    for src in resolved_files:
        dest = package_dir / src.name
        shutil.copy2(src, dest)
        files_meta.append({"path": src.name, "sha256": _sha256_file(dest)})

    report_bytes = _validation_report_bytes(report)
    (package_dir / VALIDATION_REPORT_NAME).write_bytes(report_bytes)

    uv_lock = Path(repo_dir) / "uv.lock"
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "release_id": f"mdf-{commit[:12]}" if commit else None,
        "environment": env,
        "source_commit": commit,
        "compiler_revision": compiler_revision(),
        "uv_lock_sha256": _sha256_text_file(uv_lock) if uv_lock.exists() else None,
        "ci_run_url": _ci_run_url(),
        "file_count": len(files_meta),
        "files": sorted(files_meta, key=lambda m: m["path"]),
        "validation_report_sha256": _sha256_bytes(report_bytes),
        "preview": preview,
    }

    manifest_path = package_dir / MANIFEST_NAME
    manifest_path.write_bytes(
        (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )

    return package_dir


def verify_package(package_dir: Path | str, expect_release_id: str | None = None) -> dict[str, Any]:
    """
    Standalone tamper-evident verifier (FR-F.5, FR-F.6, AC-15, AC-35): needs no source checkout.
    - manifest.json has every FR-F.2 key
    - manifest.release_id == expect_release_id (when given)
    - every listed file exists and its sha256 matches; validation-report.json hash matches
    - no file outside the manifest
    """
    pkg = Path(package_dir)
    manifest_path = pkg / MANIFEST_NAME
    if not manifest_path.exists():
        raise TamperError(f"[TAMPERED] ไม่พบ manifest.json ใน package '{pkg}'")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise TamperError(f"[TAMPERED] manifest.json อ่านไม่ได้ (JSON เสียหาย): {e}") from e

    missing_keys = [k for k in REQUIRED_MANIFEST_KEYS if k not in manifest]
    if missing_keys:
        raise TamperError(
            f"[TAMPERED] manifest.json ขาด key ตาม FR-F.2: {missing_keys} "
            "(package สร้างด้วย mdf รุ่นเก่า หรือถูกแก้ไข)"
        )

    if expect_release_id is not None and manifest["release_id"] != expect_release_id:
        raise ReleaseIdMismatchError(
            f"[RELEASE_ID_MISMATCH] release_id ไม่ตรง: manifest มี '{manifest['release_id']}' "
            f"แต่คาดว่า '{expect_release_id}' — ห้ามส่ง package นี้แทน release ที่ระบุ"
        )

    listed_files = set()
    for entry in manifest["files"]:
        fname = entry.get("path", "")
        expected_sha = entry.get("sha256", "")
        target = pkg / fname
        listed_files.add(fname)

        if not target.exists():
            raise TamperError(f"[TAMPERED] ไฟล์ '{fname}' หายไปจาก package")

        actual_sha = _sha256_file(target)
        if actual_sha != expected_sha:
            raise TamperError(
                f"[TAMPERED] ไฟล์ '{fname}' ถูกดัดแปลง (sha256 ไม่ตรง: expected {expected_sha[:12]}…, "
                f"got {actual_sha[:12]}…)"
            )

    report_path = pkg / VALIDATION_REPORT_NAME
    if not report_path.exists():
        raise TamperError(f"[TAMPERED] ไฟล์ '{VALIDATION_REPORT_NAME}' หายไปจาก package")
    if _sha256_file(report_path) != manifest["validation_report_sha256"]:
        raise TamperError(
            f"[TAMPERED] ไฟล์ '{VALIDATION_REPORT_NAME}' ถูกดัดแปลง (sha256 ไม่ตรงกับ manifest)"
        )

    # Detect extra files not in manifest (excluding manifest + validation report)
    actual_files = {p.name for p in pkg.iterdir() if p.is_file()} - {
        MANIFEST_NAME,
        VALIDATION_REPORT_NAME,
    }
    extra = actual_files - listed_files
    if extra:
        raise TamperError(f"[TAMPERED] พบไฟล์แปลกปลอมใน package ที่ไม่มีใน manifest: {sorted(extra)}")

    return {
        "status": "OK",
        "env": manifest["environment"],
        "release_id": manifest["release_id"],
        "preview": manifest["preview"],
        "file_count": manifest.get("file_count"),
        "verified_files": len(listed_files),
        "manifest_sha256": _sha256_file(manifest_path),
    }
