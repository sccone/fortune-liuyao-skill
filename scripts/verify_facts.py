"""Audit only explicit deterministic chart claims; never grade divination."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


POSITION = {"初": 1, "二": 2, "三": 3, "四": 4, "五": 5, "上": 6}
RELATIVES = ("父母", "兄弟", "子孙", "妻财", "官鬼")
DIGIT_POSITION = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}


def _claimed_position(token: str) -> int | None:
    """Accept 初/二/上爻 as well as the 第5爻 form that reports use for candidates."""
    token = token.lstrip("第")
    if token in POSITION:
        return POSITION[token]
    if token in DIGIT_POSITION:
        return DIGIT_POSITION[token]
    return int(token) if token.isdigit() and 1 <= int(token) <= 6 else None


def _audit_options(text: str, analysis: dict[str, Any], errors: list[dict[str, object]]) -> None:
    """Check only that stated option↔position mappings match the frozen bindings.

    Which option is better stays unrestricted, exactly like 吉凶 and 应期.
    """
    mapping = analysis.get("optionMapping")
    if not isinstance(mapping, dict):
        return
    bound = {
        str(item.get("optionId")): str(item.get("ref"))
        for item in mapping.get("bindings", [])
        if isinstance(item, dict)
    }
    reported: set[str] = set()
    for match in re.finditer(r"选项\s*([A-Za-z0-9]+)", text):
        option_id = match.group(1)
        if option_id not in bound and option_id not in reported:
            reported.add(option_id)
            errors.append({"type": "option_unbound", "claimed": option_id, "actual": sorted(bound)})
    for match in re.finditer(r"选项\s*([A-Za-z0-9]+)\s*(?:对应|落在|取|为|是)\s*(第?[初一二三四五六上]|第?[1-6])爻", text):
        option_id = match.group(1)
        actual_ref = bound.get(option_id)
        claimed = _claimed_position(match.group(2))
        if actual_ref is None or claimed is None:
            continue
        kind, _, raw = actual_ref.partition(":")
        if claimed != int(raw):
            errors.append({
                "type": "option_binding", "optionId": option_id,
                "claimed": claimed, "actual": int(raw), "actualRef": actual_ref, "hidden": kind == "hidden",
            })


def verify_report(text: str, response: dict[str, Any]) -> dict[str, Any]:
    """Return explicit fact conflicts without judging吉凶、应期 or traditional inference."""
    chart = response.get("chart", response)
    analysis = response.get("analysis") or response.get("deterministicRuleFacts") or {}
    errors: list[dict[str, object]] = []
    for match in re.finditer(r"([初二三四五上])爻(?:为|是|临)?(父母|兄弟|子孙|妻财|官鬼)", text):
        position = POSITION[match.group(1)]
        actual = chart.get("lines", [])[position - 1].get("sixRelative")
        if actual != match.group(2):
            errors.append({"type": "line_relative", "position": position, "claimed": match.group(2), "actual": actual})
    for label, field in (("世", "shiPosition"), ("应", "yingPosition")):
        for match in re.finditer(rf"{label}爻(?:在|居|临)([初二三四五上])爻", text):
            claimed = POSITION[match.group(1)]
            actual = chart.get(field)
            if claimed != actual:
                errors.append({"type": f"{field}", "claimed": claimed, "actual": actual})
    original = (chart.get("originalHexagram") or {}).get("name")
    changed = (chart.get("changedHexagram") or {}).get("name")
    for label, actual in (("本卦", original), ("变卦", changed)):
        match = re.search(rf"{label}(?:为|是|：)\s*([^，。；\s]+)", text)
        if match and actual and match.group(1) != actual:
            errors.append({"type": label, "claimed": match.group(1), "actual": actual})
    _audit_options(text, analysis if isinstance(analysis, dict) else {}, errors)
    return {
        "schemaVersion": "fortune-liuyao-fact-audit.v1",
        "accepted": not errors,
        "errors": errors,
        "scope": "explicit_deterministic_chart_claims_and_option_bindings",
        "unrestricted": ["吉凶判断", "应期推断", "传统取象", "作用链主次", "选项优劣"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit explicit chart facts in a completed interpretation")
    parser.add_argument("--chart", required=True, type=Path, help="Unified run JSON or raw chart JSON")
    parser.add_argument("--report", required=True, type=Path, help="Completed Markdown or text interpretation")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    response = json.loads(args.chart.read_text(encoding="utf-8"))
    result = verify_report(args.report.read_text(encoding="utf-8"), response.get("result", response))
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    raise SystemExit(0 if result["accepted"] else 2)


if __name__ == "__main__":
    main()
