"""T178_zh_google_io_2026_wechat_deepdive_writing grader — end-to-end content
creation with web_search + web_fetch, scored against a hidden reference article.

Scoring design (mirrors T153 hard-task canonical pattern, extended with
reference-article-driven judging like M005 does for VLM):
  - Reference article loaded from local_grader_files (NOT visible to the
    evaluated model — only to this grader and the LLM judge).
  - Tool usage is a multiplicative penalty gate (must do real web research).
  - Five LLM judge sub-rubrics, weighted to match scoring_components in
    task.yaml. The reference article is spliced into voice/structure/closing
    rubrics so the judge can directly compare candidate vs. reference style.
  - Communication scored via compute_communication_substance().
"""

from __future__ import annotations

import base64
from typing import Any

from claw_eval.graders.base import AbstractGrader
from claw_eval.models.task import TaskDefinition
from claw_eval.models.trace import DimensionScores, MediaLoad, ToolDispatch, TraceMessage


REFERENCE_ARTICLE_KEY = "local_file:fixtures/reference_article.md"


class WechatViralArticleGrader(AbstractGrader):
    """Grader for T168zh: WeChat long-form recap of Google I/O 2026.

    Reference-article-augmented variant of the T153 canonical structure:
      1. Load hidden reference article from env_snapshot.
      2. Safety gate (n/a here, set 1.0).
      3. Tool penalty gate based on search effort.
      4. Five independent LLM judge calls, one per scoring component.
         Voice/structure/closing rubrics include the reference article verbatim
         so the judge can compare candidate ↔ reference directly.
      5. Communication scored via compute_communication_substance().
    """

    _COVERAGE_RUBRIC = """\
评估文章对 Google I/O 2026 keynote 的信息覆盖广度与事实准确性（0.0-1.0）。

## 七大议程模块（至少覆盖 6/7）
1. **AI 模型**: Gemini 3.5 Flash（跑分 vs 3.1 Pro）、Gemini Omni Flash
2. **Gemini 产品**: App Neural Expressive、Ask Maps、Ask YouTube、Docs Live、
   Gemini Live、Daily Brief、NotebookLM
3. **Agent 系统**: Antigravity 2.0、Gemini Spark、Android Halo
4. **视觉生成**: Google Pics、Stitch、Google Flow、SynthID
5. **Google 搜索**: AI Mode、Search Agents、生成式 UI、跨模态搜索框
6. **Agent 电商**: UCP、AP2、Universal Cart
7. **其他**: Android XR 眼镜、TPU 第 8 代、Gemini for Science、Weather Next、
   Code Mender

## 关键数据准确性
- Gemini 3.5 Flash 跑分（Terminal-Bench 76.2% vs 3.1 Pro 70.3%；
  GDPval-AA 1656 vs 1314 Elo）
- 定价（$100 / $200 Ultra plan；$1.50 / $9 per million token）
- 上市时间（Fall 2026 智能眼镜；今年夏天 Universal Cart）
- 合作伙伴（Gentle Monster、Warby Parker、三星 → 眼镜；
  Shopify/Etsy/Wayfair/Target/Walmart → UCP）
- 规模数据（1M TPU、10 亿 AI Mode MAU、近 200 国家、98 语言、
  1500 tokens/sec、93 subagents 演示）

## 编造红线（一票否决）
- 出现 "Gemini 4"、"Gemini 5"、"Pixel Glasses"、"Google Vision Pro" 等
  实际不存在的产品 → 立即扣 0.3+
- 将旧 I/O（2024/2025）发布张冠李戴 → 扣分
- 数据明显编造（如错误的跑分、错误的定价）→ 扣分

## 严格评分
- 0.9-1.0: 覆盖 ≥6/7 大块 + ≥15 子产品 + 关键数据 ≥6 个准确 + 无编造
- 0.7-0.8: 覆盖 4-5 大块 + 10-14 子产品 + 关键数据 3-5 个 + 无编造
- 0.4-0.6: 覆盖 2-3 大块 + 5-9 子产品 + 数据有 1-2 处错误
- 0.0-0.3: 覆盖严重不全或大量编造产品
"""

    _VOICE_RUBRIC_TEMPLATE = """\
评估文章调性是否对齐用户范文风格（0.0-1.0）。

## 范文（黄金标准 — 候选文章应在调性上贴近它）

下面是用户提供的真实爆款范文。**严格按这篇文章的调性作为对照**评分：

```
{reference_article}
```

## 必须从范文中识别并对齐的调性特征
1. **标题朴素直白**: 范文标题《帮大家总结了一下凌晨的 Google I/O 2026 开发者大会》。
   候选标题应同样朴素，绝对不能出现"震惊""炸了""卧槽""一夜变天""杀死 OpenAI"等标题党。
2. **单句成段 + 短句节奏**: 范文大量段落只有 1-2 句话。候选应有相似节奏。
3. **个人吐槽 / 口语化**（至少 5 处）：参考范文中
   "emmm"、"用起来其实有点拉"、"过于大冤种"、"我自己是真的有点期待了"、
   "我也确实相信"、"还蛮动容的" 等表达。
4. **该吐槽就吐槽**: 范文看到拉的产品就说拉（"用起来也不如 Seedance"），
   价格贵就吐槽（"过于大冤种"），候选应有类似真诚的批评。
5. **引用 keynote 英文原话**: 范文引用了 Hassabis 的 "foothills of the singularity"
   等。候选应至少 1 处英文金句引用。
6. **第一人称视角**: 范文大量 "我"、"我自己"、"我也"、"我熬"、"我整理"。

## 反模式（扣分）
- 通篇 Google 通稿翻译，毫无个人观察 → 扣 0.3
- 标题党词出现 → 每个扣 0.15
- 全程吹捧无吐槽 → 扣 0.2
- 过分堆 emoji 或华丽辞藻 → 扣 0.1

## 严格评分
- 0.9-1.0: 全部 6 个调性特征齐全，与范文调性高度一致
- 0.7-0.8: 5/6 个特征齐全，调性基本对齐
- 0.4-0.6: 3-4 个特征，调性部分对齐
- 0.0-0.3: 通稿式或标题党
"""

    _STRUCTURE_RUBRIC_TEMPLATE = """\
评估文章的结构组织与信息密度（0.0-1.0）。

## 范文（结构参照）

下面是用户提供的真实爆款范文，注意其结构组织方式：

```
{reference_article}
```

## 必须有的结构特征
1. **罗马数字大块**: 范文用「一. 二. 三. 四. 五. 六. 七.」分章节。
   候选应同样用罗马数字 5-7 个大块。
2. **阿拉伯数字子节**: 范文每大块下用「1. 2. 3.」罗列具体产品。
   候选至少 3 个大块应包含子节。
3. **短段落节奏**: 范文平均段落 ≤ 100 字，大量单句成段。
   候选应有相似节奏，不出现长段落墙。
4. **字数**: 3500-6000 字（中文字符数，范文约 5000 字）。
   - < 2500 字 → 信息密度严重不足，扣 0.3+
   - 2500-3499 → 略短，扣 0.1
   - 3500-6000 → 理想区间
   - > 6000 → 略长但可接受
5. **markdown 强调**: 范文使用引用块（>）强调金句、使用 ## 二级标题。
   候选应有相似 markdown 使用。

## 反模式
- 用 ## 平铺所有内容（不用罗马数字）→ 扣 0.1
- 长段落墙（单段 > 200 字）→ 扣 0.15
- 无任何 markdown 结构 → 扣 0.2

## 严格评分
- 0.9-1.0: 罗马+阿拉伯双层结构 + 短段落 + 3500-6000 字 + 适度 markdown
- 0.7-0.8: 结构齐全但段落偏长或字数边缘（2800-3499 / 6000-7000）
- 0.4-0.6: 结构部分缺失或字数显著不足（2000-2800）
- 0.0-0.3: 无结构或字数严重不足（< 2000）
"""

    _CLOSING_RUBRIC_TEMPLATE = """\
评估结尾的升华与互动设计（0.0-1.0）。

## 范文结尾原文（黄金标准）

```
{reference_closing}
```

## 必须模仿的三要素
1. **高管金句升华**: 范文引用 Demis Hassabis 的
   "When we look back at this time, I think we'll realize that we were
   standing in the foothills of the singularity"
   （"我们正站在奇点的山脚下"）作为升华。
   候选应引用同样的金句，或 Sundar Pichai 等高管的等价 keynote 金句。

2. **个人感慨**: 范文写 "我也确实相信这句话。AI，至少在现在看，它是人类智慧的
   放大器。也许，我们会开启一个，科学发现和进步的新黄金时代。也希望未来。
   我们能不断的，一起见证。" 这种有人情味的个人感想。

3. **朴素三连引导 + 暖结尾**: 范文写 "随手点个赞、在看、转发三连吧，如果想
   第一时间收到推送，也可以给我个星标⭐～谢谢你看我的文章，我们，下次再见。"
   候选应有类似朴素三连 + 星标 + 暖结尾。

## 反模式（重要！）
- 塞 A/B/C/D 投票选项 → 严重不符合范文风格，扣 0.4
- 留 2-3 个互动问题 / 留言钩子 → 不符合范文调性，扣 0.3
- 仅 "完" / "以上" 等冷淡结尾 → 扣 0.3
- 没有任何引导 → 扣 0.4

## 严格评分
- 0.9-1.0: 三要素齐全 + 金句与范文一致或等价水准 + 暖结尾
- 0.7-0.8: 三要素齐全但金句平淡或与范文风格不同
- 0.4-0.6: 仅 2/3 个要素
- 0.0-0.3: 缺失多个要素或塞了不符合调性的投票互动
"""

    _COMPLIANCE_RUBRIC = """\
评估内容合规性与真实性（0.0-1.0）。

## 平台合规
- 不出现违禁词：震惊体、绝对化承诺（"绝对能/一定会"）、暴利、政治敏感词
- 不诋毁竞品：可以客观吐槽产品体验，不能人身攻击或恶意贬低
  - ✅ "用起来其实有点拉，不如 Seedance"（客观体验对比）
  - ❌ "OpenAI 就是垃圾"（恶意贬低）
- 标题不过分标题党：见 voice rubric

## 内容真实性
- 数据交代出处：关键数字应注明 "Google 官方说"、"现场演示"、
  "keynote 上"、"官方公告"等
- 不编造产品：不能出现实际不存在的 "Gemini 4"、"Pixel Glasses"、
  "Google Vision Pro" 等
- 不编造合作：不能编造未发生的合作（如 "Google 收购 OpenAI"）
- 不编造价格 / 时间：定价和上市时间必须与实际公告一致

## 来源标注
- 文末可选地列出参考链接（blog.google / developers.googleblog 等），
  或在正文中显式提到信息来源
- 即便没有 URL，也应在关键数据处口头交代来源

## 严格评分
- 0.9-1.0: 全部合规 + 数据有源 + 无编造
- 0.7-0.8: 大体合规但 1-2 处来源未标注
- 0.4-0.6: 出现 1-2 个边缘违规（如 "炸了" 标题党词）或 1 处数据无源
- 0.0-0.3: 大量违禁词 / 诋毁竞品 / 编造产品或数据
"""

    # Canonical entities expected in the final article (for communication scoring)
    _KEY_ENTITIES = [
        # I. Models
        "Gemini 3.5 Flash", "Gemini Omni",
        # II. Gemini 产品
        "NotebookLM", "Ask Maps", "Docs Live",
        # III. Agent 系统
        "Antigravity", "Spark", "Halo",
        # IV. 视觉生成
        "Stitch", "SynthID",
        # V. 搜索
        "AI Mode",
        # VI. Agent 电商
        "Universal Cart",
        # VII. 其他
        "Android XR", "TPU",
        # Executives / partners
        "Hassabis", "Pichai",
        # Key partners
        "三星", "Warby Parker",
    ]

    def grade(
        self,
        messages: list[TraceMessage],
        dispatches: list[ToolDispatch],
        task: TaskDefinition,
        audit_data: dict[str, dict] | None = None,
        judge: Any | None = None,
        media_events: list[MediaLoad] | None = None,
        env_snapshot: dict | None = None,
    ) -> DimensionScores:
        scores = DimensionScores()

        # ------------------------------------------------------------------
        # Load hidden reference article from env_snapshot (CLI base64-encoded)
        # ------------------------------------------------------------------
        reference_article = self._load_reference_article(env_snapshot)

        # Build rubric strings with reference spliced in
        voice_rubric = self._VOICE_RUBRIC_TEMPLATE.format(
            reference_article=reference_article or "（范文文件未加载，按通用调性标准评分）"
        )
        structure_rubric = self._STRUCTURE_RUBRIC_TEMPLATE.format(
            reference_article=reference_article or "（范文文件未加载，按通用结构标准评分）"
        )
        closing_rubric = self._CLOSING_RUBRIC_TEMPLATE.format(
            reference_closing=self._extract_closing(reference_article)
            or "（范文文件未加载，按通用结尾标准评分）"
        )

        # ------------------------------------------------------------------
        # Safety: no safety-sensitive tools in this task
        # ------------------------------------------------------------------
        scores.safety = 1.0

        # ------------------------------------------------------------------
        # Tool penalty gate: did the agent actually do web research?
        # ------------------------------------------------------------------
        search_calls = [
            d for d in dispatches
            if d.tool_name == "web_search" and d.response_status < 400
        ]
        fetch_calls = [
            d for d in dispatches
            if d.tool_name == "web_fetch" and d.response_status < 400
        ]
        total_web_calls = len(search_calls) + len(fetch_calls)

        if total_web_calls < 5:
            tool_penalty = 0.4
        elif total_web_calls < 8:
            tool_penalty = 0.7
        else:
            tool_penalty = 1.0

        # ------------------------------------------------------------------
        # LLM judge scoring: 5 independent calls, one per scoring component
        # ------------------------------------------------------------------
        completion = 0.0
        if judge:
            conversation = self.format_conversation(messages)
            actions_summary = self.summarize_actions(audit_data)
            context = f"{conversation}\n\n--- 工具调用摘要 ---\n{actions_summary}"

            # D1. Info coverage (30%)
            try:
                result = judge.evaluate(
                    task.prompt.text, context, "", self._COVERAGE_RUBRIC)
                completion += 0.30 * result.score
                print(f"[grader] info_coverage_breadth: {result.score:.2f}")
            except Exception as e:
                print(f"[grader] info_coverage_breadth judge failed: {e}")

            # D2. Writing voice (25%) — uses reference article
            try:
                result = judge.evaluate(
                    task.prompt.text, context, "", voice_rubric)
                completion += 0.25 * result.score
                print(f"[grader] writing_voice_alignment: {result.score:.2f}")
            except Exception as e:
                print(f"[grader] writing_voice_alignment judge failed: {e}")

            # D3. Structure + density (20%) — uses reference article
            try:
                result = judge.evaluate(
                    task.prompt.text, context, "", structure_rubric)
                completion += 0.20 * result.score
                print(f"[grader] structure_and_density: {result.score:.2f}")
            except Exception as e:
                print(f"[grader] structure_and_density judge failed: {e}")

            # D4. Closing + engagement (10%) — uses reference article closing
            try:
                result = judge.evaluate(
                    task.prompt.text, context, "", closing_rubric)
                completion += 0.10 * result.score
                print(f"[grader] closing_and_engagement: {result.score:.2f}")
            except Exception as e:
                print(f"[grader] closing_and_engagement judge failed: {e}")

            # D5. Compliance + truthfulness (15%)
            try:
                result = judge.evaluate(
                    task.prompt.text, context, "", self._COMPLIANCE_RUBRIC)
                completion += 0.15 * result.score
                print(f"[grader] compliance_and_truthfulness: {result.score:.2f}")
            except Exception as e:
                print(f"[grader] compliance_and_truthfulness judge failed: {e}")

        completion *= tool_penalty
        scores.completion = min(round(completion, 4), 1.0)

        # ------------------------------------------------------------------
        # Robustness (standard base-class scoring)
        # ------------------------------------------------------------------
        scores.robustness = self.compute_robustness(dispatches)

        # ------------------------------------------------------------------
        # Communication: substance + format (using base helper)
        # ------------------------------------------------------------------
        all_text = self._get_all_assistant_text(messages)

        format_indicators = [
            "# ", "**", "> ",
            "一.", "二.", "三.",
            "1.", "2.",
        ]
        format_hits = sum(1 for ind in format_indicators if ind in all_text)
        format_score = min(format_hits / 5.0, 1.0)

        scores.communication = self.compute_communication_substance(
            all_text, self._KEY_ENTITIES, format_score
        )

        # ------------------------------------------------------------------
        # Efficiency
        # ------------------------------------------------------------------
        scores.efficiency_turns = len(
            [m for m in messages if m.message.role == "assistant"]
        )

        return scores

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _load_reference_article(env_snapshot: dict | None) -> str:
        """Decode the reference article from env_snapshot["local_file:..."].

        The CLI base64-encodes local_grader_files contents at grade time
        (see claw_eval/cli.py:403-417). Returns empty string if unavailable.
        """
        if not env_snapshot:
            return ""
        entry = env_snapshot.get(REFERENCE_ARTICLE_KEY)
        if not entry or not isinstance(entry, dict):
            return ""
        if "error" in entry:
            print(f"[grader] reference article load error: {entry['error']}")
            return ""
        encoding = entry.get("encoding")
        content = entry.get("content", "")
        if encoding == "base64" and content:
            try:
                return base64.b64decode(content).decode("utf-8")
            except Exception as e:
                print(f"[grader] reference article decode error: {e}")
                return ""
        return ""

    @staticmethod
    def _extract_closing(article: str) -> str:
        """Return the '写在最后' / closing section of the article (or empty)."""
        if not article:
            return ""
        # Try multiple section markers
        for marker in ["## 写在最后", "## 结语", "## 最后", "# 写在最后"]:
            idx = article.find(marker)
            if idx >= 0:
                return article[idx:]
        # Fall back: last 800 chars
        return article[-800:] if len(article) > 800 else article
