import hashlib
import json
import os
import shutil
import subprocess  # nosec B404
from importlib import metadata
from pathlib import Path
from typing import Any

from mdf.calendar import compiled_calendar
from mdf.compile import compile_project, load_env_config
from mdf.loading import discover_datasets, load_yaml_file
from mdf.validation import ValidationReport, validate_project

MANIFEST_VERSION = 3  # v1/v2 still readable by verify_package (T-49/T-56, FR-M.7/FR-M.8)
MANIFEST_NAME = "manifest.json"
VALIDATION_REPORT_NAME = "validation-report.json"

# FR-M.7: `kind` values allowed in a v3 manifest entry -- whitelist, read from the
# manifest field only. Never guessed from a file extension (HRM correction #1, H-113).
KIND_RESOLVED_CONFIG = "resolved_config"
KIND_ODCS_CONTRACT = "odcs_contract"
_V3_KIND_WHITELIST = frozenset({KIND_RESOLVED_CONFIG, KIND_ODCS_CONTRACT})
# FR-M.8 (3): every dataset in a v3 package = 1 contract + exactly these resolved layers
V3_LAYERS = ("bronze", "silver")
_KNOWN_MANIFEST_VERSIONS = (1, 2, 3)

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


def _parse_resolved_filename(name: str) -> tuple[str, str, str]:
    """Parse '{layer}.{source}.{dataset}.resolved.json' -> (layer, source, dataset)
    (FR-M.7: used only at build time; verify_package never parses an attacker-controlled
    filename this way -- it only compares against the expected name built from manifest
    fields, see HRM correction #1, H-113).
    """
    suffix = ".resolved.json"
    if not name.endswith(suffix):
        raise ValueError(f"not a resolved config filename: {name!r}")
    parts = name[: -len(suffix)].split(".", 2)
    if len(parts) != 3:
        raise ValueError(f"not a resolved config filename: {name!r}")
    layer, source, dataset = parts
    return layer, source, dataset


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


def calendar_pending_owner_datasets(base_dir: Path | str) -> list[str]:
    """FR-M.4: dataset ids with a missing (not malformed) calendar field.

    Reuses mdf.calendar.compiled_calendar — the single calendar parser (T-54/T-55).
    """
    ids: list[str] = []
    for ds in discover_datasets(base_dir):
        contract = load_yaml_file(ds.contract_path) or {}
        _, missing, _ = compiled_calendar(contract)
        if missing:
            ids.append(contract.get("id", f"{ds.source}.{ds.dataset}"))
    return sorted(ids)


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
    Build a release package in build/<env>/release/ (FR-F.1, FR-F.2, FR-M.7):
    resolved/*.json + <source>/<dataset>.odcs.yaml (ODCS contract bytes, manifest_version 3)
    + validation-report.json + manifest.json.
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

    files_meta: list[dict[str, Any]] = []
    contract_keys_done: set[tuple[str, str]] = set()
    for src in resolved_files:
        # T-48/FR-D.8: compile_project writes build/<env>/resolved/<source>/<file> —
        # the source is the immediate parent folder name, not parsed from the filename.
        source = src.parent.name
        layer, src_in_name, dataset = _parse_resolved_filename(src.name)
        if src_in_name != source:
            raise RuntimeError(
                f"[PACKAGE_LAYOUT] '{src}' อยู่ใต้โฟลเดอร์ '{source}' แต่ชื่อไฟล์ระบุ source "
                f"'{src_in_name}' — compile output ผิดรูปแบบ"
            )
        dest_dir = package_dir / source
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        rel_path = f"{source}/{src.name}".replace("\\", "/")
        files_meta.append(
            {
                "path": rel_path,
                "sha256": _sha256_file(dest),
                "kind": KIND_RESOLVED_CONFIG,
                "source": source,
                "dataset": dataset,
                "layer": layer,
            }
        )

        key = (source, dataset)
        if key not in contract_keys_done:
            contract_keys_done.add(key)
            # FR-M.7 / HRM correction #2 (H-113): copy the contract from the exact path
            # compile used (lineage.contract_file of the resolved JSON just written) --
            # never re-globbed from DataContract/ -- as raw bytes (no YAML load/dump).
            lineage = json.loads(src.read_text(encoding="utf-8"))["lineage"]
            contract_bytes = Path(lineage["contract_file"]).read_bytes()
            contract_sha = _sha256_bytes(contract_bytes)
            if contract_sha != lineage["contract_sha256"]:
                raise RuntimeError(
                    f"[PACKAGE_CONTRACT_CHANGED] '{lineage['contract_file']}' เปลี่ยนหลัง compile "
                    "(sha256 ไม่ตรง lineage.contract_sha256) — รัน mdf package ใหม่"
                )
            bundle_path = f"{source}/{dataset}.odcs.yaml"
            if lineage.get("contract_bundle_path") != bundle_path:
                raise RuntimeError(
                    f"[PACKAGE_LAYOUT] lineage.contract_bundle_path ของ '{src.name}' "
                    f"ไม่ใช่ '{bundle_path}'"
                )
            (dest_dir / f"{dataset}.odcs.yaml").write_bytes(contract_bytes)
            files_meta.append(
                {
                    "path": bundle_path,
                    "sha256": contract_sha,
                    "kind": KIND_ODCS_CONTRACT,
                    "source": source,
                    "dataset": dataset,
                }
            )

    report_bytes = _validation_report_bytes(report)
    (package_dir / VALIDATION_REPORT_NAME).write_bytes(report_bytes)

    pending_owner = calendar_pending_owner_datasets(base_dir)
    if pending_owner:
        print(f"[WARN] calendar PENDING_OWNER: {', '.join(pending_owner)}")

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


def _check_source_file_path(fname: str, manifest_version: int) -> tuple[str, str]:
    """FR-F.8 (v2) / FR-M.8 (v3): string-level path checks BEFORE any resolve()/file read.

    Returns (source_segment, file_segment) for a path of exactly '<source>/<file>'.
    """
    if "\\" in fname:
        raise TamperError(
            f"[TAMPERED] path '{fname}' มี backslash ซึ่งไม่อนุญาตใน manifest_version "
            f"{manifest_version}"
        )
    if fname.startswith("/") or (len(fname) > 1 and fname[1] == ":"):
        raise TamperError(f"[TAMPERED] path '{fname}' เป็น absolute path ซึ่งไม่อนุญาต")
    segments = fname.split("/")
    if any(seg in ("..", "") for seg in segments) or len(segments) != 2:
        raise TamperError(
            f"[TAMPERED] path '{fname}' ต้องมีรูปแบบ '<source>/<file>' เป๊ะ 2 segment "
            "(ห้าม '..' หรือ segment ว่าง)"
        )
    return segments[0], segments[1]


def _v3_expected_path(entry: dict[str, Any]) -> str:
    """Path a v3 entry MUST have, built only from its manifest fields (FR-M.8 (2)).

    `kind` decides the filename pattern; it is never inferred from the file extension.
    """
    source, dataset = entry["source"], entry["dataset"]
    if entry["kind"] == KIND_RESOLVED_CONFIG:
        return f"{source}/{entry['layer']}.{source}.{dataset}.resolved.json"
    return f"{source}/{dataset}.odcs.yaml"


def _check_v3_entry(entry: dict[str, Any]) -> None:
    """FR-M.8 (1)(2): kind whitelist + required fields + path == name built from fields."""
    fname = entry.get("path")
    kind = entry.get("kind")
    if kind not in _V3_KIND_WHITELIST:
        raise TamperError(
            f"[TAMPERED] path '{fname}' มี kind {kind!r} ที่ไม่อยู่ใน whitelist "
            f"{sorted(_V3_KIND_WHITELIST)} (manifest_version 3)"
        )
    required = ["source", "dataset"] + (["layer"] if kind == KIND_RESOLVED_CONFIG else [])
    for key in required:
        value = entry.get(key)
        if not isinstance(value, str) or not value:
            raise TamperError(f"[TAMPERED] path '{fname}' (kind {kind}) ขาด field '{key}'")
    if kind == KIND_RESOLVED_CONFIG and entry["layer"] not in V3_LAYERS:
        raise TamperError(
            f"[TAMPERED] path '{fname}' มี layer {entry['layer']!r} ที่ไม่รองรับ "
            f"(ต้องเป็น {list(V3_LAYERS)})"
        )
    if kind == KIND_ODCS_CONTRACT and "layer" in entry:
        raise TamperError(f"[TAMPERED] path '{fname}' (kind {kind}) ต้องไม่มี field 'layer'")
    expected = _v3_expected_path(entry)
    if fname != expected:
        raise TamperError(
            f"[TAMPERED] path '{fname}' ไม่ตรงกับ kind/source/dataset/layer ใน manifest "
            f"(ควรเป็น '{expected}')"
        )


def _check_v3_bundle(pkg: Path, manifest: dict[str, Any]) -> None:
    """FR-M.8 (3)(4) + FR-M.7 file_count, run after every file's sha256 was verified.

    (3) every dataset has exactly 1 contract + 1 bronze + 1 silver.
    (4) lineage.contract_sha256 of every resolved config == sha256 of the bundled
        contract, and lineage.contract_bundle_path == that contract's path.
    """
    files = manifest["files"]
    if manifest.get("file_count") != len(files):
        raise TamperError(
            f"[TAMPERED] file_count ({manifest.get('file_count')!r}) ไม่เท่ากับจำนวน "
            f"files[] ({len(files)}) (manifest_version 3)"
        )
    groups: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
    for e in files:
        slot = e["layer"] if e["kind"] == KIND_RESOLVED_CONFIG else KIND_ODCS_CONTRACT
        groups.setdefault((e["source"], e["dataset"]), {}).setdefault(slot, []).append(e)
    for (source, dataset), slots in sorted(groups.items()):
        for slot in (KIND_ODCS_CONTRACT, *V3_LAYERS):
            n = len(slots.get(slot, []))
            if n != 1:
                raise TamperError(
                    f"[TAMPERED] dataset '{source}.{dataset}' ต้องมี {slot} 1 ไฟล์พอดี "
                    f"แต่พบ {n} (manifest_version 3)"
                )
        contract = slots[KIND_ODCS_CONTRACT][0]
        for layer in V3_LAYERS:
            resolved = slots[layer][0]
            try:
                data = json.loads((pkg / resolved["path"]).read_text(encoding="utf-8"))
                lineage = data["lineage"]
                lineage_sha = lineage["contract_sha256"]
                bundle_path = lineage.get("contract_bundle_path")
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                raise TamperError(
                    f"[TAMPERED] '{resolved['path']}' อ่าน lineage ไม่ได้: {e}"
                ) from e
            if lineage_sha != contract["sha256"]:
                raise TamperError(
                    f"[TAMPERED] '{resolved['path']}' lineage.contract_sha256 ไม่ตรงกับ sha256 "
                    f"ของ contract ที่แนบ '{contract['path']}'"
                )
            if bundle_path != contract["path"]:
                raise TamperError(
                    f"[TAMPERED] '{resolved['path']}' lineage.contract_bundle_path "
                    f"({bundle_path!r}) ไม่ตรงกับ '{contract['path']}'"
                )


def verify_package(package_dir: Path | str, expect_release_id: str | None = None) -> dict[str, Any]:
    """
    Standalone tamper-evident verifier (FR-F.5, FR-F.6, AC-15, AC-35): needs no source checkout.
    - manifest.json has every FR-F.2 key
    - manifest.release_id == expect_release_id (when given)
    - every listed file exists and its sha256 matches; validation-report.json hash matches
    - no file outside the manifest
    - layout from manifest_version only: 1 flat (+ legacy warning), 2 `<source>/<file>`,
      3 = v2 rules + kind/source/dataset/layer + contract bundle checks (FR-M.8)
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

    manifest_version = manifest["manifest_version"]
    warnings: list[str] = []
    pkg_resolved = pkg.resolve()

    # Layout is decided from manifest_version ONLY (ADR-003 รอบ 11 ข้อ 4) — never from
    # the folder structure or file extensions. bool is excluded (True == 1 in Python).
    if isinstance(manifest_version, bool) or manifest_version not in _KNOWN_MANIFEST_VERSIONS:
        raise TamperError(f"[TAMPERED] unknown manifest_version: {manifest_version!r}")
    if manifest_version == 1:
        warnings.append("[WARN] legacy flat layout (manifest_version 1)")

    if not isinstance(manifest["files"], list) or not all(
        isinstance(e, dict) for e in manifest["files"]
    ):
        raise TamperError("[TAMPERED] manifest.files ต้องเป็น list ของ object")

    listed_files = set()
    for entry in manifest["files"]:
        fname = entry.get("path", "")
        expected_sha = entry.get("sha256", "")
        if not isinstance(fname, str) or not fname:
            raise TamperError(f"[TAMPERED] manifest entry ไม่มี path ที่ถูกต้อง: {entry!r}")

        if manifest_version == 1:
            # v1: bare filename only, no '/' allowed (FR-F.2 legacy flat layout)
            if "/" in fname or "\\" in fname:
                raise TamperError(
                    f"[TAMPERED] path '{fname}' ผิดรูปแบบ manifest_version 1 "
                    "(ต้องเป็นชื่อไฟล์เปล่า ไม่มี '/')"
                )
        else:
            # v2 + v3: FR-F.8 — string-level checks BEFORE any resolve()/file read
            source_seg, file_seg = _check_source_file_path(fname, manifest_version)
            if manifest_version == 2:
                # FR-F.8(4): first segment must equal source encoded in the filename
                # {layer}.{source}.{dataset}.resolved.json
                name_parts = file_seg.split(".")
                if len(name_parts) < 2 or name_parts[1] != source_seg:
                    raise TamperError(
                        f"[TAMPERED] path '{fname}' segment แรก ('{source_seg}') ไม่ตรงกับ source "
                        f"ที่เข้ารหัสในชื่อไฟล์ '{file_seg}'"
                    )
            else:
                # v3: FR-M.8 (1)(2) — kind whitelist + filename built from the manifest
                # fields must equal the path (implies segment 1 == source, FR-F.8(4)).
                _check_v3_entry(entry)

        target = pkg / fname
        resolved_target = target.resolve()
        if not resolved_target.is_relative_to(pkg_resolved):
            raise TamperError(f"[TAMPERED] path '{fname}' resolve หลุดออกนอก package root")

        listed_files.add(fname)

        if not target.exists():
            raise TamperError(f"[TAMPERED] ไฟล์ '{fname}' หายไปจาก package")

        actual_sha = _sha256_file(target)
        if actual_sha != expected_sha:
            raise TamperError(
                f"[TAMPERED] ไฟล์ '{fname}' ถูกดัดแปลง (sha256 ไม่ตรง: expected {expected_sha[:12]}…, "
                f"got {actual_sha[:12]}…)"
            )

    if manifest_version == 3:
        _check_v3_bundle(pkg, manifest)

    report_path = pkg / VALIDATION_REPORT_NAME
    if not report_path.exists():
        raise TamperError(f"[TAMPERED] ไฟล์ '{VALIDATION_REPORT_NAME}' หายไปจาก package")
    if _sha256_file(report_path) != manifest["validation_report_sha256"]:
        raise TamperError(
            f"[TAMPERED] ไฟล์ '{VALIDATION_REPORT_NAME}' ถูกดัดแปลง (sha256 ไม่ตรงกับ manifest)"
        )

    # Detect extra files/folders not in manifest — recursive walk (FR-F.8 (2)(3), AC-47 And)
    listed_paths = {(pkg / fname).resolve() for fname in listed_files}
    root_exempt = {MANIFEST_NAME, VALIDATION_REPORT_NAME}
    extra: list[str] = []
    for p in pkg.rglob("*"):
        if p.is_dir():
            continue
        if p.parent == pkg and p.name in root_exempt:
            continue
        if p.resolve() not in listed_paths:
            extra.append(str(p.relative_to(pkg).as_posix()))
    if extra:
        raise TamperError(
            f"[TAMPERED] พบไฟล์แปลกปลอมใน package ที่ไม่มีใน manifest: {sorted(extra)}"
        )

    # Empty (or listed-file-less) directories also count as tampering evidence
    for d in pkg.rglob("*"):
        if not d.is_dir():
            continue
        has_listed_file = any(
            (lp.exists() and lp.is_relative_to(d.resolve())) for lp in listed_paths
        )
        if not has_listed_file:
            raise TamperError(
                f"[TAMPERED] พบโฟลเดอร์ '{d.relative_to(pkg).as_posix()}' ที่ไม่มีไฟล์ใน manifest"
            )

    return {
        "status": "OK",
        "env": manifest["environment"],
        "release_id": manifest["release_id"],
        "preview": manifest["preview"],
        "file_count": manifest.get("file_count"),
        "verified_files": len(listed_files),
        "manifest_sha256": _sha256_file(manifest_path),
        "warnings": warnings,
    }
