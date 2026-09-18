"""Turn the deterministic chart into a plain factual narration.

This is 盘面陈述, not 解读. Every sentence restates something the engine already
computed, so the text is correct by construction: it cannot misstate the chart
because it never asserts anything the chart does not contain. It deliberately
makes no 吉凶 judgement, picks no option and predicts no outcome — weighing
conflicting evidence and committing to a tendency is exactly the part that needs
a reader or a model.

It exists so a caller without a model, without a key, or without a network still
has something true and useful to show instead of an empty screen.

Both languages are generated from the same walk over the chart rather than from
two separate writers, so neither can quietly grow a claim the other does not make.
Every phrase a sentence needs lives in `Phrases`, which is frozen and complete:
adding a phrase to one language fails to construct the other until it is supplied.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lexicon import DEFAULT_LANGUAGE, hexagram as _hexagram, normalize, term


@dataclass(frozen=True)
class Phrases:
    """Every word this module prints, for one language."""

    positions: dict[int, str]
    position_fallback: str
    hidden_suffix: str
    # A candidate row names the line and then marks it; a reference names the
    # hidden line itself. Chinese distinguishes the two, so both forms are kept.
    hidden_marker: str
    # Phrased from the line's side, which is what a reader is judging. The engine
    # stores the calendar as the actor, so generated_by means the line feeds the
    # month or day and controlled_by means the line restrains it. Only same_element,
    # generates and controls score a signal; the other two are narrated, not scored.
    month_day: dict[str, str]
    # Mirrors _strength_status exactly: it counts signals, it does not weigh them.
    strength: dict[str, str]
    signal_count: str
    # The engine stores the yongshen as the actor; stated here from the option's side.
    yongshen_relation: dict[str, str]
    return_relation: dict[str, str]
    advance_retreat: dict[str, str]
    mechanism: dict[str, str]
    pattern: dict[str, str]
    mapping_mode: dict[str, str]
    limits: dict[str, str]
    month_source: str
    day_source: str
    sentence_join: str
    list_join: str
    clause_join: str
    detail_join: str
    detail_lead: str
    question_label: str
    heading_chart: str
    heading_yongshen: str
    heading_moving: str
    heading_hidden: str
    heading_restricted: str
    heading_timing: str
    heading_options: str
    hexagram_line: str
    palace_line: str
    shi_ying_line: str
    calendar_line: str
    no_void: str
    structure_line: str
    yongshen_found: str
    yongshen_absent: str
    yongshen_none: str
    all_still: str
    moving_row: str
    changed_void: str
    hidden_row: str
    timing_intro: str
    timing_row: str
    option_mode_line: str
    option_row: str
    not_comparable: str
    yongshen_link_intro: str
    carries_yongshen: str
    yongshen_link: str
    option_link_row: str
    scope_note: str
    disclaimer: str


ZH = Phrases(
    positions={1: "初爻", 2: "二爻", 3: "三爻", 4: "四爻", 5: "五爻", 6: "上爻"},
    position_fallback="第{position}爻",
    hidden_suffix="伏神",
    hidden_marker="（伏神）",
    month_day={
        "same_element": "与{source}比和",
        "generates": "得{source}生",
        "controls": "受{source}克",
        "generated_by": "泄于{source}",
        "controlled_by": "克{source}",
    },
    strength={
        "supported": "有扶无克",
        "weakened": "有克无扶",
        "contested": "一扶一克",
        "neutral": "月日无生克信号",
        "not_computed_for_hidden": "伏神不计旺衰",
    },
    signal_count="信号计数：{status}",
    yongshen_relation={
        "same_element": "与用神比和",
        "generates": "得用神生",
        "controls": "受用神克",
        "generated_by": "生用神",
        "controlled_by": "克用神",
    },
    return_relation={
        "same_element": "变爻与本爻比和",
        "generates_original": "回头生",
        "controls_original": "回头克",
        "other": "动变无直接生克",
    },
    advance_retreat={"advance": "化进神", "retreat": "化退神", "none": ""},
    mechanism={
        "void_fill": "填实",
        "void_clash": "冲空",
        "month_break_exit": "出月破",
        "month_break_harmony": "合破",
        "month_break_value": "破而逢值",
        "moving_harmony": "动而逢合",
        "moving_value": "动而逢值",
        "hidden_release": "冲飞出伏",
    },
    pattern={"six_clash": "六冲", "six_harmony": "六合", "ordinary": "常规"},
    mapping_mode={"shi_ying": "世应取用", "yongshen_multi": "用神两现取用"},
    limits={"void": "旬空", "month_break": "月破", "day_clash": "日冲"},
    month_source="月建{branch}",
    day_source="日辰{ganzhi}",
    sentence_join="",
    list_join="、",
    clause_join="，",
    detail_join="；",
    detail_lead="：",
    question_label="**所问：** {question}",
    heading_chart="## 盘面",
    heading_yongshen="## 用神",
    heading_moving="## 动爻",
    heading_hidden="## 伏神",
    heading_restricted="## 受限之爻",
    heading_timing="## 应期候选",
    heading_options="## 选项对比",
    hexagram_line="本卦为{original}，变卦为{changed}。",
    palace_line="{palace}宫{element}，{stage}。",
    shi_ying_line="世爻在{shi}（{shi_label}），应爻在{ying}（{ying_label}）。",
    calendar_line="月建{month}，日辰{day}，旬空{void}。",
    no_void="无",
    structure_line="卦式由{original}转为{changed}。",
    yongshen_found="规则层取{relative}为用神，共 {count} 处出现：",
    yongshen_absent="规则层取{relative}为用神，但本卦六爻未见，需另寻飞伏或改取。",
    yongshen_none="规则层未给出用神：该领域无固定取用，需依问题本身确定。",
    all_still="六爻皆静，无动变。",
    moving_row="- {position} {label} 动，化{changed}{detail}。",
    changed_void="变爻旬空",
    hidden_row="- {position}下伏 {hidden}，飞神为 {flying}。",
    timing_intro="以下是规则层列出的触发条件，属于候选而非断定的日期：",
    timing_row="- {mechanism}：逢{branch}",
    option_mode_line="取用格式：{mode}。绑定在起卦前声明并已冻结。",
    option_row="- 选项 {option}（{label}）对应{position}{detail}",
    not_comparable=(
        "各选项所绑六亲不同，两侧旺衰不是同类比，不能直接比大小。"
        "六亲由卦宫五行与该爻纳甲五行算出，是爻的属性，与选项本身无关。"
    ),
    yongshen_link_intro="用神与各方的关系（六亲不同时，这才是可比的量）：",
    carries_yongshen="该爻本身即用神",
    yongshen_link="对{position}的用神{relation}",
    option_link_row="- 选项 {option}：{statements}。",
    scope_note=(
        "> 以上为盘面事实陈述，逐条来自确定性排盘，不含吉凶判断、选项取舍或应期断定。"
        "综合判断需要权衡相互冲突的证据，不在本层生成范围内。"
    ),
    disclaimer="> 本内容基于玄学体系生成，仅供文化爱好与思维参考，不构成任何重大人生决策的专业建议。",
)

EN = Phrases(
    positions={1: "the bottom line", 2: "line 2", 3: "line 3",
               4: "line 4", 5: "line 5", 6: "the top line"},
    position_fallback="line {position}",
    hidden_suffix=" (hidden)",
    hidden_marker=" (hidden)",
    month_day={
        "same_element": "matches {source} in element",
        "generates": "is generated by {source}",
        "controls": "is controlled by {source}",
        "generated_by": "drains into {source}",
        "controlled_by": "controls {source}",
    },
    strength={
        "supported": "support, no restraint",
        "weakened": "restraint, no support",
        "contested": "one support, one restraint",
        "neutral": "no generating or controlling signal from month or day",
        "not_computed_for_hidden": "strength is not computed for a hidden line",
    },
    signal_count="signal count: {status}",
    yongshen_relation={
        "same_element": "matches the yongshen in element",
        "generates": "is generated by the yongshen",
        "controls": "is controlled by the yongshen",
        "generated_by": "generates the yongshen",
        "controlled_by": "controls the yongshen",
    },
    return_relation={
        "same_element": "the changed line matches the original in element",
        "generates_original": "the change generates the original line",
        "controls_original": "the change controls the original line",
        "other": "no direct generation or control between the two",
    },
    advance_retreat={"advance": "changing to an advancing line",
                     "retreat": "changing to a retreating line", "none": ""},
    mechanism={
        "void_fill": "the void is filled",
        "void_clash": "the void is clashed",
        "month_break_exit": "the month break is left behind",
        "month_break_harmony": "the break is harmonized",
        "month_break_value": "the break meets its own branch",
        "moving_harmony": "the moving line meets harmony",
        "moving_value": "the moving line meets its own branch",
        "hidden_release": "the flying line is clashed, releasing the hidden one",
    },
    pattern={"six_clash": "Six Clashes", "six_harmony": "Six Harmonies", "ordinary": "ordinary"},
    mapping_mode={"shi_ying": "the Shi and Ying positions",
                  "yongshen_multi": "two appearances of the yongshen"},
    limits={"void": "void", "month_break": "month break", "day_clash": "day clash"},
    month_source="the month branch {branch}",
    day_source="the day {ganzhi}",
    sentence_join=" ",
    list_join=", ",
    clause_join=", ",
    detail_join="; ",
    detail_lead=": ",
    question_label="**Question:** {question}",
    heading_chart="## The Chart",
    heading_yongshen="## Yongshen",
    heading_moving="## Moving Lines",
    heading_hidden="## Hidden Lines",
    heading_restricted="## Restricted Lines",
    heading_timing="## Timing Candidates",
    heading_options="## Option Comparison",
    hexagram_line="The primary hexagram is {original}, changing to {changed}.",
    palace_line="Palace {palace} ({element}), {stage}.",
    shi_ying_line="Shi, the asking side, is on {shi} ({shi_label}); Ying, the other side, is on {ying} ({ying_label}).",
    calendar_line="Month branch {month}, day {day}, void branches {void}.",
    no_void="none",
    structure_line="The structure moves from {original} to {changed}.",
    yongshen_found="The rule layer takes {relative} as the yongshen. It appears in {count} place(s):",
    yongshen_absent=(
        "The rule layer takes {relative} as the yongshen, but it appears on none of the six "
        "lines, so it must be sought among the hidden lines or taken differently."
    ),
    yongshen_none=(
        "The rule layer names no yongshen: this domain has no fixed choice, so it must be "
        "settled from the question itself."
    ),
    all_still="All six lines are still; nothing changes.",
    moving_row="- {position}, {label}, is moving and becomes {changed}{detail}.",
    changed_void="the changed line is void",
    hidden_row="- Hidden beneath {position}: {hidden}. The flying line above it is {flying}.",
    timing_intro=(
        "These are the trigger conditions the rule layer lists. They are candidates, "
        "not dated predictions:"
    ),
    timing_row="- {mechanism}: when {branch} comes round",
    option_mode_line="Bound by {mode}. The bindings were declared before the cast and are frozen.",
    option_row="- Option {option} ({label}) maps to {position}{detail}",
    not_comparable=(
        "The options are bound to different six relatives, so their strengths are not "
        "like for like and cannot be ranked against each other. A six relative is computed "
        "from the palace element and the line's own najia element: it is a property of the "
        "line, not of the option placed on it."
    ),
    yongshen_link_intro=(
        "How each side stands to the yongshen. When the six relatives differ, this is the "
        "quantity that is comparable:"
    ),
    carries_yongshen="the line is itself the yongshen",
    yongshen_link="toward the yongshen on {position}, it {relation}",
    option_link_row="- Option {option}: {statements}.",
    scope_note=(
        "> The above states facts from the chart, each one computed deterministically. "
        "It contains no judgement of fortune, chooses no option and fixes no date. "
        "Weighing conflicting evidence is not produced at this layer."
    ),
    disclaimer=(
        "> This content is generated from a metaphysical tradition, for cultural interest "
        "and reflection only. It is not professional advice for any significant life decision."
    ),
)

PHRASES = {"zh": ZH, "en": EN}


def _position_name(position: int, phrases: Phrases) -> str:
    return phrases.positions.get(position, phrases.position_fallback.format(position=position))


def _opening(text: str) -> str:
    """Capitalize a phrase that has been moved to the front of a sentence.

    English position names read mid-sentence ("on the bottom line"), so the same
    string needs a capital when a bullet starts with it. A no-op for Chinese,
    which has no case.
    """
    return text[:1].upper() + text[1:] if text else text


def _ref_name(ref: str, phrases: Phrases) -> str:
    kind, _, raw = str(ref).partition(":")
    if not raw.isdigit():
        return ref
    name = _position_name(int(raw), phrases)
    return f"{name}{phrases.hidden_suffix}" if kind == "hidden" else name


def _ganzhi(stem: str, branch: str, language: str) -> str:
    """Najia is a coordinate pair; English keeps the two halves visibly paired."""
    if normalize(language) == "zh":
        return f"{stem}{branch}"
    return "-".join(part for part in (term(stem, language), term(branch, language)) if part)


def _najia_label(line: dict[str, Any], language: str) -> str:
    """Relative plus najia, without the element.

    Hidden and flying lines are named this way: the row states where they sit,
    and the element belongs to the reasoning about them rather than to the name.
    """
    stem_branch = _ganzhi(line.get("najiaStem", ""), line.get("najiaBranch", ""), language)
    relative = term(line.get("sixRelative"), language)
    return f"{relative}{stem_branch}" if normalize(language) == "zh" else f"{relative} {stem_branch}"


def _line_label(line: dict[str, Any], language: str) -> str:
    stem_branch = _ganzhi(line.get("najiaStem", ""), line.get("najiaBranch", ""), language)
    relative = term(line.get("sixRelative"), language)
    element = term(line.get("najiaElement"), language)
    if normalize(language) == "zh":
        return f"{relative}{stem_branch}{element}"
    return f"{relative} {stem_branch} ({element})"


def _calendar_standing(line: dict[str, Any], month_branch: str, day_ganzhi: str,
                       phrases: Phrases, language: str) -> str:
    parts = []
    sources = (
        (line.get("monthRelation"), phrases.month_source.format(branch=term(month_branch, language))),
        (line.get("dayRelation"), phrases.day_source.format(ganzhi=_day(day_ganzhi, language))),
    )
    for relation, source in sources:
        template = phrases.month_day.get(relation)
        if template:
            parts.append(template.format(source=source))
    return phrases.clause_join.join(parts)


def _day(day_ganzhi: str, language: str) -> str:
    if normalize(language) == "zh" or len(day_ganzhi) != 2:
        return day_ganzhi
    return _ganzhi(day_ganzhi[0], day_ganzhi[1], language)


def _limits(line: dict[str, Any], phrases: Phrases) -> list[str]:
    return [
        phrases.limits[name] for name, flag in (
            ("void", line.get("isVoid")),
            ("month_break", line.get("isMonthBreak")),
            ("day_clash", line.get("isDayClash")),
        ) if flag
    ]


def narrate(result: dict[str, Any], language: str = DEFAULT_LANGUAGE) -> str:
    """Return a Markdown narration of the chart's deterministic facts."""
    language = normalize(language)
    phrases = PHRASES[language]
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
        rows.append(phrases.question_label.format(question=question))
        rows.append("")

    rows.append(phrases.heading_chart)
    rows.append("")
    rows.append(
        phrases.hexagram_line.format(
            original=_hexagram(chart["originalHexagram"]["name"], language),
            changed=_hexagram(chart["changedHexagram"]["name"], language),
        )
        + phrases.sentence_join
        + phrases.palace_line.format(
            palace=term(chart.get("palace", ""), language),
            element=term(chart.get("palaceElement", ""), language),
            stage=term(chart.get("palaceStage", ""), language),
        )
    )
    rows.append(
        phrases.shi_ying_line.format(
            shi=_position_name(chart["shiPosition"], phrases),
            shi_label=_line_label(lines[chart["shiPosition"] - 1], language),
            ying=_position_name(chart["yingPosition"], phrases),
            ying_label=_line_label(lines[chart["yingPosition"] - 1], language),
        )
    )
    voids = [term(branch, language) for branch in chart.get("voidBranches") or []]
    rows.append(
        phrases.calendar_line.format(
            month=term(month_branch, language),
            day=_day(day_ganzhi, language),
            void=phrases.list_join.join(voids) or phrases.no_void,
        )
    )
    rows.append(
        phrases.structure_line.format(
            original=phrases.pattern.get(chart.get("originalHexagramPattern"), phrases.pattern["ordinary"]),
            changed=phrases.pattern.get(chart.get("changedHexagramPattern"), phrases.pattern["ordinary"]),
        )
    )

    yongshen = analysis.get("yongshenRelative")
    candidates = analysis.get("candidates") or []
    rows.append("")
    rows.append(phrases.heading_yongshen)
    rows.append("")
    if yongshen and candidates:
        rows.append(phrases.yongshen_found.format(relative=term(yongshen, language), count=len(candidates)))
        rows.append("")
        for candidate in candidates:
            where = _opening(_position_name(candidate["position"], phrases))
            if candidate.get("hidden"):
                where = f"{where}{phrases.hidden_marker}"
            standing = _calendar_standing(candidate, month_branch, day_ganzhi, phrases, language)
            raw_status = (candidate.get("strengthEvidence") or {}).get("status", "")
            status = phrases.strength.get(raw_status, "")
            if status and raw_status != "not_computed_for_hidden":
                status = phrases.signal_count.format(status=status)
            limits = _limits(candidate, phrases)
            detail = phrases.detail_join.join(
                part for part in [standing, status, phrases.list_join.join(limits)] if part
            )
            suffix = f"{phrases.detail_lead}{detail}" if detail else ""
            rows.append(f"- {where} {_line_label(candidate, language)}{suffix}")
    elif yongshen:
        rows.append(phrases.yongshen_absent.format(relative=term(yongshen, language)))
    else:
        rows.append(phrases.yongshen_none)

    moving = [line for line in lines if line.get("moving")]
    rows.append("")
    rows.append(phrases.heading_moving)
    rows.append("")
    if not moving:
        rows.append(phrases.all_still)
    for line in moving:
        changed = line.get("changedLine") or {}
        pieces = [phrases.return_relation.get(changed.get("returnRelation"), "")]
        advance = phrases.advance_retreat.get(changed.get("advanceRetreat"), "")
        if advance:
            pieces.append(advance)
        if changed.get("isVoid"):
            pieces.append(phrases.changed_void)
        detail = phrases.clause_join.join(piece for piece in pieces if piece)
        changed_label = (
            f"{term(changed.get('sixRelative'), language)}"
            f"{'' if language == 'zh' else ' '}"
            f"{_ganzhi(changed.get('najiaStem', ''), changed.get('najiaBranch', ''), language)}"
        )
        rows.append(
            phrases.moving_row.format(
                position=_opening(_position_name(line["position"], phrases)),
                label=_line_label(line, language),
                changed=changed_label,
                detail=f"{phrases.clause_join}{detail}" if detail else "",
            )
        )

    hidden = chart.get("hiddenLines") or []
    if hidden:
        rows.append("")
        rows.append(phrases.heading_hidden)
        rows.append("")
        for item in hidden:
            rows.append(
                phrases.hidden_row.format(
                    position=_position_name(item["position"], phrases),
                    hidden=_najia_label(item, language),
                    flying=_najia_label(
                        {
                            "sixRelative": item.get("flyingSixRelative"),
                            "najiaStem": item.get("flyingStem"),
                            "najiaBranch": item.get("flyingBranch"),
                        },
                        language,
                    ),
                )
            )

    restricted = [(line, _limits(line, phrases)) for line in lines if _limits(line, phrases)]
    if restricted:
        rows.append("")
        rows.append(phrases.heading_restricted)
        rows.append("")
        for line, limits in restricted:
            rows.append(
                f"- {_opening(_position_name(line['position'], phrases))} "
                f"{_line_label(line, language)}{phrases.detail_lead}{phrases.list_join.join(limits)}"
            )

    timing = analysis.get("timingCandidates") or []
    if timing:
        rows.append("")
        rows.append(phrases.heading_timing)
        rows.append("")
        rows.append(phrases.timing_intro)
        rows.append("")
        seen: set[tuple[str, str]] = set()
        for item in timing:
            key = (item.get("mechanism", ""), item.get("triggerBranch", ""))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                phrases.timing_row.format(
                    mechanism=phrases.mechanism.get(item.get("mechanism"), item.get("mechanism", "")),
                    branch=term(item.get("triggerBranch", ""), language),
                )
            )

    mapping = analysis.get("optionMapping")
    if isinstance(mapping, dict):
        labels = {
            str(option.get("optionId")): str(option.get("label", ""))
            for option in (analysis.get("questionContext") or {}).get("options", [])
        }
        arguments = {item["optionId"]: item for item in analysis.get("optionArguments") or []}
        rows.append("")
        rows.append(phrases.heading_options)
        rows.append("")
        rows.append(
            phrases.option_mode_line.format(
                mode=phrases.mapping_mode.get(mapping.get("mappingMode"), mapping.get("mappingMode", ""))
            )
        )
        rows.append("")
        for binding in mapping.get("bindings", []):
            option_id = str(binding.get("optionId"))
            argument = arguments.get(option_id, {})
            detail = []
            if argument.get("sixRelative"):
                detail.append(term(argument["sixRelative"], language))
            status = phrases.strength.get(argument.get("strengthStatus", ""), "")
            if status:
                detail.append(status)
            rows.append(
                phrases.option_row.format(
                    option=option_id,
                    label=labels.get(option_id, ""),
                    position=_ref_name(binding.get("ref", ""), phrases),
                    detail=f"{phrases.detail_lead}{phrases.clause_join.join(detail)}" if detail else "",
                )
            )
        if mapping.get("strengthComparable") is False:
            rows.append("")
            rows.append(phrases.not_comparable)
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
            rows.append(phrases.yongshen_link_intro)
            rows.append("")
            for option_id, argument in described:
                statements = []
                if argument.get("carriesYongshen"):
                    statements.append(phrases.carries_yongshen)
                for link in argument.get("yongshenLinks") or []:
                    relation = phrases.yongshen_relation.get(
                        link.get("relationFromYongshen"), link.get("relationFromYongshen", "")
                    )
                    statements.append(
                        phrases.yongshen_link.format(
                            position=_ref_name(link.get("ref", ""), phrases), relation=relation
                        )
                    )
                rows.append(
                    phrases.option_link_row.format(
                        option=option_id, statements=phrases.detail_join.join(statements)
                    )
                )

    rows.append("")
    rows.append(phrases.scope_note)
    rows.append("")
    rows.append(phrases.disclaimer)
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Narrate a chart's deterministic facts without a model")
    parser.add_argument("--chart", required=True, type=Path, help="Unified run JSON or raw chart result")
    parser.add_argument("--language", choices=("zh", "en"), default=DEFAULT_LANGUAGE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.chart.read_text(encoding="utf-8"))
    text = narrate(source.get("result", source), args.language)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
