#!/usr/bin/env python3
"""
かいごのとなり — 市区町村ページ生成ビルダー

  data/<slug>.json      … ページのデータ（メタ情報・掲載事業者・FAQ・内部リンク）
  content/<slug>.html   … そのカテゴリ固有の解説本文（{{LISTING}} / {{FAQ}} を差し込む）
  templates/city.html   … 全ページ共通の骨組み

  slug の規約: <category_id>_<pref_id>_<city_id>
  出力先:      <category_id>/<pref_id>/<city_id>/index.html

使い方:
  python3 build.py            # data/ 配下すべてを生成
  python3 build.py houmon-kaigo_tokyo_setagaya   # 個別に生成

依存ライブラリなし（標準ライブラリのみ）。
"""
import json
import pathlib
import re
import sys

BASE = pathlib.Path(__file__).parent
SITE = "https://kaigonotonari.com"


def image_size(path: pathlib.Path, fallback=(1200, 630)):
    """PNG/JPEG の実寸を読む。読めなければ fallback を返す（CLS 対策の width/height 用）。"""
    try:
        import struct
        b = path.read_bytes()
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", b[16:24])
        i = 2
        while i < len(b) - 9:
            if b[i] != 0xFF:
                i += 1
                continue
            m = b[i + 1]
            if m in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    except Exception:
        pass
    return fallback


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_jsonld(d: dict) -> str:
    """WebSite / WebPage / BreadcrumbList / ItemList / FAQPage をまとめて生成する。"""
    cat, area, seo = d["category"], d["area"], d["seo"]
    url = seo["canonical"]
    graph = [
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/",
         "name": "かいごのとなり", "inLanguage": "ja"},
        {"@type": "WebPage", "@id": f"{url}#webpage", "url": url, "name": seo["og_title"],
         "isPartOf": {"@id": f"{SITE}/#website"},
         "datePublished": d["published"], "dateModified": d["modified"], "inLanguage": "ja"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": cat["name"], "item": f"{SITE}{cat['path']}"},
            {"@type": "ListItem", "position": 3, "name": area["pref_name"],
             "item": f"{SITE}{cat['path']}{area['pref_id']}/"},
            {"@type": "ListItem", "position": 4, "name": area["city_name"]},
        ]},
    ]
    if d["items"]:
        clean = []
        for it in d["items"]:
            o = {k: v for k, v in it.items() if not k.startswith("_")}
            if isinstance(o.get("parentOrganization"), str):
                o["parentOrganization"] = {"@type": "Organization", "name": o["parentOrganization"]}
            clean.append(o)
        graph.append({"@type": "ItemList",
                      "name": f"{area['city_name']}の{cat['name']}",
                      "numberOfItems": len(d["items"]),
                      "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": it}
                                          for i, it in enumerate(clean)]})
    if d["faq"]:
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in d["faq"]]})
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, indent=1)


def render_listing(d: dict) -> str:
    """掲載事業者カードを描画する。住所・電話は data の値をそのまま使う。"""
    out = []
    if d.get("listing_note"):
        out.append(f'    <p class="cnt">{d["listing_note"]}</p>')
    for i, it in enumerate(d["items"], 1):
        rows = []
        addr = it.get("address")
        if addr:
            street = " ".join(x for x in [addr.get("addressRegion", ""), addr.get("addressLocality", ""),
                                          addr.get("streetAddress", "")] if x)
            rows.append(f"<dt>所在地</dt><dd>{esc(street)}</dd>")
        if it.get("parentOrganization"):
            org = it["parentOrganization"]
            org = org if isinstance(org, str) else org.get("name", "")
            rows.append(f"<dt>運営法人</dt><dd>{esc(org)}</dd>")
        if it.get("telephone"):
            tel = re.sub(r"[^0-9]", "", it["telephone"])
            rows.append(f'<dt>電話</dt><dd><a class="tel" href="tel:{tel}">{esc(it["telephone"])}</a></dd>')
        if it.get("faxNumber"):
            rows.append(f'<dt>FAX</dt><dd>{esc(it["faxNumber"])}</dd>')
        if it.get("_hours"):
            rows.append(f'<dt>電話受付</dt><dd>{esc(it["_hours"])}</dd>')
        if it.get("_closed"):
            rows.append(f'<dt>休業日</dt><dd>{esc(it["_closed"])}</dd>')
        if it.get("identifier"):
            rows.append(f'<dt>事業所番号</dt><dd class="id">{esc(it["identifier"])}</dd>')
        if it.get("areaServed"):
            rows.append(f'<dt>対応エリア</dt><dd>{esc(it["areaServed"])}</dd>')
        if it.get("description"):
            rows.append(f'<dt>特徴</dt><dd>{esc(it["description"])}</dd>')
        tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in it.get("_tags", []))
        out.append(
            '    <div class="card">\n'
            f'      <h3><span class="no">{i}</span>{esc(it["name"])}</h3>\n'
            f'      <dl class="dl">{"".join(rows)}</dl>\n'
            + (f'      <div class="tags">{tags}</div>\n' if tags else "")
            + "    </div>"
        )
    out.append(
        '    <div class="warn"><strong>掲載情報についてのお願い</strong><br>'
        f'掲載内容は{d["modified"]}時点で各事業者・自治体が公表している情報にもとづいています。'
        '変更される場合がありますので、お問い合わせの前に必ず公式情報をご確認ください。'
        '掲載内容の訂正・削除のご依頼は運営者までご連絡ください。</div>'
    )
    return "\n".join(out)


def render_faq(d: dict) -> str:
    return "\n".join(
        "    <details>\n"
        f'      <summary>{esc(f["q"])}</summary>\n'
        f'      <div class="ans"><p>{f["a"]}</p></div>\n'
        "    </details>"
        for f in d["faq"]
    )


GYO = [("あ行", "あいうえお"), ("か行", "かきくけこがぎぐげご"), ("さ行", "さしすせそざじずぜぞ"),
       ("た行", "たちつてとだぢづでど"), ("な行", "なにぬねの"), ("は行", "はひふへほばびぶべぼ"),
       ("ま行", "まみむめも"), ("や行", "やゆよ"), ("ら行", "らりるれろ"), ("わ行", "わをん")]


def render_towns(d: dict) -> str:
    """市区町村内の町域を五十音の行ごとに並べる。ロングテール検索語をページ内に持たせる。"""
    ref = d.get("towns")
    if not ref:
        return ""
    site = json.loads((BASE / "data" / "site.json").read_text(encoding="utf-8"))
    towns = site.get("towns", {}).get(ref["pref"], {}).get(ref["city"], [])
    if not towns:
        return ""
    rows = []
    for label, heads in GYO:
        group = [t for t in towns if t["kana"] and t["kana"][0] in heads]
        if not group:
            continue
        chips = "".join(f'<li>{esc(t["name"])}</li>' for t in sorted(group, key=lambda x: x["kana"]))
        rows.append(f'      <div class="town-row"><b>{label}</b><ul class="towns">{chips}</ul></div>')
    city = d["area"]["city_name"]
    return (f'    <h2 id="towns">{city}の町域一覧（対応エリアの目安）</h2>\n'
            f'    <p>{city}には{len(towns)}の町域があります。掲載事業者の対応範囲は町域単位で分かれていることが多いため、'
            'お問い合わせの際はお住まいの町名・番地までお伝えください。</p>\n'
            '    <div class="towns-wrap">\n' + "\n".join(rows) + "\n    </div>\n"
            '    <p class="tiny">※町域ごとの事業者ページは、掲載できる事業者が3件以上そろった町域から順次公開します。</p>')


def render_toc(content: str) -> str:
    """本文中の <h2 id="..."> から目次を組み立てる。"""
    rows = []
    for anchor, text in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', content, re.S):
        label = re.sub(r"<[^>]+>", "", text).strip()
        rows.append('        <li><a href="#%s">%s</a></li>' % (anchor, label))
    return "\n".join(rows)


def build(slug: str) -> pathlib.Path:
    d = json.loads((BASE / "data" / f"{slug}.json").read_text(encoding="utf-8"))
    content = (BASE / "content" / f"{slug}.html").read_text(encoding="utf-8")
    tpl = (BASE / "templates" / "city.html").read_text(encoding="utf-8")

    cat, area = d["category"], d["area"]
    out_dir = BASE / cat["id"] / area["pref_id"] / area["city_id"]
    root = "../" * 3  # /<cat>/<pref>/<city>/ からサイトルートまで

    content = content.replace("{{LISTING}}", render_listing(d))
    content = content.replace("{{FAQ}}", render_faq(d))
    towns_html = render_towns(d)

    hero_img = ""
    if d.get("hero_image"):
        w, h = image_size(BASE / d["hero_image"])
        hero_img = (f'<img class="hero-img" src="{root}{d["hero_image"]}" '
                    f'alt="{esc(d["h1"])}" width="{w}" height="{h}" fetchpriority="high">')

    repl = {
        "{{TITLE}}": d["seo"]["title"], "{{DESCRIPTION}}": d["seo"]["description"],
        "{{CANONICAL}}": d["seo"]["canonical"], "{{OG_TITLE}}": d["seo"]["og_title"],
        "{{OG_DESCRIPTION}}": d["seo"]["og_description"], "{{OG_IMAGE}}": d["seo"]["og_image"],
        "{{JSONLD}}": build_jsonld(d), "{{ROOT}}": root,
        "{{CAT_ID}}": cat["id"], "{{CAT_NAME}}": cat["name"],
        "{{PREF_ID}}": area["pref_id"], "{{PREF_NAME}}": area["pref_name"],
        "{{CITY_NAME}}": area["city_name"],
        "{{H1}}": d["h1"], "{{PUBLISHED}}": d["published"], "{{MODIFIED}}": d["modified"],
        "{{COUNT_LABEL}}": d["count_label"], "{{LEAD}}": d["lead"], "{{HERO_IMAGE}}": hero_img,
        "{{TOC}}": render_toc(content + towns_html), "{{CONTENT}}": content,
        "{{TOWNS}}": towns_html,
        "{{RELATED}}": d["related"], "{{NEARBY_HEADING}}": d["nearby_heading"],
        "{{NEARBY}}": d["nearby"],
        "{{SOURCES}}": "\n".join(f"        <li>{s}</li>" for s in d["sources"]),
        "{{SIDEBAR}}": d["sidebar"], "{{MCTA}}": d["mcta"],
    }
    html = tpl
    for k, v in repl.items():
        html = html.replace(k, v)
    html = html.replace("{{ROOT}}", root)  # data 側に埋まった {{ROOT}} を最後に解決する

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    slugs = sys.argv[1:] or sorted(p.stem for p in (BASE / "data").glob("*_*.json"))
    for s in slugs:
        p = build(s)
        print(f"built  {p.relative_to(BASE)}  ({p.stat().st_size:,} bytes)")
