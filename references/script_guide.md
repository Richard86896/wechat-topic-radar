# 热搜抓取脚本指南

## scripts/fetch_hot_topics.py

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

## scripts/fetch_github_trending.py

```bash
python3 scripts/fetch_github_trending.py --ai-only --limit 15
python3 scripts/fetch_github_trending.py --json --limit 25
```

## scripts/fetch_x_announcements.py

```bash
python3 scripts/fetch_x_announcements.py
python3 scripts/fetch_x_announcements.py --accounts openai anthropic
python3 scripts/fetch_x_announcements.py --all --json
```

需要 BRAVE_SEARCH_API_KEY（与 brave_search.py 共用）。

## scripts/brave_search.py

```bash
python3 scripts/brave_search.py "查询内容" --count 5
```

## scripts/verify_scores.py

```bash
python3 scripts/verify_scores.py "04.选题决策/每日选题/YYYYMMDD-每日选题.md"
```
