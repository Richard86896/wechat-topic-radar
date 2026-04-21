#!/usr/bin/env python3
"""
热搜话题抓取脚本
从 newsnow.busiyi.world API 抓取各平台热搜榜单

支持平台: zhihu, weibo, weixin, baidu, toutiao, douyin, bilibili, xiaohongshu, ithome, juejin, github, hackernews, solidot, v2ex, nowcoder, pcbeta, sspai, producthunt
"""

import argparse
import json
import subprocess
import sys
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any


# 支持的平台ID映射
PLATFORM_IDS = {
    # 主流平台
    "zhihu": "知乎",
    "weibo": "微博热搜",
    "weixin": "微信热文",
    "baidu": "百度热搜",
    "toutiao": "今日头条",
    "douyin": "抖音热榜",
    "bilibili": "B站热榜",
    "xiaohongshu": "小红书",
    # 科技类平台
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
}

# API基础URL
API_BASE_URL = "https://newsnow.busiyi.world/api/s"


def fetch_hot_topics(platform: str, latest: bool = True) -> Dict[str, Any]:
    """
    抓取指定平台的热搜榜单

    Args:
        platform: 平台ID (如 zhihu, weibo 等)
        latest: 是否获取最新榜单

    Returns:
        包含热搜话题的字典
    """
    params = {
        "id": platform,
        "latest": "true" if latest else "false"
    }

    try:
        full_url = f"{API_BASE_URL}?{urllib.parse.urlencode(params)}"
        result = subprocess.run(
            ['curl', '-sL', full_url,
             '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
             '-H', 'Accept: application/json, text/plain, */*',
             '-H', 'Accept-Language: zh-CN,zh;q=0.9,en;q=0.8',
             '-H', 'Referer: https://newsnow.busiyi.world/'],
            capture_output=True,
            text=True,
            timeout=30
        )
        raw_data = result.stdout

        # 检查是否被Cloudflare拦截
        if "<!DOCTYPE html>" in raw_data or "cloudflare" in raw_data.lower():
            return {
                "platform": platform,
                "platform_name": PLATFORM_IDS.get(platform, platform),
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": "Cloudflare blocking",
                "topics": []
            }

        data = json.loads(raw_data)

        # 解析 newsnow API 响应格式
        items = []
        if isinstance(data, dict):
            if "items" in data:
                items = data.get("items", [])
            elif "data" in data:
                items = data.get("data", [])

        # 转换为统一格式
        topics = []
        for idx, item in enumerate(items, 1):
            topic = {
                "rank": idx,
                "title": item.get("title", ""),
                "url": item.get("url", ""),
            }
            if "extra" in item and isinstance(item["extra"], dict):
                topic["hot_value"] = item["extra"].get("info", "")
                topic["description"] = item["extra"].get("hover", "")
            topics.append(topic)

        return {
            "platform": platform,
            "platform_name": PLATFORM_IDS.get(platform, platform),
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "topics": topics
        }
    except subprocess.TimeoutExpired as e:
        return {
            "platform": platform,
            "platform_name": PLATFORM_IDS.get(platform, platform),
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": str(e),
            "topics": []
        }
    except json.JSONDecodeError:
        return {
            "platform": platform,
            "platform_name": PLATFORM_IDS.get(platform, platform),
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": "Invalid JSON response",
            "topics": []
        }


def fetch_multiple_platforms(platforms: List[str]) -> Dict[str, Any]:
    """
    抓取多个平台的热搜榜单

    Args:
        platforms: 平台ID列表

    Returns:
        合并的结果
    """
    all_results = []
    for platform in platforms:
        result = fetch_hot_topics(platform)
        all_results.append(result)

    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]

    return {
        "timestamp": datetime.now().isoformat(),
        "total_platforms": len(platforms),
        "successful_count": len(successful),
        "failed_count": len(failed),
        "results": all_results,
        "errors": [r for r in failed]
    }


def print_json(data: Dict[str, Any]) -> None:
    """格式化输出JSON"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def print_plain_text(data: Dict[str, Any]) -> None:
    """简化输出，便于阅读"""
    if not data.get("results"):
        # 单平台结果
        if data.get("success"):
            print(f"\n=== {data['platform_name']} 热榜 ===")
            for i, topic in enumerate(data.get("topics", [])[:20], 1):
                title = topic.get("title", topic.get("word", ""))
                hot = topic.get("hot_value", "")
                print(f"{i}. {title} ({hot})")
        else:
            print(f"抓取失败: {data.get('error', 'Unknown error')}")
        return

    # 多平台结果
    for result in data["results"]:
        if result["success"]:
            print(f"\n=== {result['platform_name']} ===")
            for i, topic in enumerate(result.get("topics", [])[:10], 1):
                title = topic.get("title", topic.get("word", ""))
                hot = topic.get("hot_value", "")
                print(f"  {i}. {title} ({hot})")
        else:
            print(f"\n=== {result['platform_name']} === 抓取失败")


def main():
    parser = argparse.ArgumentParser(
        description="抓取各平台热搜话题",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
支持平台:
  zhihu       知乎热榜
  weibo       微博热搜
  weixin      微信热文
  baidu       百度热搜
  toutiao     今日头条
  douyin      抖音热榜
  bilibili    B站热榜
  xiaohongshu 小红书

示例:
  python3 fetch_hot_topics.py --platform zhihu
  python3 fetch_hot_topics.py --platform zhihu,weibo --json
  python3 fetch_hot_topics.py --platform all
        """
    )

    parser.add_argument(
        "--platform", "-p",
        type=str,
        default="zhihu",
        help="平台ID，多个用逗号分隔，或用 'all' 获取所有平台"
    )

    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="输出JSON格式"
    )

    parser.add_argument(
        "--latest",
        type=lambda x: x.lower() == "true",
        default=True,
        help="是否获取最新榜单 (true/false)"
    )

    args = parser.parse_args()

    # 解析平台列表
    if args.platform.lower() == "all":
        platforms = list(PLATFORM_IDS.keys())
    elif "," in args.platform:
        platforms = [p.strip() for p in args.platform.split(",")]
    else:
        platforms = [args.platform]

    # 验证平台ID
    invalid = [p for p in platforms if p not in PLATFORM_IDS]
    if invalid:
        print(f"错误：不支持的平台ID: {invalid}")
        print(f"支持的平台: {list(PLATFORM_IDS.keys())}")
        sys.exit(1)

    # 抓取数据
    if len(platforms) == 1:
        result = fetch_hot_topics(platforms[0], args.latest)
    else:
        result = fetch_multiple_platforms(platforms)

    # 输出
    if args.json:
        print_json(result)
    else:
        print_plain_text(result)


if __name__ == "__main__":
    main()