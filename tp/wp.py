"""Talk to the WordPress REST API.

Configuration (environment):
    WP_URL           e.g. https://example.com   (required)
    Auth, either:
      - a Network secret in the cloud environment that adds an
        "Authorization: Basic ..." header for your site's host (preferred:
        the password never enters the session), or
      - WP_USER and WP_APP_PASSWORD environment variables.
    POST_STATUS      draft (default) | publish | pending

Usage:
    python -m tp.wp check                     # confirm the connection and the user's role
    python -m tp.wp recent [--days 3]         # titles of recent posts (drafts included)
    python -m tp.wp publish article.json      # upload images, create the post, print its URL

article.json:
    {
      "title": "...", "slug": "...", "excerpt": "meta description, <=160 chars",
      "content_html": "<p>...</p> ... {{INFOGRAPHIC_1}} ...",
      "category": "Sports", "tags": ["IPL", "Virat Kohli"],
      "infographics": [{"png": "out/1.png", "alt": "...", "caption": "..."}],
      "sources": [{"title": "...", "url": "https://...", "source": "The Hindu"}]
    }
The first infographic also becomes the featured image. The Sources section is
added here from "sources", so every post links to its real sources.
"""
import argparse
import html
import json
import mimetypes
import os
import sys
from datetime import datetime, timedelta, timezone

import requests


def _base():
    url = os.environ.get("WP_URL", "").rstrip("/")
    if not url:
        sys.exit("WP_URL is not set")
    return url + "/wp-json/wp/v2"


def _session():
    s = requests.Session()
    s.headers["User-Agent"] = "trend-poster/1.0"
    user, pw = os.environ.get("WP_USER"), os.environ.get("WP_APP_PASSWORD")
    if user and pw:
        s.auth = (user, pw)
    return s


def _check(r):
    if r.status_code >= 400:
        sys.exit(f"WordPress error {r.status_code}: {r.text[:500]}")
    return r.json()


def check(s):
    me = _check(s.get(_base() + "/users/me", params={"context": "edit"}, timeout=30))
    print(json.dumps({"name": me.get("name"), "roles": me.get("roles")}, indent=2))


def recent(s, days):
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    posts = _check(s.get(_base() + "/posts", params={
        "after": after, "per_page": 100, "status": "publish,draft,pending,future",
        "context": "edit", "_fields": "id,title,status,date,link"}, timeout=30))
    for p in posts:
        print(f'{p["date"]}  [{p["status"]}]  {p["title"]["raw"]}')


def term_id(s, taxonomy, name):
    found = _check(s.get(f"{_base()}/{taxonomy}", params={"search": name, "per_page": 20}, timeout=30))
    for t in found:
        if html.unescape(t["name"]).strip().lower() == name.strip().lower():
            return t["id"]
    r = s.post(f"{_base()}/{taxonomy}", json={"name": name}, timeout=30)
    if r.status_code == 400 and "term_exists" in r.text:
        return r.json()["data"]["term_id"]
    return _check(r)["id"]


def upload(s, path, alt, caption):
    ctype = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        media = _check(s.post(_base() + "/media", data=f.read(), timeout=120, headers={
            "Content-Type": ctype,
            "Content-Disposition": f'attachment; filename="{os.path.basename(path)}"'}))
    _check(s.post(f"{_base()}/media/{media['id']}", json={"alt_text": alt, "caption": caption}, timeout=30))
    return media["id"], media["source_url"]


def sources_html(sources):
    items = "".join(
        f'<li><a href="{html.escape(x["url"], quote=True)}" target="_blank" rel="noopener nofollow">'
        f'{html.escape(x["title"])}</a>{" (" + html.escape(x["source"]) + ")" if x.get("source") else ""}</li>'
        for x in sources)
    return f"\n<h2>Sources</h2>\n<ul>{items}</ul>\n"


def publish(s, path):
    with open(path, encoding="utf-8") as f:
        a = json.load(f)
    if len(a.get("sources", [])) < 2:
        sys.exit("refusing to post: fewer than 2 sources")
    base_dir = os.path.dirname(os.path.abspath(path))
    content = a["content_html"]
    featured = None
    for i, g in enumerate(a.get("infographics", []), 1):
        png = g["png"] if os.path.isabs(g["png"]) else os.path.join(base_dir, g["png"])
        mid, url = upload(s, png, g.get("alt", ""), g.get("caption", ""))
        featured = featured or mid
        fig = (f'<figure class="wp-block-image size-large"><img src="{url}" alt="{html.escape(g.get("alt", ""), quote=True)}" '
               f'class="wp-image-{mid}"/><figcaption>{html.escape(g.get("caption", ""))}</figcaption></figure>')
        marker = "{{INFOGRAPHIC_%d}}" % i
        content = content.replace(marker, fig) if marker in content else content + fig
    content += sources_html(a["sources"])
    body = {
        "title": a["title"], "content": content, "excerpt": a.get("excerpt", ""),
        "status": os.environ.get("POST_STATUS", "draft"),
        "categories": [term_id(s, "categories", a["category"])] if a.get("category") else [],
        "tags": [term_id(s, "tags", t) for t in a.get("tags", [])[:8]],
    }
    if a.get("slug"):
        body["slug"] = a["slug"]
    if featured:
        body["featured_media"] = featured
    post = _check(s.post(_base() + "/posts", json=body, timeout=60))
    print(json.dumps({"id": post["id"], "status": post["status"], "link": post["link"],
                      "edit": os.environ["WP_URL"].rstrip("/") + f"/wp-admin/post.php?post={post['id']}&action=edit"}))


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    r = sub.add_parser("recent"); r.add_argument("--days", type=int, default=3)
    pb = sub.add_parser("publish"); pb.add_argument("article")
    a = p.parse_args(argv)
    s = _session()
    {"check": lambda: check(s), "recent": lambda: recent(s, a.days),
     "publish": lambda: publish(s, a.article)}[a.cmd]()


if __name__ == "__main__":
    main()
