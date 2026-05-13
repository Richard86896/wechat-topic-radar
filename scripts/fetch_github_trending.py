#!/usr/bin/env python3
"""
GitHub Trending 直接抓取脚本

直接抓取 GitHub Trending 页面，获取每日/每周热门仓库。
不依赖 NewsNow 等聚合源，解决 GitHub 数据滞后问题。

用法：
  python3 scripts/fetch_github_trending.py                        # 全部语言，每日
  python3 scripts/fetch_github_trending.py --lang python           # Python，每日
  python3 scripts/fetch_github_trending.py --since weekly          # 全部语言，每周
  python3 scripts/fetch_github_trending.py --ai-only              # 只看 AI 相关
  python3 scripts/fetch_github_trending.py --json                  # JSON 输出
  python3 scripts/fetch_github_trending.py --limit 10              # 只取前10
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Optional


TRENDING_URL = "https://github.com/trending"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page(url: str) -> Optional[str]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def parse_trending_repos(html: str) -> List[Dict]:
    """Parse GitHub Trending page by extracting <article> blocks."""
    repos = []
    articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)

    for art in articles:
        repo = {}

        # 1. Repo name from <h2> <a href="/owner/repo">
        h2 = re.search(r'<h2[^>]*>(.*?)</h2>', art, re.DOTALL)
        if h2:
            link = re.search(r'href="/([^"]+)"', h2.group(1))
            if link:
                full_name = link.group(1).strip()
                repo["full_name"] = full_name
                repo["url"] = f"https://github.com/{full_name}"
            else:
                continue
        else:
            continue

        # 2. Description: find the last meaningful <p> block
        #    The structure is: <p class="...col-9...">description text</p>
        p_blocks = re.findall(r'<p\s+class="[^"]*"[^>]*>(.*?)</p>', art, re.DOTALL)
        desc = ""
        for p in p_blocks:
            clean = re.sub(r'<[^>]+>', ' ', p).strip()
            clean = re.sub(r'\s+', ' ', clean).strip()
            # Skip blocks that are just buttons or empty
            if clean and len(clean) > 10 and "Star" not in clean and "Sponsor" not in clean:
                desc = clean
        repo["description"] = desc[:200]

        # 3. Language
        lang_m = re.search(r'itemprop="programmingLanguage"[^>]*>\s*([^<]+)', art)
        repo["language"] = lang_m.group(1).strip() if lang_m else ""

        # 4. Stars today
        stars_m = re.search(r'([\d,]+)\s+stars\s+today', art)
        repo["stars_today"] = int(stars_m.group(1).replace(",", "")) if stars_m else 0

        # 5. Total stars and forks from the bottom links
        stat_links = re.findall(
            r'class="Link--muted[^"]*"[^>]*>\s*(?:<[^>]+>)*\s*([\d,km.]+)',
            art
        )
        repo["total_stars"] = stat_links[0] if len(stat_links) >= 1 else ""
        repo["forks"] = stat_links[1] if len(stat_links) >= 2 else ""

        repo["fetched_at"] = datetime.now().isoformat()
        repos.append(repo)

    return repos


def filter_ai_related(repos: List[Dict]) -> List[Dict]:
    ai_keywords = [
        "ai", "llm", "gpt", "claude", "gemini", "transformer", "neural",
        "machine learning", "deep learning", "nlp", "diffusion",
        "rag", "agent", "openai", "anthropic", "deepseek", "mistral",
        "embedding", "inference", "finetune", "fine-tune", "lora",
        "langchain", "llamaindex", "ollama", "copilot", "cursor",
        "vector", "semantic", "prompt", "chatbot", "assistant",
        "training", "dataset", "benchmark", "whisper", "tts",
        "stable diffusion", "midjourney", "autonomous", "reasoning",
    ]
    for repo in repos:
        text = f"{repo.get('full_name', '')} {repo.get('description', '')} {repo.get('language', '')}".lower()
        repo["ai_relevant"] = any(kw in text for kw in ai_keywords)
    return repos


def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub Trending repositories")
    parser.add_argument("--lang", default="", help="Language filter (python, rust, etc.)")
    parser.add_argument("--since", default="daily", choices=["daily", "weekly", "monthly"])
    parser.add_argument("--ai-only", action="store_true", help="Only AI-related repos")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    url = TRENDING_URL
    parts = []
    if args.lang:
        parts.append(args.lang)
    if args.since != "daily":
        parts.append(args.since)
    if parts:
        url += "/" + "/".join(parts)

    html = fetch_page(url)
    if not html:
        print("Failed to fetch GitHub Trending", file=sys.stderr)
        sys.exit(1)

    repos = parse_trending_repos(html)
    if not repos:
        print(f"Parse failed (HTML len={len(html)}, articles may have changed structure)", file=sys.stderr)
        sys.exit(1)

    if args.ai_only:
        repos = filter_ai_related(repos)
        repos = [r for r in repos if r.get("ai_relevant")]

    repos = repos[:args.limit]

    if args.json_output:
        print(json.dumps(repos, ensure_ascii=False, indent=2))
    else:
        print(f"GitHub Trending ({args.since}, lang={'all' if not args.lang else args.lang})")
        print(f"Found {len(repos)} repos" + (" [AI-only]" if args.ai_only else ""))
        print("-" * 70)
        for i, r in enumerate(repos, 1):
            print(f"{i}. {r['full_name']}")
            print(f"   Stars: {r.get('total_stars', '?')} (+{r.get('stars_today', 0)} today) | {r.get('language', '?')}")
            if r.get("description"):
                print(f"   {r['description'][:120]}")
            print(f"   {r['url']}")
            print()


if __name__ == "__main__":
    main()
