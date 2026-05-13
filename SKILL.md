---
name: wechat-topic-radar
description: Use this skill when the user asks for AI公众号选题推荐, says "每日选题", or uses "选题：{关键词}" to generate 5-10 WeChat article ideas with titles, audience, content angles, score, date, and source links.
version: "2.5.0"
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

## 功能概述

本技能从热搜榜单抓取AI相关热点话题，经过多轮过滤后生成符合公众号传播规律的选题推荐。


## Vault 输出位置硬规则

- 在 Richard 的 Obsidian vault 中，所有“每日选题 / 选题雷达 / 四平台选题 / 话题排名”类 Markdown 输出，默认且必须保存到：`04.选题决策/每日选题/`。
- 不要创建或使用 vault 根目录下的 `topics/` 作为长期输出目录。
- 如需保存配图，使用：`04.选题决策/每日选题/images/`。
- 命令示例、脚本 `--output` 参数、事实校验路径都应使用上述目录。



## 环境能力组合拳（2026-05-10）

选题准确度不依赖单一 skill 或单一热榜，而依赖当前环境里的多能力组合：

1. **NewsNow 热榜聚合**：用于广撒网抓取多平台热点，覆盖 GitHub、Hacker News、IT之家、掘金、V2EX、少数派、Product Hunt、知乎、微博、微信、百度、头条、抖音、B站、小红书等。
2. **AI HOT 精选（aihot fallback）**：NewsNow 过载或返回空结果时，立即切换到 aihot.virxact.com 精选 API 作为 AI 资讯备用数据源。命令：
   ```bash
   UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
   curl -sH "User-Agent: $UA" "https://aihot.virxact.com/api/public/items?mode=selected&since=24h"
   ```
   - 返回的是 AI HOT 编辑精选条目，质量高、AI 相关性强，可直接进入候选池；
   - 不需要 API Key，公开匿名访问；
   - **必须带 User-Agent**，否则 403 被拦截；
   - aihot 只作为"发现线索"数据源，主推荐仍需 Brave/Tavily 交叉验证。
3. **Tavily / web_search 搜索验证**：用于查询权威媒体、官方公告、产品博客、深度报道，判断一个热榜线索是否真实、是否有足够素材。
3. **web_extract / 原文抓取**：用于读取官方博客、GitHub README、Hugging Face、产品官网、技术文档等一手信息。
4. **浏览器实时抓取**：用于直接打开 GitHub Trending、Hacker News、Product Hunt、官网页面等动态页面，绕过 API 缺失、聚合延迟或页面结构限制。
5. **多模型推理**：用于对候选话题做交叉判断，包括账号匹配、实操价值、副业连接度、传播潜力、表达风险。
6. **三平台推送**：飞书、Telegram、微信均可作为选题报告推送渠道；生成报告后可按用户要求推送到指定平台。

默认工作原则：
- NewsNow 只负责”发现线索”，不负责最终判断；NewsNow 失败时自动 fallback 到 aihot 精选 API；
- aihot 精选同样只作为”发现线索”，主推荐必须经过 Brave/Tavily 交叉验证；
- 社交平台热榜只作为”热度信号”，不能单独作为可信来源；
- 主推荐必须经过搜索或原文抓取交叉验证；
- 有官方 / GitHub / Hugging Face / 产品官网 / 权威媒体支撑的话题优先；
- 最终推荐不是热度最高的 10 个，而是最适合账号写、最能落地、最有可靠来源的不少于5个。

## 准确选题硬规则（2026-05-10）

当用户要求”每日话题排名 / 每日选题 / 选题推荐”时，默认不是输出泛泛 TOP10，而是执行”多信号叠加后输出最终不少于5个推荐”：

1. **广撒网**：优先抓取 18 个平台热榜：GitHub、Hacker News、IT之家、掘金、V2EX、少数派、Product Hunt、知乎、微博、微信、百度、头条、抖音、B站、小红书、Solidot、牛客、PCBeta。
2. **交叉验证**：对候选话题必须补充搜索/抓取/浏览器验证；优先官方博客、GitHub README、Hugging Face、产品官网、权威媒体。
3. **可信度评分**：使用脚本输出的 `credibility_score`、`credibility_level`、`red_flags`；低于 40 分直接拒绝，低于 60 分只能作为线索，不能作为主推荐。
4. **三层过滤**：关键词过滤 → AI 模糊过滤 → 实操价值过滤。
5. **账号匹配**：优先”AI领域职场成长与工具应用，以及利用 AI 搞副业”；尤其关注 AI 工具应用、AI 副业、职场成长、实操教程、AI 行业动态。
6. **三步评分**：① 否决过滤 → ② 七维评分（100分制+加分项，满分120）→ ③ 八维爆款诊断（找短板，不打分）。详见”选题评分系统”。
7. **最终输出**：默认输出不少于5个推荐；如需 TOP10，先给表格，并标出”观察/不建议主写”的理由。

推荐输出结构：

| 排名 | 最终推荐选题 | 分数 | 核心信号 | 可信来源 | 为什么适合账号 | 建议内容形态 |
|---:|---|---:|---|---|---|---|

然后补充：
- 今日第 1 推荐的文章角度；
- 备选池不少于5个；
- 拒绝/降级原因。



### Tavily 搜索助手

当前共享 skill 已提供 `scripts/tavily_search.py`，会从以下位置自动读取 `TAVILY_API_KEY`：

1. 进程环境变量；
2. `wechat-topic-radar/.env.local`；
3. `~/.config/wechat-topic-radar/env`。

示例：

```bash
python3 scripts/tavily_search.py "Claude Code Routines official" --max-results 5
```

注意：不要在输出中打印 API Key；只输出搜索结果和来源链接。



### Brave Search 搜索助手

当前共享 skill 已提供 `scripts/brave_search.py`，会从以下位置自动读取 `BRAVE_SEARCH_API_KEY`：

1. 进程环境变量；
2. `wechat-topic-radar/.env.local`；
3. `~/.config/wechat-topic-radar/env`。

示例：

```bash
python3 scripts/brave_search.py "OpenAI official blog" --count 5
```

注意：不要在输出中打印 API Key；只输出搜索结果和来源链接。

## 触发方式

### 方式一：每日选题
输入 `每日选题` 或类似表达
- 从知乎、微博、微信、科技类平台等抓取热搜榜单
- 过滤低价值新闻，提取AI相关热点
- 生成5-10个有实操价值的选题

### 方式二：关键词选题
输入 `选题：{关键词}` 或 `选题：AI` 等格式
- 基于指定关键词搜索相关话题
- 使用爆款标题公式进行网络搜索（公众号、知乎、机器之心）
- 结合搜索结果生成垂直领域选题

### 方式三：斜杠命令
可直接运行 `/wechat-topic-radar 每日选题` 或 `/wechat-topic-radar 选题：智能体`
- 如果 `$ARGUMENTS` 为空，默认按 `每日选题` 处理
- 如果 `$ARGUMENTS` 不带 `选题：` 前缀但不是 `每日选题`，按关键词处理

## 配置文件

技能使用以下配置文件（位于 references/ 目录）：

| 文件 | 说明 |
|------|------|
| `persona.md` | 公众号人设配置：定义目标读者、内容风格 |
| `keywords_filter.md` | 热搜过滤关键词：包含需要排除的关键词 |
| `prompt_filter.md` | AI提示词模糊过滤：包含需要排除的内容模式 |
| `viral_headlines.md` | 爆款标题公式库：生成搜索用的爆款标题 |
| `language_safety.md` | 语言安全规则：禁用词、表述规范、数据标注要求 |
| `data_sources.md` | 数据源配置：微信/小红书替代源、API key、fallback 规则 |
| `platform_templates.md` | 四平台选题适配模板：公众号、小红书、微信视频号、抖音 |
| `account_profile.md` | 也船长AI账号配置与专属评分规则 |

**重要**：使用技能前应先读取并加载这些配置文件。

## 输出格式

每个选题包含以下字段：

```
## 选题 {n}（{综合评分}/120）
- **选题主题**: {简明扼要的主题概括}
- **爆款标题推荐**:
  1. {标题1}
  2. {标题2}
  3. {标题3}
  4. {标题4}
  5. {标题5}
- **目标读者画像**: {年龄、职业、兴趣特征等}
- **内容要点提示**: {核心内容方向、角度、切入点}
- **选题评分**: {X}/120
  - 相关性：{X}/20
  - 读者价值：{X}/20
  - 判断空间：{X}/15
  - 落地性：{X}/15
  - 时效性：{X}/10
  - 证据素材：{X}/10
  - 差异化：{X}/10
  - **七维小计**：{XX}（= 前7项之和，必须验算）
  - 加分项：{+X}（最多+20，写明命中了哪几项，每项+4）
  - **总分/120**：{XX}（= 七维小计 + 加分项，必须验算）
- **爆款诊断**（八维雷达，找短板用）:
  - 数据震撼力 / 故事性 / 争议性 / 实操价值 / 情绪共鸣 / 社交货币 / 标题吸引力 / 可读性
  - 短板提示：{哪个维度最弱，标题/角度应如何补}
- **热点日期**: {yyyy年mm月dd日}
- **原文链接**: {相关热点新闻链接}
```

## 选题评分系统（三步法）

评分分三步执行，各有不同目的，**不可混在一个公式里**：

| 步骤 | 目的 | 工具 | 输出 |
|------|------|------|------|
| ① 否决过滤 | 淘汰不该写的 | account_profile 否决规则 | 通过 / 淘汰 |
| ② 七维评分 | 排名选题优先级 | account_profile 七维框架 | 综合评分 X/120 |
| ③ 八维爆款诊断 | 找短板，指导写作 | 爆款潜力 8 维度 | 短板提示 + 标题补强建议 |

---

### 第一步：否决过滤

以下任一条件命中，**直接淘汰**，不进入评分：

- 事实来源不清，且标题明显耸动
- 与 AI 出海 / AI 编程 / 大厂生态 / 新工具机会无连接
- 只能复述新闻，无法给出判断或落地解释
- 过度娱乐化，无法沉淀账号资产
- 需要强情绪、焦虑、站队才能传播
- 读者看完没有下一步动作
- 可信度评分 < 40（脚本输出的 credibility_score）

---

### 第二步：七维评分（100分制 + 加分项，满分120）

评分框架如下（account_profile.md 不再维护评分逻辑，以本文件为准）：

| 维度 | 满分 | 评估要点 |
|------|:---:|------|
| **相关性** | 20 | 与主赛道关键词（AI出海/AI编程/Agent/新工具/AI副业）的匹配程度 |
| **读者价值** | 20 | 读者看完能否获得判断、行动建议或实操内容 |
| **判断空间** | 15 | 能否给出"值不值得关注/适不适合自己/下一步怎么做"的判断 |
| **落地性** | 15 | 读者能否从文章中获得可执行的下一步动作 |
| **时效性** | 10 | 传播窗口：今日热点10 / 近7天8 / 近30天5 / 更早2 |
| **证据与素材** | 10 | 官方公告/GitHub/权威媒体/一手数据是否充足 |
| **差异化** | 10 | 中文圈是否已有大量同质内容，是否有独特角度 |

**加分项**（每项+4，最多+20）：
- 能连接到 AI 出海场景
- 能连接到 AI 编程 / Agent / workflow 场景
- 有真实实测或亲身观察
- 能输出一张表 / 一套清单 / 一个框架
- 能沉淀进长期判断资产

> **减分项已移入否决门（第一步）**：凡"只能搬运新闻""来源不可信""话题太宽写不出判断"等情况，在第一步直接淘汰，不再在评分阶段扣分。

```
综合评分 = 七维总分(0-100) + 加分项(0~+20)
理论范围：0 ~ 120
```

> **强制校验规则（2026-05-13）**：每个选题的评分必须写出验算算式，格式如下：
> ```
> 七维小计 = XX + XX + XX + XX + XX + XX + XX = {结果}
> 总分 = 七维小计({结果}) + 加分项({+X}) = {最终分数}
> ```
> 若算式不成立，评分视为无效。评分由语言模型心算，必须用算式自检，防止出现今天报告中出现的加法错误。

**评分等级**：

| 等级 | 分数范围 | 说明 |
|------|----------|------|
| S级 | ≥105 | 绝佳选题，今天就写 |
| A级 | 90-104 | 优质选题，值得主推 |
| B级 | 75-89 | 良好选题，可以一试 |
| C级 | 60-74 | 普通选题，慎用 |
| D级 | <60 | 低价值选题，不推荐 |

**爆款加速标注**（不影响分数，仅辅助决策）：
- 八维诊断中 ≥5 个维度为"强" → 在推荐等级旁标注 ⚡ 爆款加速

---

### 第三步：八维爆款诊断（不打分，只找短板）

对通过前两步的候选，用以下 8 个维度做诊断，**不参与评分计算**，仅用于指导标题和角度优化：

| 维度 | 诊断问题 | 短板时的补强方向 |
|------|----------|----------------|
| 数据震撼力 | 有没有具体数字让人"哇"？ | 标题加数字、正文补数据 |
| 故事性 | 能不能讲一个完整的故事？ | 找到真实案例或人物 |
| 争议性 | 有没有不同观点可以碰撞？ | 标题用疑问句、正文列正反 |
| 实操价值 | 读者能照做吗？ | 加步骤、加清单、加工具推荐 |
| 情绪共鸣 | 读者会"啊，我也这样"吗？ | 从痛点切入、用第一人称 |
| 社交货币 | 读者会转发给同事吗？ | 加"转给XX"的暗示、加判断结论 |
| 标题吸引力 | 标题够不够想点？ | 用数字/疑问/对比/悬念重构标题 |
| 可读性 | 30秒能看懂核心意思吗？ | 精简段落、加小标题、加粗重点 |

**输出格式**（附加在每个选题评分之后）：
```
- **爆款诊断**：实操价值强，社交货币弱
  - 短板：标题太平，缺少"转给同事"的理由
  - 补强：标题加判断结论，让读者转发时有话可说
```

## 数量要求

- 选题数量：每次输出 **5-10个选题**
- 标题数量：每个选题 **5个爆款标题**

## 操作流程

### 每日选题流程

1. **加载配置**：读取 `account_profile.md`（账号专属评分框架，优先级最高）、`persona.md`（定位摘要）、`keywords_filter.md`、`prompt_filter.md`、`viral_headlines.md`
   - 评分时以 `account_profile.md` 的 7 维框架为准，而非通用的 8 维爆款潜力
   - 人设匹配度评估：对照 `account_profile.md` 的主赛道关键词和选题否决规则
2. **抓取热搜**：
   - 调用 `scripts/fetch_hot_topics.py` 抓取多平台热搜
   - 微信/小红书数据源已支持多 provider fallback；详见 `references/data_sources.md`
   - 推荐命令：`python3 scripts/fetch_hot_topics.py --platform weixin,xiaohongshu --provider auto --json`
   - 支持平台：zhihu、weibo、weixin、baidu、toutiao、douyin、bilibili、xiaohongshu、ithome、juejin、github、hackernews、solidot、v2ex、nowcoder、pcbeta、sspai、producthunt
   - API格式：`https://newsnow.busiyi.world/api/s?id={platform}&latest=true`
   - **若 NewsNow 返回 D1_ERROR / 过载 / 空结果**：立即切换 aihot fallback（见"环境能力组合拳"第2条），不要等待重试
3. **过滤处理**：
   - 第一轮：关键词过滤（keywords_filter.md）
   - 第二轮：AI提示词模糊过滤（prompt_filter.md）
   - 第三轮：过滤纯新闻、无实操价值的热点
4. **话题分析**：从过滤后的热点中提取有价值的话题方向
5. **生成选题**：结合人设配置，按输出格式生成5-10个选题
6. **选题评分**：按选题评分系统对每个选题进行评分
7. **补充标题**：为每个选题生成5个具有爆款潜力的标题
8. **保存文件**：将选题按固定模板保存到 `04.选题决策/每日选题/` 文件夹

### 关键词选题流程（爆款公式搜索）

1. **加载配置**：读取 `account_profile.md`（账号专属评分框架）、`persona.md`（定位摘要）、`keywords_filter.md`、`prompt_filter.md`、`viral_headlines.md`
2. **网络搜索**：
   - 使用 WebSearch 搜索以下平台，每个平台搜索3-5个爆款标题变体：
     - 公众号：`site:mp.weixin.qq.com "{关键词}"` + 爆款标题
     - 知乎：`site:zhihu.com "{关键词}"` + 爆款标题
     - 机器之心：`site:jiqizhixin.com "{关键词}"` + 爆款标题
3. **爆款标题生成**：
   - 从 viral_headlines.md 读取爆款公式库
   - 对每个关键词，使用公式生成5个变体标题进行搜索
   - 爆款公式示例：
     - "{XX天内} XX万人都在用/看/学"
     - "{XX岁前}一定要知道的XX件事"
     - "为什么XX都在XX？"
     - "XX天学会了XX，方法分享"
     - "XX和XX的区别是什么？"
     - "手把手教你XX"
4. **话题分析**：从搜索结果中提取相关话题和优质内容
5. **生成选题**：按输出格式生成选题
6. **选题评分**：按选题评分系统对每个选题进行评分
7. **补充标题**：为每个选题生成5个标题
8. **保存文件**：将选题按固定模板保存到 `04.选题决策/每日选题/` 文件夹


### 四平台选题生成流程

当用户需要公众号、小红书、微信视频号、抖音选题适配时：

1. 先用 `scripts/fetch_hot_topics.py` 抓取热点 JSON。
2. 再用 `scripts/generate_platform_topics.py` 转换成目标平台选题。
3. 目标平台支持：`wechat_article`、`xhs`、`wechat_video`、`douyin`、`all`。

示例：

```bash
# 先抓取热点
python3 scripts/fetch_hot_topics.py --platform zhihu,weibo,douyin,ithome,juejin,github --json > /tmp/hot.json

# 生成四平台选题
python3 scripts/generate_platform_topics.py --input /tmp/hot.json --platform all --limit 3 --output 04.选题决策/每日选题/$(date +%Y%m%d)-四平台选题.md

# 只生成抖音选题
python3 scripts/generate_platform_topics.py --input /tmp/hot.json --platform douyin --limit 5

# 只生成小红书 AI 编程相关选题
python3 scripts/generate_platform_topics.py --input /tmp/hot.json --platform xhs --keyword AI编程 --limit 5
```

四平台定位：

| 平台 | 重点 |
|---|---|
| `wechat_article` | 长文深度、信息增量、实操价值 |
| `xhs` | 封面点击、收藏价值、图文卡片结构 |
| `wechat_video` | 熟人转发、专业口播、观点密度 |
| `douyin` | 前3秒钩子、完播潜力、情绪/冲突 |

## 热搜抓取脚本

### 脚本位置
`scripts/fetch_hot_topics.py`

### 支持的平台ID

| 平台 | ID | 说明 |
|------|-----|------|
| **主流平台** | | |
| 知乎 | zhihu | 知乎热榜 |
| 微博 | weibo | 微博热搜 |
| 微信 | weixin | 微信热文 |
| 百度 | baidu | 百度热搜 |
| 头条 | toutiao | 今日头条热榜 |
| 抖音 | douyin | 抖音热榜 |
| 哔哩哔哩 | bilibili | B站热榜 |
| 小红书 | xiaohongshu | 小红书热榜 |
| **科技类平台** | | |
| IT之家 | ithome | IT之家热榜 |
| 掘金 | juejin | 掘金热榜 |
| GitHub | github | GitHub Trending |
| Hacker News | hackernews | Hacker News |
| Solidot | solidot | Solidot |
| V2EX | v2ex | V2EX |
| 牛客网 | nowcoder | 牛客网热帖 |
| 远景论坛 | pcbeta | 远景论坛 |
| 少数派 | sspai | 少数派 |
| ProductHunt | producthunt | ProductHunt |

### 使用示例

```bash
# 抓取知乎热搜
python3 scripts/fetch_hot_topics.py --platform zhihu

# 抓取多个平台热搜
python3 scripts/fetch_hot_topics.py --platform zhihu,weibo

# 抓取科技类平台
python3 scripts/fetch_hot_topics.py --platform ithome,juejin,github

# 抓取所有平台热搜
python3 scripts/fetch_hot_topics.py --platform all
```

### 输出格式

脚本输出JSON格式的热搜列表：
```json
{
  "platform": "zhihu",
  "timestamp": "2026-04-20T10:30:00",
  "topics": [
    {
      "rank": 1,
      "title": "GPT-5.4发布",
      "url": "https://zhihu.com/...",
      "hot_value": 5000000
    }
  ]
}
```

## 过滤规则

### 关键词过滤（keywords_filter.md）

包含需要排除的关键词，每行一个：
- 纯新闻事件（如：某某明星离婚、某某会议开幕）
- 与AI无关的话题
- 低热度话题

### AI提示词模糊过滤（prompt_filter.md）

包含需要排除的内容模式（支持模糊匹配）：
- 纯新闻报道类（无分析无观点）
- 标题党特征（过度夸张、虚假悬念）
- 与目标人设不符的内容

### 新闻过滤规则

以下类型的热搜会被过滤：
1. 纯新闻事件，无分析价值
2. 娱乐八卦、社会事件
3. 实时股价、汇率波动
4. 天气预报类
5. 节假日祝福类

保留的内容类型：
- 有观点的分析
- 有实操价值的教程
- 有深度的行业解读
- 有争议的话题讨论

## 爆款标题公式（viral_headlines.md）

详见 references/viral_headlines.md

### 公式分类

1. **情绪驱动型** - 引发好奇、情感共鸣
2. **数字量化型** - 用具体数字增强可信度
3. **疑问引导型** - 使用疑问句引发思考
4. **实用价值型** - 明确告诉读者能获得什么
5. **热点借势型** - 结合当下流行语或事件

## 注意事项

- 优先选择有实时新闻支撑的选题
- 标题避免过度标题党，保持内容真实性
- 评分使用七维框架（100分制+加分项，满分120），不要用已废弃的115分制（减分版）
- 爆款诊断（八维）只用于找短板和指导标题优化，不参与评分计算
- 优先推荐B级（75分）以上的选题
- 链接优先选择权威媒体或行业媒体报道
- 每次使用前先检查配置文件是否需要更新

## 文件输出模板

### 保存位置
选题文件保存到 `04.选题决策/每日选题/` 文件夹下

### 文件命名规则
```
年月日-每日选题.md
年月日-特定选题.md
```

示例：
- `20260421-每日选题.md`
- `20260421-AI副业.md`

### 选题输出模板

```markdown
# 选题报告：{选题主题}

## 基本信息
- **选题类型**：每日选题 / 特定选题
- **生成日期**：{yyyy年mm月dd日}
- **选题评分等级**：{S/A/B/C/D}级

## 选题 {n}：{选题主题}

### 1. 选题评分（七维框架）
- **综合评分**：{X}/120（{等级}）
  - 相关性：{X}/20
  - 读者价值：{X}/20
  - 判断空间：{X}/15
  - 落地性：{X}/15
  - 时效性：{X}/10
  - 证据素材：{X}/10
  - 差异化：{X}/10
  - **七维小计**：{XX}（= 前7项之和，必须验算）
  - 加分项：{+X}（最多+20，写明命中了哪几项，每项+4）
  - **总分/120**：{XX}（= 七维小计 + 加分项，必须验算）

### 2. 爆款诊断（八维雷达）
- 数据震撼力：{强/中/弱}
- 故事性：{强/中/弱}
- 争议性：{强/中/弱}
- 实操价值：{强/中/弱}
- 情绪共鸣：{强/中/弱}
- 社交货币：{强/中/弱}
- 标题吸引力：{强/中/弱}
- 可读性：{强/中/弱}
- **短板提示**：{哪个维度最弱，标题/角度应如何补}

### 3. 匹配到的关键词
{关键词1}、{关键词2}、{关键词3}

### 4. 写作角度建议
{核心内容方向、角度、切入点分析}

### 5. 标题建议 TOP5
1. {标题1}
2. {标题2}
3. {标题3}
4. {标题4}
5. {标题5}

### 6. 原文信息
- **热点日期**：{yyyy年mm月dd日}
- **原文链接**：{URL}

---

## 选题 {n+1}：{选题主题}
...（重复上述结构）
```

### 输出要求
1. 每个选题按上述模板格式输出
2. 文件保存后告知用户文件路径
3. 优先推荐B级（75分）以上的选题
4. 确保原文链接和日期准确

## 文章配图生成

### 配图脚本
调用 `scripts/generate_image.py` 使用 Replicate API 生成配图

### 环境配置
需要设置环境变量 `REPLICATE_API_TOKEN`：
```bash
export REPLICATE_API_TOKEN="your_api_token_here"
```

### 配图类型

| 配图位置 | 类型 | 说明 |
|----------|------|------|
| 封面图 | 人物+场景 | 吸引眼球的封面 |
| 内文图 | 信息图/场景图 | 配合文章内容 |
| 结尾图 | 行动号召图 | 引导转发/关注 |

### 配图流程

1. **生成提示词**：根据选题内容，从 `references/image_prompts.md` 读取模板，生成具体提示词
2. **调用API**：使用 `scripts/generate_image.py` 生成图片
3. **保存图片**：图片保存到 `04.选题决策/每日选题/images/` 目录
4. **输出链接**：返回图片路径或URL

### 封面图生成示例

选题主题：库克卸任苹果CEO

```bash
python3 scripts/generate_image.py \
  --prompt "Professional magazine cover image featuring Tim Cook and Jon Ternus, Apple CEO transition, AI era, clean corporate aesthetic, 16:9 aspect ratio" \
  --output 04.选题决策/每日选题/images/20260421-cover.png
```

### 支持的配图尺寸

| 用途 | 尺寸 | 宽高比 |
|------|------|--------|
| 封面图 | 900x383 | 2.35:1 |
| 文中图 | 800x600 | 4:3 |
| 结尾图 | 800x400 | 2:1 |
| 朋友圈图 | 1080x1080 | 1:1 |

### 配图风格

- 封面图：专业、现代、科技感
- 内文图：信息图风格、数据可视化
- 结尾图：激励、行动号召

## 环境变量配置

### 必需的环境变量

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| `REPLICATE_API_TOKEN` | Replicate API密钥 | https://replicate.com/account/api-tokens |

### 配置方法

**macOS/Linux:**
```bash
export REPLICATE_API_TOKEN="your_token_here"
```

**Windows (PowerShell):**
```powershell
$env:REPLICATE_API_TOKEN="your_token_here"
```

**永久保存:**
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export REPLICATE_API_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc
```

### 验证配置
```bash
python3 scripts/generate_image.py --test
```

## 文章生成与实时事实校验

### 生成流程（含校验）

生成完整文章时，按以下步骤执行：

```
1. 选题确认 → 2. 资料搜集 → 3. 实时事实验证 → 4. 文章撰写 → 5. 自动校验 → 6. 输出
```

**步骤1-2：选题确认与资料搜集**
- 确认选题主题和核心观点
- 搜集相关资料和新闻来源

**步骤3：实时事实验证（新增）**
对文章中的关键事实，使用 WebSearch 进行实时验证：

| 核查项 | 搜索验证方式 | 示例 |
|--------|-------------|------|
| 高管职位 | `"{姓名}" Apple position 2026` | `John Ternus Apple position 2026` |
| 财务数据 | `Apple Q4 2025 earnings report` | 搜索最新财报数据 |
| 公司历史 | `Apple founded year history` | 搜索确认成立时间 |
| 事件日期 | `Tim Cook retirement announcement April 2026` | 搜索确认日期 |
| 技术归属 | `Apple chip development leader Johny Srouji` | 搜索确认技术负责人 |
| 高管年龄 | `Tim Cook born age` | 搜索确认年龄 |

**步骤4：文章撰写**
- 根据验证后的资料撰写文章
- 遵循 language_safety.md 中的表述规范

**步骤5：自动校验（新增）**
使用 fact_checker.py 进行最终校验：
```bash
python3 scripts/fact_checker.py 04.选题决策/每日选题/xxx.md
```

**步骤6：输出**
- 输出校验通过的文章
- 如有错误，返回修正

---

### 实时校验触发词

生成文章时，遇到以下关键词必须触发搜索验证：

1. **人物 + 职位**：CEO、CTO、VP、SVP 等 → 搜索验证职位
2. **数字 + 公司**：营收、市值、用户数等 → 搜索最新数据
3. **公司 + 时间**：成立年份、上市时间等 → 搜索确认
4. **事件 + 日期**：发布、退休、任命等 → 搜索确认日期

---

### 校验命令

```bash
# 检查单篇文章
python3 scripts/fact_checker.py 04.选题决策/每日选题/20260421-库克卸任苹果CEO.md

# 检查目录下所有文章
python3 scripts/fact_checker.py --check-all 04.选题决策/每日选题/

# JSON格式输出（用于自动化）
python3 scripts/fact_checker.py 04.选题决策/每日选题/xxx.md --format json
```

### 校验输出示例

```
============================================================
文件: 04.选题决策/每日选题/20260421-库克卸任苹果CEO.md
============================================================

📊 检查结果: PASS
   错误: 0 | 警告: 1

📋 问题列表:

⚠️ [fact] 库克出生于1960年1月24日，2026年为66岁
   建议: 改为'66岁'或'65岁'（取决于精确度）

============================================================
📊 汇总:
   检查文件: 1
   总错误: 0 | 总警告: 1

✅ 全部检查通过!
```

---

### 表述自检清单

撰写文章时对照检查：

- [ ] 原因推断是否加了"可能"、"或许"等限定词
- [ ] 未来预测是否加了"可能"、"预期"等限定词
- [ ] 财务数据是否加了"约"、"接近"等限定词
- [ ] 高管归因是否准确（通过 WebSearch 实时验证）
- [ ] 时间事件是否准确（通过 WebSearch 实时验证）
- [ ] 行业对比是否保持中性（避免过度贬低或吹捧）
- [ ] 是否使用了禁用词汇（对照 language_safety.md）
- [ ] 数据是否有来源标注（公开财报、公开报道等）

---

### 语言安全规则摘要

撰写时避免以下表述：

| 情形 | 避免用语 | 推荐用语 |
|------|----------|----------|
| 未经证实原因 | "XX选择在AI爆发期卸任" | "XX此时卸任，原因多方面" |
| 猜测方向 | "苹果将推出XX" | "苹果可能探索XX方向" |
| 精确数据 | "$4,160亿" | "约$4,160亿" |
| 主观判断 | "苹果AI明显落后" | "苹果在AI浪潮中相对谨慎" |
| 未发生事件 | "库克已退休" | "库克宣布将于9月退休" |

详见 `references/language_safety.md`
