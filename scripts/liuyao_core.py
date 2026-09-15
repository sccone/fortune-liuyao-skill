"""Standalone Wenwang Najia Liuyao chart and rule-fact engine.

It accepts bottom-up 6/7/8/9 line values and explicit calendar facts, and
returns plain JSON-compatible dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any, Iterable


VENDOR_DIR = Path(__file__).resolve().parents[1] / "vendor"
if (VENDOR_DIR / "lunar_python").is_dir() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))


STEMS = tuple("甲乙丙丁戊己庚辛壬癸")
BRANCHES = tuple("子丑寅卯辰巳午未申酉戌亥")

TRIGRAMS = {
    (1, 1, 1): ("乾", "金"), (1, 1, 0): ("兑", "金"),
    (1, 0, 1): ("离", "火"), (1, 0, 0): ("震", "木"),
    (0, 1, 1): ("巽", "木"), (0, 1, 0): ("坎", "水"),
    (0, 0, 1): ("艮", "土"), (0, 0, 0): ("坤", "土"),
}

HEXAGRAM_NAMES = {
    "乾": {"乾": "乾为天", "兑": "天泽履", "离": "天火同人", "震": "天雷无妄", "巽": "天风姤", "坎": "天水讼", "艮": "天山遁", "坤": "天地否"},
    "兑": {"乾": "泽天夬", "兑": "兑为泽", "离": "泽火革", "震": "泽雷随", "巽": "泽风大过", "坎": "泽水困", "艮": "泽山咸", "坤": "泽地萃"},
    "离": {"乾": "火天大有", "兑": "火泽睽", "离": "离为火", "震": "火雷噬嗑", "巽": "火风鼎", "坎": "火水未济", "艮": "火山旅", "坤": "火地晋"},
    "震": {"乾": "雷天大壮", "兑": "雷泽归妹", "离": "雷火丰", "震": "震为雷", "巽": "雷风恒", "坎": "雷水解", "艮": "雷山小过", "坤": "雷地豫"},
    "巽": {"乾": "风天小畜", "兑": "风泽中孚", "离": "风火家人", "震": "风雷益", "巽": "巽为风", "坎": "风水涣", "艮": "风山渐", "坤": "风地观"},
    "坎": {"乾": "水天需", "兑": "水泽节", "离": "水火既济", "震": "水雷屯", "巽": "水风井", "坎": "坎为水", "艮": "水山蹇", "坤": "水地比"},
    "艮": {"乾": "山天大畜", "兑": "山泽损", "离": "山火贲", "震": "山雷颐", "巽": "山风蛊", "坎": "山水蒙", "艮": "艮为山", "坤": "山地剥"},
    "坤": {"乾": "地天泰", "兑": "地泽临", "离": "地火明夷", "震": "地雷复", "巽": "地风升", "坎": "地水师", "艮": "地山谦", "坤": "坤为地"},
}

NAJIA = {
    "乾": (("甲", ("子", "寅", "辰")), ("壬", ("午", "申", "戌"))),
    "坤": (("乙", ("未", "巳", "卯")), ("癸", ("丑", "亥", "酉"))),
    "震": (("庚", ("子", "寅", "辰")), ("庚", ("午", "申", "戌"))),
    "巽": (("辛", ("丑", "亥", "酉")), ("辛", ("未", "巳", "卯"))),
    "坎": (("戊", ("寅", "辰", "午")), ("戊", ("申", "戌", "子"))),
    "离": (("己", ("卯", "丑", "亥")), ("己", ("酉", "未", "巳"))),
    "艮": (("丙", ("辰", "午", "申")), ("丙", ("戌", "子", "寅"))),
    "兑": (("丁", ("巳", "卯", "丑")), ("丁", ("亥", "酉", "未"))),
}

BRANCH_ELEMENTS = {
    "子": "水", "亥": "水", "寅": "木", "卯": "木", "巳": "火", "午": "火",
    "申": "金", "酉": "金", "辰": "土", "戌": "土", "丑": "土", "未": "土",
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
SIX_SPIRITS = ("青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武")
SPIRIT_START = {"甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2, "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5}

PALACE_PATTERNS = {
    (0, 0, 0, 0, 0, 0): ("本宫", 6),
    (1, 0, 0, 0, 0, 0): ("一世", 1),
    (1, 1, 0, 0, 0, 0): ("二世", 2),
    (1, 1, 1, 0, 0, 0): ("三世", 3),
    (1, 1, 1, 1, 0, 0): ("四世", 4),
    (1, 1, 1, 1, 1, 0): ("五世", 5),
    (1, 1, 1, 0, 1, 0): ("游魂", 4),
    (0, 0, 0, 0, 1, 0): ("归魂", 3),
}

ADVANCE_BRANCH = {"亥": "子", "寅": "卯", "巳": "午", "申": "酉", "丑": "辰", "辰": "未", "未": "戌", "戌": "丑"}
RETREAT_BRANCH = {target: source for source, target in ADVANCE_BRANCH.items()}
CLASH = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅", "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}
HARMONY = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯", "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}
HARM = {"子": "未", "未": "子", "丑": "午", "午": "丑", "寅": "巳", "巳": "寅", "卯": "辰", "辰": "卯", "申": "亥", "亥": "申", "酉": "戌", "戌": "酉"}
PUNISH_GROUPS = (("寅", "巳", "申"), ("丑", "戌", "未"), ("子", "卯"))
SELF_PUNISH = {"辰", "午", "酉", "亥"}
THREE_HARMONY = {
    "water": ("申", "子", "辰"), "wood": ("亥", "卯", "未"),
    "fire": ("寅", "午", "戌"), "metal": ("巳", "酉", "丑"),
}
SIX_CLASH_HEXAGRAMS = {"乾为天", "兑为泽", "离为火", "震为雷", "巽为风", "坎为水", "艮为山", "坤为地", "天雷无妄", "雷天大壮"}
SIX_HARMONY_HEXAGRAMS = {"天地否", "地天泰", "水泽节", "泽水困", "山火贲", "火山旅", "雷地豫", "地雷复"}

DOMAIN_YONGSHEN = {
    "career": "官鬼", "wealth": "妻财", "academic": "父母", "exam": "父母",
    "travel": "世爻", "home": "父母", "legal_risk": "官鬼",
}

QUESTION_FORMS = ("single_target", "option_comparison")
MAPPING_MODES = ("shi_ying", "yongshen_multi")


def validate_lines(values: Iterable[int]) -> list[int]:
    lines = [int(value) for value in values]
    if len(lines) != 6 or any(value not in (6, 7, 8, 9) for value in lines):
        raise ValueError("linesBottomUp must contain exactly six values from 6, 7, 8, 9")
    return lines


def derive_calendar(moment: datetime, day_boundary_policy: str = "zi_hour") -> dict[str, str]:
    try:
        from lunar_python import Solar
    except ImportError as exc:
        raise RuntimeError("calendar conversion requires lunar_python==1.4.8") from exc
    day_moment = moment + timedelta(days=1) if day_boundary_policy == "zi_hour" and moment.hour >= 23 else moment
    day_lunar = Solar.fromYmdHms(day_moment.year, day_moment.month, day_moment.day, day_moment.hour, day_moment.minute, day_moment.second).getLunar()
    month_lunar = Solar.fromYmdHms(moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second).getLunar()
    previous_jieqi = month_lunar.getPrevJieQi()
    next_jieqi = month_lunar.getNextJieQi()
    return {
        "localWallClock": moment.replace(tzinfo=None).isoformat(),
        "timezone": getattr(moment.tzinfo, "key", None) or str(moment.tzinfo),
        "dayGanzhi": day_lunar.getEightChar().getDay(),
        "monthBranch": month_lunar.getEightChar().getMonthZhi(),
        "monthGanzhi": month_lunar.getEightChar().getMonth(),
        "yearGanzhi": month_lunar.getEightChar().getYear(),
        "timeGanzhi": month_lunar.getEightChar().getTime(),
        "lunarDateText": f"农历{month_lunar.getYearInChinese()}年{month_lunar.getMonthInChinese()}月{month_lunar.getDayInChinese()}",
        "solarTermWindow": {
            "previous": {"name": previous_jieqi.getName(), "date": str(previous_jieqi.getSolar())},
            "next": {"name": next_jieqi.getName(), "date": str(next_jieqi.getSolar())},
        },
        "dayBoundaryPolicy": day_boundary_policy,
        "calendarLibrary": "lunar_python_vendored",
        "calendarLibraryVersion": "1.4.8",
    }


def _hexagram(bits: tuple[int, ...]) -> dict[str, Any]:
    lower_name, lower_element = TRIGRAMS[bits[:3]]
    upper_name, upper_element = TRIGRAMS[bits[3:]]
    return {
        "name": HEXAGRAM_NAMES[upper_name][lower_name],
        "upperTrigram": {"name": upper_name, "element": upper_element},
        "lowerTrigram": {"name": lower_name, "element": lower_element},
    }


def _palace(bits: tuple[int, ...]) -> tuple[str, str, str, int]:
    for pure_bits, (name, element) in TRIGRAMS.items():
        difference = tuple(left ^ right for left, right in zip(bits, pure_bits + pure_bits))
        if difference in PALACE_PATTERNS:
            stage, shi = PALACE_PATTERNS[difference]
            return name, element, stage, shi
    raise ValueError("hexagram does not match a Jing Fang eight-palace pattern")


def _six_relative(palace_element: str, line_element: str) -> str:
    if line_element == palace_element:
        return "兄弟"
    if GENERATES[line_element] == palace_element:
        return "父母"
    if GENERATES[palace_element] == line_element:
        return "子孙"
    if CONTROLS[line_element] == palace_element:
        return "官鬼"
    return "妻财"


def _najia(hexagram: dict[str, Any], position: int) -> tuple[str, str, str]:
    trigram = hexagram["lowerTrigram"]["name"] if position <= 3 else hexagram["upperTrigram"]["name"]
    side = 0 if position <= 3 else 1
    index = position - 1 if position <= 3 else position - 4
    stem, branches = NAJIA[trigram][side]
    branch = branches[index]
    return stem, branch, BRANCH_ELEMENTS[branch]


def _void_branches(day_ganzhi: str) -> list[str]:
    if len(day_ganzhi) != 2 or day_ganzhi[0] not in STEMS or day_ganzhi[1] not in BRANCHES:
        raise ValueError("dayGanzhi must be a valid stem-branch pair")
    start = (BRANCHES.index(day_ganzhi[1]) - STEMS.index(day_ganzhi[0])) % 12
    return [BRANCHES[(start - 2) % 12], BRANCHES[(start - 1) % 12]]


def _element_relation(actor: str, target: str) -> str:
    if actor == target:
        return "same_element"
    if GENERATES[actor] == target:
        return "generates"
    if CONTROLS[actor] == target:
        return "controls"
    if GENERATES[target] == actor:
        return "generated_by"
    return "controlled_by"


def _return_relation(changed: str, original: str) -> str:
    if changed == original:
        return "same_element"
    if GENERATES[changed] == original:
        return "generates_original"
    if CONTROLS[changed] == original:
        return "controls_original"
    return "other"


def _flying_hidden_relation(flying: str, hidden: str) -> str:
    if flying == hidden:
        return "same_element"
    if GENERATES[flying] == hidden:
        return "generates_hidden"
    if CONTROLS[flying] == hidden:
        return "controls_hidden"
    if GENERATES[hidden] == flying:
        return "generated_by_hidden"
    return "controlled_by_hidden"


def _branch_relations(left: str, right: str) -> list[str]:
    result: list[str] = []
    if CLASH[left] == right:
        result.append("clash")
    if HARMONY[left] == right:
        result.append("harmony")
    if HARM[left] == right:
        result.append("harm")
    if left == right and left in SELF_PUNISH:
        result.append("self_punishment")
    if any(left in group and right in group and left != right for group in PUNISH_GROUPS):
        result.append("punishment_component")
    return result


def _pattern(name: str) -> str:
    if name in SIX_CLASH_HEXAGRAMS:
        return "six_clash"
    if name in SIX_HARMONY_HEXAGRAMS:
        return "six_harmony"
    return "ordinary"


def _strength_status(signals: list[dict[str, str]]) -> str:
    support = sum(item["direction"] == "support" for item in signals)
    pressure = sum(item["direction"] == "pressure" for item in signals)
    if support and pressure:
        return "contested"
    if support:
        return "supported"
    if pressure:
        return "weakened"
    return "neutral"


def _timing_candidates(candidate: dict[str, Any], month_branch: str) -> list[dict[str, Any]]:
    branch = candidate["najiaBranch"]
    result: list[dict[str, Any]] = []
    if candidate.get("isVoid"):
        result.extend([
            {"mechanism": "void_fill", "triggerBranch": branch, "meaning": "用神填实候选"},
            {"mechanism": "void_clash", "triggerBranch": CLASH[branch], "meaning": "冲空候选"},
        ])
    if candidate.get("isMonthBreak"):
        result.extend([
            {"mechanism": "month_break_value", "triggerBranch": branch, "meaning": "月破逢值候选"},
            {"mechanism": "month_break_harmony", "triggerBranch": HARMONY[branch], "meaning": "月破逢合候选"},
            {"mechanism": "month_break_exit", "triggerBranch": CLASH[month_branch], "meaning": "出当前月令候选"},
        ])
    if candidate.get("moving"):
        result.extend([
            {"mechanism": "moving_value", "triggerBranch": branch, "meaning": "动爻逢值候选"},
            {"mechanism": "moving_harmony", "triggerBranch": HARMONY[branch], "meaning": "动爻逢合候选"},
        ])
    if candidate.get("hidden"):
        flying = candidate.get("flyingBranch")
        if flying:
            result.append({"mechanism": "hidden_release", "triggerBranch": CLASH[flying], "meaning": "冲飞出伏候选"})
    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for item in result:
        dedup[(item["mechanism"], item["triggerBranch"])] = item
    return list(dedup.values())


def _normalize_options(options: Any) -> list[dict[str, Any]]:
    """Validate declared options; refuse anything a later fact audit could not check."""
    if not isinstance(options, (list, tuple)) or len(options) < 2:
        raise ValueError("option_comparison requires at least two options")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for option in options:
        if not isinstance(option, dict):
            raise ValueError("each option must be an object")
        option_id = str(option.get("optionId") or "").strip()
        label = str(option.get("label") or "").strip()
        if not option_id or not label:
            raise ValueError("each option requires optionId and label")
        if option_id in seen:
            raise ValueError(f"duplicate optionId: {option_id}")
        seen.add(option_id)
        normalized.append({"optionId": option_id, "label": label, "isStatusQuo": bool(option.get("isStatusQuo"))})
    return normalized


def _resolve_ref(ref: Any, lines: list[dict[str, Any]], hidden_lines: list[dict[str, Any]]) -> dict[str, Any]:
    kind, _, raw = str(ref).partition(":")
    if kind not in ("line", "hidden") or not raw.isdigit():
        raise ValueError(f"binding ref must look like line:N or hidden:N; got {ref!r}")
    position = int(raw)
    for item in lines if kind == "line" else hidden_lines:
        if item["position"] == position:
            return {**item, "hidden": kind == "hidden"}
    raise ValueError(f"binding ref does not exist in this chart: {ref}")


def _yongshen_links(
    line: dict[str, Any], candidates: list[dict[str, Any]], hidden: bool
) -> list[dict[str, Any]]:
    """Relation from each yongshen appearance to this line.

    Two options may sit on different 六亲, which makes their own strength values
    incomparable. How the yongshen acts on each side is the comparable quantity.
    """
    links: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_hidden = bool(candidate.get("hidden"))
        if candidate["position"] == line["position"] and candidate_hidden == hidden:
            continue
        links.append({
            "ref": f"{'hidden' if candidate_hidden else 'line'}:{candidate['position']}",
            "relationFromYongshen": _element_relation(candidate["najiaElement"], line["najiaElement"]),
        })
    return links


def _option_argument(
    option_id: str, ref: str, line: dict[str, Any], shi_line: dict[str, Any],
    candidates: list[dict[str, Any]], yongshen: str | None,
) -> dict[str, Any]:
    """Mirror candidateArguments so option comparison reuses one evidence shape."""
    signals = (line.get("strengthEvidence") or {}).get("signals", [])
    limitations = [
        name for name, flag in (
            ("hidden", line.get("hidden")), ("void", line.get("isVoid")),
            ("month_break", line.get("isMonthBreak")), ("day_clash", line.get("isDayClash")),
        ) if flag
    ]
    return {
        "optionId": option_id, "ref": ref, "position": line["position"],
        "hidden": bool(line.get("hidden")), "moving": bool(line.get("moving")),
        "sixRelative": line.get("sixRelative"),
        "strengthStatus": (line.get("strengthEvidence") or {}).get("status", "not_computed_for_hidden"),
        "supportingSignals": [item for item in signals if item.get("direction") == "support"],
        "limitingStates": limitations,
        "timingCandidates": line.get("timingCandidates", []),
        "relationToShi": _branch_relations(line["najiaBranch"], shi_line["najiaBranch"]),
        "yongshenRelative": yongshen,
        "carriesYongshen": bool(
            yongshen and (line.get("isShi") if yongshen == "世爻" else line.get("sixRelative") == yongshen)
        ),
        "yongshenLinks": _yongshen_links(line, candidates, ref.startswith("hidden:")),
        "conclusionScope": "option_comparison_only_not_outcome",
    }


def _build_option_mapping(
    *,
    options: list[dict[str, Any]],
    mapping_mode: str | None,
    bindings: Any,
    lines: list[dict[str, Any]],
    hidden_lines: list[dict[str, Any]],
    shi_position: int,
    ying_position: int,
    candidates: list[dict[str, Any]],
    question_category: str,
    month_branch: str,
    yongshen: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Bind declared options to chart positions. Refuse to guess: a wrong binding is unfalsifiable."""
    if mapping_mode not in MAPPING_MODES:
        raise ValueError(f"mappingMode must be one of {MAPPING_MODES}; got {mapping_mode!r}")
    # Exhaustively true across all 64 hexagrams: a 六亲 occupies at most two of
    # the six lines, hidden appearances included. So yongshen_multi can never
    # carry three options, whatever the bindings say, and saying so here beats
    # letting a cast proceed and fail on the ordinal lookup.
    if mapping_mode == "yongshen_multi" and len(options) > 2:
        raise ValueError(
            f"yongshen_multi cannot carry {len(options)} options: a 六亲 occupies at most "
            "two of the six lines, so only two can be bound to separate appearances. "
            "Ask about two options at a time."
        )
    if mapping_mode == "shi_ying":
        if len(options) != 2:
            raise ValueError("shi_ying mapping supports exactly two options")
        if bindings:
            raise ValueError("shi_ying mapping derives bindings from 世/应 and rejects manual bindings")
        if DOMAIN_YONGSHEN.get(question_category) == "世爻":
            raise ValueError(f"shi_ying mapping conflicts with the 世爻 yongshen of domain '{question_category}'")
        status_quo = [option for option in options if option["isStatusQuo"]]
        if len(status_quo) > 1:
            raise ValueError("shi_ying mapping accepts at most one status-quo option")
        # A status quo takes 世; with two fresh options, declaration order decides instead.
        # Both are fixed before the cast, so the mapping stays frozen either way.
        tie_break = "status_quo" if status_quo else "declaration_order"
        first = status_quo[0] if status_quo else options[0]
        other = next(option for option in options if option["optionId"] != first["optionId"])
        resolved = [(first, f"line:{shi_position}", "shi"), (other, f"line:{ying_position}", "ying")]
    else:
        declared: dict[str, str] = {}
        ordinals: dict[str, int] = {}
        for binding in bindings or []:
            if not isinstance(binding, dict):
                raise ValueError("each binding must be an object")
            option_id = str(binding.get("optionId") or "").strip()
            ref = str(binding.get("ref") or "").strip()
            ordinal = binding.get("ordinal")
            if not option_id:
                raise ValueError("each binding requires optionId")
            if option_id in declared or option_id in ordinals:
                raise ValueError(f"duplicate binding for option {option_id}")
            if ref and ordinal is not None:
                raise ValueError(f"binding for option {option_id} sets both ref and ordinal")
            if ordinal is not None:
                # An ordinal names which appearance of the yongshen to take,
                # counting the six lines bottom-up and then any hidden ones. It
                # exists because a concrete position cannot be known before the
                # cast, which made "declared before the cast" impossible to honour
                # for this mapping mode.
                if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 1:
                    raise ValueError(f"ordinal for option {option_id} must be a positive integer")
                ordinals[option_id] = ordinal
            elif ref:
                declared[option_id] = ref
            else:
                raise ValueError(f"binding for option {option_id} requires either ref or ordinal")

        known = {option["optionId"] for option in options}
        if declared and ordinals:
            raise ValueError("bindings must use either refs or ordinals, not a mix of both")
        bound = declared or ordinals
        missing = sorted(known - set(bound))
        if missing:
            raise ValueError(f"yongshen_multi mapping requires a binding for every option; missing {missing}")
        unknown = sorted(set(bound) - known)
        if unknown:
            raise ValueError(f"binding refers to undeclared optionId: {unknown}")
        if len(set(bound.values())) != len(bound):
            raise ValueError("two options cannot bind to the same yongshen appearance")

        if ordinals:
            # Resolved against this cast's own candidates, in the order the engine
            # collected them: the visible lines bottom-up, then the hidden ones.
            appearances = [
                f"{'hidden' if candidate.get('hidden') else 'line'}:{candidate['position']}"
                for candidate in candidates
            ]
            over = {oid: n for oid, n in ordinals.items() if n > len(appearances)}
            if over:
                raise ValueError(
                    f"the chart shows {len(appearances)} appearance(s) of the yongshen, "
                    f"but {sorted(over)} asked for {sorted(over.values())}. "
                    "Re-ask with shi_ying, or with fewer options."
                )
            declared = {oid: appearances[n - 1] for oid, n in ordinals.items()}
            tie_break = "ordinal_rule"
        else:
            tie_break = "explicit_binding"
        resolved = [(option, declared[option["optionId"]], "yongshen_appearance") for option in options]

    shi_line = lines[shi_position - 1]
    bound_refs: list[str] = []
    option_arguments: list[dict[str, Any]] = []
    for option, ref, basis in resolved:
        line = _resolve_ref(ref, lines, hidden_lines)
        line.setdefault("timingCandidates", _timing_candidates(line, month_branch))
        bound_refs.append(ref)
        option_arguments.append(_option_argument(option["optionId"], ref, line, shi_line, candidates, yongshen))
    bound_relatives = {
        argument["optionId"]: argument["sixRelative"] for argument in option_arguments
    }
    mapping = {
        "mappingMode": mapping_mode,
        "declaredBefore": "cast",
        "tieBreak": tie_break,
        "boundRelatives": bound_relatives,
        # Strength is only comparable across options that sit on the same 六亲.
        "strengthComparable": len(set(bound_relatives.values())) == 1,
        "bindings": [
            {"optionId": option["optionId"], "ref": ref, "basis": basis, "hidden": ref.startswith("hidden:")}
            for option, ref, basis in resolved
        ],
        "unmappedCandidates": [
            f"{'hidden' if candidate.get('hidden') else 'line'}:{candidate['position']}"
            for candidate in candidates
            if f"{'hidden' if candidate.get('hidden') else 'line'}:{candidate['position']}" not in bound_refs
        ],
        "conclusionScope": "option_comparison_only_not_outcome",
    }
    return mapping, option_arguments


def build_chart(
    lines_bottom_up: Iterable[int],
    *,
    day_ganzhi: str,
    month_branch: str,
    cast_at: str,
    question_category: str = "general",
    question_subtype: str | None = None,
    question_text: str | None = None,
    question_perspective: str | None = None,
    question_form: str = "single_target",
    options: Any = None,
    mapping_mode: str | None = None,
    bindings: Any = None,
) -> dict[str, Any]:
    values = validate_lines(lines_bottom_up)
    if month_branch not in BRANCHES:
        raise ValueError("monthBranch must be a valid earthly branch")
    original_bits = tuple(1 if value in (7, 9) else 0 for value in values)
    changed_bits = tuple(bit ^ int(value in (6, 9)) for bit, value in zip(original_bits, values))
    original = _hexagram(original_bits)
    changed = _hexagram(changed_bits)
    palace, palace_element, palace_stage, shi_position = _palace(original_bits)
    ying_position = ((shi_position + 2) % 6) + 1
    void_branches = _void_branches(day_ganzhi)
    day_branch = day_ganzhi[1]

    lines: list[dict[str, Any]] = []
    for index, (value, bit, changed_bit) in enumerate(zip(values, original_bits, changed_bits)):
        position = index + 1
        stem, branch, element = _najia(original, position)
        month_relation = _element_relation(BRANCH_ELEMENTS[month_branch], element)
        day_relation = _element_relation(BRANCH_ELEMENTS[day_branch], element)
        signals: list[dict[str, str]] = []
        for source, relation in (("month", month_relation), ("day", day_relation)):
            if relation in ("same_element", "generates"):
                signals.append({"source": source, "relation": relation, "direction": "support"})
            elif relation == "controls":
                signals.append({"source": source, "relation": relation, "direction": "pressure"})
        changed_line = None
        if value in (6, 9):
            c_stem, c_branch, c_element = _najia(changed, position)
            return_relation = _return_relation(c_element, element)
            advance_retreat = "advance" if ADVANCE_BRANCH.get(branch) == c_branch else "retreat" if RETREAT_BRANCH.get(branch) == c_branch else "none"
            changed_line = {
                "yinYang": "阳" if changed_bit else "阴",
                "najiaStem": c_stem, "najiaBranch": c_branch, "najiaElement": c_element,
                "sixRelative": _six_relative(palace_element, c_element),
                "returnRelation": return_relation,
                "advanceRetreat": advance_retreat,
                "isVoid": c_branch in void_branches,
            }
        lines.append({
            "position": position, "value": value, "yinYang": "阳" if bit else "阴",
            "moving": value in (6, 9), "changedYinYang": "阳" if changed_bit else "阴",
            "isShi": position == shi_position, "isYing": position == ying_position,
            "najiaStem": stem, "najiaBranch": branch, "najiaElement": element,
            "sixRelative": _six_relative(palace_element, element),
            "sixSpirit": SIX_SPIRITS[(SPIRIT_START[day_ganzhi[0]] + index) % 6],
            "isVoid": branch in void_branches,
            "isMonthBreak": CLASH[month_branch] == branch,
            "isDayClash": CLASH[day_branch] == branch,
            "monthRelation": month_relation, "dayRelation": day_relation,
            "strengthEvidence": {"status": _strength_status(signals), "signals": signals},
            "changedLine": changed_line,
        })

    pure_bits = next(bits for bits, values_ in TRIGRAMS.items() if values_[0] == palace)
    pure = _hexagram(pure_bits + pure_bits)
    visible_relatives = {line["sixRelative"] for line in lines}
    hidden_lines: list[dict[str, Any]] = []
    for position in range(1, 7):
        stem, branch, element = _najia(pure, position)
        relative = _six_relative(palace_element, element)
        if relative in visible_relatives:
            continue
        flying = lines[position - 1]
        hidden_lines.append({
            "position": position, "hidden": True,
            "najiaStem": stem, "najiaBranch": branch, "najiaElement": element,
            "sixRelative": relative,
            "flyingStem": flying["najiaStem"], "flyingBranch": flying["najiaBranch"],
            "flyingElement": flying["najiaElement"], "flyingSixRelative": flying["sixRelative"],
            "flyingToHiddenRelation": _flying_hidden_relation(flying["najiaElement"], element),
            "isVoid": branch in void_branches,
            "isMonthBreak": CLASH[month_branch] == branch,
            "isDayClash": CLASH[day_branch] == branch,
        })

    relations: list[dict[str, Any]] = []
    for left_index in range(6):
        for right_index in range(left_index + 1, 6):
            for relation in _branch_relations(lines[left_index]["najiaBranch"], lines[right_index]["najiaBranch"]):
                relations.append({"leftPosition": left_index + 1, "rightPosition": right_index + 1, "relation": relation})

    branch_sources: dict[str, list[dict[str, Any]]] = {branch: [] for branch in BRANCHES}
    for line in lines:
        branch_sources[line["najiaBranch"]].append({"source": "line", "position": line["position"], "moving": line["moving"]})
    branch_sources[day_branch].append({"source": "day"})
    branch_sources[month_branch].append({"source": "month"})
    harmony_facts: list[dict[str, Any]] = []
    for group_name, group in THREE_HARMONY.items():
        present = [branch for branch in group if branch_sources[branch]]
        if len(present) >= 2:
            harmony_facts.append({
                "group": group_name, "branches": list(group), "presentBranches": present,
                "missingBranches": [branch for branch in group if branch not in present],
                "complete": len(present) == 3,
                "sources": {branch: branch_sources[branch] for branch in present},
                "conclusionScope": "structure_candidate_only",
            })
    punishment_facts = [item for item in relations if "punishment" in item["relation"]]

    original_pattern = _pattern(original["name"])
    changed_pattern = _pattern(changed["name"])
    transition = {
        ("six_clash", "six_harmony"): "six_clash_to_six_harmony",
        ("six_harmony", "six_clash"): "six_harmony_to_six_clash",
        ("six_clash", "six_clash"): "six_clash_to_six_clash",
        ("six_harmony", "six_harmony"): "six_harmony_to_six_harmony",
    }.get((original_pattern, changed_pattern), "other")

    if question_category == "relationship":
        yongshen = "官鬼" if question_perspective in ("female", "woman", "女") else "妻财" if question_perspective in ("male", "man", "男") else None
    else:
        yongshen = DOMAIN_YONGSHEN.get(question_category)
    candidates: list[dict[str, Any]] = []
    if yongshen and yongshen != "世爻":
        candidates.extend({**line, "hidden": False} for line in lines if line["sixRelative"] == yongshen)
        candidates.extend(line for line in hidden_lines if line["sixRelative"] == yongshen)
    elif yongshen == "世爻":
        candidates.append({**lines[shi_position - 1], "hidden": False})
    for candidate in candidates:
        candidate["timingCandidates"] = _timing_candidates(candidate, month_branch)

    candidate_arguments: list[dict[str, Any]] = []
    for candidate in candidates:
        strengths = (candidate.get("strengthEvidence") or {}).get("signals", [])
        supports = [item for item in strengths if item.get("direction") == "support"]
        limitations: list[str] = []
        if candidate.get("hidden"):
            limitations.append("hidden")
        if candidate.get("isVoid"):
            limitations.append("void")
        if candidate.get("isMonthBreak"):
            limitations.append("month_break")
        if candidate.get("isDayClash"):
            limitations.append("day_clash")
        candidate_arguments.append({
            "candidateRef": f"{'hidden' if candidate.get('hidden') else 'line'}:{candidate['position']}",
            "position": candidate["position"], "hidden": bool(candidate.get("hidden")),
            "moving": bool(candidate.get("moving")),
            "strengthStatus": (candidate.get("strengthEvidence") or {}).get("status", "not_computed_for_hidden"),
            "supportingSignals": supports, "limitingStates": limitations,
            "conclusionScope": "candidate_comparison_only_not_outcome",
        })

    if question_form not in QUESTION_FORMS:
        raise ValueError(f"questionForm must be one of {QUESTION_FORMS}; got {question_form!r}")
    option_mapping: dict[str, Any] | None = None
    option_arguments: list[dict[str, Any]] = []
    normalized_options: list[dict[str, Any]] = []
    if question_form == "option_comparison":
        normalized_options = _normalize_options(options)
        option_mapping, option_arguments = _build_option_mapping(
            options=normalized_options, mapping_mode=mapping_mode, bindings=bindings,
            lines=lines, hidden_lines=hidden_lines,
            shi_position=shi_position, ying_position=ying_position,
            candidates=candidates, question_category=question_category, month_branch=month_branch,
            yongshen=yongshen,
        )
    elif options or mapping_mode or bindings:
        raise ValueError("options, mappingMode and bindings require questionForm 'option_comparison'")

    context_arguments = {
        "shi": {"position": shi_position, "line": lines[shi_position - 1]},
        "ying": {"position": ying_position, "line": lines[ying_position - 1]},
        "shiYingBranchRelations": _branch_relations(lines[shi_position - 1]["najiaBranch"], lines[ying_position - 1]["najiaBranch"]),
    }

    chart = {
        "schemaVersion": "fortune-liuyao-chart.v1",
        "schoolProfile": "wenwang_najia_v1",
        "transformationRuleVersion": "standalone-transformations.v1",
        "castAt": cast_at, "dayGanzhi": day_ganzhi, "monthBranch": month_branch,
        "voidBranches": void_branches,
        "originalHexagram": original, "changedHexagram": changed,
        "originalHexagramPattern": original_pattern, "changedHexagramPattern": changed_pattern,
        "hexagramPatternTransition": transition,
        "palace": palace, "palaceElement": palace_element, "palaceStage": palace_stage,
        "shiPosition": shi_position, "yingPosition": ying_position,
        "hiddenLines": hidden_lines, "lines": lines,
    }
    analysis = {
        "schemaVersion": "fortune-liuyao-rule-facts.v1",
        "questionCategory": question_category,
        "questionContext": {
            "domain": question_category, "subtype": question_subtype,
            "question": question_text, "perspective": question_perspective,
            "questionForm": question_form,
            **({"options": normalized_options} if normalized_options else {}),
        },
        "schoolProfile": "wenwang_najia_v1",
        "yongshenRelative": yongshen,
        # Under yongshen_multi every bound appearance is read as a co-equal yongshen,
        # so the usual 用神多现 tie-break is suspended rather than silently reused.
        "selectionStatus": (
            "suspended_for_option_comparison"
            if option_mapping and option_mapping["mappingMode"] == "yongshen_multi"
            else "candidates_identified" if candidates else "route_requires_context"
        ),
        "selectionCompleteness": "complete" if yongshen else "needs_clarification",
        "candidates": candidates,
        "shiPosition": shi_position, "yingPosition": ying_position,
        "lineFacts": lines, "hiddenLineFacts": hidden_lines,
        "branchRelationFacts": relations,
        "threeHarmonyFacts": harmony_facts,
        "punishmentFacts": punishment_facts,
        "candidateArguments": candidate_arguments,
        **({"optionMapping": option_mapping, "optionArguments": option_arguments} if option_mapping else {}),
        "contextArguments": context_arguments,
        "ruleDecisions": [
            {"ruleId": "role-route", "assertion": f"question target relative: {yongshen}", "conclusionScope": "role_mapping_only"}
        ] if yongshen else [],
        "timingCandidates": [item for candidate in candidates for item in candidate.get("timingCandidates", [])],
        "timingAnalysis": {
            "candidateCount": sum(len(candidate.get("timingCandidates", [])) for candidate in candidates),
            "calendarConversionBoundary": "branch_candidates_only",
            "conclusionScope": "conditional_timing_candidates_not_guaranteed_dates",
        },
    }
    return {
        "schemaVersion": "fortune-liuyao-runtime.v1",
        "castingAudit": {"linesBottomUp": values, "order": "bottom_up", "movingValues": [6, 9]},
        "chart": chart,
        "analysis": analysis,
        "deterministicRuleFacts": analysis,
    }
