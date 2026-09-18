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

# The audit is the only thing standing between a reading and a misstated chart,
# so it has to bite in whichever language the reading was written in. An English
# reading checked by Chinese patterns matches nothing and is accepted vacuously,
# which is worse than no audit at all because it still reports "accepted".
#
# The English patterns mirror the Chinese ones clause for clause rather than
# casting a wider net: only an explicit claim is checked, because a false
# rejection discards a reading the caller already paid for.
EN_POSITION = {"bottom": 1, "top": 6}
EN_RELATIVES = {"parent": "父母", "sibling": "兄弟", "offspring": "子孙",
                "wealth": "妻财", "officer": "官鬼"}
# A line is named three ways in English, and the number follows the word where
# Chinese puts it first -- "line 3", not "3 line". Writing the Chinese order here
# is a silent failure: the pattern simply never matches and every English reading
# is accepted without being checked.
EN_LINE = (r"(?:the\s+)?(?:(?P<line_word>bottom|top)\s+line"
           r"|lines?\s+(?P<line_num>[1-6])"
           r"|(?P<line_ord>[1-6])(?:st|nd|rd|th)\s+line)")


def _en_position(match: "re.Match[str]") -> int | None:
    groups = match.groupdict()
    if groups.get("line_word"):
        return EN_POSITION[groups["line_word"].lower()]
    raw = groups.get("line_num") or groups.get("line_ord")
    return int(raw) if raw else None


def _claimed_position(token: str) -> int | None:
    """Accept 初/二/上爻, the 第5爻 form reports use, and the English line names."""
    token = token.strip().lstrip("第")
    if token in POSITION:
        return POSITION[token]
    if token in DIGIT_POSITION:
        return DIGIT_POSITION[token]
    if token.lower() in EN_POSITION:
        return EN_POSITION[token.lower()]
    return int(token) if token.isdigit() and 1 <= int(token) <= 6 else None


def _audit_english(text: str, chart: dict[str, Any], errors: list[dict[str, object]]) -> None:
    """Check the same three claim shapes the Chinese pass checks."""
    lines = chart.get("lines", [])
    verbs = r"(?:is|are|sits\s+as|carries|holds|bears)\s+(?:the\s+)?"
    relatives = "|".join(EN_RELATIVES)
    for match in re.finditer(rf"{EN_LINE}\s+{verbs}(?P<relative>{relatives})\b", text, re.IGNORECASE):
        position = _en_position(match)
        claimed = EN_RELATIVES[match.group("relative").lower()]
        if position is None or position > len(lines):
            continue
        actual = lines[position - 1].get("sixRelative")
        if actual != claimed:
            errors.append({"type": "line_relative", "position": position,
                           "claimed": claimed, "actual": actual})
    for label, field in (("Shi", "shiPosition"), ("Ying", "yingPosition")):
        for match in re.finditer(rf"\b{label}\b[^.\n]{{0,32}}?\b(?:on|at)\s+{EN_LINE}", text, re.IGNORECASE):
            claimed = _en_position(match)
            actual = chart.get(field)
            if claimed is not None and actual is not None and claimed != actual:
                errors.append({"type": field, "claimed": claimed, "actual": actual})


def _audit_english_hexagrams(text: str, chart: dict[str, Any], errors: list[dict[str, object]]) -> None:
    """Flag a King Wen name that belongs to a different hexagram.

    Compared on the transliterated name rather than the whole rendered string,
    because a reading may reasonably shorten "Water over Thunder - Zhun" to
    "Zhun". Several hexagrams transliterate alike without tones; that only makes
    the check more forgiving, which is the direction a fact audit should err in.
    """
    try:
        from lexicon import KING_WEN
    except ImportError:  # Auditing works without the lexicon; it just skips this claim.
        return
    pinyin = {}
    for name, (roman, _gloss) in KING_WEN.items():
        pinyin.setdefault(roman.lower(), set()).add(name)
    for label, pattern, key in (
        ("本卦", r"primary hexagram\s*(?:is|:)\s*([^.;\n]{1,60})", "originalHexagram"),
        ("变卦", r"chang(?:ing|es|ed)\s+(?:in)?to\s*([^.;\n]{1,60})", "changedHexagram"),
    ):
        actual_name = (chart.get(key) or {}).get("name")
        if not actual_name:
            continue
        actual_king_wen = actual_name[0] if actual_name[1:2] == "为" else actual_name[2:]
        actual_roman = KING_WEN.get(actual_king_wen, ("", ""))[0].lower()
        for match in re.finditer(pattern, text, re.IGNORECASE):
            claimed_romans = {
                word.lower() for word in re.findall(r"[A-Za-z]+", match.group(1))
            } & set(pinyin)
            if claimed_romans and actual_roman not in claimed_romans:
                errors.append({"type": label, "claimed": match.group(1).strip(), "actual": actual_name})


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
    for match in re.finditer(r"(?:选项\s*|[Oo]ption\s+)([A-Za-z0-9]+)", text):
        option_id = match.group(1)
        if option_id not in bound and option_id not in reported:
            reported.add(option_id)
            errors.append({"type": "option_unbound", "claimed": option_id, "actual": sorted(bound)})
    claims = list(re.finditer(r"选项\s*([A-Za-z0-9]+)\s*(?:对应|落在|取|为|是)\s*(第?[初一二三四五六上]|第?[1-6])爻", text))
    claims += list(re.finditer(
        rf"[Oo]ption\s+([A-Za-z0-9]+)\b[^.\n]{{0,32}}?"
        rf"\b(?:maps to|is on|sits on|is bound to|takes)\s+{EN_LINE}", text, re.IGNORECASE))
    for match in claims:
        option_id = match.group(1)
        actual_ref = bound.get(option_id)
        claimed = (_en_position(match) if match.groupdict().get("line_word")
                   or match.groupdict().get("line_num") or match.groupdict().get("line_ord")
                   else _claimed_position(match.group(2)))
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
    _audit_english(text, chart, errors)
    _audit_english_hexagrams(text, chart, errors)
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
