"""English renderings for the chart's own vocabulary.

Chinese is the engine's native form: every value in a chart is already the term
a reader of the system expects, so there is no Chinese table here and nothing to
drift out of step with the engine. Only the English overlay is written down.

Najia stems and branches are coordinates in a sixty-step cycle, not words, so
they are transliterated rather than translated -- 庚戌 is "Geng-Xu", because
"Metal-Dog" would name an animal that plays no part in the calculation. Hexagram
names keep the same shape they have in Chinese: the trigram pair that a Liuyao
reader uses to find the chart, then the King Wen name that identifies it.
"""

from __future__ import annotations

from typing import Any

LANGUAGES = ("zh", "en")
DEFAULT_LANGUAGE = "zh"


def normalize(language: str | None) -> str:
    """Fold anything unrecognized onto Chinese rather than failing a reading."""
    if not language:
        return DEFAULT_LANGUAGE
    tag = str(language).replace("_", "-").lower()
    if tag.startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


ELEMENT = {"金": "Metal", "木": "Wood", "水": "Water", "火": "Fire", "土": "Earth"}

# Trigram name, then the image it carries. The image is what composes a hexagram
# name; the name is what identifies the palace.
TRIGRAM = {"乾": "Qian", "兑": "Dui", "离": "Li", "震": "Zhen",
           "巽": "Xun", "坎": "Kan", "艮": "Gen", "坤": "Kun"}
IMAGE = {"天": "Heaven", "泽": "Lake", "火": "Fire", "雷": "Thunder",
         "风": "Wind", "水": "Water", "山": "Mountain", "地": "Earth"}

SIX_RELATIVE = {"父母": "Parent", "兄弟": "Sibling", "子孙": "Offspring",
                "妻财": "Wealth", "官鬼": "Officer"}

# 腾蛇 is the spelling the engine emits; 螣蛇 is the same spirit and is accepted
# so a chart from another source does not come back half translated.
SIX_SPIRIT = {"青龙": "Azure Dragon", "朱雀": "Vermilion Bird", "勾陈": "Hooked Chen",
              "腾蛇": "Soaring Snake", "螣蛇": "Soaring Snake",
              "白虎": "White Tiger", "玄武": "Dark Warrior"}

STEM = {"甲": "Jia", "乙": "Yi", "丙": "Bing", "丁": "Ding", "戊": "Wu",
        "己": "Ji", "庚": "Geng", "辛": "Xin", "壬": "Ren", "癸": "Gui"}

BRANCH = {"子": "Zi", "丑": "Chou", "寅": "Yin", "卯": "Mao", "辰": "Chen", "巳": "Si",
          "午": "Wu", "未": "Wei", "申": "Shen", "酉": "You", "戌": "Xu", "亥": "Hai"}

YIN_YANG = {"阳": "Yang", "阴": "Yin"}

# Where the hexagram sits in its palace's sequence. Positional, so the English is
# positional too rather than an interpretation of what each stage means.
PALACE_STAGE = {
    "本宫": "Pure", "一世": "1st Generation", "二世": "2nd Generation",
    "三世": "3rd Generation", "四世": "4th Generation", "五世": "5th Generation",
    "游魂": "Wandering Soul", "归魂": "Returning Soul",
}

# The 64 King Wen names, transliterated with the standard English rendering. The
# full display name is composed from the trigram images, exactly as in Chinese:
# 水雷屯 becomes "Water over Thunder - Zhun (Difficulty at the Beginning)".
KING_WEN = {
    "乾": ("Qian", "The Creative"), "坤": ("Kun", "The Receptive"),
    "屯": ("Zhun", "Difficulty at the Beginning"), "蒙": ("Meng", "Youthful Folly"),
    "需": ("Xu", "Waiting"), "讼": ("Song", "Conflict"),
    "师": ("Shi", "The Army"), "比": ("Bi", "Holding Together"),
    "小畜": ("Xiao Xu", "Taming Power of the Small"), "履": ("Lu", "Treading"),
    "泰": ("Tai", "Peace"), "否": ("Pi", "Standstill"),
    "同人": ("Tong Ren", "Fellowship"), "大有": ("Da You", "Great Possession"),
    "谦": ("Qian", "Modesty"), "豫": ("Yu", "Enthusiasm"),
    "随": ("Sui", "Following"), "蛊": ("Gu", "Work on the Decayed"),
    "临": ("Lin", "Approach"), "观": ("Guan", "Contemplation"),
    "噬嗑": ("Shi He", "Biting Through"), "贲": ("Bi", "Grace"),
    "剥": ("Bo", "Splitting Apart"), "复": ("Fu", "Return"),
    "无妄": ("Wu Wang", "Innocence"), "大畜": ("Da Xu", "Taming Power of the Great"),
    "颐": ("Yi", "Nourishment"), "大过": ("Da Guo", "Preponderance of the Great"),
    "坎": ("Kan", "The Abysmal"), "离": ("Li", "The Clinging"),
    "咸": ("Xian", "Influence"), "恒": ("Heng", "Duration"),
    "遁": ("Dun", "Retreat"), "大壮": ("Da Zhuang", "Power of the Great"),
    "晋": ("Jin", "Progress"), "明夷": ("Ming Yi", "Darkening of the Light"),
    "家人": ("Jia Ren", "The Family"), "睽": ("Kui", "Opposition"),
    "蹇": ("Jian", "Obstruction"), "解": ("Xie", "Deliverance"),
    "损": ("Sun", "Decrease"), "益": ("Yi", "Increase"),
    "夬": ("Guai", "Breakthrough"), "姤": ("Gou", "Coming to Meet"),
    "萃": ("Cui", "Gathering Together"), "升": ("Sheng", "Pushing Upward"),
    "困": ("Kun", "Oppression"), "井": ("Jing", "The Well"),
    "革": ("Ge", "Revolution"), "鼎": ("Ding", "The Cauldron"),
    "震": ("Zhen", "The Arousing"), "艮": ("Gen", "Keeping Still"),
    "渐": ("Jian", "Development"), "归妹": ("Gui Mei", "The Marrying Maiden"),
    "丰": ("Feng", "Abundance"), "旅": ("Lu", "The Wanderer"),
    "巽": ("Xun", "The Gentle"), "兑": ("Dui", "The Joyous"),
    "涣": ("Huan", "Dispersion"), "节": ("Jie", "Limitation"),
    "中孚": ("Zhong Fu", "Inner Truth"), "小过": ("Xiao Guo", "Preponderance of the Small"),
    "既济": ("Ji Ji", "After Completion"), "未济": ("Wei Ji", "Before Completion"),
}


def _hexagram_english(name: str) -> str:
    """Compose the English display name from the Chinese one.

    Two shapes exist. The eight doubled trigrams are written 乾为天; everything
    else is upper image, lower image, then the King Wen name.
    """
    if len(name) >= 3 and name[1] == "为":
        trigram, image = TRIGRAM.get(name[0]), IMAGE.get(name[2])
        if trigram and image:
            pinyin, gloss = KING_WEN.get(name[0], (trigram, ""))
            return f"{image} Doubled - {pinyin} ({gloss})" if gloss else f"{image} Doubled - {pinyin}"
        return name
    upper, lower, king_wen = IMAGE.get(name[:1]), IMAGE.get(name[1:2]), name[2:]
    entry = KING_WEN.get(king_wen)
    if not (upper and lower and entry):
        return name
    return f"{upper} over {lower} - {entry[0]} ({entry[1]})"


def _table() -> dict[str, str]:
    """Every chart value that has an English rendering, as one flat map.

    Flat because a caller looks up whatever string the chart handed it without
    having to know which category it came from. The keys are whole values, so
    the single characters that appear in several categories -- 水 as an element
    and as a trigram image -- cannot collide.
    """
    table: dict[str, str] = {}
    # YIN_YANG is deliberately absent: a line's polarity is drawn as a broken or
    # solid bar, never printed, and "Yin" would otherwise collide with the branch
    # 寅 sitting next to a stem in the same row.
    for source in (ELEMENT, SIX_RELATIVE, SIX_SPIRIT, STEM, BRANCH, PALACE_STAGE, TRIGRAM):
        table.update(source)
    return table


_FLAT_EN = _table()


def term(value: str | None, language: str = DEFAULT_LANGUAGE) -> str:
    """Render one chart value. Anything without a rendering is passed through."""
    if value is None:
        return ""
    if normalize(language) == "zh":
        return str(value)
    return _FLAT_EN.get(str(value), str(value))


def hexagram(name: str | None, language: str = DEFAULT_LANGUAGE) -> str:
    if not name:
        return ""
    return str(name) if normalize(language) == "zh" else _hexagram_english(str(name))


def chart_lexicon(result: dict[str, Any], language: str) -> dict[str, str]:
    """Translations for exactly the values this chart contains.

    Returned with the chart so a client renders the same words the reading uses,
    without carrying its own copy of the tables -- and so a second client, on a
    platform this repo does not build, needs no copy either. Empty for Chinese,
    where the chart values are already the words.
    """
    if normalize(language) == "zh":
        return {}
    chart = result.get("chart") or {}
    values: set[str] = set()
    for hexagram_key in ("originalHexagram", "changedHexagram"):
        entry = chart.get(hexagram_key) or {}
        if entry.get("name"):
            values.add(str(entry["name"]))
        for trigram_key in ("upperTrigram", "lowerTrigram"):
            trigram = entry.get(trigram_key) or {}
            values.update(str(trigram[field]) for field in ("name", "element") if trigram.get(field))
    for field in ("palace", "palaceElement", "palaceStage"):
        if chart.get(field):
            values.add(str(chart[field]))
    values.update(str(branch) for branch in chart.get("voidBranches") or [])
    if chart.get("monthBranch"):
        values.add(str(chart["monthBranch"]))
    # The day is one string of two characters; the client renders them as a pair,
    # so each half has to be translatable on its own.
    values.update(str(chart.get("dayGanzhi") or ""))
    rows = list(chart.get("lines") or []) + list(chart.get("hiddenLines") or [])
    rows += [line["changedLine"] for line in chart.get("lines") or [] if line.get("changedLine")]
    for row in rows:
        for field in ("sixRelative", "sixSpirit", "najiaStem", "najiaBranch", "najiaElement",
                      "yinYang", "changedYinYang", "flyingStem", "flyingBranch",
                      "flyingElement", "flyingSixRelative"):
            if row.get(field):
                values.add(str(row[field]))
    table: dict[str, str] = {}
    for value in values:
        # Every hexagram name is at least three characters and every other chart
        # value is at most two, so length alone tells them apart. Without that,
        # 坎 -- a trigram whose name is also a King Wen name -- would be routed
        # to the hexagram composer and come back untranslated.
        rendered = hexagram(value, "en") if len(value) >= 3 else term(value, "en")
        if rendered != value:
            table[value] = rendered
    return table
