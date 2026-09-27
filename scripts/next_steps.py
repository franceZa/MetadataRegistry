"""FR-L.14 · T-45 — print "what to do next" for a release, per delivery_mode.

One source of truth for the guidance shown in the GitHub Actions job summary (release.yml) and
in runbooks/release-delivery.md, so they never drift apart.

usage: python scripts/next_steps.py <auto|u2m|manual> <mdf-sha12> \
           [--run-url URL] [--repo owner/name]

Never prints hosts, emails or tokens: it only knows the release id, repo and run URL.
"""

from __future__ import annotations

import argparse
import re
import sys

MODES = ("auto", "u2m", "manual")
RUNBOOK = "runbooks/release-delivery.md"


def _auto(rid: str, repo: str, run_url: str | None) -> list[str]:
    where = f"[หน้า run นี้]({run_url})" if run_url else "หน้า run นี้"
    return [
        f"## ขั้นต่อไป — `{rid}` · mode **auto** (GitHub Actions ส่งเอง)",
        "",
        f"1. เปิด {where} → job **Deliver to Databricks (dev)**",
        "2. ถ้าขึ้น *Waiting for review* → กด **Review deployments** → เลือก `dev` → **Approve**",
        "3. รอ job เขียว แล้วเปิด artifact `mdf-delivery-" + rid + "` ดูหลักฐาน (masked)",
        "4. ตรวจใน Databricks SQL editor:",
        "```sql",
        "SELECT release_id, event, manifest_sha256, actor, event_ts",
        "FROM dev_catalog.ops.release_registry",
        f"WHERE release_id = '{rid}' ORDER BY event_ts;",
        "```",
        "   ต้องได้ REGISTERED 1 แถว + ACTIVATED 1 แถว `actor = github-oidc`",
        "",
        "**ถ้า job หยุดที่ Preflight** (ยังไม่มี federation / เป็น Free Edition): เปลี่ยน "
        "`config/env/dev.yaml` เป็น `delivery_mode: u2m` ผ่าน PR แล้วทำตามขั้นของ u2m "
        f"(`python scripts/next_steps.py u2m {rid}`) · ดู `{RUNBOOK}`",
    ]


def _u2m(rid: str, repo: str, run_url: str | None) -> list[str]:
    return [
        f"## ขั้นต่อไป — `{rid}` · mode **u2m** (คุณ login · สคริปต์ทำที่เหลือ)",
        "",
        "ทำบนเครื่องคุณ ใน git-bash / terminal ที่ root ของ repo:",
        "",
        "1. ดึงโค้ดของ release นี้ (bundle ที่ deploy ต้องตรงกับ release):",
        "```bash",
        "git fetch origin --tags",
        f"git worktree add ../mdf-{rid} {rid}",
        f"cd ../mdf-{rid}",
        "```",
        "2. login ครั้งเดียว (เปิดเบราว์เซอร์ให้กดยืนยัน) — "
        "ข้ามได้ถ้า `databricks auth profiles` ขึ้น Valid YES:",
        "```bash",
        "databricks auth login --host https://<workspace-host> --profile mdf-free",
        "```",
        "3. รันสคริปต์ (ทำ CD-1…8 ให้เองทั้งหมด):",
        "```bash",
        "export DATABRICKS_CONFIG_PROFILE=mdf-free MDF_WAREHOUSE_ID=<sql-warehouse-id>",
        f"bash scripts/deliver_release.sh {rid}",
        "```",
        "4. จบเมื่อเห็น `── ✅ delivered " + rid + f"` · หลักฐานอยู่ที่ `build/deliver/{rid}/evidence.md`",
        "",
        "**ถ้าติด** (ลง CLI ไม่ได้ · login ไม่ผ่าน · เครื่องไม่มี bash): ถอยไป mode manual "
        f"(`python scripts/next_steps.py manual {rid}`) · ดู `{RUNBOOK}`",
    ]


def _manual(rid: str, repo: str, run_url: str | None) -> list[str]:
    rel = f"https://github.com/{repo}/releases/tag/{rid}"
    vol = f"/Volumes/dev_catalog/ops/files/releases/{rid}"
    return [
        f"## ขั้นต่อไป — `{rid}` · mode **manual** (ทำเองในเบราว์เซอร์ ไม่ต้องมี CLI)",
        "",
        f"- [ ] **M-1** เปิด [หน้า Release]({rel}) → ดาวน์โหลดไฟล์ทั้ง 8 ไฟล์ "
        "(6 × `*.resolved.json`, `manifest.json`, `validation-report.json`)",
        "- [ ] **M-2** Databricks → **Catalog** → `dev_catalog` → `ops` → Volume `files` → "
        f"โฟลเดอร์ `releases` → **Create directory** ชื่อ `{rid}`",
        "  - ถ้ามีโฟลเดอร์นี้อยู่แล้ว **และมี `manifest.json`** = ส่งไปแล้ว ข้ามไป M-4",
        f"- [ ] **M-3** เข้า `{vol}` → **Upload to this volume** → อัปโหลดทุกไฟล์ "
        "**ยกเว้น `manifest.json`** → เสร็จแล้วค่อยอัปโหลด `manifest.json` เป็นไฟล์สุดท้าย",
        "- [ ] **M-4** **SQL Editor** → วางไฟล์ `sql/manual/register_release.sql` → ตั้ง parameter "
        f"`release_id = {rid}` → **Run all**",
        "  - ถ้า error `[TAMPERED]` / `[RELEASE_ID_MISMATCH]` / `[RELEASE_NOT_FOUND]` → "
        "แก้ตามข้อความ (ส่วนใหญ่คืออัปโหลดไม่ครบหรือผิดโฟลเดอร์) แล้ว Run all ใหม่",
        "- [ ] **M-5** ดูผล statement สุดท้าย: REGISTERED 1 แถว · `actor = manual-ui` · "
        "`manifest_sha256` ต้องตรงกับ "
        "digest ของ `manifest.json` บนหน้า Release (กดที่ชื่อไฟล์จะเห็น sha256)",
        "- [ ] **M-6** วาง `sql/manual/activate_release.sql` → `release_id = "
        + rid
        + "` → **Run all**",
        f"- [ ] **M-7** ผลสุดท้ายต้องขึ้น `active_release_id = {rid}`",
        "",
        f"รายละเอียดพร้อมภาพหน้าจอ: `{RUNBOOK}` · rollback = ทำ M-6 ด้วย release เก่า",
    ]


BUILDERS = {"auto": _auto, "u2m": _u2m, "manual": _manual}


def render(mode: str, release_id: str, repo: str, run_url: str | None = None) -> str:
    if mode not in MODES:
        raise ValueError(f"delivery_mode ต้องเป็น auto, u2m หรือ manual (ได้ '{mode}')")
    if not re.fullmatch(r"mdf-[0-9a-f]{12}", release_id):
        raise ValueError(f"release_id ต้องเป็น mdf-<sha12> (ได้ '{release_id}')")
    return "\n".join(BUILDERS[mode](release_id, repo, run_url)) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("mode")
    p.add_argument("release_id")
    p.add_argument("--run-url")
    p.add_argument("--repo", default="franceZa/MetadataRegistry")
    a = p.parse_args(argv)
    try:
        sys.stdout.write(render(a.mode, a.release_id, a.repo, a.run_url))
    except ValueError as e:
        print(f"[NEXT_STEPS] {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
