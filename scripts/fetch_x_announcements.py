#!/usr/bin/env python3
"""
AI 公司官方公告监控脚本（Brave Search 版）

通过 Brave Search API 搜索 AI 公司官方 X 账号的最新推文和公告。
Nitter 镜像已基本不可用，改用 Brave Search 作为主力数据源。

用法：
  python3 scripts/fetch_x_announcements.py                    # 全部高优先级账号
  python3 scripts/fetch_x_announcements.py --accounts openai anthropic
  python3 scripts/fetch_x_announcements.py --json
  python3 scripts/fetch_x_announcements.py --all               # 包含低优先级
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


AI_ACCOUNTS = {
    "openai": {
        "name": "OpenAI",
        "handle": "@OpenAI",
        "importance": "high",
        "x_url": "https://x.com/OpenAI",
        "blog": "https://openai.com/blog",
    },
    "anthropic": {
        "name": "Anthropic",
        "handle": "@AnthropicAI",
        "importance": "high",
        "x_url": "https://x.com/AnthropicAI",
        "blog": "https://www.anthropic.com/news",
    },
    "google_ai": {
        "name": "Google DeepMind",
        "handle": "@GoogleDeepMind",
        "importance": "high",
        "x_url": "https://x.com/GoogleDeepMind",
        "blog": "https://deepmind.google/discover/blog/",
    },
    "meta_ai": {
        "name": "Meta AI",
        "handle": "@MetaAI",
        "importance": "high",
        "x_url": "https://x.com/MetaAI",
        "blog": "https://ai.meta.com/blog/",
    },
    "mistral": {
        "name": "Mistral AI",
        "handle": "@MistralAI",
        "importance": "medium",
        "x_url": "https://x.com/MistralAI",
        "blog": "https://mistral.ai/news/",
    },
    "github": {
        "name": "GitHub",
        "handle": "@github",
        "importance": "medium",
        "x_url": "https://x.com/github",
        "blog": "https://github.blog/",
    },
    "huggingface": {
        "name": "Hugging Face",
        "handle": "@huggingface",
        "importance": "medium",
        "x_url": "https://x.com/huggingface",
        "blog": "https://huggingface.co/blog",
    },
    "deepseek": {
        "name": "DeepSeek",
        "handle": "@deepseek_ai",
        "importance": "medium",
        "x_url": "https://x.com/deepseek_ai",
        "blog": "https://api-docs.deepseek.com/news",
    },
    "ollama": {
        "name": "Ollama",
        "handle": "@ollama",
        "importance": "low",
        "x_url": "https://x.com/ollama",
    },
    "cursor": {
        "name": "Cursor",
        "handle": "@cursor_ai",
        "importance": "low",
        "x_url": "https://x.com/cursor_ai",
    },
    "replit": {
        "name": "Replit",
        "handle": "@reaborat",
        "importance": "low",
        "x_url": "https://x.com/replit",
    },
}


def load_brave_key() -> Optional[str]:
    """Load BRAVE_SEARCH_API_KEY from env or config files."""
    key = os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("BRAVE_API_KEY")
    if key:
        return key

    search_paths = [
        Path(__file__).parent.parent / ".env.local",
        Path.home() / ".config" / "wechat-topic-radar" / "env",
    ]
    for p in search_paths:
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line.startswith("BRAVE_SEARCH_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
                if line.startswith("BRAVE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def brave_search(query: str, api_key: str, count: int = 5) -> List[Dict]:
    """Call Brave Search API and return results."""
    url = (
        "https://api.search.brave.com/res/v1/web/search"
        f"?q={urllib.parse.quote(query)}&count={count}&freshness=pw"
    )
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("web", {}).get("results", [])
    except Exception as e:
        print(f"  Brave search error: {e}", file=sys.stderr)
        return []


def search_account(account_key: str, account: Dict, api_key: str) -> Dict:
    """Search for recent posts from an AI company account."""
    name = account["name"]

    # Strategy 1: Search for latest announcements from the company
    query = f"{name} AI announcement OR release OR launch 2026"
    results = brave_search(query, api_key, count=5)

    # Strategy 2: Search their blog directly
    if account.get("blog"):
        blog_query = f"{account['blog']}"
        blog_results = brave_search(blog_query, api_key, count=3)
        # Deduplicate by URL
        seen_urls = {r.get("url") for r in results}
        for br in blog_results:
            if br.get("url") not in seen_urls:
                results.append(br)

    return {
        "account": account["name"],
        "handle": account["handle"],
        "importance": account["importance"],
        "x_url": account["x_url"],
        "results": results,
        "result_count": len(results),
    }


def main():
    parser = argparse.ArgumentParser(description="Monitor AI company announcements")
    parser.add_argument("--accounts", nargs="*", help="Account keys (openai anthropic ...)")
    parser.add_argument("--all", action="store_true", dest="all_accounts", help="Include low-importance")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    api_key = load_brave_key()
    if not api_key:
        print("ERROR: BRAVE_SEARCH_API_KEY not found. Set env var or add to .env.local", file=sys.stderr)
        sys.exit(1)

    # Filter accounts
    to_check = {}
    for key, info in AI_ACCOUNTS.items():
        if args.accounts and key not in args.accounts:
            continue
        if not args.all_accounts and info["importance"] == "low":
            continue
        to_check[key] = info

    if not to_check:
        print("No accounts to check", file=sys.stderr)
        sys.exit(1)

    results = []
    for key, info in to_check.items():
        print(f"Searching {info['name']}...", file=sys.stderr)
        r = search_account(key, info, api_key)
        results.append(r)

    if args.json_output:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"AI Company Announcements (Brave Search)")
        print(f"Checked {len(results)} accounts")
        print("=" * 70)

        for r in results:
            has_results = r["result_count"] > 0
            status = "✓" if has_results else "✗"
            print(f"\n{status} {r['account']} ({r['handle']}) [{r['importance']}]")
            for item in r["results"][:3]:
                title = item.get("title", "")
                url = item.get("url", "")
                desc = item.get("description", "")[:120]
                print(f"  - {title}")
                if desc:
                    print(f"    {desc}")
                print(f"    {url}")
            if not r["results"]:
                print(f"  无最新结果 → {r['x_url']}")


if __name__ == "__main__":
    main()
