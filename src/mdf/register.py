"""Release registration job (T-38 · FR-L.6–L.8 · AC-40 · AC-42).

Runs inside the Databricks workspace as `mdf-register` (wheel entry point) from job
`mdf_release_register_dev`. It never guesses a release: `--release-id` is required.

  register: verify /Volumes/<catalog>/ops/files/releases/<id>/ in the workspace, then append
            one REGISTERED row (skip if the same hash is already registered, fail if different).
  activate: re-verify, require a matching REGISTERED row, then append ACTIVATED
            (skip if this release is already the latest ACTIVATED).

Registry IO is behind a small interface so the decision logic is unit-tested without Spark.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from mdf.package import verify_package

RELEASE_ID_RE = re.compile(r"^mdf-[0-9a-f]{12}$")
CATALOG_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
REGISTERED = "REGISTERED"
ACTIVATED = "ACTIVATED"

COLUMNS = (
    "release_id",
    "event",
    "source_commit",
    "manifest_sha256",
    "file_count",
    "volume_path",
    "github_release_url",
    "ci_run_url",
    "actor",
    "event_ts",
)


class RegisterError(RuntimeError):
    """Registration refused; the job must fail (non-zero exit)."""


class Registry(Protocol):
    def rows_for(self, release_id: str) -> list[dict[str, Any]]: ...

    def latest_activated(self) -> str | None: ...

    def append(self, row: dict[str, Any]) -> None: ...


@dataclass
class Outcome:
    action: str  # "appended" | "skipped"
    event: str
    release_id: str
    manifest_sha256: str


def release_dir(volume_root: Path | str, catalog: str, release_id: str) -> Path:
    return Path(volume_root) / catalog / "ops" / "files" / "releases" / release_id


def _check_inputs(release_id: str | None, catalog: str) -> str:
    if not release_id:
        raise RegisterError(
            "[NO_RELEASE_ID] ต้องระบุ --release-id (mdf-<sha12>) — job ไม่เดา release ล่าสุด (AC-42)"
        )
    if not RELEASE_ID_RE.match(release_id):
        raise RegisterError(f"[BAD_RELEASE_ID] release_id '{release_id}' ไม่ตรงรูปแบบ mdf-<sha12>")
    if not CATALOG_RE.match(catalog):
        raise RegisterError(f"[BAD_CATALOG] catalog '{catalog}' ไม่ถูกต้อง")
    return release_id


def _verify(volume_root: Path | str, catalog: str, release_id: str) -> tuple[Path, dict, dict]:
    import json

    rdir = release_dir(volume_root, catalog, release_id)
    if not (rdir / "manifest.json").exists():
        raise RegisterError(
            f"[RELEASE_NOT_FOUND] ไม่พบ release ที่ '{rdir}' (หรือยังไม่ sealed: ไม่มี manifest.json)"
        )
    try:
        result = verify_package(rdir, expect_release_id=release_id)
    except RuntimeError as e:
        raise RegisterError(f"[VERIFY_FAILED] {e}") from e
    if result["preview"]:
        raise RegisterError(f"[PREVIEW_PACKAGE] '{release_id}' เป็น preview package — ห้าม register")
    manifest = json.loads((rdir / "manifest.json").read_text(encoding="utf-8"))
    return rdir, result, manifest


def run(
    registry: Registry,
    *,
    release_id: str | None,
    mode: str,
    catalog: str,
    actor: str,
    github_release_url: str | None = None,
    volume_root: Path | str = "/Volumes",
    now: datetime | None = None,
) -> Outcome:
    rid = _check_inputs(release_id, catalog)
    if mode not in ("register", "activate"):
        raise RegisterError(f"[BAD_MODE] mode ต้องเป็น register หรือ activate (ได้ '{mode}')")
    rdir, result, manifest = _verify(volume_root, catalog, rid)
    sha = result["manifest_sha256"]

    existing = registry.rows_for(rid)
    registered = [r for r in existing if r["event"] == REGISTERED]
    conflicting = sorted({r["manifest_sha256"] for r in registered if r["manifest_sha256"] != sha})
    if conflicting:
        raise RegisterError(
            f"[HASH_CONFLICT] '{rid}' ถูก register ไว้แล้วด้วย manifest_sha256 อื่น "
            f"({conflicting[0][:12]}…) แต่ใน Volume ตอนนี้คือ {sha[:12]}… — release ถูกแก้หลัง seal"
        )

    if mode == "register":
        event = REGISTERED
        if registered:
            return Outcome("skipped", event, rid, sha)
    else:
        event = ACTIVATED
        if not registered:
            raise RegisterError(f"[NOT_REGISTERED] '{rid}' ยังไม่มีแถว REGISTERED — รัน register ก่อน")
        if registry.latest_activated() == rid:
            return Outcome("skipped", event, rid, sha)

    registry.append(
        {
            "release_id": rid,
            "event": event,
            "source_commit": manifest["source_commit"],
            "manifest_sha256": sha,
            "file_count": int(manifest["file_count"]),
            "volume_path": str(rdir).replace("\\", "/"),
            "github_release_url": github_release_url or None,
            "ci_run_url": manifest.get("ci_run_url"),
            "actor": actor,
            "event_ts": now or datetime.now(UTC),
        }
    )
    return Outcome("appended", event, rid, sha)


class SparkRegistry:  # pragma: no cover - exercised on Databricks (T-41)
    """Registry backed by {catalog}.ops.release_registry via Spark (no SQL string building)."""

    def __init__(self, catalog: str):
        from pyspark.sql import SparkSession

        self.spark = SparkSession.builder.getOrCreate()
        self.table = f"{catalog}.ops.release_registry"

    def rows_for(self, release_id: str) -> list[dict[str, Any]]:
        from pyspark.sql import functions as F

        df = self.spark.table(self.table).where(F.col("release_id") == release_id)
        return [r.asDict() for r in df.select("event", "manifest_sha256").collect()]

    def latest_activated(self) -> str | None:
        from pyspark.sql import functions as F

        rows = (
            self.spark.table(self.table)
            .where(F.col("event") == ACTIVATED)
            .orderBy(F.col("event_ts").desc())
            .limit(1)
            .select("release_id")
            .collect()
        )
        return rows[0]["release_id"] if rows else None

    def append(self, row: dict[str, Any]) -> None:
        schema = self.spark.table(self.table).schema
        df = self.spark.createDataFrame([tuple(row[c] for c in COLUMNS)], schema)
        df.write.mode("append").saveAsTable(self.table)


def main(argv: list[str] | None = None, registry: Registry | None = None) -> int:
    p = argparse.ArgumentParser(prog="mdf-register", description="Register/activate an mdf release")
    p.add_argument("--release-id", default="")
    p.add_argument("--mode", default="register", choices=["register", "activate"])
    p.add_argument("--catalog", default="dev_catalog")
    p.add_argument("--actor", default="manual")
    p.add_argument("--github-release-url", default="")
    p.add_argument("--volume-root", default="/Volumes")
    args = p.parse_args(argv)
    try:
        reg = registry if registry is not None else SparkRegistry(args.catalog)
        out = run(
            reg,
            release_id=args.release_id,
            mode=args.mode,
            catalog=args.catalog,
            actor=args.actor,
            github_release_url=args.github_release_url,
            volume_root=args.volume_root,
        )
    except RegisterError as e:
        print(str(e))
        return 1
    print(
        f"✅ {out.event} {out.action}: release_id={out.release_id} "
        f"manifest_sha256={out.manifest_sha256}"
    )
    return 0


def entrypoint() -> None:  # pragma: no cover - console script
    rc = main()
    if rc:
        sys.exit(rc)
