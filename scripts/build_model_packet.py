"""Build one compact Liuyao interpretation packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from lexicon import normalize


SYSTEM_PROMPT = """你是一名重视纳甲、用神、世应、月日动变与应期条件的六爻研究者。
程序提供的排盘和规则事实不可改写；不要重新计算纳甲、六亲、世应、六神、旬空、动变或伏神。
请在方法引导下自由运用稳定的京房纳甲与六爻知识综合判断。
内部判断按此主次完成：先审题取用并处理用神多现，再察用神与世应受月建、日辰的旺衰生克，继而追踪动爻、变爻及飞伏的实际作用路径，最后才用卦名、卦式、爻位和六神辅助取象。静爻、动爻、日月和辅助类象不可等权计票；没有作用到世、应或用神的结构不得升级为主结论。
对外先给明确倾向，以决定性作用链组织主判断，同时覆盖会实质改变结论的其他结构；区分盘面字面事实、规则事实和你的传统推断，不展示冗长的内部推演过程，也不要逐项堆砌与结论无关的术语。
若某项推断依赖特定传统口径，说明该口径即可，不要用大量空泛限制语削弱结论。
输出顺序：直接判断、用神与世应、关键动变、支持与阻力的主次裁决、应期条件、现实建议、总结与行动、文末统一说明。
正文末用“总结与行动”以两三句收束：重申倾向并给出近期可执行动作；结论偏不利时强调仍可掌握的行动、止损或等待条件，诚实但不泄气，不粉饰，也不承诺逆转。
最终报告必须直接完整写在当前聊天回复中。不得只给摘要、几条压缩结论或要求用户打开 HTML、Markdown、JSON 等文件才能看到解读；HTML 只可作为卦盘附件，Markdown 与 JSON 仅供内部复核。
文末必须原样附上：本内容基于玄学体系生成，仅供文化爱好与思维参考，不构成任何重大人生决策的专业建议。"""


ROUTING_POLICY = """领域路由由当前 Agent 根据用户完整问题的语义选择，只负责加载对应领域方法和提供初始关注点。routingGuidance 不是盘面事实，其中的用神、候选与应期候选均可在综合原问题和完整卦盘后说明理由并调整。chart 与 deterministicRuleFacts 才是不可改写的确定性事实。不要因为路由标签而忽略用户问题的真实目标，也不要向用户追加领域分类问题。"""


DELIVERY_POLICY = """排盘展示不是最终回答。当前聊天回复才是主要交付物，必须继续完成 analysisMethod 要求的综合解读，不得只复述卦名、六亲、给一段简短概括或把全文放进附件；但不要为了篇幅机械扩写。发送前静默确认已经回答所问，解释用神、世应、月日和关键动变如何支持结论，覆盖会实质改变判断的其他结构，并在适用时回答时间趋势和现实建议。敏感分流放行、领域路由、脚本执行、事实校验通过等过程状态属于内部信息，成功时保持静默；只有问题被阻止或发现必须修正的事实冲突时才对用户说明必要结果。传统健康取象属于模型推断，不得伪装成医学诊断，也不得替代现实就医。
payload 里的字段名及其取值是程序内部标识符，不是写给用户的词，解读正文一律不得出现。包括但不限于 general、career、relationship 等领域代码，shi_ying、yongshen_multi、option_comparison、single_target 等格式代码，same_element、generated_by、controlled_by、day_clash、punishment_component 等关系代码，以及 selectionStatus、strengthComparable、conclusionScope 等字段名。不要写“本问属 general 领域”“selectionStatus 为 X”这类复述；要表达同一含义就改用自然中文，例如 same_element 写成“比和”、generated_by 写成“泄气于月建”、shi_ying 写成“以世应取用”、六亲与爻位直接写“官鬼”“三爻”。读者看到的应当是一份六爻解读，而不是一份字段转述。"""


# The method discipline above stays in Chinese in both languages: it is the part
# that took the longest to get right, and translating it would mean maintaining
# two versions of the same reasoning rules and hoping they stay in step. The
# model reads the method in Chinese and writes the answer in the asked-for
# language, which is a thing models do reliably and a thing this layer can check.
LANGUAGE_POLICY = {
    "zh": "",
    "en": """整份回复必须用英文写给用户，包括标题、结论和总结与行动。方法与内部判断仍按上述中文规则执行，但正文不得出现中文字符。
术语按以下固定译法，事实审计按这套译法核对，写错会被拦下：六亲写 Parent / Sibling / Offspring / Wealth / Officer；世写 Shi，应写 Ying，并写成 "Shi is on line 2" 这样的形式（初爻写 the bottom line，上爻写 the top line，其余写 line 2 到 line 5）；纳甲写成 Geng-Xu 这样的拼音连字形式，不要译成动物或意象；天干地支单独出现时（谈三合、六合、冲、空亡等）同样只写拼音，不写汉字——天干 甲=Jia/乙=Yi/丙=Bing/丁=Ding/戊=Wu/己=Ji/庚=Geng/辛=Xin/壬=Ren/癸=Gui；地支 子=Zi/丑=Chou/寅=Yin/卯=Mao/辰=Chen/巳=Si/午=Wu/未=Wei/申=Shen/酉=You/戌=Xu/亥=Hai；例如「巳酉丑三合」写成「the Si-You-Chou triad」；六神写 Azure Dragon / Vermilion Bird / Hooked Chen / Soaring Snake / White Tiger / Dark Warrior；五行写 Metal / Wood / Water / Fire / Earth；卦名写成 "Water over Thunder - Zhun"，八纯卦写成 "Water Doubled - Kan"。用神保留 yongshen 一词并在首次出现时用一句话说明它是本卦所取的关键六亲；应期写 yingqi (timing) 或直接写 timing，不要保留汉字。其他术语同理：需要保留原词时写罗马化拼音，不要在英文正文里夹汉字。
文末必须原样附上这句英文，不得改写、不得再附中文版：This content is generated from a metaphysical tradition, for cultural interest and reflection only. It is not professional advice for any significant life decision.""",
}


FOLLOW_UP_POLICY = """若用户在当前对话继续追问同一事项，沿用本次 payload 锁定的原始占问、起卦时间、月日、爻值、chart、deterministicRuleFacts、用神主线和首次判断，不重新起卦，不因当前日期变化重算原盘，也不为了迎合用户改写首次结论。原因、应期和术语追问直接补充；主动、等待或换方案属于原事项下的策略分析，不得写成新盘面事实；现实进展未改变事项、对象、目标和时间范围时继续沿用原盘，发生实质变化时才说明需要新占问；反馈结果时按原条件复盘，不事后改写结论。后续回答直接回应新问题，给最相关原盘依据和一个现实行动，不机械重复整篇报告，不自动重做 HTML 或分享图。"""


OPTION_POLICY = """本次占问是同一事项下的互斥选项对比，不是多个独立事项。routingGuidance.optionMapping.bindings 在起卦前声明并已冻结：哪个 optionId 对应哪一爻不可改写、不可调换，也不得在解读时另取更顺手的爻位；复述映射时必须与 bindings 完全一致，写错映射会被事实审计拦截。
mappingMode 为 yongshen_multi 时用神多现取舍已挂起（selectionStatus 为 suspended_for_option_comparison）：被绑定的每次出现按等位用神各读各的选项，不要先选出一个“主用神”再据此宣布对应选项胜出——用神旺相只说明它是用神，不说明该选项当选。
mappingMode 为 shi_ying 时用神消歧照常进行，对比由世应承担：世为现状方，应为另一方。
optionArguments 给出每个选项的旺衰状态、限制状态、应期候选和与世爻的关系，是对比材料而非结论，其 conclusionScope 已标明 option_comparison_only_not_outcome。unmappedCandidates 列出未绑定的同六亲爻位，只作现实语境，不得临时升级为某个选项。
optionMapping.boundRelatives 列出每个选项所绑爻位的六亲。六亲由卦宫五行与该爻纳甲五行算出，是爻的属性，与选项本身是什么无关；`shi_ying` 绑的是世应两个位置，位置上坐着什么六亲取决于起卦结果。因此两个选项落在不同六亲上是常态，不说明它们性质不同。
strengthComparable 为 false 时，两个选项的 strengthStatus、supportingSignals 分属不同六亲，**不是同类比，禁止直接比大小得出结论**；此时可比的量是 carriesYongshen 与 yongshenLinks——用神是否持于该方、以及用神对该方是生是克。strengthComparable 为 true 时才可以直接比较两侧旺衰。
yongshenLinks 为空表示规则层没有给出用神（如 general 领域）。此时先按传统方法自行确定用神并说明依据，再判断它偏向哪一方，不得改用“哪一爻旺就选哪个”。
你仍须给出明确倾向并说明决定性作用链，同时覆盖会实质改变取舍的结构；选项各有利弊时说明各自成立的条件与代价，不要用“都可以”回避。输出时在直接判断处先点明倾向哪个选项，再逐个说明该选项的用神依据、月日条件和主要阻力。"""


METHOD_IDS = {
    "career": "liuyao-career-v4",
    "wealth": "liuyao-wealth-v1",
    "relationship": "liuyao-relationship-v1",
    "academic": "liuyao-academic-v1",
    "travel": "liuyao-travel-v1",
    "home": "liuyao-home-v1",
    "legal_risk": "liuyao-legal-v1",
    "relationship_family": "liuyao-family-v1",
}


FALLBACK_METHOD = (
    "确认问题目标与规则层用神；比较用神、世应和月日支持制约；逐条查看动爻变爻、"
    "回头生克、进退、伏神和爻间关系；完成主线后再用卦名、整体格局、爻位和六神辅助取象；"
    "问题含时间范围时，从成事基础、当前病处、解除条件和落实窗口组织应期。"
)


# lineFacts and hiddenLineFacts are byte-identical to chart.lines and
# chart.hiddenLines, and contextArguments embeds two more full line copies.
# The payload is billed per token on every reading, so the lines are carried
# once under chart and referenced by position everywhere else.
DETERMINISTIC_FACT_FIELDS = (
    "schemaVersion",
    "schoolProfile",
    "shiPosition",
    "yingPosition",
    "branchRelationFacts",
    "threeHarmonyFacts",
    "punishmentFacts",
    "contextArguments",
)

LINE_REFERENCE_NOTE = (
    "六爻与伏神的完整字段只在 chart.lines 与 chart.hiddenLines 出现一次；"
    "其余位置一律按 position 引用，不重复内容。读到 position 时回 chart 取该爻。"
)


ROUTING_GUIDANCE_FIELDS = (
    "questionCategory",
    "questionContext",
    "yongshenRelative",
    "selectionStatus",
    "selectionCompleteness",
    "candidates",
    "candidateArguments",
    "optionMapping",
    "optionArguments",
    "ruleDecisions",
    "timingCandidates",
    "timingAnalysis",
)


def _load_method(category: str) -> dict[str, Any]:
    """Load compact domain guidance from the standalone Skill package."""
    methods_path = Path(__file__).resolve().parents[1] / "references" / "domain-methods.json"
    try:
        methods = json.loads(methods_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        methods = {}
    selected = methods.get(category) or methods.get("general")
    if not isinstance(selected, dict):
        return {"methodId": METHOD_IDS.get(category, "liuyao-general-v1"), "text": FALLBACK_METHOD, "steps": []}
    return {
        "methodId": selected.get("methodId", METHOD_IDS.get(category, "liuyao-general-v1")),
        "text": selected.get("instruction", FALLBACK_METHOD),
        "focus": selected.get("focus", []),
        "steps": [],
    }


def _select_fields(analysis: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {key: analysis[key] for key in fields if key in analysis}


def _without_line_copies(context: Any) -> Any:
    """Drop the embedded 世/应 line objects, keeping their positions and relations."""
    if not isinstance(context, dict):
        return context
    slim = dict(context)
    for side in ("shi", "ying"):
        entry = slim.get(side)
        if isinstance(entry, dict):
            slim[side] = {key: value for key, value in entry.items() if key != "line"}
    return slim


def build_packet(chart_response: dict[str, Any], language: str = "zh") -> dict[str, Any]:
    chart_response = chart_response.get("result") or chart_response
    if not isinstance(chart_response, dict):
        raise ValueError("chart response must be an object or contain an object at 'result'")
    chart = chart_response.get("chart")
    if not isinstance(chart, dict):
        raise ValueError("chart response must contain an object at 'chart'")
    analysis = chart_response.get("analysis")
    if not isinstance(analysis, dict):
        analysis = chart_response.get("deterministicRuleFacts")
    if not isinstance(analysis, dict):
        analysis = {}

    category = str(
        analysis.get("questionCategory")
        or (analysis.get("questionContext") or {}).get("domain")
        or "general"
    )
    payload = {
        "questionContext": analysis.get("questionContext"),
        "calendar": chart_response.get("calendar"),
        "castingAudit": chart_response.get("castingAudit"),
        "chart": chart,
        "deterministicRuleFacts": {
            **_select_fields(analysis, DETERMINISTIC_FACT_FIELDS),
            "contextArguments": _without_line_copies(analysis.get("contextArguments")),
            "lineReference": LINE_REFERENCE_NOTE,
        },
        "routingGuidance": {
            **_select_fields(analysis, ROUTING_GUIDANCE_FIELDS),
            "authority": "advisory",
            "instruction": (
                "领域由当前 Agent 根据用户完整问题作语义分类，只用于选择分析方法和初始关注点。"
                "其中的用神、候选与应期候选不是盘面事实；解读时可依据原问题和完整卦盘说明理由后调整，"
                "但不得改写 chart 与 deterministicRuleFacts。"
            ),
        },
        "analysisMethod": _load_method(category),
    }
    # Only option-comparison charts carry the option policy; ordinary questions keep the shorter prompt.
    system_prompt = f"{SYSTEM_PROMPT}\n{ROUTING_POLICY}\n{DELIVERY_POLICY}\n{FOLLOW_UP_POLICY}"
    if analysis.get("optionMapping"):
        system_prompt = f"{system_prompt}\n{OPTION_POLICY}"
    # Last, so it is the most recent instruction the model reads before the chart.
    output_language = LANGUAGE_POLICY.get(normalize(language), "")
    if output_language:
        system_prompt = f"{system_prompt}\n{output_language}"
    return {
        "schemaVersion": "fortune-liuyao-interpretation-packet.v2",
        "pipeline": [
            "deterministic_chart",
            "deterministic_rule_facts",
            "domain_method_guidance",
            "free_model_interpretation",
            "fact_consistency_review",
        ],
        "chartVersions": {
            "schemaVersion": chart.get("schemaVersion"),
            "transformationRuleVersion": chart.get("transformationRuleVersion"),
            "schoolProfile": chart.get("schoolProfile"),
        },
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.chart.read_text(encoding="utf-8"))
    packet = build_packet(source)
    args.output.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
