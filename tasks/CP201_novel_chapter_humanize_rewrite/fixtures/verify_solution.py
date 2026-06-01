"""Hidden verifier for CP201 — Novel Chapter Humanize Rewrite.

Checks that the rewritten chapter removes AI-writing patterns and
improves human-like writing quality, while preserving plot coherence.
Includes hidden checks for style consistency, new-pattern introduction,
dialogue naturalization, and sensory specificity.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Embedded original text fingerprint for change detection
_ORIGINAL_FIRST_LINE = "清晨的阳光如同利剑一般穿透了沉重的乌云，洒落在这座古老而神秘的城池上方。"
_ORIGINAL_MD5 = "9c0fdeac157172601909840e9e933587"
_ORIGINAL_CHAR_COUNT = 1660  # len(re.sub(r"\s+", "", original))

# Key sentences from original to detect unchanged content
_ORIGINAL_MARKERS = [
    "如同利剑一般穿透了沉重的乌云",
    "苏铭站在客栈的二楼窗前，眉头紧锁，若有所思地望着楼下那条繁华而喧嚣的长街",
    "他的眼中闪过一丝不易察觉的寒芒",
    "嘴角微微上扬，露出一个意味深长的笑容",
    "动作干脆利落，不拖泥带水，浑身上下散发着一股令人心折的自信与从容",
    "空气仿佛凝固了一般",
    "面容冷峻如刀削斧凿一般，一双鹰目精光四射",
    "仿佛前方等待他的不是两百余名精锐杀手，而是一场平平无奇的早茶",
    "赵严的瞳孔猛地一缩",
    "那符文折射出璀璨的光芒，照亮了赵严逐渐扭曲的面容",
    "输得彻彻底底",
]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_chapter(ws: Path) -> str:
    """Find the chapter 42 content."""
    candidates = [
        ws / "novel" / "chapters" / "chapter_042.md",
        ws / "chapters" / "chapter_042.md",
        ws / "chapter_042.md",
        ws / "novel" / "chapter_042.md",
    ]
    for p in candidates:
        if p.exists():
            return _read(p)

    # Search more broadly
    for p in ws.rglob("*.md"):
        content = _read(p)
        if "第42章" in content and len(content) > 500:
            return content

    return ""


def _check_is_modified(text: str) -> bool:
    """Check if the text has been modified from the original."""
    import hashlib
    md5 = hashlib.md5(text.encode("utf-8")).hexdigest()
    if md5 == _ORIGINAL_MD5:
        return False

    # Also check if first meaningful line is unchanged
    lines = [l for l in text.split("\n") if l.strip() and not l.startswith("#")]
    if lines and lines[0].strip() == _ORIGINAL_FIRST_LINE:
        # First line unchanged - check how many markers remain
        marker_count = sum(1 for m in _ORIGINAL_MARKERS if m in text)
        if marker_count >= 8:  # 8 out of 11 markers = basically unchanged
            return False

    return True


def _count_ai_patterns(text: str) -> dict:
    """Count common AI-writing pattern occurrences."""
    patterns = {
        "adjective_stacking": [
            r"[^\s，。]{2,4}而[^\s，。]{2,4}的",  # "古老而神秘的" pattern
        ],
        "cliche_actions": [
            r"眼中闪过.{1,3}(精光|寒芒|杀意|光芒)",
            r"嘴角.{0,2}(微微|轻轻)?(上扬|勾起|挂着)",
            r"瞳孔.{0,2}(猛地)?一(缩|震)",
            r"浑身一(震|颤|僵)",
            r"不可抑制地",
            r"不易察觉的",
        ],
        "atmosphere_abuse": [
            r"空气.{0,4}(仿佛|似乎|好像).{0,4}(凝固|凝结|静止)",
            r"温度.{0,4}(仿佛|瞬间).{0,4}(降|冰点)",
            r"时间.{0,4}(仿佛|似乎).{0,4}(静止|凝固|停滞)",
        ],
        "telling_not_showing": [
            r"(心中|眼中|脸上)(满是|充满|溢满|涌起)[^\s，。]{2,6}(之色|之意)?",
            r"声音中带着.{2,6}",
            r"语气中.{0,4}(满是|充满|带着)",
        ],
        "formulaic_descriptions": [
            r"如同.{2,8}一般",
            r"仿佛.{2,10}(一样|一般|似的)",
            r"犹如.{2,8}(一般|一样)",
        ],
        "excessive_punctuation": [
            r"！{2,}",
            r"……{2,}",
        ],
    }

    counts = {}
    for category, regexes in patterns.items():
        total = 0
        for regex in regexes:
            total += len(re.findall(regex, text))
        counts[category] = total

    return counts


def _check_plot_preserved(text: str) -> float:
    """Check that key plot elements are preserved."""
    plot_elements = [
        ("苏铭", 0.15),
        ("赵严", 0.10),
        ("王家", 0.15),
        ("长街", 0.10),
        ("护卫", 0.10),
        ("令牌", 0.15),
        ("城主", 0.10),
        ("收刀", 0.15),
    ]

    score = 0.0
    for element, weight in plot_elements:
        if element in text:
            score += weight

    return min(score, 1.0)


def _check_substantial_rewrite(text: str) -> float:
    """Check that the rewrite is substantial based on original markers."""
    if not text or len(text) < 500:
        return 0.0

    # Count how many original markers remain
    remaining = sum(1 for m in _ORIGINAL_MARKERS if m in text)
    total = len(_ORIGINAL_MARKERS)

    # Fewer remaining markers = more rewriting done
    removal_ratio = 1.0 - (remaining / total)

    if removal_ratio >= 0.9:
        return 1.0
    elif removal_ratio >= 0.7:
        return 0.8
    elif removal_ratio >= 0.5:
        return 0.6
    elif removal_ratio >= 0.3:
        return 0.4
    else:
        return 0.1


def _check_length_control(text: str) -> float:
    """Check that rewrite doesn't bloat the text."""
    rew_chars = len(re.sub(r"\s+", "", text))
    orig_chars = _ORIGINAL_CHAR_COUNT

    if orig_chars == 0:
        return 0.0

    ratio = rew_chars / orig_chars

    # Tighter sweet spot: truly trimmed rewrites (60-85%) score highest
    if 0.60 <= ratio <= 0.85:
        return 1.0
    elif 0.85 < ratio <= 0.95:
        return 0.6
    elif 0.50 <= ratio < 0.60:
        return 0.7
    elif 0.95 < ratio <= 1.05:
        return 0.3
    elif ratio > 1.05:
        return 0.0
    elif 0.35 <= ratio < 0.50:
        return 0.4
    else:
        return 0.1


def _check_structural_variety(text: str) -> float:
    """Check paragraph length variance - less formulaic = higher score."""
    paragraphs = [p for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    if len(paragraphs) < 3:
        return 0.2

    lengths = [len(p.strip()) for p in paragraphs]
    avg_len = sum(lengths) / len(lengths)
    if avg_len <= 0:
        return 0.0

    variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
    cv = (variance ** 0.5) / avg_len

    if cv >= 0.6:
        return 1.0
    elif cv >= 0.4:
        return 0.7
    elif cv >= 0.2:
        return 0.4
    else:
        return 0.2


# =====================================================================
# HIDDEN CHECKS — harder criteria that differentiate strong from weak
# =====================================================================


def _check_new_ai_patterns(text: str) -> float:
    """HIDDEN: Check if the rewrite introduces NEW AI cliches not in the original.

    Weak models often remove the flagged patterns but substitute with other
    equally formulaic AI writing. Strong models use genuinely fresh language.
    """
    # New AI patterns that the original did NOT have but models love to introduce
    new_cliche_patterns = [
        # Dramatic narration padding
        r"(此刻|这一刻|那一瞬|这一瞬).{0,4}(似乎|仿佛|好像)",
        r"(无形|一股).{0,6}(压力|威压|气场|杀气).{0,4}(笼罩|弥漫|扩散|席卷)",
        r"(不怒自威|杀伐果断|举重若轻|云淡风轻)",
        # Emotional labeling (new forms of telling-not-showing)
        r"(内心深处|心底|心中)(涌起|泛起|升起).{2,8}(感觉|情绪|波澜)",
        r"一股.{2,6}(涌上|袭来|蔓延|充斥)",
        # Overwrought reaction descriptions
        r"(浑身|全身)(的|上下).{0,4}(汗毛|毛孔).{0,4}(倒竖|炸开|张开)",
        r"(仿佛|好像|犹如)(被|有).{2,8}(扼住|掐住|击中|刺穿|贯穿)",
        r"(宛如|仿佛|好像|犹如)(一头|一尊|一柄|一把)",
        # Purple prose replacements (often introduced during "humanization")
        r"(那双|一双).{0,4}(眸子|眼眸|凤目|星眸|桃花眼)",
        r"(修长|白皙|骨节分明)的(手指|双手)",
        r"(唇角|薄唇|嘴角)(微微)?勾(起|出).{0,4}(弧度|弧线|笑意)",
        # Artificial rhythm markers
        r"——$",  # dash at end of line for cheap suspense
        r"^……$",  # ellipsis as entire line
        # Transition padding
        r"(故事|一切|这一切)(才刚刚|远没有|并没有)(开始|结束)",
        r"(殊不知|却不知|他不知道的是)",
    ]

    total_new_cliches = 0
    for regex in new_cliche_patterns:
        total_new_cliches += len(re.findall(regex, text, re.MULTILINE))

    # Strict scoring: any new AI patterns are penalized
    if total_new_cliches == 0:
        return 1.0
    elif total_new_cliches <= 1:
        return 0.7
    elif total_new_cliches <= 3:
        return 0.4
    elif total_new_cliches <= 5:
        return 0.2
    else:
        return 0.0


def _check_dialogue_naturalization(text: str) -> float:
    """HIDDEN: Check dialogue quality — natural speech vs literary/performative speech.

    The writing guide says: "人物说话不要每句都像在做演讲，允许打断、吞吐、说半句"
    Weak models produce formal, complete, declarative dialogue.
    Strong models produce choppy, interrupted, colloquial dialogue.
    """
    # Extract all dialogue
    dialogues = re.findall(r'[""](.*?)["""]', text)
    if not dialogues:
        return 0.3  # No dialogue at all is a problem

    total_dialogues = len(dialogues)
    if total_dialogues < 3:
        return 0.3

    # Negative indicators: performative/literary speech
    performative_count = 0
    for d in dialogues:
        # Long unbroken speech (>40 chars without pause)
        if len(d) > 60 and "，" not in d[:30]:
            performative_count += 1
        # Rhetorical declarations
        if re.search(r"(岂不是|难道|何惧|何足挂齿|焉能|岂能|定要)", d):
            performative_count += 1
        # Overly neat phrasing with balanced structure
        if re.search(r".{4,8}，.{4,8}[。！]$", d) and len(d) < 25:
            performative_count += 1

    # Positive indicators: natural speech
    natural_count = 0
    for d in dialogues:
        # Short utterances (< 15 chars) - people often speak briefly
        if len(d) < 15:
            natural_count += 1
        # Contains hesitation, interruption
        if re.search(r"(……|——|、|这个|那个|嗯|哦|啊|吧|嘛|呢$)", d):
            natural_count += 1
        # Incomplete sentences (no period/exclamation at natural end)
        if not d.endswith(("。", "！", "？")) and len(d) > 5:
            natural_count += 1

    performative_ratio = performative_count / total_dialogues
    natural_ratio = natural_count / total_dialogues

    # Score based on balance
    score = 0.0
    # Reward natural markers
    if natural_ratio >= 0.5:
        score += 0.5
    elif natural_ratio >= 0.3:
        score += 0.3
    elif natural_ratio >= 0.1:
        score += 0.15

    # Penalize performative markers
    if performative_ratio <= 0.1:
        score += 0.5
    elif performative_ratio <= 0.25:
        score += 0.3
    elif performative_ratio <= 0.4:
        score += 0.15

    return min(score, 1.0)


def _check_sensory_specificity(text: str) -> float:
    """HIDDEN: Check for scene-specific sensory details vs generic descriptions.

    The writing guide demands: "加入只有这个场景才有的具体细节（声音、气味、触感），不用万能公式"
    Chapter 41 exemplifies this: "药霾", "棉絮里稻草的窸窣声", "粥稀得能照见人影"

    Weak models use generic sensory words. Strong models invent details
    specific to this street-confrontation scene.
    """
    # Generic sensory filler (low value)
    generic_sensory = [
        r"(冰冷|温暖|灼热|刺骨)的(风|空气|气息)",
        r"(刺眼|耀眼|明亮|昏暗)的(阳光|光芒|光线)",
        r"(沉闷|清脆|尖锐)的(声音|响声)",
        r"(浓郁|淡淡)的(血腥味|杀气|香味|气息)",
    ]

    # Specific sensory markers (high value) - concrete, unique details
    specific_sensory = [
        # Concrete sounds unique to this scene
        r"(蹄铁|马蹄|铁蹄).{0,6}(石板|砖|地面|青石)",
        r"(甲片|铁甲|锁甲).{0,6}(碰撞|摩擦|哗|响)",
        r"(吞咽|咽).{0,4}(口水|唾沫)",
        # Concrete tactile/physical details
        r"(汗|水).{0,4}(顺着|沿着|从).{2,8}(滑|流|淌|滴)",
        r"(握|攥|捏).{0,4}(刀柄|剑柄|缰绳|拳)",
        # Specific visual details (not generic "light" or "dark")
        r"(青石|石板|砖缝|瓦楞|门板|招牌|幌子)",
        r"(灰|尘|土).{0,4}(扬|飞|落|沾)",
        # Street-specific atmosphere
        r"(店铺|摊|铺|坊|巷|门|窗).{0,6}(关|闭|开|掩|紧|锁)",
        r"(马|骡|驴).{0,6}(嘶|喘|蹄|鼻息|打响鼻)",
    ]

    generic_count = 0
    for regex in generic_sensory:
        generic_count += len(re.findall(regex, text))

    specific_count = 0
    for regex in specific_sensory:
        specific_count += len(re.findall(regex, text))

    # Scoring: reward specific, penalize generic-only
    # Require MANY specific details and few generic ones for top scores
    if specific_count >= 8 and generic_count <= 1:
        return 1.0
    elif specific_count >= 6 and generic_count <= 2:
        return 0.8
    elif specific_count >= 5:
        return 0.65
    elif specific_count >= 4:
        return 0.5
    elif specific_count >= 3:
        return 0.4
    elif specific_count >= 2:
        return 0.3
    elif specific_count >= 1:
        return 0.2
    else:
        return 0.05


def _check_style_consistency_with_ch41(text: str, ws: Path) -> float:
    """HIDDEN: Check if rewrite matches chapter 41's terse, grounded style.

    Chapter 41 characteristics:
    - Average sentence length ~15-20 chars (short, punchy)
    - High ratio of dialogue to narration
    - Minimal adjectives per sentence (usually 0-1)
    - Concrete nouns over abstract ones
    - Paragraphs often 1-3 sentences
    """
    # Analyze rewrite's sentence characteristics
    # Split on Chinese sentence endings
    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]

    if not sentences:
        return 0.0

    # 1. Average sentence length (ch41 target: 12-20 chars, very terse)
    avg_sent_len = sum(len(s) for s in sentences) / len(sentences)

    sent_len_score = 0.0
    if 12 <= avg_sent_len <= 20:
        sent_len_score = 1.0
    elif 20 < avg_sent_len <= 25:
        sent_len_score = 0.6
    elif 25 < avg_sent_len <= 30:
        sent_len_score = 0.3
    elif avg_sent_len > 30:
        sent_len_score = 0.0
    elif avg_sent_len < 12:
        sent_len_score = 0.5

    # 2. Long sentence ratio (sentences > 50 chars should be rare, < 15%)
    long_sents = sum(1 for s in sentences if len(s) > 50)
    long_ratio = long_sents / len(sentences)

    long_score = 0.0
    if long_ratio <= 0.05:
        long_score = 1.0
    elif long_ratio <= 0.10:
        long_score = 0.7
    elif long_ratio <= 0.20:
        long_score = 0.4
    elif long_ratio <= 0.30:
        long_score = 0.2
    else:
        long_score = 0.0

    # 3. Adjective density (count modifier patterns per sentence)
    adj_patterns = [
        r"[^\s，。]{2,4}的",  # XX的 pattern
    ]
    total_adjs = 0
    for regex in adj_patterns:
        total_adjs += len(re.findall(regex, text))

    adj_per_sent = total_adjs / len(sentences) if sentences else 0
    # Ch41 has ~0.5-1.0 adj per sentence
    adj_score = 0.0
    if adj_per_sent <= 1.0:
        adj_score = 1.0
    elif adj_per_sent <= 1.5:
        adj_score = 0.6
    elif adj_per_sent <= 2.0:
        adj_score = 0.3
    else:
        adj_score = 0.1

    # 4. Comma density: ch41 averages ~0.8 commas per sentence (simple structure)
    # AI-style writing packs 2-3 commas per sentence (multi-clause, padded)
    comma_count = text.count("，")
    comma_per_sent = comma_count / len(sentences) if sentences else 0

    comma_score = 0.0
    if comma_per_sent <= 1.0:
        comma_score = 1.0
    elif comma_per_sent <= 1.3:
        comma_score = 0.7
    elif comma_per_sent <= 1.6:
        comma_score = 0.4
    elif comma_per_sent <= 2.0:
        comma_score = 0.2
    else:
        comma_score = 0.0

    return round((sent_len_score * 0.25 + long_score * 0.30 + adj_score * 0.20 + comma_score * 0.25), 4)


def _check_show_dont_tell(text: str) -> float:
    """HIDDEN: Measure ratio of 'shown' emotion vs 'told' emotion.

    The writing guide says: "用动作和细节暗示情绪，不要直接告诉读者角色在想什么"
    Chapter 41 does this perfectly: "苏铭端着碗没动，眼睛眯了起来" (shows wariness)
    instead of "苏铭心中警觉" (tells it).

    Weak models still label emotions explicitly even during humanization rewrites.
    Strong models replace emotion labels with behavioral cues.
    """
    # Telling patterns: explicit emotion labels
    telling_patterns = [
        r"(心中|心里|内心)(满是|充满|涌起|升起|浮现|泛起|闪过).{1,8}",
        r"(眼中|眼里|目光中)(满是|充满|流露|透着|带着).{1,8}",
        r"(脸上|面上)(满是|浮现|流露|露出).{1,8}(之色|之意|表情|神色)",
        r"(感到|感觉到|心想|暗想|心道).{2,15}",
        r"(难以抑制|不可抑制|无法抑制|按捺不住)的.{2,6}",
        r"(一股|一阵).{1,4}(感|意|情绪|怒火|杀意|悲伤|喜悦)(涌上|袭来|充斥|弥漫)",
        r"他(知道|明白|清楚|意识到).{0,4}(自己|心中|内心).{2,10}",
        r"(语气|声音|口吻)中(满是|充满|带着|透着|流露着).{2,8}",
    ]

    # Showing patterns: emotion through action/physical detail
    showing_patterns = [
        r"(攥|握|捏|掐|抠).*?(指节|手指|拳|指甲|手心).{0,6}(白|红|青|颤|紧)",
        r"(咽|吞|抿|咬).{0,4}(口水|唾沫|嘴唇|牙关|舌头)",
        r"(喉结|喉咙|嗓子).{0,4}(动|滚|哽|干)",
        r"(脚步|步子|步伐).{0,6}(停|顿|慢|快|重|轻|乱)",
        r"(没.{0,2}(说话|吭声|开口|接话|回答))",
        r"(转身|别过|侧|偏).{0,4}(脸|头|身|目光)",
        r"(肩|背|腰|脊).{0,6}(僵|直|弓|塌|绷|松)",
        r"(呼吸|气息).{0,4}(急|重|浅|深|稳|乱|屏|停)",
    ]

    telling_count = 0
    for regex in telling_patterns:
        telling_count += len(re.findall(regex, text))

    showing_count = 0
    for regex in showing_patterns:
        showing_count += len(re.findall(regex, text))

    total = telling_count + showing_count
    if total == 0:
        return 0.3  # No emotional content at all is odd for this scene

    # Score based on show/tell ratio
    show_ratio = showing_count / total if total > 0 else 0
    telling_density = telling_count / (len(text) / 100)  # per 100 chars

    # Strict: even 2-3 telling instances in ~1500 chars is too many
    if telling_count == 0 and showing_count >= 4:
        return 1.0
    elif telling_count <= 1 and showing_count >= 3:
        return 0.8
    elif telling_count <= 2 and show_ratio >= 0.6:
        return 0.6
    elif telling_count <= 3 and show_ratio >= 0.4:
        return 0.4
    elif telling_count <= 5:
        return 0.25
    else:
        return 0.1


def _check_verb_precision(text: str) -> float:
    """HIDDEN: Check for precise, specific verbs vs generic catch-all verbs.

    Chapter 41 uses: "呛了一嘴", "蹲在井沿旁边", "端着碗看了一眼", "别回腰后"
    These are precise physical actions with specific targets/manner.

    Weak models default to: 说道, 看着, 走了过来, 转过身来, 抬起头
    These are generic, carry no sensory weight.

    Strong rewrites pick verbs that encode HOW something was done.
    """
    # Generic verbs (weak indicator) — each occurrence counted
    generic_verb_patterns = [
        r"(说道|开口道|低声道|厉声道|冷声道|沉声道|淡淡道)",
        r"(看着|望着|盯着|注视着|凝视着)",
        r"(走了过来|走了过去|走上前|大步走|缓缓走)",
        r"(转过身来|转过头|抬起头|低下头|微微点头)",
        r"(伸出手|抬起手|放下手|挥了挥手)",
        r"(站在那里|站在.{2,4}前|立在)",
    ]

    # Precise verbs (strong indicator) — specific manner/object encoded in verb
    precise_verb_patterns = [
        # Verbs with encoded manner (how)
        r"(蹲|趴|倚|靠|歪|窝|缩|蜷|踞)",
        r"(攥|捻|拈|搓|掖|掀|别|塞|拽|扯|撕|掰|捞)",
        r"(啐|啧|嗤|哼|嘟囔|嘀咕|呸)",
        r"(踱|蹭|挪|窜|蹿|溜|闪|晃|颠)",
        r"(劈|剁|砍|戳|捅|扎|刺|削|挑|撩|横|挡|格|架)",
        # Verbs with specific target making action concrete
        r"(摁|按|扣|抠|掐|捏|拧).{0,4}(住|着|紧|死)",
        r"(勒|拽|扯|拉).{0,4}(缰绳|马缰|袖子|衣角|腰带)",
        r"(灌|呛|噎|咽|吐|啜|抿|含).{0,4}(酒|水|茶|血|气|药)",
    ]

    generic_count = 0
    for regex in generic_verb_patterns:
        generic_count += len(re.findall(regex, text))

    precise_count = 0
    for regex in precise_verb_patterns:
        precise_count += len(re.findall(regex, text))

    total_verbs = generic_count + precise_count
    if total_verbs == 0:
        return 0.2

    precise_ratio = precise_count / total_verbs
    # Also penalize high absolute count of generic verbs
    # In ~1500 chars of text, more than 8 generic verbs is formulaic
    generic_density = generic_count / max(len(re.sub(r"\s+", "", text)) / 200, 1)

    if precise_ratio >= 0.7 and generic_density <= 1.0:
        return 1.0
    elif precise_ratio >= 0.55 and generic_density <= 1.5:
        return 0.75
    elif precise_ratio >= 0.4 and generic_density <= 2.0:
        return 0.55
    elif precise_ratio >= 0.3:
        return 0.35
    elif precise_ratio >= 0.2:
        return 0.2
    else:
        return 0.05


def _check_single_beat_pacing(text: str) -> float:
    """HIDDEN: Check for single-beat paragraphs used as pacing/rhythm tools.

    Chapter 41's signature technique: short standalone paragraphs that create
    rhythm and emphasis through isolation:
      - '苏铭。' (one word, standalone)
      - '"在。"' (one-word reply, own paragraph)
      - '"行。"苏铭说完就上了楼。' (action-beat paragraph)

    Weak models write uniformly-sized paragraphs (3-5 sentences each).
    Strong models vary: some paragraphs are 1 sentence, some are 4-5, creating
    a heartbeat-like rhythm that makes confrontation scenes tense.

    This measures: presence of short standalone paragraphs (<=20 chars)
    AND alternation between short and long paragraphs.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    if len(paragraphs) < 5:
        return 0.2

    # Count single-beat paragraphs (<=20 chars — a single short sentence or word)
    short_paras = [p for p in paragraphs if len(p) <= 20]
    short_count = len(short_paras)

    # Count transitions: short->long or long->short
    transitions = 0
    for i in range(1, len(paragraphs)):
        prev_short = len(paragraphs[i - 1]) <= 30
        curr_short = len(paragraphs[i]) <= 30
        if prev_short != curr_short:
            transitions += 1

    transition_ratio = transitions / (len(paragraphs) - 1)
    short_ratio = short_count / len(paragraphs)

    # Target: ~25-40% of paragraphs are single-beat, with frequent transitions
    # Ch41 has roughly 35% short paras and 60%+ transitions
    # Weak models rarely achieve >20% single-beat because they write uniform 3-5 sentence paragraphs
    score = 0.0

    # Short paragraph presence (stricter: need genuinely short paras <=20 chars)
    if 0.25 <= short_ratio <= 0.45:
        score += 0.5
    elif 0.20 <= short_ratio < 0.25:
        score += 0.3
    elif 0.15 <= short_ratio < 0.20:
        score += 0.15
    elif short_ratio > 0.45:
        score += 0.25  # too many shorts is choppy
    else:
        score += 0.0

    # Transition frequency (rhythm alternation)
    if transition_ratio >= 0.60:
        score += 0.5
    elif transition_ratio >= 0.50:
        score += 0.35
    elif transition_ratio >= 0.40:
        score += 0.2
    elif transition_ratio >= 0.30:
        score += 0.1
    else:
        score += 0.0

    return min(score, 1.0)


def grade_workspace(ws: Path) -> dict:
    """Grade the novel chapter humanization task."""
    text = _find_chapter(ws)

    if not text:
        return {
            "overall_score": 0.0,
            "components": {"no_output": 1.0},
            "error": "No chapter_042.md found",
        }

    if not _check_is_modified(text):
        return {
            "overall_score": 0.0,
            "components": {"unchanged": 1.0},
            "error": "Chapter was not modified from original",
        }

    components = {}

    # 1. AI pattern reduction (weight: 0.15, reduced from 0.30)
    _orig_patterns_total = 19  # pre-computed from original
    rew_patterns = _count_ai_patterns(text)
    rew_total = sum(rew_patterns.values())

    if _orig_patterns_total > 0:
        reduction_ratio = 1.0 - (rew_total / _orig_patterns_total)
        if reduction_ratio >= 0.9:
            components["ai_pattern_reduction"] = 1.0
        elif reduction_ratio >= 0.8:
            components["ai_pattern_reduction"] = 0.8
        elif reduction_ratio >= 0.6:
            components["ai_pattern_reduction"] = 0.6
        elif reduction_ratio >= 0.4:
            components["ai_pattern_reduction"] = 0.35
        elif reduction_ratio >= 0.2:
            components["ai_pattern_reduction"] = 0.2
        else:
            components["ai_pattern_reduction"] = 0.05
    else:
        components["ai_pattern_reduction"] = 0.5

    # 2. Plot coherence preserved (weight: 0.15, reduced from 0.25)
    components["plot_preserved"] = _check_plot_preserved(text)

    # 3. Substantial rewrite (weight: 0.10, reduced from 0.20)
    components["substantial_rewrite"] = _check_substantial_rewrite(text)

    # 4. Length control (weight: 0.10, reduced from 0.15)
    components["length_control"] = _check_length_control(text)

    # 5. Structural variety (weight: 0.05, reduced from 0.10)
    components["structural_variety"] = _check_structural_variety(text)

    # --- HIDDEN CHECKS (harder, differentiate strong from weak) ---

    # 6. New AI pattern introduction (weight: 0.16)
    # Models often substitute old cliches with new ones
    components["no_new_ai_patterns"] = _check_new_ai_patterns(text)

    # 7. Dialogue naturalization (weight: 0.12)
    # Natural vs performative speech quality
    components["dialogue_quality"] = _check_dialogue_naturalization(text)

    # 8. Sensory specificity (weight: 0.10)
    # Scene-specific concrete details vs generic filler
    components["sensory_specificity"] = _check_sensory_specificity(text)

    # 9. Style consistency with chapter 41 (weight: 0.07)
    # Terse, grounded sentence structure
    components["style_consistency"] = _check_style_consistency_with_ch41(text, ws)

    # 10. Show-don't-tell ratio (weight: 0.14)
    # Emotion through action vs explicit labeling
    components["show_dont_tell"] = _check_show_dont_tell(text)

    # 11. Verb precision (weight: 0.12)
    # Specific action verbs vs generic catch-all verbs
    components["verb_precision"] = _check_verb_precision(text)

    # 12. Single-beat pacing (weight: 0.10)
    # Short standalone paragraphs for rhythm, like chapter 41
    components["single_beat_pacing"] = _check_single_beat_pacing(text)

    weights = {
        "ai_pattern_reduction": 0.07,
        "plot_preserved": 0.08,
        "substantial_rewrite": 0.05,
        "length_control": 0.04,
        "structural_variety": 0.03,
        "no_new_ai_patterns": 0.15,
        "dialogue_quality": 0.11,
        "sensory_specificity": 0.09,
        "style_consistency": 0.06,
        "show_dont_tell": 0.13,
        "verb_precision": 0.10,
        "single_beat_pacing": 0.09,
    }

    # NOTE on weight distribution:
    # Easy checks (most models pass): 0.27 total
    # Hard hidden checks (differentiate strong from weak): 0.73 total

    # Verify weights sum to ~1.0
    assert abs(sum(weights.values()) - 1.0) < 0.02, f"Weights sum to {sum(weights.values())}"

    overall = sum(weights.get(k, 0) * v for k, v in components.items() if k in weights)

    # Apply a ceiling: even a perfect rewrite rarely scores above 0.85
    # This accounts for the inherent subjectivity of creative writing
    overall = min(overall, 0.85)

    return {
        "overall_score": round(overall, 4),
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "ai_patterns_remaining": rew_total,
    }


def main():
    ws = Path("/workspace/fixtures")
    if not (ws / "novel").exists():
        ws = Path("/workspace")
    print(json.dumps(grade_workspace(ws), ensure_ascii=False))


if __name__ == "__main__":
    main()
