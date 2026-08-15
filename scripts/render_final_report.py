"""Audit an Agent interpretation and merge it into the standalone chart HTML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from render_chart import render_html
from verify_facts import verify_report


def build_final_report(session: dict[str, object], report: str) -> tuple[str, dict[str, object]]:
    if not report.strip():
        raise ValueError("interpretation report is empty")
    result = session.get("result", session)
    if not isinstance(result, dict):
        raise ValueError("session must contain a chart result")
    audit = verify_report(report, result)
    if not audit["accepted"]:
        return "", audit
    return render_html(session, report), audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and render a complete Liuyao HTML report")
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audit-output", type=Path)
    args = parser.parse_args()

    session = json.loads(args.session.read_text(encoding="utf-8"))
    report = args.report.read_text(encoding="utf-8")
    final_html, audit = build_final_report(session, report)
    audit_text = json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
    if args.audit_output:
        args.audit_output.write_text(audit_text, encoding="utf-8")
    if not audit["accepted"]:
        print(audit_text, end="")
        raise SystemExit(2)
    args.output.write_text(final_html, encoding="utf-8")
    print(json.dumps({"ok": True, "html": str(args.output.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
