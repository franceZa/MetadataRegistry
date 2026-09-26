import argparse
import sys
from typing import List, Optional

from mdf.compile import compile_project
from mdf.diff import run_diff
from mdf.package import build_package, verify_package
from mdf.rules import RuleConfigError
from mdf.trace import format_trace, trace_table
from mdf.validation import validate_project


def _cmd_validate(args) -> int:
    report = validate_project(base_dir=args.datacontract_dir, config_dir=args.config_dir)
    print(report.format_thai_summary())
    return 0 if report.is_valid else 1


def _cmd_compile(args) -> int:
    try:
        written = compile_project(env=args.env, base_dir=args.datacontract_dir, config_dir=args.config_dir)
        print(f"✅ compile สำเร็จ: เขียน resolved JSON {len(written)} ไฟล์ลง build/{args.env}/resolved/")
        for p in written:
            print(f"   - {p}")
        return 0
    except RuntimeError as e:
        print(str(e))
        return 1


def _cmd_diff(args) -> int:
    try:
        result = run_diff(rev=args.base, base_dir=args.datacontract_dir)
        print(result.summary_thai())
        return 1 if result.has_breaking else 0
    except Exception as e:
        print(f"[DIFF_ERROR] ไม่สามารถ diff กับ baseline '{args.base}' ได้: {e}")
        return 1


def _cmd_package(args) -> int:
    try:
        pkg_dir = build_package(env=args.env, release=args.release)
        print(f"✅ package สร้างที่: {pkg_dir}")
        if not args.release:
            print("   (โหมด preview — ใช้ --release เพื่อบังคับ release gate)")
        return 0
    except RuntimeError as e:
        print(str(e))
        return 1


def _cmd_verify_package(args) -> int:
    try:
        result = verify_package(args.package_dir)
        print(f"✅ package ผ่านการตรวจสอบ (OK): env={result['env']}, files={result['verified_files']}")
        return 0
    except RuntimeError as e:
        print(str(e))
        return 1


def _cmd_trace(args) -> int:
    try:
        trace = trace_table(args.table, env=args.env)
        print(format_trace(trace))
        return 0
    except (ValueError, FileNotFoundError) as e:
        print(f"[TRACE_ERROR] {e}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdf",
        description="mdf — Metadata-driven Data Contract validator & Bronze/Silver config generator (Phase 1)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="ตรวจสอบ DataContract + config ทั้งโปรเจกต์")
    _add_common_args(p_validate)
    p_validate.set_defaults(func=_cmd_validate)

    p_compile = sub.add_parser("compile", help="สร้าง resolved JSON configs ลง build/<env>/resolved/")
    _add_common_args(p_compile)
    p_compile.add_argument("--env", default="dev", help="ชื่อ environment (default: dev)")
    p_compile.set_defaults(func=_cmd_compile)

    p_diff = sub.add_parser("diff", help="เทียบ metadata ปัจจุบันกับ git baseline rev")
    _add_common_args(p_diff)
    p_diff.add_argument("--base", required=True, help="git revision ของ baseline (เช่น 88b982d)")
    p_diff.set_defaults(func=_cmd_diff)

    p_package = sub.add_parser("package", help="รวม resolved configs เป็น release package")
    _add_common_args(p_package)
    p_package.add_argument("--env", default="dev", help="ชื่อ environment (default: dev)")
    p_package.add_argument("--release", action="store_true", help="บังคับ release gate (AC-16)")
    p_package.set_defaults(func=_cmd_package)

    p_verify = sub.add_parser("verify-package", help="ตรวจสอบความถูกต้อง (tamper-evident) ของ package")
    p_verify.add_argument("package_dir", help="โฟลเดอร์ package ที่มี manifest.json")
    p_verify.set_defaults(func=_cmd_verify_package)

    p_trace = sub.add_parser("trace", help="แสดง lineage ของ target table (เช่น silver.cc.credit_card_txn)")
    p_trace.add_argument("table", help="ชื่อ table รูปแบบ <layer>.<source>.<dataset>")
    p_trace.add_argument("--env", default="dev", help="ชื่อ environment (default: dev)")
    p_trace.set_defaults(func=_cmd_trace)

    return parser


def _add_common_args(p) -> None:
    p.add_argument("--datacontract-dir", default="DataContract", help="โฟลเดอร์ DataContract (default: DataContract)")
    p.add_argument("--config-dir", default="config", help="โฟลเดอร์ config (default: config)")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RuleConfigError as e:
        # FR-C.6: rule/library config errors exit 2
        print(f"[RULE_CONFIG_ERROR] {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
