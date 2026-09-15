"""Turn the deterministic chart into a plain factual narration.

This is 盘面陈述, not 解读. Every sentence restates something the engine already
computed, so the text is correct by construction: it cannot misstate the chart
because it never asserts anything the chart does not contain. It deliberately
makes no 吉凶 judgement, picks no option and predicts no outcome — weighing
conflicting evidence and committing to a tendency is exactly the part that needs
a reader or a model.

It exists so a caller without a model, without a key, or without a network still
has something true and useful to show instead of an empty screen.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

POSITION_NAMES = {1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"}

# Phrased from the line's side, which is what a reader is judging. The engine
# stores the calendar as the actor, so generated_by means the line feeds the
# month or day and controlled_by means the line restrains it. Only same_element,
# generates and controls score a signal; the other two are narrated, not scored.
MONTH_DAY_RELATION = {
    "same_element": "与{source}比和",
    "generates": "得{source}生",
    "controls": "受{source}克",
    "generated_by": "泄于{source}",
    "controlled_by": "克{source}",
}

# Mirrors _strength_status exactly: it counts signals, it does not weigh them.
STRENGTH_STATUS = {
    "supported": "有扶无克",
    "weakened": "有克无扶",
    "contested": "一扶一克",
    "neutral": "月日无生克信号",
    "not_computed_for_hidden": "伏神不计旺衰",
}

# The engine stores the yongshen as the actor; stated here from the option's side.
YONGSHEN_RELATION = {
    "same_element": "与用神比和",
    "generates": "得用神生",
    "controls": "受用神克",
    "generated_by": "生用神",
    "controlled_by": "克用神",
}

RETURN_RELATION = {
    "same_element": "变爻与本爻比和",
    "generates_original": "回头生",
    "controls_original": "回头克",
    "other": "动变无直接生克",
}

ADVANCE_RETREAT = {"advance": "化进神", "retreat": "化退神", "none": ""}

MECHANISM = {
    "void_fill": "填实",
    "void_clash": "冲空",
    "month_break_exit": "出月破",
    "month_break_harmony": "合破",
    "month_break_value": "破而逢值",
    "moving_harmony": "动而逢合",
    "moving_value": "动而逢值",
    "hidden_release": "冲飞出伏",
}

PATTERN = {"six_clash": "六冲", "six_harmony": "六合", "ordinary": "常规"}

MAPPING_MODE = {"shi_ying": "世应取用", "yongshen_multi": "用神两现取用"}


def _position_name(position: int) -> str:
    return POSITION_NAMES.get(position, f"第{position}爻")


def _ref_name(ref: str) -> str:
    kind, _, raw = str(ref).partition(":")
    if not raw.isdigit():
        return ref
    return f"{_position_name(int(raw))}伏神" if kind == "hidden" else _position_name(int(raw))


def _line_label(line: dict[str, Any]) -> str:
    return f"{line['sixRelative']}{line['najiaStem']}{line['najiaBranch']}{line['najiaElement']}"


def _calendar_standing(line: dict[str, Any], month_branch: str, day_ganzhi: str) -> str:
    parts = []
    for relation, source in (
        (line.get("monthRelation"), f"月建{month_branch}"),
        (line.get("dayRelation"), f"日辰{day_ganzhi}"),
    ):
        template = MONTH_DAY_RELATION.get(relation)
        if template:
            parts.append(template.format(source=source))
    return "，".join(parts)


def _limits(line: dict[str, Any]) -> list[str]:
    return [
        name for name, flag in (
            ("旬空", line.get("isVoid")),
            ("月破", line.get("isMonthBreak")),
            ("日冲", line.get("isDayClash")),
        ) if flag
    ]


def narrate(result: dict[str, Any]) -> str:
    """Return a Markdown narration of the chart's deterministic facts."""
    chart = result.get("chart") or {}
    analysis = result.get("analysis") or result.get("deterministicRuleFacts") or {}
    if not chart.get("lines"):
        raise ValueError("result must contain a chart with lines")

    month_branch = chart.get("monthBranch", "")
    day_ganzhi = chart.get("dayGanzhi", "")
    lines = chart["lines"]
    rows: list[str] = []

    question = (analysis.get("questionContext") or {}).get("question")
    if question:
        rows.append(f"**所问：** {question}")
        rows.append("")

    rows.append("## 盘面")
    rows.append("")
    rows.append(
        f"本卦为{chart['originalHexagram']['name']}，变卦为{chart['changedHexagram']['name']}。"
        f"{chart.get('palace', '')}宫{chart.get('palaceElement', '')}，{chart.get('palaceStage', '')}。"
    )
    rows.append(
        f"世爻在{_position_name(chart['shiPosition'])}（{_line_label(lines[chart['shiPosition'] - 1])}），"
        f"应爻在{_position_name(chart['yingPosition'])}（{_line_label(lines[chart['yingPosition'] - 1])}）。"
    )
    rows.append(f"月建{month_branch}，日辰{day_ganzhi}，旬空{'、'.join(chart.get('voidBranches') or []) or '无'}。")
    rows.append(
        f"卦式由{PATTERN.get(chart.get('originalHexagramPattern'), '常规')}"
        f"转为{PATTERN.get(chart.get('changedHexagramPattern'), '常规')}。"
    )

    yongshen = analysis.get("yongshenRelative")
    candidates = analysis.get("candidates") or []
    rows.append("")
    rows.append("## 用神")
    rows.append("")
    if yongshen and candidates:
        rows.append(f"规则层取{yongshen}为用神，共 {len(candidates)} 处出现：")
        rows.append("")
        for candidate in candidates:
            where = f"{_position_name(candidate['position'])}{'（伏神）' if candidate.get('hidden') else ''}"
            standing = _calendar_standing(candidate, month_branch, day_ganzhi)
            raw_status = (candidate.get("strengthEvidence") or {}).get("status", "")
            status = STRENGTH_STATUS.get(raw_status, "")
            if status and raw_status not in ("not_computed_for_hidden",):
                status = f"信号计数：{status}"
            limits = _limits(candidate)
            detail = "；".join(part for part in [standing, status, "、".join(limits)] if part)
            rows.append(f"- {where} {_line_label(candidate)}{'：' + detail if detail else ''}")
    elif yongshen:
        rows.append(f"规则层取{yongshen}为用神，但本卦六爻未见，需另寻飞伏或改取。")
    else:
        rows.append("规则层未给出用神：该领域无固定取用，需依问题本身确定。")

    moving = [line for line in lines if line.get("moving")]
    rows.append("")
    rows.append("## 动爻")
    rows.append("")
    if not moving:
        rows.append("六爻皆静，无动变。")
    for line in moving:
        changed = line.get("changedLine") or {}
        pieces = [RETURN_RELATION.get(changed.get("returnRelation"), "")]
        advance = ADVANCE_RETREAT.get(changed.get("advanceRetreat"), "")
        if advance:
            pieces.append(advance)
        if changed.get("isVoid"):
            pieces.append("变爻旬空")
        rows.append(
            f"- {_position_name(line['position'])} {_line_label(line)} 动，"
            f"化{changed.get('sixRelative', '')}{changed.get('najiaStem', '')}{changed.get('najiaBranch', '')}"
            f"{'，' + '，'.join(p for p in pieces if p) if any(pieces) else ''}。"
        )

    hidden = chart.get("hiddenLines") or []
    if hidden:
        rows.append("")
        rows.append("## 伏神")
        rows.append("")
        for item in hidden:
            rows.append(
                f"- {_position_name(item['position'])}下伏 {item['sixRelative']}{item['najiaStem']}{item['najiaBranch']}，"
                f"飞神为 {item.get('flyingSixRelative', '')}{item.get('flyingStem', '')}{item.get('flyingBranch', '')}。"
            )

    restricted = [(line, _limits(line)) for line in lines if _limits(line)]
    if restricted:
        rows.append("")
        rows.append("## 受限之爻")
        rows.append("")
        for line, limits in restricted:
            rows.append(f"- {_position_name(line['position'])} {_line_label(line)}：{'、'.join(limits)}")

    timing = analysis.get("timingCandidates") or []
    if timing:
        rows.append("")
        rows.append("## 应期候选")
        rows.append("")
        rows.append("以下是规则层列出的触发条件，属于候选而非断定的日期：")
        rows.append("")
        seen: set[tuple[str, str]] = set()
        for item in timing:
            key = (item.get("mechanism", ""), item.get("triggerBranch", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(f"- {MECHANISM.get(item.get('mechanism'), item.get('mechanism', ''))}：逢{item.get('triggerBranch', '')}")

    mapping = analysis.get("optionMapping")
    if isinstance(mapping, dict):
        labels = {
            str(option.get("optionId")): str(option.get("label", ""))
            for option in (analysis.get("questionContext") or {}).get("options", [])
        }
        arguments = {item["optionId"]: item for item in analysis.get("optionArguments") or []}
        rows.append("")
        rows.append("## 选项对比")
        rows.append("")
        rows.append(f"取用格式：{MAPPING_MODE.get(mapping.get('mappingMode'), mapping.get('mappingMode', ''))}。绑定在起卦前声明并已冻结。")
        rows.append("")
        for binding in mapping.get("bindings", []):
            option_id = str(binding.get("optionId"))
            argument = arguments.get(option_id, {})
            detail = []
            if argument.get("sixRelative"):
                detail.append(argument["sixRelative"])
            status = STRENGTH_STATUS.get(argument.get("strengthStatus", ""), "")
            if status:
                detail.append(status)
            rows.append(
                f"- 选项 {option_id}（{labels.get(option_id, '')}）对应{_ref_name(binding.get('ref', ''))}"
                f"{'：' + '，'.join(detail) if detail else ''}"
            )
        if mapping.get("strengthComparable") is False:
            rows.append("")
            rows.append(
                "各选项所绑六亲不同，两侧旺衰不是同类比，不能直接比大小。"
                "六亲由卦宫五行与该爻纳甲五行算出，是爻的属性，与选项本身无关。"
            )
        # Follow binding order, and lead with the quantity that is comparable when
        # the two sides sit on different 六亲: where the yongshen stands.
        ordered = [str(binding.get("optionId")) for binding in mapping.get("bindings", [])]
        described = [
            (option_id, arguments[option_id])
            for option_id in ordered
            if option_id in arguments
            and (arguments[option_id].get("yongshenLinks") or arguments[option_id].get("carriesYongshen"))
        ]
        if described:
            rows.append("")
            rows.append("用神与各方的关系（六亲不同时，这才是可比的量）：")
            rows.append("")
            for option_id, argument in described:
                statements = []
                if argument.get("carriesYongshen"):
                    statements.append("该爻本身即用神")
                for link in argument.get("yongshenLinks") or []:
                    relation = YONGSHEN_RELATION.get(
                        link.get("relationFromYongshen"), link.get("relationFromYongshen", "")
                    )
                    statements.append(f"对{_ref_name(link.get('ref', ''))}的用神{relation}")
                rows.append(f"- 选项 {option_id}：{'；'.join(statements)}。")

    rows.append("")
    rows.append(
        "> 以上为盘面事实陈述，逐条来自确定性排盘，不含吉凶判断、选项取舍或应期断定。"
        "综合判断需要权衡相互冲突的证据，不在本层生成范围内。"
    )
    rows.append("")
    rows.append("> 本内容基于玄学体系生成，仅供文化爱好与思维参考，不构成任何重大人生决策的专业建议。")
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Narrate a chart's deterministic facts without a model")
    parser.add_argument("--chart", required=True, type=Path, help="Unified run JSON or raw chart result")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.chart.read_text(encoding="utf-8"))
    text = narrate(source.get("result", source))
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
