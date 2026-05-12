#!/usr/bin/env python3
"""
四平台选题生成器

把 fetch_hot_topics.py 输出的热点 JSON，转换为公众号/小红书/微信视频号/抖音四种平台表达。

定位：
- 不调用大模型，使用规则模板生成可编辑的一稿。
- 适合作为 wechat-topic-radar 的结构化中间产物。
- 如需要更高级标题/脚本，可把本脚本输出交给上层 LLM 精修。
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PLATFORMS = ["wechat_article", "xhs", "wechat_video", "douyin"]
PLATFORM_LABELS = {
    "wechat_article": "公众号",
    "xhs": "小红书",
    "wechat_video": "微信视频号",
    "douyin": "抖音",
}

PLATFORM_PRIORITY_BONUS = {
    "wechat_article": 8,
    "wechat_video": 5,
    "xhs": 3,
    "douyin": 0,
}

STRONG_ACCOUNT_KEYWORDS = [
    "AI出海", "出海", "跨境", "海外获客", "SEO", "内容增长", "独立站", "SaaS",
    "AI编程", "编程", "代码", "Claude Code", "Codex", "Cursor", "Trae",
    "Agent", "智能体", "workflow", "工作流", "自动化", "GitHub",
    "新模型", "大模型", "新工具", "开源", "API", "多模态", "语音大模型",
    "OpenAI", "Anthropic", "Claude", "DeepSeek", "Gemini", "Google", "Meta", "xAI",
    "MiniMax", "智谱", "月之暗面", "阶跃星辰", "阿里", "腾讯", "百度", "字节", "蚂蚁",
]

WEAK_OR_RISK_KEYWORDS = [
    "明星", "演唱会", "跑男", "马嘉祺", "王菲", "世界杯", "国乒", "榴莲", "皮皮虾",
    "怀孕", "男友", "离婚", "彩票", "天气", "调休",
]

VETO_PATTERNS = [
    r"马斯克官宣xAI解散",
]

AI_KEYWORDS = [
    "AI", "人工智能", "大模型", "智能体", "Agent", "LLM", "GPT", "OpenAI",
    "Claude", "Gemini", "DeepSeek", "Anthropic", "xAI", "英伟达", "NVIDIA",
    "黄仁勋", "芯片", "算力", "机器人", "具身", "自动驾驶", "编程", "代码",
    "Cursor", "Trae", "Codex", "Figma", "多模态", "识图", "开源", "模型",
]

SOURCE_WEIGHTS = {
    "tikhub": 8,
    "rnote": 8,
    "juhe": 7,
    "alapi": 6,
    "newsnow": 5,
    "direct": 4,
}

PLATFORM_BASE = {
    "wechat_article": 74,
    "xhs": 72,
    "wechat_video": 72,
    "douyin": 72,
}


def now_date_cn() -> str:
    return datetime.now().strftime("%Y年%m月%d日")


def slug_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def as_list(data: Any) -> List[Dict[str, Any]]:
    """兼容单平台/多平台 fetch 输出。"""
    topics: List[Dict[str, Any]] = []
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        for result in data["results"]:
            for t in result.get("topics", []) or []:
                if isinstance(t, dict):
                    merged = dict(t)
                    merged.setdefault("platform", result.get("platform"))
                    merged.setdefault("source", result.get("source"))
                    topics.append(merged)
    elif isinstance(data, dict) and isinstance(data.get("topics"), list):
        for t in data.get("topics", []) or []:
            if isinstance(t, dict):
                merged = dict(t)
                merged.setdefault("platform", data.get("platform"))
                merged.setdefault("source", data.get("source"))
                topics.append(merged)
    elif isinstance(data, list):
        topics = [t for t in data if isinstance(t, dict)]
    return topics


def dedupe_topics(topics: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for t in topics:
        title = (t.get("title") or "").strip()
        if not title:
            continue
        key = re.sub(r"\s+", "", title.lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def keyword_hits(title: str) -> List[str]:
    return [k for k in AI_KEYWORDS if re.search(re.escape(k), title, re.I)]



def account_keyword_hits(title: str) -> List[str]:
    return [k for k in STRONG_ACCOUNT_KEYWORDS if re.search(re.escape(k), title, re.I)]


def weak_or_risk_hits(title: str) -> List[str]:
    return [k for k in WEAK_OR_RISK_KEYWORDS if re.search(re.escape(k), title, re.I)]


def has_veto_risk(title: str) -> bool:
    return any(re.search(p, title, re.I) for p in VETO_PATTERNS)


def topic_recommendation(score: int, title: str) -> str:
    if has_veto_risk(title):
        return "需核验"
    if score >= 100:
        return "优先制作"
    if score >= 85:
        return "可进入内容池"
    if score >= 70:
        return "备选观察"
    return "不建议"


def opportunity_reason(topic: Dict[str, Any], platform: str) -> str:
    title = topic.get("title", "")
    hits = account_keyword_hits(title)
    risks = weak_or_risk_hits(title)
    reasons = []
    if hits:
        reasons.append("匹配主线：" + "、".join(hits[:3]))
    if platform == "wechat_article":
        reasons.append("适合做判断+证据+边界+落地建议")
    elif platform == "wechat_video":
        reasons.append("适合转成短观点口播")
    elif platform == "xhs":
        reasons.append("适合拆成清单/步骤/避坑卡片")
    elif platform == "douyin":
        reasons.append("适合测试短视频钩子")
    if risks:
        reasons.append("弱相关/风险词：" + "、".join(risks[:2]))
    if has_veto_risk(title):
        reasons.append("事实需核验，避免直接采用耸动标题")
    return "；".join(reasons)


def topic_score(topic: Dict[str, Any], target_platform: str) -> int:
    """也船长AI专属评分。

    分数含义：不是泛热度，而是“这个账号是否值得做”。
    核心偏好：AI出海、AI编程、Agent工作流、大厂生态、新工具/新模型、可落地。
    """
    title = topic.get("title", "")
    source = topic.get("source", "")
    platform = topic.get("platform", "")
    score = 48

    # 平台优先级：公众号文章 > 视频号 > 小红书 > 抖音
    score += PLATFORM_PRIORITY_BONUS.get(target_platform, 0)

    # 账号主线相关性，比泛 AI 关键词更重要
    strong_hits = account_keyword_hits(title)
    ai_hits = keyword_hits(title)
    score += min(len(strong_hits) * 7, 28)
    score += min(len(ai_hits) * 2, 10)

    # 来源权重
    score += SOURCE_WEIGHTS.get(source, 3)

    # 排名权重，避免热榜靠后但强相关的题被压死
    try:
        rank = int(topic.get("rank") or 99)
    except Exception:
        rank = 99
    if rank <= 3:
        score += 7
    elif rank <= 10:
        score += 4
    elif rank <= 20:
        score += 2

    # 也船长AI的“可落地/可判断”偏好
    if re.search(r"工具|教程|指南|清单|实践|上手|配置|命令|Hooks|工作流|Agent|开源|GitHub|API|SDK|自动化|实战", title, re.I):
        score += 10
    if re.search(r"出海|跨境|SEO|增长|获客|独立站|SaaS|内容生产|广告素材", title, re.I):
        score += 14
    if re.search(r"发布|开放|上线|价格|能力|模型|大厂|生态|趋势|安全|风险|协议|算力", title, re.I):
        score += 6

    # 平台形态适配
    if target_platform == "wechat_article" and re.search(r"发布|开放|时代|趋势|安全|架构|深度|实践|分析|协议|生态|模型|大厂", title, re.I):
        score += 7
    if target_platform == "wechat_video" and re.search(r"为什么|怎么|意味着|替代|改变|风险|问题|差距|火了|来了|识别", title, re.I):
        score += 6
    if target_platform == "xhs" and re.search(r"工具|教程|指南|清单|技巧|方法|上手|避坑|效率|命令|配置", title, re.I):
        score += 8
    if target_platform == "douyin" and re.search(r"为什么|问题|差距|火了|来了|改变|风险|替代", title, re.I):
        score += 5

    # 弱相关/娱乐社会热点降权：即使带 AI 词，也不一定适合账号
    weak_hits = weak_or_risk_hits(title)
    score -= min(len(weak_hits) * 10, 25)

    # 事实风险/耸动标题降权
    if has_veto_risk(title):
        score -= 22
    if re.search(r"官宣|解散|全部|彻底|疯了|炸裂|内幕|爆料", title, re.I):
        score -= 6

    # 没有账号主线命中，只是泛 AI，降低期待
    if not strong_hits and ai_hits:
        score -= 5
    if not strong_hits and not ai_hits:
        score -= 18

    return max(0, min(score, 120))


def clean_topic(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"[，。！？]+$", "", title)
    return title


def short_subject(title: str) -> str:
    title = clean_topic(title)
    # 去除平台热榜常见问句尾巴，便于标题改写
    title = re.sub(r"，?这.*$", "", title)
    title = re.sub(r"，?有哪些.*$", "", title)
    title = re.sub(r"，?你怎么看.*$", "", title)
    return title[:42]


def risk_tip(title: str) -> str:
    if re.search(r"安全|漏洞|攻击|风险|投毒|账号", title, re.I):
        return "涉及安全风险时避免制造恐慌，区分已验证事实、推测和个人建议。"
    if re.search(r"赚钱|副业|变现|投资", title, re.I):
        return "避免收益承诺，补充成本、门槛和失败风险。"
    return "避免绝对化表达，注明信息来自公开热点/公开报道，关键事实需二次核验。"


def tags_for(title: str, platform: str) -> str:
    base = []
    if re.search(r"DeepSeek", title, re.I):
        base += ["DeepSeek", "AI工具"]
    if re.search(r"Claude|Codex|Cursor|Trae|编程|代码|Agent|智能体", title, re.I):
        base += ["AI编程", "智能体", "效率工具"]
    if re.search(r"小红书|内容|选题|爆款", title, re.I):
        base += ["小红书运营", "内容创作", "选题"]
    if re.search(r"安全|漏洞|投毒|账号", title, re.I):
        base += ["网络安全", "AI安全", "避坑"]
    if not base:
        base = ["AI", "科技趋势", "效率提升"]
    if platform == "xhs":
        return " ".join(f"#{x}" for x in dict.fromkeys(base + ["AI工具", "职场效率"]))
    if platform == "douyin":
        return " ".join(f"#{x}" for x in dict.fromkeys(base + ["科技", "人工智能"]))
    return "、".join(dict.fromkeys(base))


def render_wechat_article(topic: Dict[str, Any], n: int) -> str:
    title = clean_topic(topic.get("title", ""))
    subject = short_subject(title)
    score = topic_score(topic, "wechat_article")
    url = topic.get("url", "")
    return f"""## 公众号选题 {n}：{subject}

- **选题主题**：{subject}
- **推荐标题**：
  1. {subject}：普通人/从业者真正应该关注什么？
  2. {subject}背后，AI 行业正在出现一个新变化
  3. 从{subject}看 2026 年 AI 工具的机会与边界
- **目标读者**：AI 工具用户、产品经理、开发者、内容创作者、关注效率提升的职场人。
- **核心观点**：不要只追热点，要判断它是否改变了真实工作流、成本结构或内容生产方式。
- **文章结构**：
  1. 背景：这个热点为什么今天值得看
  2. 关键变化：它和过去同类工具/事件有什么不同
  3. 影响分析：对普通用户、开发者、内容创作者分别意味着什么
  4. 实操建议：可以如何试用、验证或规避风险
  5. 边界条件：哪些说法仍需事实核验，哪些场景不适用
- **开头钩子**：如果你只把它当成一个新闻，可能会错过背后的工作流变化。
- **金句**：真正拉开差距的不是知道一个新工具，而是把它放进自己的流程里。
- **原文链接**：{url or '无'}
- **评分**：{score}/120
"""


def render_xhs(topic: Dict[str, Any], n: int) -> str:
    title = clean_topic(topic.get("title", ""))
    subject = short_subject(title)
    score = topic_score(topic, "xhs")
    return f"""## 小红书选题 {n}：{subject}

- **选题主题**：{subject}
- **封面标题**：这个 AI 热点，普通人可以这样用
- **首图副标题**：不是追新闻，而是拆成可执行的方法
- **目标人群**：AI 工具新手、职场人、内容创作者、独立开发者。
- **用户痛点**：热点很多但不知道和自己有什么关系；工具很多但不知道怎么上手。
- **图文卡片结构**：
  1. 结果/痛点：为什么这个热点值得看
  2. 方法总览：从“看热闹”到“能复用”的 3 步
  3. 步骤一：判断它解决什么真实问题
  4. 步骤二：找一个低成本试用场景
  5. 案例/对比：适合谁，不适合谁
  6. 避坑：不要直接相信夸张标题
  7. 总结/收藏引导：保存这套判断框架，下次看 AI 热点也能用
- **正文口语化文案**：今天看到「{subject}」这个话题，我不建议只看热闹。更有用的做法是：先判断它解决什么问题，再找一个你自己的小场景试一下，最后决定要不要放进日常流程。
- **标签建议**：{tags_for(title, 'xhs')}
- **评论区钩子**：你想让我把这个热点拆成具体教程吗？
- **风险提示**：{risk_tip(title)}
- **评分**：{score}/120
"""


def render_wechat_video(topic: Dict[str, Any], n: int) -> str:
    title = clean_topic(topic.get("title", ""))
    subject = short_subject(title)
    score = topic_score(topic, "wechat_video")
    return f"""## 微信视频号选题 {n}：{subject}

- **选题主题**：{subject}
- **30秒口播标题**：这个 AI 热点，真正值得关注的不是热闹本身
- **前3秒开场**：最近很多人在讨论「{subject}」，但我觉得重点不是它火了。
- **核心观点**：判断 AI 热点要看它是否改变真实工作流，而不是只看声量。
- **目标人群**：关注 AI、效率工具、内容生产和职业变化的微信用户。
- **口播脚本**：
  - **0-3秒**：最近很多人在讨论「{subject}」，但重点不是它火了。
  - **3-15秒**：真正要看的是，它有没有改变一个具体流程：比如写代码、找资料、做内容、做决策。
  - **15-45秒**：如果它只是多了一个功能，那可能只是新闻；但如果它能让一个重复任务自动化，那就是生产方式变化。
  - **45-60秒**：我的建议是，别急着追所有热点，选一个和你工作有关的小场景试一下。
  - **60-75秒**：如果你想，我可以继续把这个热点拆成一套可执行清单。
- **画面建议**：真人口播 + 屏幕录制/关键词大字卡，背景保持专业简洁。
- **字幕金句**：不要追所有 AI 热点，要找到能进入你工作流的那一个。
- **转发理由**：适合转给正在关注 AI 工具和效率提升的朋友/同事。
- **评论区问题**：你现在最想让 AI 帮你自动完成哪件事？
- **风险提示**：{risk_tip(title)}
- **评分**：{score}/120
"""


def render_douyin(topic: Dict[str, Any], n: int) -> str:
    title = clean_topic(topic.get("title", ""))
    subject = short_subject(title)
    score = topic_score(topic, "douyin")
    return f"""## 抖音选题 {n}：{subject}

- **选题主题**：{subject}
- **爆款短标题**：AI 热点别只看热闹，重点在这里
- **前3秒钩子**：你以为这只是一个 AI 新闻？其实它可能会影响你的工作方式。
- **冲突点**：大多数人只看工具名，少数人会把它变成自己的流程优势。
- **目标人群**：AI 工具用户、职场人、开发者、内容创作者。
- **30-60秒脚本**：
  - **0-3秒**：你以为这只是一个 AI 新闻？其实它可能会影响你的工作方式。
  - **3-10秒**：今天这个话题是「{subject}」。别急着问它火不火，先问它能不能帮你省掉一个重复动作。
  - **10-35秒**：判断一个 AI 热点有没有用，就看三件事：它解决什么问题？你能不能低成本试？它能不能进入你的日常流程？
  - **35-50秒**：如果答案都是 yes，它就不只是新闻，而是机会；如果不是，那就先观察。
  - **50-60秒**：你想让我把这个热点做成一份上手清单吗？评论区告诉我。
- **分镜建议**：
  1. 大字钩子开场
  2. 热点标题截图/关键词卡
  3. 三步判断法卡片
  4. 总结金句
- **屏幕字幕**：热点 ≠ 机会；能进入流程，才是机会。
- **B-roll/素材建议**：AI 工具界面、代码编辑器、资料整理、工作流箭头动画。
- **评论区问题**：你最近最想试哪个 AI 工具？
- **风险提示**：{risk_tip(title)}
- **评分**：{score}/120
"""


def render_topic(topic: Dict[str, Any], n: int, platform: str) -> str:
    if platform == "wechat_article":
        return render_wechat_article(topic, n)
    if platform == "xhs":
        return render_xhs(topic, n)
    if platform == "wechat_video":
        return render_wechat_video(topic, n)
    if platform == "douyin":
        return render_douyin(topic, n)
    raise ValueError(f"Unsupported platform: {platform}")


def select_topics(topics: List[Dict[str, Any]], platform: str, limit: int, keyword: Optional[str] = None) -> List[Dict[str, Any]]:
    filtered = dedupe_topics(topics)
    if keyword:
        pattern = re.compile(re.escape(keyword), re.I)
        k_filtered = [t for t in filtered if pattern.search(t.get("title", ""))]
        if k_filtered:
            filtered = k_filtered
    # 优先 AI 相关；如果没有，则保留全量。
    ai_related = [t for t in filtered if keyword_hits(t.get("title", ""))]
    if ai_related:
        filtered = ai_related
    return sorted(filtered, key=lambda t: topic_score(t, platform), reverse=True)[:limit]



def score_grade(score: int) -> str:
    if score >= 100:
        return "S"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def render_summary_table(selected_by_platform: Dict[str, List[Dict[str, Any]]], platforms: List[str]) -> str:
    rows = []
    rows.append("## 汇总评分表")
    rows.append("")
    rows.append("| 排名 | 平台 | 选题主题 | 综合评分 | 等级 | 建议 | 机会/风险理由 | 来源 | 原文链接 |")
    rows.append("|---:|---|---|---:|---|---|---|---|---|")
    flat = []
    for platform in platforms:
        for topic in selected_by_platform.get(platform, []):
            score = topic_score(topic, platform)
            title = clean_topic(topic.get("title", ""))
            if len(title) > 44:
                title = title[:44] + "…"
            source = topic.get("source", "") or "-"
            url = topic.get("url", "") or ""
            link = f"[链接]({url})" if url else "-"
            flat.append({
                "platform": platform,
                "title": title.replace("|", "\\|"),
                "score": score,
                "grade": score_grade(score),
                "recommendation": topic_recommendation(score, topic.get("title", "")),
                "reason": opportunity_reason(topic, platform).replace("|", "\\|"),
                "source": source,
                "link": link,
            })
    flat.sort(key=lambda x: x["score"], reverse=True)
    for idx, item in enumerate(flat, 1):
        rows.append(
            f"| {idx} | {PLATFORM_LABELS.get(item['platform'], item['platform'])} | {item['title']} | {item['score']} | {item['grade']} | {item['recommendation']} | {item['reason']} | {item['source']} | {item['link']} |"
        )
    rows.append("")
    rows.append("### 评分等级说明")
    rows.append("")
    rows.append("| 等级 | 分数范围 | 说明 |")
    rows.append("|---|---:|---|")
    rows.append("| S | 100-120 | 优先制作，具备高传播/高转化潜力 |")
    rows.append("| A | 85-99 | 值得制作，可进入近期内容池 |")
    rows.append("| B | 70-84 | 可以备选，需要优化角度 |")
    rows.append("| C | 55-69 | 谨慎使用，除非有强人设匹配 |")
    rows.append("| D | <55 | 不建议制作 |")
    rows.append("")
    return "\n".join(rows)


def render_report(topics: List[Dict[str, Any]], platforms: List[str], limit: int, keyword: Optional[str] = None) -> str:
    selected_by_platform: Dict[str, List[Dict[str, Any]]] = {}
    for platform in platforms:
        selected_by_platform[platform] = select_topics(topics, platform, limit, keyword=keyword)

    lines = []
    lines.append(f"# 四平台选题报告")
    lines.append("")
    lines.append("## 基本信息")
    lines.append(f"- **生成日期**：{now_date_cn()}")
    lines.append(f"- **目标平台**：{', '.join(platforms)}")
    if keyword:
        lines.append(f"- **关键词过滤**：{keyword}")
    lines.append(f"- **输入热点数量**：{len(topics)}")
    lines.append(f"- **入选选题数量**：{sum(len(v) for v in selected_by_platform.values())}")
    lines.append("- **评分口径**：已按也船长AI账号定位加权（公众号文章 > 视频号 > 小红书 > 抖音；优先 AI出海 / AI编程 / Agent工作流 / 大厂生态 / 新工具新模型）")
    lines.append("")
    lines.append(render_summary_table(selected_by_platform, platforms))

    for platform in platforms:
        selected = selected_by_platform.get(platform, [])
        lines.append(f"---\n\n# 平台：{PLATFORM_LABELS.get(platform, platform)}（{platform}）")
        if not selected:
            lines.append("\n未找到可用热点。")
            continue
        for i, topic in enumerate(selected, 1):
            lines.append(render_topic(topic, i, platform))
    return "\n".join(lines).rstrip() + "\n"


def load_input(path: Optional[str]) -> Any:
    if path:
        return json.loads(Path(path).read_text())
    import sys
    return json.load(sys.stdin)


def main() -> None:
    parser = argparse.ArgumentParser(description="把热点 JSON 转换为公众号/小红书/微信视频号/抖音四平台选题")
    parser.add_argument("--input", "-i", help="fetch_hot_topics.py 输出的 JSON 文件；省略则读 stdin")
    parser.add_argument("--platform", "-p", default="all", help="wechat_article,xhs,wechat_video,douyin 或 all，可逗号分隔")
    parser.add_argument("--limit", "-n", type=int, default=5, help="每个平台输出选题数量")
    parser.add_argument("--keyword", "-k", help="可选关键词过滤")
    parser.add_argument("--output", "-o", help="输出 markdown 文件路径")
    args = parser.parse_args()

    platforms = PLATFORMS if args.platform == "all" else [p.strip() for p in args.platform.split(",") if p.strip()]
    invalid = [p for p in platforms if p not in PLATFORMS]
    if invalid:
        raise SystemExit(f"Unsupported platform(s): {invalid}; supported: {PLATFORMS}")

    data = load_input(args.input)
    topics = as_list(data)
    report = render_report(topics, platforms, args.limit, keyword=args.keyword)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)
        print(str(out))
    else:
        print(report)


if __name__ == "__main__":
    main()
