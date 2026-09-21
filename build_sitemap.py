#!/usr/bin/env python3
"""
かいごのとなり — sitemap.xml / robots.txt 生成

生成済みの index.html を走査し、noindex が付いていないページだけを sitemap に載せる。
本番URLは data/site.json の site.url を使うので、ドメインを変えるときはそこだけ直す。

使い方:
  python3 build_sitemap.py
"""
import json
import pathlib
import re
from datetime import date

BASE = pathlib.Path(__file__).parent
SITE = json.loads((BASE / "data" / "site.json").read_text(encoding="utf-8"))
ORIGIN = SITE["site"]["url"].rstrip("/")
SKIP_DIRS = {"dist-artifact", "templates", "content", "data", "docs", "node_modules", ".git"}

# 階層ごとの優先度と更新頻度。市区町村ページが主戦場なので最も高くする。
def rank(url_path: str):
    depth = len([p for p in url_path.strip("/").split("/") if p])
    if depth == 0:
        return "1.0", "weekly"
    if depth == 1:
        return "0.8", "weekly"
    if depth == 2:
        return "0.8", "weekly"
    return "0.9", "monthly"


def collect():
    rows = []
    for p in sorted(BASE.rglob("index.html")):
        rel = p.relative_to(BASE)
        if set(rel.parts) & SKIP_DIRS:
            continue
        html = p.read_text(encoding="utf-8")
        if re.search(r'<meta name="robots"[^>]*noindex', html):
            print(f"skip (noindex)  {rel}")
            continue
        url_path = "/" + str(rel.parent).replace("\\", "/").lstrip(".").strip("/")
        url_path = "/" if url_path in ("/", "//") else url_path.rstrip("/") + "/"
        m = re.search(r'"dateModified":\s*"([\d-]+)"', html) or re.search(r"更新日：([\d-]+)", html)
        rows.append((url_path, m.group(1) if m else date.today().isoformat()))
    return rows


def main():
    rows = collect()
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url_path, lastmod in rows:
        pri, freq = rank(url_path)
        out += ["  <url>",
                f"    <loc>{ORIGIN}{url_path}</loc>",
                f"    <lastmod>{lastmod}</lastmod>",
                f"    <changefreq>{freq}</changefreq>",
                f"    <priority>{pri}</priority>",
                "  </url>"]
    out.append("</urlset>")
    (BASE / "sitemap.xml").write_text("\n".join(out) + "\n", encoding="utf-8")

    robots = f"""User-agent: *
Allow: /

# 生成物ではない作業用ディレクトリはクロールさせない
Disallow: /data/
Disallow: /content/
Disallow: /templates/
Disallow: /docs/
Disallow: /dist-artifact/

Sitemap: {ORIGIN}/sitemap.xml
"""
    (BASE / "robots.txt").write_text(robots, encoding="utf-8")
    print(f"\nsitemap.xml  {len(rows)} URLs  (origin: {ORIGIN})")
    for u, m in rows:
        print(f"  {m}  {u}")
    print("robots.txt   written")


if __name__ == "__main__":
    main()
