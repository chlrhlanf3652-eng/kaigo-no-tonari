#!/usr/bin/env python3
"""
かいごのとなり — サイトトップ / カテゴリハブ / 都道府県ページ生成ビルダー

  data/site.json          … カテゴリ・都道府県・市区町村の一覧（公開状態つき）
  content/hub_<cat>.html  … カテゴリハブの解説本文
  content/pref_<cat>_<pref>.html … 都道府県ページの解説本文（任意）
  templates/hub.html      … 共通の骨組み

  生成されるページ:
    /index.html                  サイトトップ
    /<cat>/index.html            カテゴリハブ（全国）
    /<cat>/<pref>/index.html     都道府県ページ

  status が "live" の市区町村だけをリンクにする。"planned" は灰色表示にして
  リンクを張らない（中身のないページを量産して薄いページ扱いされるのを避けるため）。

依存ライブラリなし（標準ライブラリのみ）。
"""
import json
import pathlib
import re
import sys

BASE = pathlib.Path(__file__).parent
SITE = "https://kaigonotonari.com"
S = json.loads((BASE / "data" / "site.json").read_text(encoding="utf-8"))
CATS = {c["id"]: c for c in S["categories"]}
OG = f"{SITE}/assets/ogp-houmon-kaigo.jpg"


def live_areas(cat_id, pref_id=None):
    """そのカテゴリで実際にページデータがある市区町村の数を返す。"""
    pat = f"{cat_id}_{pref_id}_*.json" if pref_id else f"{cat_id}_*_*.json"
    return len(list((BASE / "data").glob(pat)))


def has_data(cat_id, pref_id, city_id):
    return (BASE / "data" / f"{cat_id}_{pref_id}_{city_id}.json").exists()


def crumbs(pairs):
    rows = []
    for name, href in pairs:
        rows.append(f'      <li><a href="{href}">{name}</a></li>' if href
                    else f"      <li>{name}</li>")
    return "\n".join(rows)


def area_grid(entries, href_of):
    """公開済みはリンク、準備中は灰色のまま並べる。"""
    cells = []
    for e in entries:
        if e["status"] == "live":
            cells.append(f'<a class="area live" href="{href_of(e)}">{e["name"]}'
                         f'<span class="badge">掲載中</span></a>')
        else:
            cells.append(f'<span class="area soon">{e["name"]}'
                         f'<span class="badge">準備中</span></span>')
    return '<div class="areas">' + "".join(cells) + "</div>"


def page(out_rel, root, title, desc, h1, lead, breadcrumb, content, canonical, jsonld,
         ogp=None, hero=None):
    tpl = (BASE / "templates" / "hub.html").read_text(encoding="utf-8")
    repl = {
        "{{TITLE}}": title, "{{DESCRIPTION}}": desc, "{{OG_TITLE}}": h1,
        "{{CANONICAL}}": canonical, "{{OG_IMAGE}}": ogp or OG, "{{JSONLD}}": jsonld,
        "{{ROOT}}": root, "{{H1}}": h1, "{{LEAD}}": lead,
        "{{HERO}}": (f'<img class="hero-img" src="{root}assets/{hero}" alt="{h1}" '
                     f'loading="eager" fetchpriority="high">' if hero else ""),
        "{{BREADCRUMB}}": breadcrumb, "{{CONTENT}}": content,
    }
    html = tpl
    for k, v in repl.items():
        html = html.replace(k, v)
    html = html.replace("{{ROOT}}", root)
    out = BASE / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"built  {out_rel}  ({out.stat().st_size:,} bytes)")


def ld(graph):
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, indent=1)


def partial(name, root):
    p = BASE / "content" / f"{name}.html"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").replace("{{ROOT}}", root)


# ------------------------------------------------------------- static pages
# 運営・法務まわりの固定ページ。掲載責任と AdSense 審査の前提になる。
STATIC = [
    ("about", "運営者情報", "運営者情報｜かいごのとなり",
     "かいごのとなりの運営者情報と掲載方針。事業者情報は厚生労働省の公表システムと自治体・各事業者の公式発表を出典とし、ページごとに出典と最終確認日を明記しています。",
     "公表情報にもとづいて、出典を示して掲載しています。", "ogp-about.jpg"),
    ("contact", "お問い合わせ・掲載依頼", "お問い合わせ・掲載依頼｜かいごのとなり",
     "掲載内容の訂正・削除、新規掲載のご依頼、情報の誤りのご指摘を受け付けています。掲載されている事業者の方からのご依頼は最優先で、5営業日以内に対応します。",
     "掲載内容の訂正・削除のご依頼は、<strong>理由の説明なしに</strong>お受けします。5営業日以内にご返信します。", "ogp-contact.jpg"),
    ("privacy", "プライバシーポリシー", "プライバシーポリシー｜かいごのとなり",
     "かいごのとなりにおける個人情報の取り扱い、Cookie・アクセス解析の利用、広告配信、第三者提供、開示・訂正・削除のご請求について定めています。",
     "当サイトにおける個人情報の取り扱いについて定めています。", None),
    ("disclaimer", "免責事項", "免責事項｜かいごのとなり",
     "かいごのとなりの免責事項。掲載情報の正確性と更新、責任の範囲、医療・介護の判断、外部リンク、著作権、掲載内容の訂正・削除の受け付けについて定めています。ご利用の前にお読みください。",
     "掲載情報は公表情報にもとづいていますが、ご利用の前に必ず各事業者・各窓口で最新情報をご確認ください。", None),
    ("ad-policy", "広告について", "広告について｜かいごのとなり",
     "当サイトの広告表記、掲載している広告の種類、掲載順に報酬を反映しないという原則、表現上の注意について説明しています。ステルスマーケティング規制への対応も記載しています。",
     "当サイトはアフィリエイトプログラムと広告配信を利用しています。<strong>掲載順は報酬では決めません。</strong>", None),
    ("guide", "制度ガイド", "介護制度ガイド｜かいごのとなり",
     "介護保険の手続き、費用のしくみ、介護食、高齢者の住まいについて、制度のしくみと手続きの順番をまとめたガイド一覧です。事業者を探す前に全体像をつかめます。",
     "制度のしくみ、手続きの順番、用語の意味をまとめています。事業者一覧を読む前にどうぞ。", None),
    ("guide/soudan-madoguchi", "介護の相談窓口の探し方", "介護の相談窓口の探し方｜かいごのとなり",
     "介護がはじめての方の相談先である地域包括支援センターについて、自治体ごとに違う呼び名、担当地域の決まり方、相談前に用意しておくとよいものをまとめました。",
     "介護がはじめての方の相談先は、市区町村が設置している<strong>地域包括支援センター</strong>です。相談は無料です。", None),
]


def build_static():
    for slug, name, title, desc, lead, ogp in STATIC:
        depth = slug.count("/") + 1
        root = "../" * depth
        key = "page_" + slug.replace("/", "_")
        url = f"{SITE}/{slug}/"
        crumb = [("ホーム", root)]
        if "/" in slug:
            crumb.append(("制度ガイド", f"{root}guide/"))
        crumb.append((name, None))
        graph = [
            {"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/",
             "name": S["site"]["name"], "inLanguage": "ja"},
            {"@type": "WebPage", "@id": f"{url}#webpage", "url": url, "name": name,
             "isPartOf": {"@id": f"{SITE}/#website"}, "datePublished": "2026-09-21",
             "dateModified": "2026-09-21", "inLanguage": "ja"},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n,
                 **({"item": f"{SITE}/"} if i == 0 else {})}
                for i, (n, _) in enumerate(crumb)]},
        ]
        content = "  " + partial(key, root).strip() + "\n"
        page(f"{slug}/index.html", root, title, desc, name, lead,
             crumbs(crumb), content, url,
             ld(graph), ogp=f"{SITE}/assets/{ogp}" if ogp else None, hero=ogp)


# ---------------------------------------------------------------- site top
def build_top():
    root = ""
    cards = []
    for c in S["categories"]:
        n = live_areas(c["id"])
        label = f"掲載エリア {n}件" if n else "準備中"
        cards.append(
            f'<a class="cat" href="{c["id"]}/">'
            f'<b>{c["name"]}</b><span>{c["tagline"]}</span>'
            f'<em>{label}</em></a>')
    content = (
        '  <h2 id="cat">サービスから探す</h2>\n'
        '  <div class="cats">' + "".join(cards) + "</div>\n"
        + partial("hub_top", root)
    )
    graph = [
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/",
         "name": S["site"]["name"], "inLanguage": "ja"},
        {"@type": "Organization", "@id": f"{SITE}/#org", "name": S["site"]["name"],
         "url": f"{SITE}/"},
    ]
    page("index.html", root,
         "かいごのとなり｜高齢者と家族のための地域サービス情報",
         "訪問介護・高齢者向け宅配弁当・高齢者が借りられる賃貸を、市区町村ごとにまとめた情報サイトです。料金の目安、制度の使い方、地域の相談窓口まで、家族がはじめて介護に向き合うときに必要な情報を集めました。",
         "介護のことは、となりで調べる。",
         "親の暮らしを支えるサービスは、地域ごとに事業者も制度も違います。かいごのとなりは、<strong>市区町村単位</strong>で使える事業者と公的な相談窓口をまとめています。",
         crumbs([("ホーム", None)]), content, f"{SITE}/", ld(graph))


# ------------------------------------------------------------- category hub
def build_hub(cat_id):
    c = CATS[cat_id]
    root = "../"
    prefs = [dict(p, status="live" if live_areas(cat_id, p["id"]) else "planned")
             for p in S["prefs"]]
    grid = area_grid(prefs, lambda e: f"{e['id']}/")
    content = (
        '  <h2 id="area">都道府県から探す</h2>\n'
        f"  {grid}\n"
        '  <p class="tiny">準備中のエリアは、掲載できる事業者情報がそろい次第の公開となります。</p>\n'
        + partial(f"hub_{cat_id}", root)
        + '\n  <h2 id="other">ほかのカテゴリ</h2>\n  <div class="lg">'
        + "".join(f'<a href="{root}{o["id"]}/">{o["name"]}<small>{o["tagline"]}</small></a>'
                  for o in S["categories"] if o["id"] != cat_id)
        + "</div>\n"
    )
    url = f"{SITE}/{cat_id}/"
    graph = [
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/",
         "name": S["site"]["name"], "inLanguage": "ja"},
        {"@type": "CollectionPage", "@id": f"{url}#webpage", "url": url,
         "name": c["hub"]["h1"], "isPartOf": {"@id": f"{SITE}/#website"}, "inLanguage": "ja"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": c["name"]}]},
    ]
    ogp = c["hub"].get("ogp")
    page(f"{cat_id}/index.html", root, c["hub"]["title"], c["hub"]["description"],
         c["hub"]["h1"], c["hub"]["lead"],
         crumbs([("ホーム", root), (c["name"], None)]), content, url, ld(graph),
         ogp=f"{SITE}/assets/{ogp}" if ogp else None, hero=ogp)


# ---------------------------------------------------------- prefecture page
def build_pref(cat_id, pref_id):
    c = CATS[cat_id]
    pref = next(p for p in S["prefs"] if p["id"] == pref_id)
    root = "../../"
    cities = [dict(c, status="live" if has_data(cat_id, pref_id, c["id"]) else "planned")
              for c in S["cities"].get(pref_id, [])]
    grid = area_grid(cities, lambda e: f"{e['id']}/")
    live = [x for x in cities if x["status"] == "live"]
    content = (
        '  <h2 id="city">市区町村から探す</h2>\n'
        f"  {grid}\n"
        f'  <p class="tiny">{pref["name"]}内で掲載中のエリアは{len(live)}件です。'
        '準備中のエリアは、掲載できる事業者情報がそろい次第の公開となります。</p>\n'
        + partial(f"pref_{cat_id}_{pref_id}", root)
        + f'\n  <h2 id="other">{pref["name"]}のほかのサービス</h2>\n  <div class="lg">'
        + "".join(f'<a href="{root}{o["id"]}/{pref_id}/">{pref["name"]}の{o["name"]}'
                  f'<small>{o["tagline"]}</small></a>'
                  for o in S["categories"] if o["id"] != cat_id)
        + "</div>\n"
    )
    url = f"{SITE}/{cat_id}/{pref_id}/"
    graph = [
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/",
         "name": S["site"]["name"], "inLanguage": "ja"},
        {"@type": "CollectionPage", "@id": f"{url}#webpage", "url": url,
         "name": f"{pref['name']}の{c['name']}", "isPartOf": {"@id": f"{SITE}/#website"},
         "inLanguage": "ja"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": f"{SITE}/"},
            {"@type": "ListItem", "position": 2, "name": c["name"], "item": f"{SITE}/{cat_id}/"},
            {"@type": "ListItem", "position": 3, "name": pref["name"]}]},
    ]
    page(f"{cat_id}/{pref_id}/index.html", root,
         f"{pref['name']}の{c['name']}を市区町村から探す｜かいごのとなり",
         f"{pref['name']}の{c['name']}を市区町村ごとにまとめています。{c['tagline']}。"
         f"地域の相談窓口や料金の目安もあわせて確認できます。",
         f"{pref['name']}の{c['name']}", c["hub"]["lead"],
         crumbs([("ホーム", root), (c["name"], f"{root}{cat_id}/"), (pref["name"], None)]),
         content, url, ld(graph))


if __name__ == "__main__":
    build_top()
    build_static()
    for cid in CATS:
        build_hub(cid)
        for pref in S["prefs"]:
            if live_areas(cid, pref["id"]):
                build_pref(cid, pref["id"])
