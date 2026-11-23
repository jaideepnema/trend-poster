"""Find freely licensed photos on Wikimedia Commons, with the credit each one needs.

Never use photos from news sites, Google, or social media: those are copyrighted.

Usage:
    python -m tp.photos search "Virat Kohli" [--limit 6]
        Prints JSON candidates: title, description, license, credit, page, url.
    python -m tp.photos download "<url from search>" out/<slug>/photo1.jpg

In article.json, add each chosen photo to "photos":
    {"file": "photo1.jpg", "alt": "...", "caption": "...", "credit": "<credit from search>"}
"""
import argparse
import html
import json
import re
import sys
import time

import requests

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "trend-poster/1.0 (WordPress news blog; python-requests)"}
# Licences that allow commercial reuse. Attribution and share-alike are met by the credit line.
OK_LICENSES = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? [\d.]+|cc by(-sa)?$)", re.I)
MIN_WIDTH = 800


def _clean(text):
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _get(url, **kw):
    """GET with a short backoff: Wikimedia answers 429 when asked too fast."""
    wait = 0
    for _ in range(4):
        time.sleep(wait)
        r = requests.get(url, headers=UA, timeout=60, **kw)
        if r.status_code != 429:
            break
        wait = min(int(r.headers.get("Retry-After", 0) or 0) or 10 * (_ + 1), 45)
    r.raise_for_status()
    return r


def search(query, limit=6):
    params = {
        "action": "query", "format": "json", "formatversion": 2,
        "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 30,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1600,
    }
    r = _get(API, params=params)
    pages = sorted(r.json().get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = _clean(meta.get("LicenseShortName", {}).get("value"))
        if info.get("mime") not in ("image/jpeg", "image/png") or info.get("width", 0) < MIN_WIDTH:
            continue
        if not OK_LICENSES.match(lic):
            continue
        artist = _clean(meta.get("Artist", {}).get("value")) or "Unknown author"
        out.append({
            "title": p["title"].removeprefix("File:"),
            "description": _clean(meta.get("ImageDescription", {}).get("value"))[:300],
            "date": _clean(meta.get("DateTimeOriginal", {}).get("value"))[:40],
            "license": lic,
            "credit": f'{artist[:80]} / {lic}, via Wikimedia Commons',
            "page": info.get("descriptionurl"),
            "url": info.get("thumburl") or info.get("url"),
            "width": info.get("width"),
        })
        if len(out) >= limit:
            break
    return out


def download(url, path):
    r = _get(url)
    with open(path, "wb") as f:
        f.write(r.content)
    return path


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--limit", type=int, default=6)
    d = sub.add_parser("download"); d.add_argument("url"); d.add_argument("path")
    a = p.parse_args(argv)
    if a.cmd == "search":
        json.dump(search(a.query, a.limit), sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print(download(a.url, a.path))


if __name__ == "__main__":
    main()
