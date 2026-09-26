import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from mdf.compile import compile_project, load_env_config


class ReleaseGateError(RuntimeError):
    """Raised when the release gate refuses packaging (AC-16)."""


class TamperError(RuntimeError):
    """Raised when package verification detects tampering (AC-15)."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def check_release_gate(env: str, config_dir: Path | str = "config") -> None:
    """
    Release gate (AC-16 context): refuse --release when
    - env config has dummy: true
    - secret_scope is a placeholder (<TODO...)
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


def build_package(
    env: str = "dev",
    base_dir: Path | str = "DataContract",
    config_dir: Path | str = "config",
    release: bool = False,
) -> Path:
    """
    Build a release package: compile resolved configs, bundle them into
    build/<env>/release/ with a manifest.json listing every file + sha256 (AC-15).
    When release=True, the release gate is enforced (AC-16).
    """
    if release:
        check_release_gate(env, config_dir)

    # Compile (validates first; raises on invalid workspace)
    resolved_files = compile_project(env=env, base_dir=base_dir, config_dir=config_dir)

    package_dir = Path("build") / env / "release"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    files_meta: list[dict[str, str]] = []
    for src in resolved_files:
        dest = package_dir / src.name
        shutil.copy2(src, dest)
        files_meta.append(
            {
                "file": src.name,
                "sha256": _sha256_file(dest),
            }
        )

    manifest = {
        "package": f"mdf-release-{env}",
        "env": env,
        "file_count": len(files_meta),
        "files": sorted(files_meta, key=lambda m: m["file"]),
    }

    manifest_path = package_dir / "manifest.json"
    manifest_path.write_bytes(json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"))

    return package_dir


def verify_package(package_dir: Path | str) -> dict[str, Any]:
    """
    Standalone tamper-evident verifier (AC-15): recompute sha256 of every file
    listed in manifest.json and compare. Any mismatch = TAMPERED (raises TamperError).
    Also detects missing files and files not listed in the manifest.
    Returns verification summary dict when intact.
    """
    pkg = Path(package_dir)
    manifest_path = pkg / "manifest.json"
    if not manifest_path.exists():
        raise TamperError(f"[TAMPERED] ไม่พบ manifest.json ใน package '{pkg}'")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise TamperError(f"[TAMPERED] manifest.json อ่านไม่ได้ (JSON เสียหาย): {e}") from e

    listed_files = set()
    for entry in manifest.get("files", []):
        fname = entry.get("file", "")
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

    # Detect extra files not in manifest (excluding manifest itself)
    actual_files = {p.name for p in pkg.iterdir() if p.is_file()} - {"manifest.json"}
    extra = actual_files - listed_files
    if extra:
        raise TamperError(f"[TAMPERED] พบไฟล์แปลกปลอมใน package ที่ไม่มีใน manifest: {sorted(extra)}")

    return {
        "status": "OK",
        "env": manifest.get("env"),
        "file_count": manifest.get("file_count"),
        "verified_files": len(listed_files),
    }
