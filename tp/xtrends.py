"""India's X (Twitter) trending topics, read from the free public aggregator getdaytrends.com.

X's own trends API is paid, so this reads a public page instead. It has no
official guarantee: if the page layout changes or the site is down, this
prints an error and exits with code 2, and the run should carry on with
Google Trends alone.

Usage:
    python -m tp.xtrends [--limit 25] [--min-tweets 0]

Prints JSON: candidates in X's own ranking (1 = top), with a tweet count when
the site shows one. These trends carry no news links; research them with
search. Many X trends are hashtag campaigns, greetings or fan hashtags, so
apply the playbook's rules strictly.
"""
import argparse
import html
import json
import re
import sys

import requests

from tp import state

URL = "https://getdaytrends.com/india/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; trend-poster/1.0)"}


def parse_count(text):
    m = re.match(r"([\d.,]+)\s*([KkMm]?)\s*tweets", text or "")
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    return int(n * {"k": 1_000, "m": 1_000_000}.get(m.group(2).lower(), 1))


def parse_page(page):
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        pos = re.search(r'class="pos">\s*(\d+)\s*<', row)
        name = re.search(r'<td class="main"><a[^>]*>(.*?)</a>', row, re.S)
        if not (pos and name):
            continue
        tw = re.search(r'class="small text-muted">([^<]*)<', row)
        out.append({
            "rank": int(pos.group(1)),
            "trend": html.unescape(re.sub(r"<[^>]+>", "", name.group(1))).strip(),
            "tweets": parse_count(tw.group(1)) if tw else None,
        })
    return out


def fetch():
    r = requests.get(URL, headers=UA, timeout=30)
    r.raise_for_status()
    trends = parse_page(r.text)
    if len(trends) < 10:  # layout changed or a block page
        raise RuntimeError(f"expected 30+ trends, parsed {len(trends)}")
    return trends


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--min-tweets", type=int, default=0)
    a = p.parse_args(argv)
    try:
        trends = fetch()
    except Exception as e:  # network, block page, layout change
        print(json.dumps({"source": "x", "error": str(e), "candidates": []}))
        sys.exit(2)
    st = state.load()
    out = [t for t in trends
           if (t["tweets"] or 0) >= a.min_tweets and not state.skip_reason(st, t["trend"])]
    json.dump({"source": "x", "candidates": out[:a.limit]}, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
