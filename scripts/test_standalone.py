"""Small golden regression set for the standalone Skill runtime."""

import json
from pathlib import Path

from cast_lines import _automatic_cast, _manual_cast
from cast_one_line import cast_one
from build_model_packet import (
    DELIVERY_POLICY, FOLLOW_UP_POLICY, OPTION_POLICY, ROUTING_POLICY, SYSTEM_PROMPT,
    _load_method, build_packet,
)
from classify_sensitive import classify
import random

from liuyao_core import build_chart
from lexicon import SIX_RELATIVE as LEXICON_SIX_RELATIVE, chart_lexicon, hexagram as hexagram_name
from narrate_facts import narrate
from render_chart import render_html
from render_chart_text import render
from render_final_report import build_final_report
from run_liuyao import run
from verify_facts import verify_report


PASSED = 0


def check(condition: bool, message: str) -> None:
    global PASSED
    if not condition:
        raise AssertionError(message)
    PASSED += 1


def check_rejected(action, message: str) -> None:
    """A refused chart must raise; silently falling back would hide a bad mapping."""
    global PASSED
    try:
        action()
    except ValueError:
        PASSED += 1
        return
    raise AssertionError(message)


def embedded_data(html: str) -> str:
    """Return only the JSON the renderer injected, never the template's own source text."""
    marker = 'const EMBEDDED_JSON="'
    start = html.index(marker) + len(marker)
    return html[start:html.index('";', start)]


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    skill_text = (project_root / "SKILL.md").read_text(encoding="utf-8")
    coin_guide = (project_root / "references" / "manual-coin-casting.md").read_text(encoding="utf-8")
    follow_up_guide = (project_root / "references" / "follow-up-dialogue.md").read_text(encoding="utf-8")
    check("系统不会根据硬币图案自动判断正反" in skill_text, "manual coin mode lacks proactive side guidance")
    check("面额数字／文字的一面记为“正”" in skill_text and "国徽、花卉等图案面记为“反”" in skill_text, "default physical coin sides mismatch")
    check("请按顺序反馈六次结果" in skill_text and "正=字／面额面，反=国徽／花卉面" in skill_text, "manual coin response format missing")
    check("正面记 3，反面记 2" in skill_text and "第一次是初爻" in skill_text, "manual coin counting prompt mismatch")
    check("Agent 必须主动展示" in coin_guide, "manual coin guidance is not mandatory")
    check("不重新起卦" in follow_up_guide and "不事后改写原始结论" in follow_up_guide, "follow-up lock guide mismatch")
    tun = build_chart(
        [7, 8, 8, 6, 7, 8],
        day_ganzhi="庚戌", month_branch="未",
        cast_at="2026-08-04T11:17:00+08:00",
        question_category="career", question_subtype="job_search",
    )
    chart = tun["chart"]
    check(chart["originalHexagram"]["name"] == "水雷屯", "original hexagram mismatch")
    check(chart["changedHexagram"]["name"] == "泽雷随", "changed hexagram mismatch")
    check((chart["palace"], chart["shiPosition"], chart["yingPosition"]) == ("坎", 2, 5), "palace/shi/ying mismatch")
    check(chart["voidBranches"] == ["寅", "卯"], "void branches mismatch")
    check(chart["lines"][3]["changedLine"]["returnRelation"] == "other", "changed relation mismatch")
    check(chart["hiddenLines"][0]["sixRelative"] == "妻财", "hidden relative mismatch")
    check(len(tun["analysis"]["candidates"]) == 2, "career yongshen candidates mismatch")

    qian = build_chart(
        [7, 7, 7, 7, 7, 7],
        day_ganzhi="甲子", month_branch="子",
        cast_at="2026-01-01T12:00:00+08:00",
    )["chart"]
    check(qian["originalHexagram"]["name"] == "乾为天", "pure Qian mismatch")
    check((qian["palace"], qian["shiPosition"], qian["yingPosition"]) == ("乾", 6, 3), "pure Qian palace mismatch")

    kun_change = build_chart(
        [6, 8, 8, 8, 8, 8],
        day_ganzhi="甲子", month_branch="子",
        cast_at="2026-01-01T12:00:00+08:00",
    )["chart"]
    check(kun_change["originalHexagram"]["name"] == "坤为地", "pure Kun mismatch")
    check(kun_change["changedHexagram"]["name"] == "地雷复", "Kun-to-Fu mismatch")

    manual = _manual_cast("正反反/正正反/反反反/正反反/正正正/正正反")
    check([row["value"] for row in manual] == [7, 8, 6, 7, 9, 8], "manual casting mismatch")

    automatic = _automatic_cast()
    check(len(automatic) == 6 and all(row["value"] in (6, 7, 8, 9) for row in automatic), "automatic casting mismatch")

    markdown = render(tun)
    check("水雷屯" in markdown and "泽雷随" in markdown and "| 爻位 |" in markdown and "伏神" in markdown, "Markdown chart mismatch")
    check("本内容基于玄学体系生成" in markdown, "Markdown safety disclaimer mismatch")
    check(_load_method("career")["methodId"] == "liuyao-career-v4", "career method version mismatch")
    check("先审题取用并处理用神多现" in SYSTEM_PROMPT, "interpretation order prompt mismatch")
    check("不可等权计票" in SYSTEM_PROMPT, "evidence priority prompt mismatch")
    check("总结与行动" in SYSTEM_PROMPT and "诚实但不泄气" in SYSTEM_PROMPT, "closing action summary prompt mismatch")
    check("不因当前日期变化重算原盘" in FOLLOW_UP_POLICY, "follow-up calendar lock missing")
    check("不自动重做 HTML 或分享图" in FOLLOW_UP_POLICY, "follow-up delivery lock missing")
    # A reading leaked "本问属 general 领域": the existing rule asked for process
    # states to stay silent, which a model can satisfy while still printing the
    # raw enum. The rule now names the vocabulary and gives replacements.
    check("程序内部标识符" in DELIVERY_POLICY, "delivery policy does not forbid internal identifiers")
    for token in ("general", "shi_ying", "same_element", "selectionStatus"):
        check(token in DELIVERY_POLICY, f"delivery policy does not name {token} as internal")
    check("比和" in DELIVERY_POLICY and "以世应取用" in DELIVERY_POLICY,
          "delivery policy forbids the identifiers without giving wording to use instead")

    check(classify("未来三个月求职是否顺利").allowed, "ordinary question was blocked")
    check(not classify("怀孕后孩子会不会健康").allowed, "sensitive pregnancy question was not blocked")
    check(classify("孩子在学校健康快乐吗").allowed, "ordinary child wellbeing question was over-blocked")
    adversarial = verify_report("本卦为乾为天。世爻在五爻。初爻为官鬼。", tun)
    check(not adversarial["accepted"] and len(adversarial["errors"]) >= 3, "fabricated chart facts escaped audit")
    natural_adversarial = verify_report("二爻妻财卯木静。", tun)
    check(not natural_adversarial["accepted"], "natural no-copula line-relative claim escaped audit")
    inference = verify_report("此事可能先难后易，辰日或有机会，仍需结合现实条件。", tun)
    check(inference["accepted"], "traditional inference was incorrectly constrained")
    one_shot = run("未来三个月能否找到合适工作", "career", "lines", "Asia/Shanghai", "7,8,8,6,7,8", None)
    check(one_shot["result"]["analysis"]["questionContext"]["domain"] == "career", "one-shot Agent route mismatch")
    check(one_shot["result"]["chart"]["originalHexagram"]["name"] == "水雷屯", "one-shot chart mismatch")
    check(len(one_shot["prompt"]) > 1000, "one-shot Agent prompt missing")
    wealth_route = run("我开了个网店，这两个月能不能回本盈利？", "wealth", "lines", "Asia/Shanghai", "7,8,8,6,7,8", None)
    check("liuyao-wealth-v1" in wealth_route["prompt"], "Agent-selected wealth method was not loaded")
    check('"authority": "advisory"' in wealth_route["prompt"], "routing guidance was not marked advisory")
    check('"yongshenRelative"' not in wealth_route["prompt"].split('"routingGuidance"', 1)[0], "routing-derived yongshen leaked into deterministic facts")
    forced_career = run("我开了个网店，这两个月能不能回本盈利？", "career", "lines", "Asia/Shanghai", "7,8,8,6,7,8", None)
    check("liuyao-career-v4" in forced_career["prompt"], "question keywords overrode the Agent-selected route")
    check("不是盘面事实" in ROUTING_POLICY, "routing policy does not distinguish guidance from facts")
    female_relationship = run("我和他还能继续发展吗", "relationship", "lines", "Asia/Shanghai", "7,8,8,6,7,8", None, "female")
    check(female_relationship["result"]["analysis"]["questionContext"]["perspective"] == "female", "relationship perspective was not passed through")
    unspecified_relationship = run("我们还能继续发展吗", "relationship", "lines", "Asia/Shanghai", "7,8,8,6,7,8", None)
    check(unspecified_relationship["result"]["analysis"]["yongshenRelative"] is None, "unspecified relationship perspective was forced into a gender route")
    single = cast_one(1)
    check(single["positionName"] == "初爻" and single["value"] in (6, 7, 8, 9), "single-line casting mismatch")
    report = """## 直接判断

这件事有推进空间，但需要先处理当前阻力。

## 盘面依据

- 本卦为水雷屯，变卦为泽雷随。
- 世爻在二爻，应爻在五爻。

## 现实建议

先验证需求，再决定投入节奏。
"""
    final_html, final_audit = build_final_report(one_shot, report)
    check(final_audit["accepted"], "valid final report failed audit")
    check("综合解读" in final_html and "这件事有推进空间" in final_html, "interpretation missing from final HTML")
    check("水雷屯" in final_html and "泽雷随" in final_html, "chart missing from final HTML")
    rejected_html, rejected_audit = build_final_report(one_shot, "本卦为乾为天。")
    check(not rejected_audit["accepted"] and not rejected_html, "invalid report produced final HTML")

    # Option comparison: the two 官鬼 of 水雷屯 (line 3 and line 5) stand in for two offers.
    offers = [
        {"optionId": "A", "label": "留在现公司", "isStatusQuo": True},
        {"optionId": "B", "label": "去 B 公司"},
    ]
    def build_offer_chart(**overrides):
        payload = {
            "day_ganzhi": "庚戌", "month_branch": "未", "cast_at": "2026-08-04T11:17:00+08:00",
            "question_category": "career", "question_form": "option_comparison",
            "options": offers, "mapping_mode": "yongshen_multi",
            "bindings": [{"optionId": "A", "ref": "line:3"}, {"optionId": "B", "ref": "line:5"}],
        }
        payload.update(overrides)
        return build_chart([7, 8, 8, 6, 7, 8], **payload)

    compared = build_offer_chart()["analysis"]
    mapping = compared["optionMapping"]
    check(mapping["mappingMode"] == "yongshen_multi", "option mapping mode mismatch")
    check(mapping["declaredBefore"] == "cast", "option mapping is not frozen to cast time")
    check([item["ref"] for item in mapping["bindings"]] == ["line:3", "line:5"], "option bindings mismatch")
    check(mapping["conclusionScope"] == "option_comparison_only_not_outcome", "option mapping scope mismatch")
    check(mapping["unmappedCandidates"] == [], "both 官鬼 candidates should be bound")
    check([item["optionId"] for item in compared["optionArguments"]] == ["A", "B"], "option arguments mismatch")
    check(mapping["boundRelatives"] == {"A": "官鬼", "B": "官鬼"}, "bound relatives mismatch")
    check(mapping["strengthComparable"] is True, "same-relative options were marked incomparable")
    check(all(item["carriesYongshen"] for item in compared["optionArguments"]), "bound 官鬼 lines not flagged as yongshen")
    check(
        compared["optionArguments"][0]["yongshenLinks"] == [{"ref": "line:5", "relationFromYongshen": "same_element"}],
        "yongshen link mismatch",
    )
    check(all(item["sixRelative"] == "官鬼" for item in compared["optionArguments"]), "options bound to wrong relative")
    check(compared["selectionStatus"] == "suspended_for_option_comparison", "用神多现 tie-break was not suspended")
    check(len(compared["candidates"]) == 2 and len(compared["candidateArguments"]) == 2, "消歧 arrays were overwritten by 择优")
    check(compared["questionContext"]["questionForm"] == "option_comparison", "questionForm not recorded")
    check([item["optionId"] for item in compared["questionContext"]["options"]] == ["A", "B"], "options not recorded")

    shi_ying = build_chart(
        [7, 8, 8, 6, 7, 8],
        day_ganzhi="庚戌", month_branch="未", cast_at="2026-08-04T11:17:00+08:00",
        question_category="career", question_form="option_comparison",
        options=offers, mapping_mode="shi_ying",
    )["analysis"]
    check(
        [(item["optionId"], item["ref"], item["basis"]) for item in shi_ying["optionMapping"]["bindings"]]
        == [("A", "line:2", "shi"), ("B", "line:5", "ying")],
        "shi_ying bindings were not derived from 世/应",
    )
    check(shi_ying["selectionStatus"] == "candidates_identified", "shi_ying must not suspend 用神消歧")
    check(shi_ying["optionMapping"]["tieBreak"] == "status_quo", "status quo did not decide the 世 side")
    fresh = build_chart(
        [7, 8, 8, 6, 7, 8],
        day_ganzhi="庚戌", month_branch="未", cast_at="2026-08-04T11:17:00+08:00",
        question_category="general", question_form="option_comparison",
        options=[{"optionId": "A", "label": "饭店A"}, {"optionId": "B", "label": "饭店B"}],
        mapping_mode="shi_ying",
    )["analysis"]["optionMapping"]
    check(fresh["tieBreak"] == "declaration_order", "two fresh options did not fall back to declaration order")
    # 六亲 follows the chart, not the options: two same-kind options routinely land on different ones.
    check(fresh["boundRelatives"] == {"A": "子孙", "B": "官鬼"}, "shi_ying bound relatives mismatch")
    check(fresh["strengthComparable"] is False, "mixed-relative options were not flagged incomparable")
    career_shi_ying = build_chart(
        [7, 8, 8, 6, 7, 8],
        day_ganzhi="庚戌", month_branch="未", cast_at="2026-08-04T11:17:00+08:00",
        question_category="career", question_form="option_comparison", mapping_mode="shi_ying",
        options=[{"optionId": "A", "label": "留任", "isStatusQuo": True}, {"optionId": "B", "label": "跳槽"}],
    )["analysis"]
    shi_side, ying_side = career_shi_ying["optionArguments"]
    check(not shi_side["carriesYongshen"] and ying_side["carriesYongshen"], "yongshen side mismatch under shi_ying")
    check(
        [item["relationFromYongshen"] for item in shi_side["yongshenLinks"]] == ["controlled_by", "controlled_by"],
        "yongshen relation to the 世 side mismatch",
    )
    check(career_shi_ying["optionMapping"]["strengthComparable"] is False, "子孙/官鬼 split was treated as comparable")
    check(
        [(item["optionId"], item["basis"]) for item in fresh["bindings"]] == [("A", "shi"), ("B", "ying")],
        "declaration order did not put the first option on 世",
    )
    check_rejected(
        lambda: build_chart(
            [7, 8, 8, 6, 7, 8], day_ganzhi="庚戌", month_branch="未", cast_at="2026-08-04T11:17:00+08:00",
            question_category="general", question_form="option_comparison", mapping_mode="shi_ying",
            options=[{"optionId": "A", "label": "甲", "isStatusQuo": True}, {"optionId": "B", "label": "乙", "isStatusQuo": True}],
        ),
        "two status-quo options accepted",
    )

    hidden_bound = build_offer_chart(bindings=[{"optionId": "A", "ref": "line:3"}, {"optionId": "B", "ref": "hidden:3"}])["analysis"]
    hidden_argument = hidden_bound["optionArguments"][1]
    check(hidden_argument["hidden"] and hidden_argument["sixRelative"] == "妻财", "hidden binding resolved to the wrong line")
    check(hidden_argument["strengthStatus"] == "not_computed_for_hidden", "hidden binding faked a strength status")
    check(hidden_bound["optionMapping"]["unmappedCandidates"] == ["line:5"], "unbound 官鬼 candidate was not reported")

    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ref": "line:3"}]), "missing binding accepted")
    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ref": "line:9"}, {"optionId": "B", "ref": "line:5"}]), "nonexistent ref accepted")
    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ref": "line:3"}, {"optionId": "C", "ref": "line:5"}]), "undeclared optionId accepted")
    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ref": "line:3"}, {"optionId": "B", "ref": "line:3"}]), "two options sharing one position accepted")
    check_rejected(lambda: build_offer_chart(options=[offers[0]]), "single-option comparison accepted")
    check_rejected(lambda: build_offer_chart(options=[offers[0], dict(offers[0])]), "duplicate optionId accepted")
    check_rejected(lambda: build_offer_chart(mapping_mode="shi_ying"), "shi_ying accepted manual bindings")
    check_rejected(lambda: build_offer_chart(mapping_mode=None), "missing mappingMode accepted")

    # Ordinals name which appearance of the yongshen to take, because a concrete
    # position cannot be known before the cast -- which is what made "declared
    # before the cast" impossible to honour for this mapping mode.
    by_ordinal = build_offer_chart(
        bindings=[{"optionId": "A", "ordinal": 1}, {"optionId": "B", "ordinal": 2}]
    )["analysis"]["optionMapping"]
    check(by_ordinal["tieBreak"] == "ordinal_rule", "ordinal binding not recorded as such")
    check([b["ref"] for b in by_ordinal["bindings"]] == ["line:3", "line:5"],
          "ordinals did not resolve to this chart's yongshen appearances")
    check(by_ordinal["strengthComparable"] is True,
          "ordinal binding should land both options on the same 六亲")

    # The same rule must follow the chart rather than a fixed position.
    elsewhere = build_chart(
        [7, 7, 7, 8, 8, 7], day_ganzhi="庚戌", month_branch="未",
        cast_at="2026-08-04T11:17:00+08:00", question_category="career",
        question_form="option_comparison", mapping_mode="yongshen_multi",
        options=offers, bindings=[{"optionId": "A", "ordinal": 1}, {"optionId": "B", "ordinal": 2}],
    )["analysis"]["optionMapping"]
    check([b["ref"] for b in elsewhere["bindings"]] == ["line:2", "line:6"],
          "the ordinal rule did not follow the other chart's own appearances")

    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ordinal": 1}, {"optionId": "B", "ordinal": 9}]),
                   "ordinal beyond the yongshen's appearances accepted")
    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ordinal": 1}, {"optionId": "B", "ordinal": 1}]),
                   "two options on one appearance accepted")
    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ordinal": 0}, {"optionId": "B", "ordinal": 2}]),
                   "ordinal 0 accepted")
    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ordinal": True}, {"optionId": "B", "ordinal": 2}]),
                   "a bool was accepted as an ordinal")
    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ref": "line:3"}, {"optionId": "B", "ordinal": 2}]),
                   "refs and ordinals were mixed")
    check_rejected(lambda: build_offer_chart(bindings=[{"optionId": "A", "ref": "line:3", "ordinal": 1}, {"optionId": "B", "ordinal": 2}]),
                   "one binding carried both ref and ordinal")

    # A 六亲 occupies at most two of the six lines in all 64 hexagrams, so three
    # options can never be bound to separate appearances.
    check_rejected(
        lambda: build_offer_chart(
            options=[{"optionId": o, "label": o} for o in ("A", "B", "C")],
            bindings=[{"optionId": o, "ordinal": n} for n, o in enumerate(("A", "B", "C"), 1)],
        ),
        "yongshen_multi accepted three options",
    )
    import itertools as _itertools
    worst = 0
    for pattern in _itertools.product([7, 8], repeat=6):
        for domain in ("career", "wealth", "academic", "home", "legal_risk"):
            worst = max(worst, len(build_chart(
                list(pattern), day_ganzhi="甲子", month_branch="子",
                cast_at="2026-01-01T12:00:00+08:00", question_category=domain,
            )["analysis"]["candidates"]))
    check(worst == 2, f"a yongshen appeared {worst} times; the two-option limit rests on this")
    check_rejected(
        lambda: build_chart(
            [7, 8, 8, 6, 7, 8], day_ganzhi="庚戌", month_branch="未", cast_at="2026-08-04T11:17:00+08:00",
            question_category="travel", question_form="option_comparison", options=offers, mapping_mode="shi_ying",
        ),
        "shi_ying accepted a domain whose yongshen is 世爻",
    )
    check_rejected(
        lambda: build_chart(
            [7, 8, 8, 6, 7, 8], day_ganzhi="庚戌", month_branch="未", cast_at="2026-08-04T11:17:00+08:00",
            question_category="career", options=offers,
        ),
        "options accepted without questionForm option_comparison",
    )

    compared_response = {"chart": build_offer_chart()["chart"], "analysis": compared}
    check(verify_report("选项 A 对应第三爻，选项 B 对应第5爻。", compared_response)["accepted"], "correct option binding was rejected")
    wrong_bind = verify_report("选项 B 落在第三爻。", compared_response)
    check(not wrong_bind["accepted"] and wrong_bind["errors"][0]["type"] == "option_binding", "wrong option binding escaped audit")
    unknown_option = verify_report("选项 C 更有利。", compared_response)
    check(not unknown_option["accepted"] and unknown_option["errors"][0]["type"] == "option_unbound", "undeclared option escaped audit")
    check(verify_report("选项 B 更有利，宜在申月推进。", compared_response)["accepted"], "option preference was incorrectly constrained")
    check(verify_report("选项 A 对应第三爻。", one_shot["result"])["accepted"], "option audit fired on a single-target chart")

    packet_prompt = run(
        "留在现公司还是去 B 公司", "career", "lines", "Asia/Shanghai", "7,8,8,6,7,8", None,
        question_form="option_comparison", options=offers, mapping_mode="yongshen_multi",
        bindings=[{"optionId": "A", "ref": "line:3"}, {"optionId": "B", "ref": "line:5"}],
    )["prompt"]
    check('"optionMapping"' in packet_prompt and '"optionArguments"' in packet_prompt, "option fields missing from Agent packet")
    check('"optionMapping"' not in packet_prompt.split('"routingGuidance"', 1)[0], "option mapping leaked into deterministic facts")
    check("用神旺相只说明它是用神" in OPTION_POLICY, "option policy does not separate 消歧 from 择优")
    check("不可改写、不可调换" in OPTION_POLICY, "option policy does not freeze the bindings")
    check(OPTION_POLICY in packet_prompt, "option policy missing from option-comparison prompt")
    check(OPTION_POLICY not in one_shot["prompt"], "option policy leaked into an ordinary question")

    # The payload is billed per token per reading, so the lines ride along exactly once.
    packet = build_packet(one_shot["result"])
    payload_text = packet["messages"][1]["content"]
    payload = json.loads(payload_text)
    facts = payload["deterministicRuleFacts"]
    check(packet["schemaVersion"].endswith(".v2"), "packet schema version not bumped after dedup")
    check("lineFacts" not in facts and "hiddenLineFacts" not in facts, "line copies returned to the payload")
    check(len(payload["chart"]["lines"]) == 6, "payload lost the lines it must carry once")
    check(
        payload_text.count(json.dumps(payload["chart"]["lines"], ensure_ascii=False)) == 1,
        "chart.lines appears more than once in the payload",
    )
    context = facts["contextArguments"]
    check("line" not in context["shi"] and "line" not in context["ying"], "世/应 line copies returned")
    check(context["shi"]["position"] == 2 and context["ying"]["position"] == 5, "世/应 positions lost in dedup")
    check("shiYingBranchRelations" in context, "世应关系事实 lost in dedup")
    check(all(key in facts for key in ("branchRelationFacts", "threeHarmonyFacts", "punishmentFacts")), "relation facts lost in dedup")
    check("chart.lines" in facts.get("lineReference", ""), "payload does not say where the lines live")

    # Rule narration: every sentence restates a computed fact, so it must be
    # correct by construction rather than merely correct on the sample chart.
    narration = narrate(tun)
    check("本卦为水雷屯，变卦为泽雷随" in narration, "narration lost the hexagram names")
    check("世爻在二爻" in narration and "应爻在五爻" in narration, "narration lost 世应")
    check("三爻 官鬼庚辰土" in narration, "narration lost a yongshen appearance")
    check("泄于月建未" in narration or "得月建未生" in narration or "受月建未克" in narration
          or "与月建未比和" in narration or "克月建未" in narration, "narration lost the month standing")
    check("四爻 父母戊申金 动" in narration, "narration lost the moving line")
    check("三爻下伏 妻财戊午" in narration, "narration lost the hidden line")
    check("不含吉凶判断" in narration, "narration does not disclaim judgement")
    check("综合判断" in narration, "narration does not say what it leaves out")
    check(verify_report(narration, tun)["accepted"], "narration failed the audit on the golden chart")

    option_narration = narrate(compared_response)
    check("取用格式：用神两现取用" in option_narration, "narration lost the mapping mode")
    check("选项 A（留在现公司）对应三爻" in option_narration, "narration lost an option binding")
    check("这才是可比的量" in option_narration, "narration does not point at the comparable quantity")
    check(verify_report(option_narration, compared_response)["accepted"], "option narration failed the audit")
    # Every identifier the rule names must actually be able to appear in a payload,
    # or the rule is warning about something that never reaches the model.
    sample_payload = json.dumps(
        json.loads(build_packet(compared_response)["messages"][1]["content"]), ensure_ascii=False
    )
    for token in ("career", "yongshen_multi", "same_element", "generated_by",
                  "selectionStatus", "conclusionScope", "option_comparison"):
        check(token in sample_payload, f"{token} is named in the rule but never appears in a payload")
    # shi_ying reaches the model on the other mapping mode.
    shi_ying_payload = build_packet(build_chart(
        [7, 8, 8, 6, 7, 8], day_ganzhi="庚戌", month_branch="未",
        cast_at="2026-08-04T11:17:00+08:00", question_category="career",
        question_form="option_comparison", mapping_mode="shi_ying",
        options=[{"optionId": "A", "label": "留任", "isStatusQuo": True}, {"optionId": "B", "label": "跳槽"}],
    ))["messages"][1]["content"]
    check("shi_ying" in shi_ying_payload, "shi_ying is named in the rule but never appears in a payload")

    stems, branches = "甲乙丙丁戊己庚辛壬癸", "子丑寅卯辰巳午未申酉戌亥"
    random.seed(11)
    audited = 0
    for index in range(120):
        values = [random.choice([6, 7, 8, 9]) for _ in range(6)]
        offset = random.randrange(60)
        extra = {}
        domain = random.choice(["general", "career", "wealth", "academic", "home", "legal_risk"])
        if index % 3 == 0:
            extra = {
                "question_form": "option_comparison", "mapping_mode": "shi_ying",
                "options": [{"optionId": "A", "label": "甲案"}, {"optionId": "B", "label": "乙案"}],
            }
        sample = build_chart(
            values, day_ganzhi=stems[offset % 10] + branches[offset % 12],
            month_branch=random.choice(branches), cast_at="2026-09-15T12:00:00+08:00",
            question_category=domain, question_text="测试问题", **extra,
        )
        if not verify_report(narrate(sample), sample)["accepted"]:
            raise AssertionError(f"narration misstated chart {index}")
        audited += 1
    check(audited == 120, "random narration sweep did not run")

    option_run = run(
        "留在现公司还是去 B 公司", "career", "lines", "Asia/Shanghai", "7,8,8,6,7,8", None,
        question_form="option_comparison", options=offers, mapping_mode="yongshen_multi",
        bindings=[{"optionId": "A", "ref": "line:3"}, {"optionId": "B", "ref": "hidden:3"}],
    )
    option_html = render_html(option_run)
    viewer_template = (project_root / "assets" / "liuyao-viewer.html").read_text(encoding="utf-8")
    check("选项对比" in viewer_template and "用神两现取用" in viewer_template, "viewer cannot label the option mapping")
    check("optByRef" in viewer_template and "refText" in viewer_template, "viewer cannot mark bound lines")
    # The template carries those identifiers itself, so assert on the injected data only.
    check("optionMapping" in embedded_data(option_html), "viewer HTML lacks the frozen bindings")
    check("hidden:3" in embedded_data(option_html), "viewer HTML lost the hidden binding")
    check("optionMapping" not in embedded_data(render_html(one_shot)), "option mapping surfaced on a single-target chart")
    option_markdown = render(option_run["result"])
    check("- A 留在现公司 → 第3爻" in option_markdown, "Markdown review copy lost the line binding")
    check("- B 去 B 公司 → 第3爻伏神 妻财" in option_markdown, "Markdown review copy lost the hidden binding")
    check("旺衰非同类比" in option_markdown, "Markdown review copy lost the comparability caveat")
    check("各选项六亲不同，旺衰非同类比" in viewer_template, "viewer cannot warn about incomparable strength")

    routing_guide = (project_root / "references" / "domain-routing.md").read_text(encoding="utf-8")
    modes_guide = (project_root / "references" / "interpretation-modes.md").read_text(encoding="utf-8")
    frontend_guide = (project_root / "references" / "frontend-contract.md").read_text(encoding="utf-8")
    check("互斥选项" in routing_guide and "映射必须在起卦前声明" in routing_guide, "routing guide lacks the option-comparison rule")
    check("判断目标与时间范围是否一致" in routing_guide, "routing guide lacks the independent-vs-exclusive test")
    check("消歧与择优是两条链路，互不替代" in modes_guide, "interpretation guide conflates 消歧 with 择优")
    check("suspended_for_option_comparison" in modes_guide, "interpretation guide lacks the suspension rule")
    check("strengthComparable" in modes_guide and "不是同类比" in modes_guide, "interpretation guide lacks the comparability rule")
    check("与选项本身是什么无关" in modes_guide, "interpretation guide does not explain where 六亲 comes from")
    check("绑定爻位" in frontend_guide, "frontend contract does not require visible bindings")
    check("--question-form option_comparison" in skill_text, "SKILL.md does not document the option flags")
    check("映射必须在起卦前声明" in skill_text, "SKILL.md does not state the pre-cast declaration rule")
    # --- language ---------------------------------------------------------
    # Chinese is the engine's native form. Any drift here means a language
    # feature quietly rewrote readings nobody asked to change.
    for combo in ("7,8,8,6,7,8", "9,6,9,6,9,6", "8,8,8,8,8,8"):
        native = run("测试问题", "career", "lines", "Asia/Shanghai", combo, None)["result"]
        check(narrate(native, "zh") == narrate(native), "language argument changed the Chinese default")
        check(narrate(native, "nonsense") == narrate(native), "an unknown language did not fall back to Chinese")

    # Its own fixture rather than whatever the random sweep happened to leave
    # behind, and an English question, since the narration echoes the question
    # verbatim and must not be blamed for the caller's own characters.
    sample = build_chart(
        [9, 8, 8, 6, 7, 8], day_ganzhi="庚戌", month_branch="未",
        cast_at="2026-08-04T11:17:00+08:00", question_category="career",
        question_text="Is this a good time to change jobs",
    )
    english = narrate(sample, "en")
    check("## The Chart" in english, "English narration lost its headings")
    check(not any("\u4e00" <= ch <= "\u9fff" for ch in english), "English narration leaked Chinese characters")
    check("Geng-" in english or "-Xu" in english or "Jia-" in english, "English narration lost the najia pair")
    for banned in ("None", "{", "}"):
        check(banned not in english, f"English narration leaked {banned!r} from a template")

    # A term the engine can emit but the lexicon has never heard of surfaces as
    # untranslated Chinese in an English chart, and only for the charts that
    # happen to contain it -- so sweep rather than spot-check. This is how the
    # engine's 腾蛇 was found sitting next to the lexicon's 螣蛇.
    seen_names, seen_terms = set(), set()
    for _ in range(200):
        chart = run("测试问题", "general", "auto", "Asia/Shanghai", None, None)["result"]
        table = chart_lexicon(chart, "en")
        for key in ("originalHexagram", "changedHexagram"):
            name = chart["chart"][key]["name"]
            seen_names.add(name)
            check(hexagram_name(name, "en") != name, f"hexagram {name} has no English rendering")
            check(hexagram_name(name, "zh") == name, "Chinese hexagram name was rewritten")
        rows = list(chart["chart"]["lines"]) + list(chart["chart"].get("hiddenLines") or [])
        for row in rows:
            for field in ("sixRelative", "sixSpirit", "najiaStem", "najiaBranch", "najiaElement"):
                value = row.get(field)
                if value:
                    seen_terms.add(value)
                    check(value in table, f"lexicon is missing {field} {value!r}")
    check(len(seen_names) > 30, "hexagram sweep did not cover enough of the 64")
    check(len(seen_terms) >= 30, "term sweep did not cover enough of the vocabulary")

    lexicon_en = chart_lexicon(sample, "en")
    check(chart_lexicon(sample, "zh") == {}, "Chinese asked for a translation table it does not need")
    check(all(value != key for key, value in lexicon_en.items()), "lexicon returned an untranslated entry")

    # The audit is the only thing between a reading and a misstated chart, so it
    # has to bite in the language the reading was written in. A pattern written
    # in the wrong word order fails silently: nothing matches, and the reading is
    # accepted without ever being checked.
    check(verify_report(narrate(sample, "en"), sample)["accepted"], "English narration failed its own audit")
    shi, ying = sample["chart"]["shiPosition"], sample["chart"]["yingPosition"]
    wrong_line = 1 + (0 if sample["chart"]["lines"][0]["sixRelative"] != "妻财" else 1)
    wrong_relative = "Wealth" if sample["chart"]["lines"][wrong_line - 1]["sixRelative"] != "妻财" else "Officer"
    for claim in (
        f"Line {wrong_line} is the {wrong_relative}.",
        f"Shi is on line {1 + shi % 6}.",
        f"Ying sits on line {1 + ying % 6}.",
    ):
        check(not verify_report(claim, sample)["accepted"], f"English audit missed a false claim: {claim}")
    true_relative = LEXICON_SIX_RELATIVE[sample["chart"]["lines"][shi - 1]["sixRelative"]]
    check(verify_report(f"Line {shi} is the {true_relative}.", sample)["accepted"],
          "English audit rejected a true claim")
    check(verify_report(f"Shi is on line {shi}.", sample)["accepted"], "English audit rejected a true Shi claim")

    english_prompt = build_packet(sample, "en")["messages"][0]["content"]
    check(build_packet(sample, "zh") == build_packet(sample), "language argument changed the default packet")
    check(SYSTEM_PROMPT in english_prompt, "English packet dropped the method discipline")
    check("not professional advice" in english_prompt, "English packet lost the English disclaimer")
    check("Shi is on line 2" in english_prompt, "English packet does not fix the Shi/Ying wording the audit checks")
    # Twice a live English reading came back English apart from a few Chinese
    # characters -- first 应期, then the bare branches of a three-harmony triad --
    # because the directive romanized the forms it happened to list and left the
    # model nothing for the rest. Patching in one term per leak does not
    # converge, so assert the tables are whole instead.
    from lexicon import BRANCH, STEM

    for character, roman in {**STEM, **BRANCH}.items():
        check(f"{character}={roman}" in english_prompt,
              f"the English directive has no romanization for {character}")
    check("yingqi" in english_prompt, "the English directive does not romanize 应期")
    # A live reading wrote "Officer (官鬼)" against a directive that banned Chinese
    # outright. Glossing a term once is the convention in English writing on this
    # subject and helps a reader cross-reference, so the rule now permits exactly
    # that and forbids the rest -- a prompt carrying a rule the model sensibly
    # breaks weakens every other rule in it.
    check("Officer (官鬼)" in english_prompt, "the English directive does not allow a first-mention gloss")
    check("不再重复附注" in english_prompt, "the English directive does not bound the gloss to first mention")

    print(f"standalone fortune-liuyao regression: {PASSED}/{PASSED} passed")


if __name__ == "__main__":
    main()
