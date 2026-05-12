# 数据源配置：微信 / 小红书替代源

`newsnow` 当前可能不再支持 `weixin`、`xiaohongshu` source id。本 skill 的 `scripts/fetch_hot_topics.py` 已改成多数据源 fallback：

- `weixin` / `wechat`：`juhe` → `alapi` → `newsnow`
- `xiaohongshu` / `xhs`：`tikhub` → `rnote` → `alapi` → `newsnow`
- 其他通用平台：默认 `newsnow`

## 快速使用

```bash
# 通用平台，免 key
python3 scripts/fetch_hot_topics.py --platform zhihu --json

# 微信，自动 fallback
python3 scripts/fetch_hot_topics.py --platform weixin --provider auto --json

# 小红书，自动 fallback
python3 scripts/fetch_hot_topics.py --platform xiaohongshu --provider auto --json

# 多平台
python3 scripts/fetch_hot_topics.py --platform weixin,xiaohongshu,zhihu,weibo --json
```

## 环境变量

### 微信：Juhe 聚合数据

```bash
export JUHE_API_KEY="你的聚合数据 key"
# 可选：覆盖接口地址
export JUHE_WECHAT_URL="https://apis.juhe.cn/fapigx/wxhottopic/query"
# 可选：追加参数
export JUHE_WECHAT_PARAMS='{"page":1}'
```

### 小红书：TikHub

```bash
export TIKHUB_API_KEY="你的 TikHub key"
# 可选：覆盖热榜接口地址
export TIKHUB_XHS_HOT_URL="https://api.tikhub.io/api/v1/xiaohongshu/web_v2/fetch_hot_list"
# 可选：覆盖搜索接口地址
export TIKHUB_XHS_SEARCH_URL="https://api.tikhub.io/api/v1/xiaohongshu/app_v2/search_notes"
```

TikHub 小红书搜索比热榜更适合选题，可用关键词触发：

```bash
python3 scripts/fetch_hot_topics.py --platform xhs --provider tikhub_search --keyword AI工具 --json
```

注意：实际测试中，TikHub 可能返回“此路由需要付费，并且不接受使用免费额度请求”。这代表 key 有效，但该 endpoint 需要余额/权限。

### 小红书：RNote

RNote endpoint 可能因套餐/部署不同而变化，因此默认要求显式配置 URL。

```bash
export RNOTE_API_KEY="你的 RNote key"
export RNOTE_XHS_HOT_URL="https://你的-rnote-endpoint/hot"
export RNOTE_XHS_SEARCH_URL="https://你的-rnote-endpoint/search"

# 关键词搜索
python3 scripts/fetch_hot_topics.py --platform xhs --provider rnote --keyword AI工具 --json
```

### 通用 fallback：ALAPI

```bash
export ALAPI_TOKEN="你的 ALAPI token"
export ALAPI_WECHAT_TYPE="weixin"
export ALAPI_XHS_TYPE="xiaohongshu"
# 如 ALAPI 文档中的 type 名称不同，改这里即可。
```

### 临时直接接入任意 JSON URL

```bash
export HOT_TOPICS_DIRECT_URL="https://example.com/hot.json"
python3 scripts/fetch_hot_topics.py --platform xhs --provider direct --json
```

直接源的 JSON 最好包含以下任一结构：

```json
{"items":[{"title":"话题", "url":"https://...", "hot_value":"123"}]}
```

或：

```json
{"data":{"list":[{"title":"话题"}]}}
```

## 统一输出字段

每个 topic 会被归一化为：

```json
{
  "rank": 1,
  "title": "话题标题",
  "url": "原文链接",
  "hot_value": "热度值",
  "description": "描述",
  "source": "newsnow|juhe|tikhub|rnote|alapi|direct",
  "platform": "weixin|xiaohongshu|zhihu...",
  "metrics": {
    "like": 0,
    "collect": 0,
    "comment": 0,
    "share": 0
  }
}
```

## 小红书选题注意

小红书不建议只看“热榜”。更稳的选题信号是：

1. 关键词搜索结果里的高赞/高收藏笔记；
2. 最近 7-30 天增长快的笔记；
3. 封面标题、首图结构、评论区问题；
4. 收藏/点赞比、评论密度；
5. 是否能拆成 5-8 张图文卡片。

因此，如果有条件，应优先配置 RNote 的搜索/笔记接口，而不是只接 TikHub 热榜。
