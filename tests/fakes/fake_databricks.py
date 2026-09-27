"""Fake `databricks` CLI for T-39 tests. No network. State lives under $FAKE_ROOT:

  $FAKE_ROOT/Volumes/...        stands in for dbfs:/Volumes/...
  $FAKE_ROOT/registry.json      stands in for {catalog}.ops.release_registry (append-only list)
  $FAKE_ROOT/calls.log          one line per invocation (argv joined by ' ')

Mirrors real CLI v1.17 behaviour observed 2026-09-27: `fs ls <missing>` -> rc 1; `fs cp` onto an
existing file without --overwrite -> skipped, rc 0; `fs cp -r dbfs:/dir local` -> files in local/.
"""

import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(os.environ["FAKE_ROOT"])
REG = ROOT / "registry.json"
FAIL_ON = os.environ.get("FAKE_FAIL_ON", "")


def _log(argv):
    with (ROOT / "calls.log").open("a", encoding="utf-8") as f:
        f.write(" ".join(argv) + "\n")


def _map(p: str) -> Path:
    if p.startswith("dbfs:/"):
        return ROOT / p[len("dbfs:/") :]
    return Path(p)


def _rows():
    return json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else []


class JsonRegistry:
    def rows_for(self, rid):
        return [r for r in _rows() if r["release_id"] == rid]

    def latest_activated(self):
        act = [r for r in _rows() if r["event"] == "ACTIVATED"]
        return max(act, key=lambda r: r["event_ts"])["release_id"] if act else None

    def append(self, row):
        rows = _rows()
        row = dict(row)
        ts = row["event_ts"]
        row["event_ts"] = ts.isoformat() if isinstance(ts, datetime) else str(ts)
        rows.append(row)
        REG.write_text(json.dumps(rows), encoding="utf-8")


def fs(args):
    op, rest = args[0], args[1:]
    if op == "ls":
        target = _map(rest[0])
        if not target.is_dir():
            print(f"Error: no such directory: {rest[0]}", file=sys.stderr)
            return 1
        names = sorted(p.name for p in target.iterdir())
        if "--output" in rest and rest[rest.index("--output") + 1] == "json":
            print(json.dumps([{"name": n, "is_directory": False} for n in names], indent=2))
        else:
            print("\n".join(names))
        return 0
    if op == "cp":
        recursive = "-r" in rest or "--recursive" in rest
        overwrite = "--overwrite" in rest
        paths = [a for a in rest if not a.startswith("-")]
        src, dst = _map(paths[0]), _map(paths[1])
        if recursive:
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                if (dst / f.name).exists() and not overwrite:
                    print(f"{f} -> {dst / f.name} (skipped; already exists)")
                    continue
                shutil.copy2(f, dst / f.name)
            return 0
        if dst.exists() and not overwrite:
            print(f"{paths[0]} -> {paths[1]} (skipped; already exists)")
            return 0
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return 0
    return 2


def bundle(args):
    if args[0] == "deploy":
        if FAIL_ON == "deploy":
            print("Error: deploy failed", file=sys.stderr)
            return 1
        print("Deployment complete!")
        return 0
    if args[0] == "run":
        params = dict(kv.split("=", 1) for kv in args[args.index("--params") + 1].split(","))
        from mdf.register import main as register_main

        rc = register_main(
            [
                "--release-id",
                params.get("release_id", ""),
                "--mode",
                params.get("mode", "register"),
                "--catalog",
                os.environ.get("MDF_CATALOG", "dev_catalog"),
                "--actor",
                params.get("actor", "manual"),
                "--github-release-url",
                params.get("github_release_url", ""),
                "--volume-root",
                str(ROOT / "Volumes"),
            ],
            registry=JsonRegistry(),
        )
        print("Run URL: https://dbc-0000-fake.cloud.databricks.com/?o=1#job/1/run/2")
        if rc:
            print("Error: run failed", file=sys.stderr)
        return rc
    return 2


def _sql(stmt: str, params: dict) -> list:
    rows = _rows()
    rid = params.get("rid")
    if stmt.startswith("SELECT release_id FROM"):
        act = sorted((r for r in rows if r["event"] == "ACTIVATED"), key=lambda r: r["event_ts"])
        return [[act[-1]["release_id"]]] if act else []
    mine = sorted((r for r in rows if r["release_id"] == rid), key=lambda r: r["event_ts"])
    if stmt.startswith("SELECT event, manifest_sha256, CAST(file_count AS STRING) FROM"):
        return [[r["event"], r["manifest_sha256"], str(r["file_count"])] for r in mine]
    return [
        [
            r["event"],
            r["manifest_sha256"],
            str(r["file_count"]),
            r["volume_path"],
            r["actor"],
            r["event_ts"],
        ]
        for r in mine
    ]


def api(args):
    if args[0] == "post" and args[1] == "/api/2.0/sql/statements":
        body = json.loads(args[args.index("--json") + 1])
        params = {p["name"]: p["value"] for p in body.get("parameters", [])}
        data = _sql(body["statement"], params)
        print(
            json.dumps(
                {
                    "statement_id": "s1",
                    "status": {"state": "SUCCEEDED"},
                    "result": {"data_array": data},
                }
            )
        )
        return 0
    return 2


def main(argv):
    _log(argv)
    args = [a for a in argv if a not in ("-t", "dev")] if argv and argv[0] == "bundle" else argv
    if args[0] == "fs":
        return fs(args[1:])
    if args[0] == "bundle":
        return bundle(args[1:])
    if args[0] == "api":
        return api(args[1:])
    if args[:2] == ["warehouses", "list"]:
        print(json.dumps([{"id": "wh-fake"}]))
        return 0
    print(f"fake databricks: unsupported {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    _ = UTC
    sys.exit(main(sys.argv[1:]))
