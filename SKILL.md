---
name: wechat-topic-radar
description: Use this skill when the user asks for AI公众号选题推荐, says "每日选题", or uses "选题：{关键词}" to generate 5-10 WeChat article ideas with titles, audience, content angles, score, date, and source links.
version: "3.0.0"
argument-hint: "每日选题 | 选题：关键词"
allowed-tools: [Read, Bash, WebSearch, WebFetch]
---

# 微信选题雷达 (WeChat Topic Radar)

AI领域微信公众号选题推荐工具，智能分析热点，生成爆款标题。

## ⚠️ 执行前必读（每次都要，不可跳过）

**第一步：读取跨会话记忆**

```bash
cat memory/hot-cache.md
```

- 本文件记录了历次升级决策，读完后才能开始执行
- 执行完毕后，若有新决策或升级，必须追加到 `memory/hot-cache.md`
- 这是防止"每次都从零开始"的唯一机制

---

## Vault 输出位置硬规则

- 所有"每日选题 / 选题雷达"类 Markdown 输出，默认保存到：`04.选题决策/每日选题/`
- 不要在 vault 根目录创建 `topics/` 等临时目录

---

## 环境能力组合拳

选题准确度依赖当前环境里的多能力组合：

1. **NewsNow 热榜聚合**：`python3 scripts/fetch_hot_topics.py --platform ithome,juejin,github,hackernews,zhihu,weibo --json`
2. **AI HOT 精选（fallback）**：NewsNow 过载时切换到 aihot API，详见 `references/script_guide.md`
3. **GitHub Trending**：`python3 scripts/fetch_github_trending.py --ai-only --limit 15`
4. **AI 公司公告**：`python3 scripts/fetch_x_announcements.py`（需 BRAVE_SEARCH_API_KEY）
5. **搜索验证**：`python3 scripts/brave_search.py "查询" --count 5`

默认原则：所有热榜只负责"发现线索"，主推荐必须经过搜索/原文抓取交叉验证。

---

## 准确选题硬规则

当用户要求"每日话题排名 / 每日选题 / 选题推荐"时：

1. **广撒网**：四路并行抓取（热榜聚合 + GitHub Trending + AI公司公告 + aihot精选）
2. **交叉验证**：对候选话题补充搜索/抓取验证；优先官方博客、GitHub README、权威媒体
3. **可信度评分**：脚本输出的 credibility_score < 40 直接拒绝，< 60 只能作为线索
4. **三层过滤**：关键词过滤 → AI 模糊过滤 → 实操价值过滤（详见 `references/filter_rules.md`）
5. **账号匹配**：优先"AI领域职场成长与工具应用，以及利用 AI 搞副业"
6. **三步评分**：① 否决过滤 → ② 七维评分（满分 120）→ ③ 八维爆款诊断（不打分，找短板）
7. **最终输出**：不少于 5 个推荐

---

## 选题评分系统（三步法）

评分分三步执行，**不可混在一个公式里**：

| 步骤 | 目的 | 输出 |
|------|------|------|
| ① 否决过滤 | 淘汰不该写的 | 通过 / 淘汰 |
| ② 七维评分 | 排名优先级 | 综合评分 X/120 |
| ③ 八维爆款诊断 | 找短板 | 短板提示 + 标题补强建议 |

### 第一步：否决过滤

以下任一条件命中，**直接淘汰**：

- 事实来源不清，且标题明显耸动
- 与 AI 出海 / AI 编程 / 大厂生态 / 新工具机会无连接
- 只能复述新闻，无法给出判断或落地解释
- 过度娱乐化，无法沉淀账号资产
- 需要强情绪、焦虑、站队才能传播
- 读者看完没有下一步动作
- 可信度评分 < 40

### 第二步：七维评分（满分 120）

| 维度 | 满分 | 评估要点 |
|------|:---:|------|
| **相关性** | 20 | 与主赛道（AI出海/AI编程/Agent/新工具/AI副业）匹配 |
| **读者价值** | 20 | 读者能否获得判断、行动建议或实操内容 |
| **判断空间** | 15 | 能否给出"值不值得关注"的判断 |
| **落地性** | 15 | 读者能否获得可执行的下一步动作 |
| **时效性** | 10 | 今日热点10 / 近7天8 / 近30天5 / 更早2 |
| **证据与素材** | 10 | 官方公告/GitHub/权威媒体是否充足 |
| **差异化** | 10 | 中文圈是否已有大量同质内容 |

**加分项**（每项+4，最多+20）：
- 能连接到 AI 出海场景
- 能连接到 AI 编程 / Agent / workflow 场景
- 有真实实测或亲身观察
- 能输出一张表 / 一套清单 / 一个框架
- 能沉淀进长期判断资产

> **强制验算规则**：每个选题的评分必须写出验算算式，格式：
> ```
> 七维小计 = XX + XX + XX + XX + XX + XX + XX = {结果}
> 总分 = 七维小计({结果}) + 加分项({+X}) = {最终分数}
> ```
>
> **自动验算脚本**：报告保存后运行：
> ```bash
> python3 scripts/verify_scores.py "04.选题决策/每日选题/YYYYMMDD-每日选题.md"
> ```

**评分等级**：

| 等级 | 分数范围 | 说明 |
|------|----------|------|
| S级 | ≥105 | 绝佳选题，今天就写 |
| A级 | 90-104 | 优质选题，值得主推 |
| B级 | 75-89 | 良好选题，可以一试 |
| C级 | 60-74 | 普通选题，慎用 |
| D级 | <60 | 不推荐 |

**爆款加速标注**：八维诊断中 ≥5 个维度为"强" → 标注 ⚡

### 第三步：八维爆款诊断（不打分，只找短板）

| 维度 | 短板补强方向 |
|------|------|
| 数据震撼力 | 标题加数字、正文补数据 |
| 故事性 | 找到真实案例或人物 |
| 争议性 | 标题用疑问句、正文列正反 |
| 实操价值 | 加步骤、清单、工具推荐 |
| 情绪共鸣 | 从痛点切入、用第一人称 |
| 社交货币 | 加判断结论，让转发有话可说 |
| 标题吸引力 | 用数字/疑问/对比/悬念重构 |
| 可读性 | 精简段落、加小标题、加粗重点 |

---

## 操作流程

### 每日选题流程

1. **加载配置**：读取 `account_profile.md`、`persona.md`、`keywords_filter.md`、`prompt_filter.md`、`viral_headlines.md`
2. **抓取热搜**（四路并行）：热榜聚合 + GitHub Trending + AI 公司公告 + aihot 精选
3. **过滤处理**：关键词过滤 → AI 模糊过滤 → 实操价值过滤
4. **话题分析**：从过滤后的热点中提取有价值的话题方向
5. **生成选题**：结合人设配置，生成 5-10 个选题
6. **选题评分**：按三步法评分
7. **保存文件**：保存到 `04.选题决策/每日选题/`，运行 `verify_scores.py` 验算

### 关键词选题流程

1. **加载配置**：同上
2. **网络搜索**：用 WebSearch 搜索公众号/知乎/机器之心平台
3. **爆款标题生成**：从 `references/viral_headlines.md` 读取公式库
4. 生成选题 → 评分 → 保存

### 四平台选题流程

当用户需要公众号/小红书/微信视频号/抖音选题适配时：

```bash
python3 scripts/fetch_hot_topics.py --platform ... --json > /tmp/hot.json
python3 scripts/generate_platform_topics.py --input /tmp/hot.json --platform all --limit 3
```

四平台定位：`wechat_article`（长文深度）、`xhs`（封面点击）、`wechat_video`（口播观点）、`douyin`（前3秒钩子）

---

## 配置文件

| 文件 | 说明 |
|------|------|
| `account_profile.md` | 账号定位、读者画像、否决规则 |
| `persona.md` | 公众号人设配置 |
| `keywords_filter.md` | 热搜排除关键词 |
| `prompt_filter.md` | AI提示词过滤模式 |
| `viral_headlines.md` | 爆款标题公式库 |
| `language_safety.md` | 禁用词、表述规范 |
| `data_sources.md` | 数据源配置 |
| `platform_templates.md` | 四平台适配模板 |

---

## 参考文档（按需读取）

| 内容 | 文件 |
|------|------|
| 脚本详细用法 | `references/script_guide.md` |
| 过滤规则详解 | `references/filter_rules.md` |
| 输出模板 | `references/output_template.md` |
| 配图与环境变量 | `references/image_guide.md` |
| 事实校验流程 | `references/fact_check_guide.md` |

---

## 注意事项

- 评分使用七维框架（100分制+加分项，满分120），不要用已废弃的 115 分制
- 爆款诊断（八维）只用于找短板，不参与评分计算
- 优先推荐 B 级（75分）以上的选题
- 链接优先选择权威媒体或行业媒体报道
- 每次使用前先检查配置文件是否需要更新
- 选题保存后必须运行 `verify_scores.py` 验算加法
