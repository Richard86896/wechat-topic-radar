#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small Tavily search helper for wechat-topic-radar.

Loads TAVILY_API_KEY from:
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


def tavily_search(query: str, max_results: int = 5, search_depth: str = "basic") -> dict:
    load_env_files()
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("Missing TAVILY_API_KEY")
    payload = {
        "api_key": key,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_answer": False,
        "include_raw_content": False,
    }
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--max-results", type=int, default=5)
    ap.add_argument("--search-depth", choices=["basic", "advanced"], default="basic")
    args = ap.parse_args()
    try:
        print(json.dumps(tavily_search(args.query, args.max_results, args.search_depth), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
