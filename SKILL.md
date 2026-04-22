---
name: wechat-topic-radar
description: Use this skill when the user asks for AI公众号选题推荐, says "每日选题", or uses "选题：{关键词}" to generate 5-10 WeChat article ideas with titles, audience, content angles, score, date, and source links.
version: "2.5.0"
argument-hint: "每日选题 | 选题：关键词"
allowed-tools: [Read, Bash, WebSearch, WebFetch]
---

# 微信选题雷达 (WeChat Topic Radar)

AI领域微信公众号选题推荐工具，智能分析热点，生成爆款标题。

## 功能概述

本技能从热搜榜单抓取AI相关热点话题，经过多轮过滤后生成符合公众号传播规律的选题推荐。

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

**重要**：使用技能前应先读取并加载这些配置文件。

## 输出格式

每个选题包含以下8个字段：

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
  - 人设匹配度：{X}/100（权重40%）
  - 爆款潜力：{X}/100（权重60%）
  - 时效性：{±X}
- **热点日期**: {yyyy年mm月dd日}
- **原文链接**: {相关热点新闻链接}
```

## 选题评分系统

### 评分构成

| 维度 | 分数范围 | 权重 | 说明 |
|------|----------|------|------|
| **人设匹配度** | 0-100 | 40% | 关键词/受众精准度，与目标读者群体匹配程度 |
| **爆款潜力** | 0-100 | 60% | 综合评估8个维度 |
| **时效性** | ±20 | 加分项 | 近30天+20，近90天+10 |

### 爆款潜力评估维度

| 维度 | 说明 | 评分要点 |
|------|------|----------|
| 数据震撼力 | 话题包含的数据是否惊人、有冲击力 | 有具体数字>模糊数字>无数据 |
| 故事性 | 话题是否有故事展开空间 | 有故事>可延伸>单一事件 |
| 争议性 | 话题是否引发讨论和不同观点 | 有争议>中性>无分歧 |
| 实操价值 | 读者能否从中获得可操作内容 | 有教程>有建议>纯分析 |
| 情绪共鸣 | 话题是否触动读者情感 | 强共鸣>弱共鸣>无共鸣 |
| 社交货币 | 读者是否愿意分享讨论 | 愿意>被动>不会 |
| 标题吸引力 | 标题是否吸引点击 | 有悬念/数字>平淡描述 |
| 可读性 | 内容是否易于理解和传播 | 通俗>专业>晦涩 |

### 综合评分计算

```
综合评分 = (人设匹配度 × 40%) + (爆款潜力 × 60%) + 时效性
```

### 评分等级

| 等级 | 分数范围 | 说明 |
|------|----------|------|
| S级 | 100-120 | 绝佳选题，必爆潜力 |
| A级 | 85-99 | 优质选题，爆款可能大 |
| B级 | 70-84 | 良好选题，可以一试 |
| C级 | 55-69 | 普通选题，慎用 |
| D级 | <55 | 低价值选题，不推荐 |

## 数量要求

- 选题数量：每次输出 **5-10个选题**
- 标题数量：每个选题 **5个爆款标题**

## 操作流程

### 每日选题流程

1. **加载配置**：读取 persona.md、keywords_filter.md、prompt_filter.md、viral_headlines.md
2. **抓取热搜**：
   - 调用 `scripts/fetch_hot_topics.py` 抓取多平台热搜
   - 支持平台：zhihu、weibo、weixin、baidu、toutiao、douyin、bilibili、xiaohongshu、ithome、juejin、github、hackernews、solidot、v2ex、nowcoder、pcbeta、sspai、producthunt
   - API格式：`https://newsnow.busiyi.world/api/s?id={platform}&latest=true`
3. **过滤处理**：
   - 第一轮：关键词过滤（keywords_filter.md）
   - 第二轮：AI提示词模糊过滤（prompt_filter.md）
   - 第三轮：过滤纯新闻、无实操价值的热点
4. **话题分析**：从过滤后的热点中提取有价值的话题方向
5. **生成选题**：结合人设配置，按输出格式生成5-10个选题
6. **选题评分**：按选题评分系统对每个选题进行评分
7. **补充标题**：为每个选题生成5个具有爆款潜力的标题
8. **保存文件**：将选题按固定模板保存到 `topics/` 文件夹

### 关键词选题流程（爆款公式搜索）

1. **加载配置**：读取 persona.md、keywords_filter.md、prompt_filter.md、viral_headlines.md
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
8. **保存文件**：将选题按固定模板保存到 `topics/` 文件夹

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
- 评分要客观，基于话题本身的传播潜力
- 优先推荐B级（70分）以上的选题
- 链接优先选择权威媒体或行业媒体报道
- 每次使用前先检查配置文件是否需要更新

## 文件输出模板

### 保存位置
选题文件保存到 `topics/` 文件夹下

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

### 1. 选题评分
- **综合评分**：{X}/120（{等级}）
  - 人设匹配度：{X}/100（权重40%）
  - 爆款潜力：{X}/100（权重60%）
  - 时效性：{±X}

### 2. 匹配到的关键词
{关键词1}、{关键词2}、{关键词3}

### 3. AI评分理由
{从人设匹配度、爆款潜力8维度、时效性等方面详细说明评分理由}

### 4. 写作角度建议
{核心内容方向、角度、切入点分析}

### 5. 标题建议 TOP3
1. {标题1}
2. {标题2}
3. {标题3}

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
3. 优先推荐B级（70分）以上的选题
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
3. **保存图片**：图片保存到 `topics/images/` 目录
4. **输出链接**：返回图片路径或URL

### 封面图生成示例

选题主题：库克卸任苹果CEO

```bash
python3 scripts/generate_image.py \
  --prompt "Professional magazine cover image featuring Tim Cook and Jon Ternus, Apple CEO transition, AI era, clean corporate aesthetic, 16:9 aspect ratio" \
  --output topics/images/20260421-cover.png
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
python3 scripts/fact_checker.py topics/xxx.md
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
python3 scripts/fact_checker.py topics/20260421-库克卸任苹果CEO.md

# 检查目录下所有文章
python3 scripts/fact_checker.py --check-all topics/

# JSON格式输出（用于自动化）
python3 scripts/fact_checker.py topics/xxx.md --format json
```

### 校验输出示例

```
============================================================
文件: topics/20260421-库克卸任苹果CEO.md
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
