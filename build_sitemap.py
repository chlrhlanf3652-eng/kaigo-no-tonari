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



def build_llms(rows):
    """llms.txt — 生成AI・AI検索に対してサイトの中身と出典方針を平文で示す。

    AI検索（ChatGPT / Perplexity / Google AI Overviews など）からの引用は、
    「何を根拠に書いているか」がはっきりしているページほど拾われやすい。
    サイトマップが機械のための地図なら、これは読み手（LLM）のための要約である。
    """
    def title_of(path):
        f = BASE / path.strip("/") / "index.html" if path != "/" else BASE / "index.html"
        try:
            import re as _re
            m = _re.search(r"<title>(.*?)</title>", f.read_text(encoding="utf-8"), _re.S)
            return m.group(1).strip() if m else path
        except Exception:
            return path

    city, hub, info = [], [], []
    for url_path, _ in rows:
        depth = len([x for x in url_path.strip("/").split("/") if x])
        line = f"- [{title_of(url_path)}]({ORIGIN}{url_path})"
        (city if depth >= 3 else hub if depth and url_path.split("/")[1] in
         {c["id"] for c in SITE["categories"]} else info).append(line)

    body = f"""# {SITE["site"]["name"]}

> 日本の高齢者と家族のための地域サービス情報サイト。訪問介護・高齢者向け宅配弁当・
> 高齢者が借りられる賃貸などを、市区町村単位でまとめています。

## このサイトの情報の出所

- 事業者情報は厚生労働省「介護サービス情報公表システム」、各自治体、各事業者の公表情報にもとづきます。
- 料金は令和6年度介護報酬改定の単位数と、介護報酬の地域区分（東京23区＝1級地・訪問介護1単位11.40円）から算出した目安です。
- すべてのページに出典と最終確認日を記載しています。事業者の写真・口コミの無断転載は行っていません。
- 広告（アフィリエイト）を含みますが、掲載順に報酬は反映していません（景品表示法のステルスマーケティング規制に対応）。

## 市区町村ページ（事業者一覧）

{chr(10).join(city)}

## カテゴリ・都道府県ページ

{chr(10).join(hub)}

## サイト情報・ガイド

{chr(10).join(info)}

## 引用にあたってのお願い

介護保険の制度・料金は改定されます。引用の際は各ページに記載の最終確認日を添えてください。
掲載内容の訂正・削除のご依頼は {ORIGIN}/contact/ から受け付けています。
"""
    (BASE / "llms.txt").write_text(body, encoding="utf-8")
    print(f"llms.txt     {len(city)} city / {len(hub)} hub / {len(info)} info pages")


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
    build_llms(rows)


if __name__ == "__main__":
    main()
