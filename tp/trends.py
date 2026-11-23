"""Fetch Google Trends' real-time trending list and return trends not yet covered.

Usage:
    python -m tp.trends [--geo IN] [--min-traffic 1000] [--limit 10]

Prints JSON: a list of candidate trends, highest traffic first, each with the
publisher articles Google attached to it.
"""
import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

import requests

from tp import state

FEED = "https://trends.google.com/trending/rss?geo={geo}"
UA = {"User-Agent": "Mozilla/5.0 (compatible; trend-poster/1.0)"}


def _local(tag):
    return tag.split("}", 1)[-1]


def _child_text(el, name):
    for c in el:
        if _local(c.tag) == name:
            return (c.text or "").strip()
    return ""


def parse_traffic(text):
    """'2000+' -> 2000, '20K+' -> 20000, '1M+' -> 1000000."""
    m = re.match(r"([\d.,]+)\s*([KkMm]?)", text or "")
    if not m:
        return 0
    n = float(m.group(1).replace(",", ""))
    mult = {"k": 1_000, "m": 1_000_000}.get(m.group(2).lower(), 1)
    return int(n * mult)


def parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    trends = []
    for item in root.iter("item"):
        news = []
        for c in item:
            if _local(c.tag) == "news_item":
                url = _child_text(c, "news_item_url")
                if url:
                    news.append({
                        "title": _child_text(c, "news_item_title"),
                        "url": url,
                        "source": _child_text(c, "news_item_source"),
                    })
        trends.append({
            "trend": _child_text(item, "title"),
            "traffic": parse_traffic(_child_text(item, "approx_traffic")),
            "started": _child_text(item, "pubDate"),
            "articles": news,
        })
    return trends


def fetch(geo):
    r = requests.get(FEED.format(geo=geo), headers=UA, timeout=30)
    r.raise_for_status()
    return parse_feed(r.content)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--geo", default="IN")
    p.add_argument("--min-traffic", type=int, default=1000)
    p.add_argument("--limit", type=int, default=10)
    a = p.parse_args(argv)

    st = state.load()
    out = []
    for t in sorted(fetch(a.geo), key=lambda t: -t["traffic"]):
        if t["traffic"] < a.min_traffic:
            continue
        why = state.skip_reason(st, t["trend"])
        if why:
            continue
        out.append(t)
        if len(out) >= a.limit:
            break
    json.dump({
        "posts_today": state.posts_today(st),
        "candidates": out,
    }, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
