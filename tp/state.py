"""Remembers which trends were already handled, so nothing is written twice.

State lives in state/covered.json in the repo; the hourly session commits it.

Usage:
    python -m tp.state mark "<trend>" --result posted|skipped [--note "..."] [--url URL]
    python -m tp.state show
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "state", "covered.json")
KEEP_DAYS = 10
SIMILARITY = 0.6  # word overlap above which two trends count as the same story
STOPWORDS = {"the", "a", "an", "of", "in", "on", "vs", "and", "to", "for", "news", "today", "live"}


def now():
    return datetime.now(IST)


def load():
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"entries": []}


def save(st):
    cutoff = (now() - timedelta(days=KEEP_DAYS)).isoformat()
    st["entries"] = [e for e in st["entries"] if e["at"] >= cutoff]
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)
        f.write("\n")


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def similar(a, b):
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return a.strip().lower() == b.strip().lower()
    return len(wa & wb) / len(wa | wb) >= SIMILARITY


def skip_reason(st, trend):
    """Why a trend should not be attempted now, or None."""
    for e in st["entries"]:
        if not similar(e["trend"], trend):
            continue
        if e["result"] == "posted":
            return "already posted"
        # A skip (e.g. too few sources) may be retried after 3 hours.
        if datetime.fromisoformat(e["at"]) > now() - timedelta(hours=3):
            return "skipped recently"
    return None


def posts_today(st):
    today = now().date().isoformat()
    return sum(1 for e in st["entries"] if e["result"] == "posted" and e["at"][:10] == today)


def mark(trend, result, note="", url=""):
    st = load()
    st["entries"].append({"trend": trend, "result": result, "note": note,
                          "url": url, "at": now().isoformat(timespec="seconds")})
    save(st)


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mark")
    m.add_argument("trend")
    m.add_argument("--result", choices=["posted", "skipped"], required=True)
    m.add_argument("--note", default="")
    m.add_argument("--url", default="")
    sub.add_parser("show")
    a = p.parse_args(argv)
    if a.cmd == "mark":
        mark(a.trend, a.result, a.note, a.url)
        print("ok")
    else:
        st = load()
        print(json.dumps({"posts_today": posts_today(st), **st}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
