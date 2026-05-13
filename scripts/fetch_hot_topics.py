#!/usr/bin/env python3
"""
热搜话题抓取脚本（多数据源版）

目标：
- 保留 newsnow.busiyi.world 作为默认通用热榜源。
- 为微信/小红书提供可配置替代源与失败 fallback。
- 统一输出结构，供 wechat-topic-radar 上层选题评分复用。

支持的 provider：
- newsnow: 通用热榜，免 key。
- juhe: 聚合数据微信热搜榜，需要 JUHE_API_KEY。
- tikhub: 小红书热榜，需要 TIKHUB_API_KEY。
- rnote: 小红书数据 API，需要 RNOTE_API_KEY，可通过 RNOTE_*_URL 配置具体 endpoint。
- alapi: 今日热榜，需要 ALAPI_TOKEN，具体 type 可通过 ALAPI_*_TYPE 配置。
- direct: 直接请求自定义 URL，便于临时接入其他服务。

常用平台别名：
- weixin / wechat: 微信话题，优先 juhe -> alapi -> newsnow。
- xiaohongshu / xhs: 小红书话题，优先 tikhub -> rnote -> alapi -> newsnow。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


PLATFORM_IDS = {
    # 主流平台（newsnow）
    "zhihu": "知乎",
    "weibo": "微博热搜",
    "weixin": "微信热文",
    "wechat": "微信热文",
    "baidu": "百度热搜",
    "toutiao": "今日头条",
    "douyin": "抖音热榜",
    "bilibili": "B站热榜",
    "xiaohongshu": "小红书",
    "xhs": "小红书",
    # 科技类平台（newsnow）
    "ithome": "IT之家",
    "juejin": "掘金",
    "github": "GitHub",
    "hackernews": "Hacker News",
    "solidot": "Solidot",
    "v2ex": "V2EX",
    "nowcoder": "牛客网",
    "pcbeta": "远景论坛",
    "sspai": "少数派",
    "producthunt": "ProductHunt",
    # 显式 provider 平台
    "juhe_wechat": "微信热搜榜（Juhe）",
    "tikhub_xhs": "小红书热榜（TikHub）",
    "tikhub_xhs_search": "小红书搜索（TikHub）",
    "rnote_xhs": "小红书数据（RNote）",
    "alapi_wechat": "微信热榜（ALAPI）",
    "alapi_xhs": "小红书热榜（ALAPI）",
}

NEWSNOW_PLATFORM_ALIASES = {
    "wechat": "weixin",
    "xhs": "xiaohongshu",
}

def load_local_env_files() -> None:
    """Load local key=value env files without external dependencies.

    Priority stays with existing process env. Files are for private local secrets and
    should never be committed.
    """
    candidates = [
        Path(__file__).resolve().parents[1] / ".env.local",
        Path.home() / ".config" / "wechat-topic-radar" / "env",
    ]
    for env_file in candidates:
        if not env_file.exists():
            continue
        try:
            for raw_line in env_file.read_text().splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            continue



load_local_env_files()

NEWSNOW_API_BASE_URL = os.getenv("NEWSNOW_API_BASE_URL", "https://newsnow.busiyi.world/api/s")

# 聚合数据微信热搜榜。可通过环境变量覆盖，方便兼容套餐/版本差异。
JUHE_WECHAT_URL = os.getenv("JUHE_WECHAT_URL", "https://apis.juhe.cn/fapigx/wxhottopic/query")
JUHE_API_KEY = os.getenv("JUHE_API_KEY") or os.getenv("JUHE_KEY")

# TikHub 小红书热榜。文档常见 endpoint，可通过环境变量覆盖。
TIKHUB_XHS_HOT_URL = os.getenv(
    "TIKHUB_XHS_HOT_URL",
    "https://api.tikhub.io/api/v1/xiaohongshu/web_v2/fetch_hot_list",
)
# TikHub 文档推荐 App V2 > App > Web V3 > Web V2 > Web。
# 搜索笔记比热榜更适合小红书选题，可用 --keyword 触发。
TIKHUB_XHS_SEARCH_URL = os.getenv(
    "TIKHUB_XHS_SEARCH_URL",
    "https://api.tikhub.io/api/v1/xiaohongshu/app_v2/search_notes",
)
TIKHUB_API_KEY = os.getenv("TIKHUB_API_KEY") or os.getenv("TIKHUB_KEY")

# RNote：不同套餐/部署 endpoint 可能不同，因此默认要求显式配置 URL。
RNOTE_XHS_HOT_URL = os.getenv("RNOTE_XHS_HOT_URL")
RNOTE_XHS_SEARCH_URL = os.getenv("RNOTE_XHS_SEARCH_URL")
RNOTE_API_KEY = os.getenv("RNOTE_API_KEY") or os.getenv("RNOTE_KEY")

# ALAPI 今日热榜。type 名称在不同版本中可能变化，因此用环境变量可配置。
ALAPI_HOT_URL = os.getenv("ALAPI_HOT_URL", "https://v2.alapi.cn/api/tophub")
ALAPI_TOKEN = os.getenv("ALAPI_TOKEN") or os.getenv("ALAPI_KEY")
ALAPI_WECHAT_TYPE = os.getenv("ALAPI_WECHAT_TYPE", "weixin")
ALAPI_XHS_TYPE = os.getenv("ALAPI_XHS_TYPE", "xiaohongshu")


class FetchError(Exception):
    pass


def now_iso() -> str:
    return datetime.now().isoformat()


def curl_json(
    url: str,
    *,
    headers: Optional[List[str]] = None,
    timeout: int = 30,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
) -> Any:
    """用 curl 请求 JSON，避免引入 requests 依赖。"""
    cmd = ["curl", "-sL", "--max-time", str(timeout), url]
    cmd += ["-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"]
    cmd += ["-H", "Accept: application/json, text/plain, */*"]
    if headers:
        for h in headers:
            cmd += ["-H", h]
    if method.upper() != "GET":
        cmd += ["-X", method.upper()]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", json.dumps(data, ensure_ascii=False)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    except subprocess.TimeoutExpired as exc:
        raise FetchError(f"Timeout: {exc}") from exc

    raw = result.stdout.strip()
    if not raw:
        raise FetchError("Empty response")
    if "<!DOCTYPE html>" in raw or "<html" in raw[:200].lower():
        if "cloudflare" in raw.lower():
            raise FetchError("Cloudflare blocking")
        raise FetchError("HTML response, expected JSON")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Invalid JSON response: {raw[:200]}") from exc


def first_list(data: Any, paths: Iterable[Tuple[Any, ...]]) -> List[Any]:
    """从多个候选路径中取第一个 list。路径元素可为 dict key 或 list index。"""
    for path in paths:
        cur = data
        ok = True
        for key in path:
            try:
                if isinstance(key, int):
                    cur = cur[key]
                else:
                    cur = cur.get(key) if isinstance(cur, dict) else None
            except Exception:
                ok = False
                break
            if cur is None:
                ok = False
                break
        if ok and isinstance(cur, list):
            return cur
    if isinstance(data, list):
        return data
    return []


def pick(item: Any, *keys: str, default: str = "") -> Any:
    if not isinstance(item, dict):
        return default
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return default



# 信源可信度评分：用于上层选题过滤。
# 说明：这是“来源质量”而非“事实真伪”判断；正式成文仍需搜索/抓取官方原文交叉验证。
TRUSTED_DOMAIN_SCORES = {
    # 官方 / 一手来源
    "openai.com": 98,
    "anthropic.com": 98,
    "googleblog.com": 97,
    "blog.google": 97,
    "ai.google.dev": 97,
    "deepmind.google": 97,
    "microsoft.com": 96,
    "github.com": 95,
    "huggingface.co": 95,
    "meta.com": 94,
    "about.fb.com": 94,
    "x.ai": 94,
    "developer.nvidia.com": 94,
    "nvidia.com": 94,
    "alibabacloud.com": 92,
    "qwenlm.github.io": 92,
    "modelscope.cn": 90,
    # 权威科技/商业媒体
    "technologyreview.com": 92,
    "theverge.com": 90,
    "techcrunch.com": 90,
    "wired.com": 90,
    "bloomberg.com": 90,
    "reuters.com": 92,
    "ft.com": 90,
    "36kr.com": 88,
    "jiqizhixin.com": 88,
    "leiphone.com": 86,
    "ithome.com": 84,
    # 技术/社区平台
    "news.ycombinator.com": 82,
    "producthunt.com": 82,
    "juejin.cn": 78,
    "v2ex.com": 76,
    "sspai.com": 76,
    "zhihu.com": 74,
    "bilibili.com": 70,
    # 泛社交/短视频/搜索热榜：只适合做热度线索，不能单独作为事实依据
    "weibo.com": 55,
    "s.weibo.com": 55,
    "xiaohongshu.com": 55,
    "douyin.com": 52,
    "baidu.com": 50,
}

PLATFORM_BASE_CREDIBILITY = {
    "github": 88,
    "hackernews": 82,
    "producthunt": 82,
    "ithome": 84,
    "juejin": 78,
    "v2ex": 76,
    "sspai": 76,
    "zhihu": 74,
    "bilibili": 70,
    "weixin": 65,
    "wechat": 65,
    "toutiao": 58,
    "weibo": 55,
    "xiaohongshu": 55,
    "xhs": 55,
    "douyin": 52,
    "baidu": 50,
}

RED_FLAG_TERMS = [
    "震惊", "惊呆", "炸裂", "爆了", "全网疯传", "疯传", "网传", "据说", "传言", "小道消息",
    "内部消息", "知情人士", "绝对", "必然", "彻底取代", "颠覆", "遥遥领先", "封神", "杀疯了",
]

def _domain_from_url(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host

def _lookup_domain_score(domain: str) -> Optional[int]:
    if not domain:
        return None
    if domain in TRUSTED_DOMAIN_SCORES:
        return TRUSTED_DOMAIN_SCORES[domain]
    parts = domain.split(".")
    for i in range(1, max(len(parts) - 1, 1)):
        parent = ".".join(parts[i:])
        if parent in TRUSTED_DOMAIN_SCORES:
            return TRUSTED_DOMAIN_SCORES[parent]
    return None

def credibility_meta(title: str, url: str, platform: str) -> Dict[str, Any]:
    domain = _domain_from_url(url)
    domain_score = _lookup_domain_score(domain)
    base_score = domain_score if domain_score is not None else PLATFORM_BASE_CREDIBILITY.get(platform, 60)
    red_flags = [term for term in RED_FLAG_TERMS if term in title]
    score = max(0, min(100, int(base_score) - len(red_flags) * 8))
    if score >= 90:
        level = "official_or_authoritative"
    elif score >= 80:
        level = "reliable_media_or_tech_community"
    elif score >= 70:
        level = "community_signal"
    elif score >= 55:
        level = "social_signal_needs_verification"
    else:
        level = "low_confidence_lead_only"
    return {
        "credibility_score": score,
        "credibility_level": level,
        "source_domain": domain,
        "red_flags": red_flags,
    }

def normalize_items(
    items: List[Any],
    *,
    platform: str,
    source: str,
    title_keys: Tuple[str, ...] = ("title", "word", "name", "keyword", "query", "desc"),
    url_keys: Tuple[str, ...] = ("url", "link", "share_url", "note_url", "target_url"),
    hot_keys: Tuple[str, ...] = ("hot_value", "hot", "score", "heat", "views", "view", "num", "rank_value"),
) -> List[Dict[str, Any]]:
    topics: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, 1):
        if isinstance(item, str):
            title = item
            url = ""
            hot = ""
            desc = ""
            raw = item
        elif isinstance(item, dict):
            title = str(pick(item, *title_keys, default="")).strip()
            # 常见嵌套字段兜底
            if not title and isinstance(item.get("topic"), dict):
                title = str(pick(item["topic"], *title_keys, default="")).strip()
            url = str(pick(item, *url_keys, default="")).strip()
            hot = pick(item, *hot_keys, default="")
            desc = pick(item, "description", "desc", "summary", "abstract", default="")
            if "extra" in item and isinstance(item["extra"], dict):
                hot = hot or item["extra"].get("info", "")
                desc = desc or item["extra"].get("hover", "")
            raw = item
        else:
            continue
        if not title:
            continue
        topic: Dict[str, Any] = {
            "rank": idx,
            "title": title,
            "url": url,
            "hot_value": hot,
            "description": desc,
            "source": source,
            "platform": platform,
        }
        topic.update(credibility_meta(title, url, platform))
        # 小红书/文章类指标兜底保留
        if isinstance(raw, dict):
            metrics = {}
            for src_key, dst_key in [
                ("liked_count", "like"),
                ("likes", "like"),
                ("collected_count", "collect"),
                ("collects", "collect"),
                ("comments_count", "comment"),
                ("comments", "comment"),
                ("share_count", "share"),
                ("shares", "share"),
            ]:
                if src_key in raw:
                    metrics[dst_key] = raw[src_key]
            if metrics:
                topic["metrics"] = metrics
        topics.append(topic)
    return topics


def success_result(platform: str, source: str, topics: List[Dict[str, Any]], **extra: Any) -> Dict[str, Any]:
    return {
        "platform": platform,
        "platform_name": PLATFORM_IDS.get(platform, platform),
        "source": source,
        "timestamp": now_iso(),
        "success": True,
        "topics": topics,
        **extra,
    }


def error_result(platform: str, source: str, error: str, **extra: Any) -> Dict[str, Any]:
    return {
        "platform": platform,
        "platform_name": PLATFORM_IDS.get(platform, platform),
        "source": source,
        "timestamp": now_iso(),
        "success": False,
        "error": error,
        "topics": [],
        **extra,
    }


def fetch_newsnow(platform: str, latest: bool = True) -> Dict[str, Any]:
    source = "newsnow"
    api_platform = NEWSNOW_PLATFORM_ALIASES.get(platform, platform)
    params = {"id": api_platform, "latest": "true" if latest else "false"}
    url = f"{NEWSNOW_API_BASE_URL}?{urllib.parse.urlencode(params)}"
    try:
        data = curl_json(url, headers=["Referer: https://newsnow.busiyi.world/"])
        if isinstance(data, dict) and data.get("error"):
            raise FetchError(data.get("message") or data.get("statusMessage") or "newsnow error")
        items = first_list(data, [("items",), ("data",), ("result",), ("data", "items")])
        topics = normalize_items(items, platform=platform, source=source)
        return success_result(platform, source, topics, request_url=url)
    except Exception as exc:
        return error_result(platform, source, str(exc), request_url=url)


def fetch_juhe_wechat(platform: str = "weixin") -> Dict[str, Any]:
    source = "juhe"
    if not JUHE_API_KEY:
        return error_result(platform, source, "Missing JUHE_API_KEY")
    params = {"key": JUHE_API_KEY}
    # 允许用户通过环境变量追加 page/size 等参数，如 JUHE_WECHAT_PARAMS='{"page":1}'
    extra_params = os.getenv("JUHE_WECHAT_PARAMS")
    if extra_params:
        try:
            params.update(json.loads(extra_params))
        except json.JSONDecodeError:
            return error_result(platform, source, "Invalid JUHE_WECHAT_PARAMS JSON")
    url = f"{JUHE_WECHAT_URL}?{urllib.parse.urlencode(params)}"
    try:
        data = curl_json(url)
        code = data.get("error_code", data.get("code")) if isinstance(data, dict) else None
        # Juhe 常见成功码 error_code=0；兼容其他服务 code=200/0。
        if code not in (None, 0, "0", 200, "200"):
            msg = data.get("reason") or data.get("msg") or data.get("message") or f"code={code}"
            raise FetchError(str(msg))
        items = first_list(data, [("result",), ("result", "list"), ("result", "data"), ("data",), ("data", "list")])
        topics = normalize_items(items, platform=platform, source=source)
        return success_result(platform, source, topics, request_url=JUHE_WECHAT_URL)
    except Exception as exc:
        return error_result(platform, source, str(exc), request_url=JUHE_WECHAT_URL)



def check_tikhub_error(data: Any) -> None:
    if not isinstance(data, dict):
        return
    detail = data.get("detail")
    if isinstance(detail, dict) and detail.get("code") not in (None, 0, "0", 200, "200"):
        raise FetchError(str(detail.get("message_zh") or detail.get("message") or f"code={detail.get('code')}"))
    code = data.get("code") or data.get("status_code")
    if code not in (None, 0, "0", 200, "200") and not data.get("data"):
        raise FetchError(str(data.get("message_zh") or data.get("message") or data.get("msg") or f"code={code}"))


def flatten_xhs_search_items(items: List[Any]) -> List[Any]:
    """TikHub 小红书搜索结果常见结构是 item.note，归一化为笔记对象。"""
    flattened: List[Any] = []
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("note"), dict):
            note = dict(item["note"])
            # 保留外层搜索结果字段
            for k in ("id", "model_type"):
                if k in item and k not in note:
                    note[k] = item[k]
            flattened.append(note)
        else:
            flattened.append(item)
    return flattened


def normalize_xhs_notes(items: List[Any], *, platform: str, source: str) -> List[Dict[str, Any]]:
    notes = flatten_xhs_search_items(items)
    topics = []
    for idx, item in enumerate(notes, 1):
        if isinstance(item, dict):
            title = str(pick(item, "display_title", "title", "desc", "name", default="")).strip()
            url = str(pick(item, "url", "share_url", "note_url", "target_url", default="")).strip()
            note_id = pick(item, "note_id", "id", default="")
            interact = item.get("interact_info") if isinstance(item.get("interact_info"), dict) else {}
            hot = pick(item, "hot_value", "liked_count", default="") or interact.get("liked_count", "")
            desc = pick(item, "desc", "description", default="")
            metrics = {}
            for raw_key, dst_key in [
                ("liked_count", "like"), ("collected_count", "collect"),
                ("comment_count", "comment"), ("share_count", "share"),
            ]:
                if raw_key in item:
                    metrics[dst_key] = item[raw_key]
                if raw_key in interact:
                    metrics[dst_key] = interact[raw_key]
            if not title:
                continue
            topic = {
                "rank": idx,
                "title": title,
                "url": url,
                "hot_value": hot,
                "description": desc,
                "source": source,
                "platform": platform,
            }
            if note_id:
                topic["note_id"] = note_id
            if metrics:
                topic["metrics"] = metrics
            topics.append(topic)
        elif isinstance(item, str):
            topics.append({"rank": idx, "title": item, "url": "", "hot_value": "", "description": "", "source": source, "platform": platform})
    return topics

def fetch_tikhub_xhs(platform: str = "xiaohongshu") -> Dict[str, Any]:
    source = "tikhub"
    if not TIKHUB_API_KEY:
        return error_result(platform, source, "Missing TIKHUB_API_KEY")
    headers = [f"Authorization: Bearer {TIKHUB_API_KEY}"]
    # 某些服务使用 X-API-Key；同时带上通常无害。
    headers.append(f"X-API-Key: {TIKHUB_API_KEY}")
    try:
        data = curl_json(TIKHUB_XHS_HOT_URL, headers=headers)
        check_tikhub_error(data)
        items = first_list(
            data,
            [
                ("data", "items"),
                ("data", "list"),
                ("data", "hot_list"),
                ("data",),
                ("items",),
                ("result",),
            ],
        )
        topics = normalize_items(items, platform=platform, source=source)
        return success_result(platform, source, topics, request_url=TIKHUB_XHS_HOT_URL)
    except Exception as exc:
        return error_result(platform, source, str(exc), request_url=TIKHUB_XHS_HOT_URL)



def fetch_tikhub_xhs_search(platform: str = "xiaohongshu", keyword: str = "AI工具", page: int = 1) -> Dict[str, Any]:
    source = "tikhub_search"
    if not TIKHUB_API_KEY:
        return error_result(platform, source, "Missing TIKHUB_API_KEY")
    headers = [f"Authorization: Bearer {TIKHUB_API_KEY}", f"X-API-Key: {TIKHUB_API_KEY}"]
    params = {
        "keyword": keyword,
        "page": page,
        "sort_type": os.getenv("TIKHUB_XHS_SEARCH_SORT", "popularity_descending"),
        "note_type": os.getenv("TIKHUB_XHS_NOTE_TYPE", "不限"),
        "time_filter": os.getenv("TIKHUB_XHS_TIME_FILTER", "一周内"),
        "search_id": os.getenv("TIKHUB_XHS_SEARCH_ID", ""),
        "search_session_id": os.getenv("TIKHUB_XHS_SEARCH_SESSION_ID", ""),
        "source": os.getenv("TIKHUB_XHS_SOURCE", "explore_feed"),
        "ai_mode": os.getenv("TIKHUB_XHS_AI_MODE", "0"),
    }
    url = f"{TIKHUB_XHS_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        data = curl_json(url, headers=headers)
        check_tikhub_error(data)
        items = first_list(
            data,
            [
                ("data", "items"), ("data", "notes"), ("data", "list"),
                ("data", "data", "items"), ("data", "data", "notes"),
                ("items",), ("result",),
            ],
        )
        topics = normalize_xhs_notes(items, platform=platform, source=source)
        return success_result(platform, source, topics, request_url=TIKHUB_XHS_SEARCH_URL, keyword=keyword)
    except Exception as exc:
        return error_result(platform, source, str(exc), request_url=TIKHUB_XHS_SEARCH_URL, keyword=keyword)


def fetch_rnote_xhs(platform: str = "xiaohongshu", keyword: Optional[str] = None) -> Dict[str, Any]:
    source = "rnote"
    url = RNOTE_XHS_SEARCH_URL if keyword else RNOTE_XHS_HOT_URL
    if not url:
        env_name = "RNOTE_XHS_SEARCH_URL" if keyword else "RNOTE_XHS_HOT_URL"
        return error_result(platform, source, f"Missing {env_name}")
    if not RNOTE_API_KEY:
        return error_result(platform, source, "Missing RNOTE_API_KEY")
    sep = "&" if "?" in url else "?"
    if keyword:
        url = f"{url}{sep}{urllib.parse.urlencode({'keyword': keyword})}"
    headers = [f"Authorization: Bearer {RNOTE_API_KEY}", f"X-API-Key: {RNOTE_API_KEY}"]
    try:
        data = curl_json(url, headers=headers)
        items = first_list(data, [("data", "items"), ("data", "notes"), ("data", "list"), ("data",), ("items",), ("result",)])
        topics = normalize_items(items, platform=platform, source=source)
        return success_result(platform, source, topics, request_url=url)
    except Exception as exc:
        return error_result(platform, source, str(exc), request_url=url)


def fetch_alapi(platform: str, type_name: str) -> Dict[str, Any]:
    source = "alapi"
    if not ALAPI_TOKEN:
        return error_result(platform, source, "Missing ALAPI_TOKEN")
    params = {"token": ALAPI_TOKEN, "type": type_name}
    extra = os.getenv("ALAPI_PARAMS")
    if extra:
        try:
            params.update(json.loads(extra))
        except json.JSONDecodeError:
            return error_result(platform, source, "Invalid ALAPI_PARAMS JSON")
    url = f"{ALAPI_HOT_URL}?{urllib.parse.urlencode(params)}"
    try:
        data = curl_json(url)
        code = data.get("code") if isinstance(data, dict) else None
        if code not in (None, 0, "0", 200, "200"):
            msg = data.get("msg") or data.get("message") or f"code={code}"
            raise FetchError(str(msg))
        items = first_list(data, [("data",), ("data", "list"), ("data", "items"), ("result",), ("items",)])
        # ALAPI 有时 data 是 dict，列表藏在更深处
        if not items and isinstance(data, dict) and isinstance(data.get("data"), dict):
            items = first_list(data["data"], [("list",), ("items",), ("data",)])
        topics = normalize_items(items, platform=platform, source=source)
        return success_result(platform, source, topics, request_url=ALAPI_HOT_URL, alapi_type=type_name)
    except Exception as exc:
        return error_result(platform, source, str(exc), request_url=ALAPI_HOT_URL, alapi_type=type_name)


def fetch_direct(platform: str, url: str, source: str = "direct") -> Dict[str, Any]:
    try:
        data = curl_json(url)
        items = first_list(data, [("data", "items"), ("data", "list"), ("data",), ("items",), ("result",), ("list",)])
        topics = normalize_items(items, platform=platform, source=source)
        return success_result(platform, source, topics, request_url=url)
    except Exception as exc:
        return error_result(platform, source, str(exc), request_url=url)


def platform_fallback_chain(platform: str) -> List[Tuple[str, Dict[str, Any]]]:
    p = platform.lower()
    if p in ("weixin", "wechat", "juhe_wechat", "alapi_wechat"):
        return [
            ("juhe_wechat", {}),
            ("alapi", {"type_name": ALAPI_WECHAT_TYPE}),
            ("newsnow", {}),
        ]
    if p in ("xiaohongshu", "xhs", "tikhub_xhs", "rnote_xhs", "alapi_xhs"):
        return [
            ("tikhub_xhs_search", {}),
            ("tikhub_xhs", {}),
            ("rnote_xhs", {}),
            ("alapi", {"type_name": ALAPI_XHS_TYPE}),
            ("newsnow", {}),
        ]
    return [("newsnow", {})]


def fetch_with_provider(platform: str, provider: str = "auto", latest: bool = True, keyword: Optional[str] = None) -> Dict[str, Any]:
    provider = provider.lower()
    platform = platform.lower()

    def call(name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        if name == "newsnow":
            return fetch_newsnow(platform, latest=latest)
        if name == "juhe_wechat":
            return fetch_juhe_wechat(platform="weixin" if platform in ("wechat", "juhe_wechat") else platform)
        if name == "tikhub_xhs":
            return fetch_tikhub_xhs(platform="xiaohongshu" if platform in ("xhs", "tikhub_xhs") else platform)
        if name == "tikhub_xhs_search":
            return fetch_tikhub_xhs_search(platform="xiaohongshu" if platform in ("xhs", "tikhub_xhs_search") else platform, keyword=keyword or os.getenv("TIKHUB_XHS_KEYWORD", "AI工具"))
        if name == "rnote_xhs":
            return fetch_rnote_xhs(platform="xiaohongshu" if platform in ("xhs", "rnote_xhs") else platform, keyword=keyword)
        if name == "alapi":
            type_name = kwargs.get("type_name") or (ALAPI_XHS_TYPE if platform in ("xiaohongshu", "xhs", "alapi_xhs") else ALAPI_WECHAT_TYPE)
            return fetch_alapi(platform, type_name=type_name)
        if name == "direct":
            direct_url = os.getenv("HOT_TOPICS_DIRECT_URL")
            if not direct_url:
                return error_result(platform, "direct", "Missing HOT_TOPICS_DIRECT_URL")
            return fetch_direct(platform, direct_url)
        return error_result(platform, name, f"Unsupported provider: {name}")

    if provider != "auto":
        provider_aliases = {
            "juhe": "juhe_wechat",
            "tikhub": "tikhub_xhs",
            "tikhub_search": "tikhub_xhs_search",
            "rnote": "rnote_xhs",
        }
        return call(provider_aliases.get(provider, provider), {})

    attempts: List[Dict[str, Any]] = []
    for name, kwargs in platform_fallback_chain(platform):
        result = call(name, kwargs)
        attempts.append({
            "source": result.get("source"),
            "success": result.get("success"),
            "topic_count": len(result.get("topics", [])),
            "error": result.get("error"),
        })
        # 成功且有数据才停止；成功但 0 条时继续 fallback。
        if result.get("success") and result.get("topics"):
            result["fallback_attempts"] = attempts
            return result

    # 如果全失败或全空，返回最后一次结果并附带完整尝试记录。
    final = attempts[-1] if attempts else {}
    result = error_result(platform, "auto", "All providers failed or returned empty topics")
    if attempts:
        result["fallback_attempts"] = attempts
        result["last_attempt"] = final
    return result


def fetch_multiple_platforms(platforms: List[str], provider: str = "auto", latest: bool = True, keyword: Optional[str] = None) -> Dict[str, Any]:
    all_results = [fetch_with_provider(platform, provider=provider, latest=latest, keyword=keyword) for platform in platforms]
    successful = [r for r in all_results if r.get("success")]
    failed = [r for r in all_results if not r.get("success")]
    return {
        "timestamp": now_iso(),
        "total_platforms": len(platforms),
        "successful_count": len(successful),
        "failed_count": len(failed),
        "results": all_results,
        "errors": failed,
    }


def print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def print_plain_text(data: Dict[str, Any]) -> None:
    if not data.get("results"):
        if data.get("success"):
            print(f"\n=== {data.get('platform_name', data.get('platform'))} [{data.get('source')}] ===")
            for i, topic in enumerate(data.get("topics", [])[:20], 1):
                title = topic.get("title", "")
                hot = topic.get("hot_value", "")
                source = topic.get("source", data.get("source", ""))
                print(f"{i}. {title} ({hot}) [{source}]")
        else:
            print(f"抓取失败: {data.get('error', 'Unknown error')}")
            if data.get("fallback_attempts"):
                print("fallback attempts:")
                for a in data["fallback_attempts"]:
                    print(f"  - {a}")
        return

    for result in data["results"]:
        if result.get("success"):
            print(f"\n=== {result.get('platform_name', result.get('platform'))} [{result.get('source')}] ===")
            for i, topic in enumerate(result.get("topics", [])[:10], 1):
                title = topic.get("title", "")
                hot = topic.get("hot_value", "")
                print(f"  {i}. {title} ({hot})")
        else:
            print(f"\n=== {result.get('platform_name', result.get('platform'))} === 抓取失败: {result.get('error')}")
            if result.get("fallback_attempts"):
                for a in result["fallback_attempts"]:
                    print(f"  - {a}")


def parse_platforms(value: str) -> List[str]:
    value = value.strip()
    if value.lower() == "all":
        # all 不包含 weixin/xiaohongshu 的付费替代源，避免无 key 时大量失败；保留原通用平台。
        return [
            "zhihu", "weibo", "baidu", "toutiao", "douyin", "bilibili",
            "ithome", "juejin", "github", "hackernews", "solidot", "v2ex",
            "nowcoder", "pcbeta", "sspai", "producthunt",
        ]
    return [p.strip().lower() for p in value.split(",") if p.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="抓取各平台热搜话题（多数据源/fallback 版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 scripts/fetch_hot_topics.py --platform zhihu
  python3 scripts/fetch_hot_topics.py --platform weixin --provider auto --json
  python3 scripts/fetch_hot_topics.py --platform xiaohongshu --provider auto --json
  python3 scripts/fetch_hot_topics.py --platform tikhub_xhs --provider tikhub --json
  python3 scripts/fetch_hot_topics.py --platform zhihu,weibo,github --json

环境变量:
  JUHE_API_KEY         聚合数据微信热搜榜 key
  TIKHUB_API_KEY       TikHub 小红书 key
  TIKHUB_XHS_SEARCH_URL TikHub 小红书搜索 endpoint
  TIKHUB_XHS_SEARCH_SORT 搜索排序，默认 popularity_descending
  TIKHUB_XHS_TIME_FILTER 时间筛选，默认 一周内
  RNOTE_API_KEY        RNote key
  RNOTE_XHS_HOT_URL    RNote 小红书热榜 endpoint
  RNOTE_XHS_SEARCH_URL RNote 小红书搜索 endpoint
  ALAPI_TOKEN          ALAPI token
  ALAPI_WECHAT_TYPE    ALAPI 微信 type，默认 weixin
  ALAPI_XHS_TYPE       ALAPI 小红书 type，默认 xiaohongshu
  HOT_TOPICS_DIRECT_URL 自定义 JSON 数据源 URL，用 --provider direct 调用
        """,
    )
    parser.add_argument("--platform", "-p", default="zhihu", help="平台ID，多个用逗号分隔，或 all")
    parser.add_argument("--provider", default="auto", choices=["auto", "newsnow", "juhe", "juhe_wechat", "tikhub", "tikhub_xhs", "tikhub_search", "tikhub_xhs_search", "rnote", "rnote_xhs", "alapi", "direct"], help="数据源，默认 auto")
    parser.add_argument("--json", "-j", action="store_true", help="输出JSON格式")
    parser.add_argument("--latest", type=lambda x: x.lower() == "true", default=True, help="是否获取最新榜单")
    parser.add_argument("--keyword", "-k", default=None, help="关键词，当前主要用于 RNote 小红书搜索")
    parser.add_argument("--list-platforms", action="store_true", help="列出支持的平台别名")
    args = parser.parse_args()

    if args.list_platforms:
        print_json({"platforms": PLATFORM_IDS, "newsnow_aliases": NEWSNOW_PLATFORM_ALIASES})
        return

    platforms = parse_platforms(args.platform)
    invalid = [p for p in platforms if p not in PLATFORM_IDS]
    if invalid:
        print(f"错误：不支持的平台ID: {invalid}", file=sys.stderr)
        print(f"支持的平台: {list(PLATFORM_IDS.keys())}", file=sys.stderr)
        sys.exit(1)

    if len(platforms) == 1:
        result = fetch_with_provider(platforms[0], provider=args.provider, latest=args.latest, keyword=args.keyword)
    else:
        result = fetch_multiple_platforms(platforms, provider=args.provider, latest=args.latest, keyword=args.keyword)

    if args.json:
        print_json(result)
    else:
        print_plain_text(result)


if __name__ == "__main__":
    main()
