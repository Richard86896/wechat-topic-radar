#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small Brave Search helper for wechat-topic-radar.

Loads BRAVE_SEARCH_API_KEY from:
1. process environment
2. skill .env.local
3. ~/.config/wechat-topic-radar/env

Never prints the API key.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def load_env_files() -> None:
    candidates = [
        Path(__file__).resolve().parents[1] / ".env.local",
        Path.home() / ".config" / "wechat-topic-radar" / "env",
    ]
    for p in candidates:
        if not p.exists():
            continue
        for raw in p.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def brave_search(query: str, count: int = 5, country: str = "US", search_lang: str = "en") -> dict:
    load_env_files()
    key = os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("BRAVE_API_KEY")
    if not key:
        raise RuntimeError("Missing BRAVE_SEARCH_API_KEY")
    params = {
        "q": query,
        "count": max(1, min(count, 20)),
        "country": country,
        "search_lang": search_lang,
    }
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "X-Subscription-Token": key,
            "User-Agent": "wechat-topic-radar/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--count", type=int, default=5)
    ap.add_argument("--country", default="US")
    ap.add_argument("--search-lang", default="en")
    args = ap.parse_args()
    try:
        print(json.dumps(brave_search(args.query, args.count, args.country, args.search_lang), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
