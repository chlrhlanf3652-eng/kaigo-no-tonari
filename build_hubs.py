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
# 都道府県ページ専用のカバー画像
PREF_OGP = {
    ("houmon-kaigo", "tokyo"): "ogp-tokyo23.jpg",
    ("takuhai-bento", "tokyo"): "ogp-tokyo-bento.jpg",
    ("koreisha-chintai", "tokyo"): "ogp-tokyo-chintai.jpg",
}


def live_areas(cat_id, pref_id=None):
    """そのカテゴリで実際にページデータがある市区町村の数を返す。"""
    pat = f"{cat_id}_{pref_id}_*.json" if pref_id else f"{cat_id}_*_*.json"
    return len(list((BASE / "data").glob(pat)))


def has_data(cat_id, pref_id, city_id):
    return (BASE / "data" / f"{cat_id}_{pref_id}_{city_id}.json").exists()



# ------------------------------------------------- 東京23区の事業所数データ
# 事業所数は tools/counts.py（LIFULL介護の掲載件数で全区そろえたもの）。
# 相談窓口の呼び名は収集キャッシュから拾い、キャッシュのない区だけ下の既定値を使う。
# 出典はいずれも各区・各情報サイトの公表情報（2026-09-21 確認）。
_MADOGUCHI_FALLBACK = {
    "chiyoda": "高齢者あんしんセンター",
    "adachi": "地域包括支援センター",
    "katsushika": "高齢者総合相談センター",
}


def tokyo23():
    """(id, 区名, 事業所数, 相談窓口の呼び名) を事業所数の多い順に返す。"""
    sys.path.insert(0, str(BASE / "tools"))
    try:
        from wards import WARDS as W
        from counts import COUNTS, MADOGUCHI_OVERRIDE
    except Exception:
        return []
    cache = BASE / "tools" / "cache"
    rows = []
    for wid, w in W.items():
        m = MADOGUCHI_OVERRIDE.get(wid)
        if not m:
            f = cache / f"{wid}.json"
            if f.exists():
                m = json.loads(f.read_text(encoding="utf-8")).get("madoguchi")
        m = m or _MADOGUCHI_FALLBACK.get(wid, "地域包括支援センター")
        rows.append((wid, w["name"], COUNTS.get(wid, 0), m))
    rows.sort(key=lambda r: -r[2])
    return rows


def tokyo23_table(cat_id):
    """東京23区の事業所数と相談窓口の呼称を一覧にする。公開済みの区はリンクにする。"""
    data = tokyo23()
    if not data:
        return ""
    total = sum(x[2] for x in data)
    rows = []
    for cid, name, cnt, center in data:
        if has_data(cat_id, "tokyo", cid):
            cell = f'<a href="{cid}/">{name}</a>'
            state = '<span class="ok">掲載中</span>'
        else:
            cell = name
            state = '<span class="soon-tag">準備中</span>'
        rows.append(f'      <tr><th>{cell}</th><td class="num">{cnt}</td>'
                    f'<td>{center}</td><td>{state}</td></tr>')
    return (
        '  <h2 id="tokyo23">東京23区の訪問介護事業所数と相談窓口の呼び名</h2>\n'
        '  <p>同じ東京23区でも、事業所の数は区によって10倍以上の開きがあります。'
        f'23区合計で約{total:,}件。あわせて、最初の相談先である地域包括支援センターは'
        '区ごとに独自の愛称を使っていることが多く、これが「調べても出てこない」原因になります。'
        'お住まいの区の呼び名をここで確認してください。</p>\n'
        '  <div class="tw">\n'
        '  <table>\n'
        '    <caption class="tiny" style="text-align:left;padding-bottom:6px">'
        '東京23区 訪問介護事業所数（多い順）と地域包括支援センターの呼称</caption>\n'
        '    <thead><tr><th style="width:22%">区</th><th style="width:16%">事業所数の目安</th>'
        '<th>最初の相談窓口の呼び名</th><th style="width:14%">当サイト</th></tr></thead>\n'
        '    <tbody>\n' + "\n".join(rows) + '\n    </tbody>\n'
        '  </table>\n'
        '  </div>\n'
        '  <p class="tiny">※事業所数は介護情報サイトの掲載件数（2026年9月時点）をもとにした目安で、'
        '指定事業所数そのものではありません。休止中・新規指定の反映には時間差があります。'
        '正確な数と一覧は厚生労働省「介護サービス情報公表システム」でご確認ください。</p>'
    )


def hero_wh(name, fallback=(1200, 630)):
    """カバー画像の実寸を返す（width/height を書いてレイアウトシフトを防ぐ）。"""
    try:
        import struct
        b = (BASE / "assets" / name).read_bytes()
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", b[16:24])
        i = 2
        while i < len(b) - 9:
            if b[i] != 0xFF:
                i += 1
                continue
            if b[i + 1] in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", b[i + 2:i + 4])[0]
    except Exception:
        pass
    return fallback


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
         ogp=None, hero=None, cat_id="", area_id="", ptype="page"):
    tpl = (BASE / "templates" / "hub.html").read_text(encoding="utf-8")
    repl = {
        "{{TITLE}}": title, "{{DESCRIPTION}}": desc, "{{OG_TITLE}}": h1,
        "{{CANONICAL}}": canonical, "{{OG_IMAGE}}": ogp or OG, "{{JSONLD}}": jsonld,
        "{{ROOT}}": root, "{{H1}}": h1, "{{LEAD}}": lead,
        "{{HERO}}": (f'<img class="hero-img" src="{root}assets/{hero}" alt="{h1}" '
                     f'width="{hero_wh(hero)[0]}" height="{hero_wh(hero)[1]}" '
                     f'loading="eager" fetchpriority="high">' if hero else ""),
        "{{BREADCRUMB}}": breadcrumb, "{{CONTENT}}": content,
        "{{CAT_ID}}": cat_id, "{{AREA_ID}}": area_id, "{{PTYPE}}": ptype,
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
     "制度のしくみ、手続きの順番、用語の意味をまとめています。事業者一覧を読む前にどうぞ。", "ogp-guide.jpg"),
    ("guide/houmon-kaigo-ryokin", "訪問介護の料金のしくみ", "訪問介護の料金のしくみ｜単位数×地域区分×負担割合",
     "訪問介護の自己負担は「単位数×1単位あたりの単価×負担割合」で決まります。令和6年度の基本報酬、1級地から8段階の地域区分、区分支給限度基準額、負担が重いときに使える仕組みまで数字でまとめました。",
     "自己負担は3つの数字で決まります。事業所に聞かなくても、自分でおおよその金額が出せます。", None),
    ("guide/houmon-kaigo-dekirukoto", "ヘルパーに頼めること・頼めないこと", "ヘルパーに頼めること・頼めないこと｜訪問介護の線引き",
     "訪問介護で頼めるのは利用者本人の日常生活に必要な支援だけです。身体介護と生活援助の違い、断られがちだが条件しだいで頼めること、保険外をどう補うかを整理しました。",
     "線引きは「利用者本人の日常生活か」だけ。この一文でほとんどの疑問は判断できます。", None),
    ("guide/jigyosho-erabikata", "訪問介護事業所の選び方", "訪問介護事業所の選び方｜契約前に聞く7つのこと",
     "距離ではなく「希望の曜日・時間帯に空きがあるか」で選びます。契約前に確認する7項目、公表情報の見るべき3点、運営法人の種別による傾向、合わなかったときの変更まで解説します。",
     "距離より、希望する曜日・時間帯にヘルパーを確保できるかが決め手です。", None),
    ("guide/youkaigo-nintei", "要介護認定の申請から利用開始まで", "要介護認定の申請から利用開始まで｜4ステップと認定調査",
     "介護保険は申し込めばすぐ使えるものではありません。相談から利用開始までの4ステップ、申請に必要なもの、認定調査で損をしないための準備、結果に納得できないときの区分変更まで説明します。",
     "全体で1か月から1か月半かかります。まず順番を押さえてください。", None),
    ("guide/koreisha-chintai-kotowarareru", "高齢者が賃貸を断られる理由と対策", "高齢者が賃貸を断られる理由と対策｜審査を通す5つの準備",
     "断られるのは年齢そのものではなく、年齢にひもづく3つの不安が理由です。貸主が何を心配しているのか、その一つひとつにどう先回りして答えるか、申し込み前にそろえる5つの準備を解説します。",
     "断られるのは年齢ではなく、年齢にひもづく3つの不安。先回りして答えを用意すれば審査は変わります。", None),
    ("guide/sakoju-toha", "サ高住と老人ホームの違い", "サ高住と老人ホームの違い｜費用・入居条件・退去要件の比較",
     "一般の賃貸、サービス付き高齢者向け住宅、住宅型・介護付有料老人ホームを、月額費用・受けられる支援・入居条件・初期費用で比較。サ高住で見落とされやすい点と、見学で聞くべき4つも挙げました。",
     "費用だけで選ぶと「入れなかった」「出ることになった」が起きます。入口と出口の条件まで見てください。", None),
    ("guide/kaigoshoku-keitai", "介護食の形態と選び方", "介護食の形態と選び方｜やわらか食・ムース食の違い",
     "普通食・やわらか食・ムース食の3段階を、噛む力と飲み込む力で選び分けます。食べにくさに気づくサイン、事業者ごとに違う呼び名の伝え方、学会分類との対応まで整理しました。",
     "本人は「食べにくい」と言いません。食卓に残るものが手がかりになります。", None),
    ("guide/haishoku-erabikata", "配食サービスの選び方", "高齢者向け配食サービスの選び方｜契約前に確認する5項目",
     "高齢者専門の配食が一般の宅食と違う3点、手渡しによる安否確認、契約前に確認する5項目、介護保険との関係、自治体の配食事業との使い分けまでまとめました。",
     "続くかどうかは「本人が食べきれるか」で決まります。まず試食から。", None),
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
             ld(graph), ogp=f"{SITE}/assets/{ogp}" if ogp else None, hero=ogp,
             ptype="static", area_id=slug)


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
         crumbs([("ホーム", None)]), content, f"{SITE}/", ld(graph), ptype="top")


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
         ogp=f"{SITE}/assets/{ogp}" if ogp else None, hero=ogp,
         cat_id=cat_id, ptype="hub")


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
        .replace("{{TOKYO23}}", tokyo23_table(cat_id) if pref_id == "tokyo" else "")
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
    hero = PREF_OGP.get((cat_id, pref_id))
    page(f"{cat_id}/{pref_id}/index.html", root,
         f"{pref['name']}の{c['name']}を市区町村から探す｜掲載{len(live)}エリア【2026年9月更新】",
         f"{pref['name']}の{c['name']}を市区町村ごとにまとめています。{c['tagline']}。"
         f"現在{len(live)}エリアを掲載中。地域の相談窓口の呼び名や料金の目安もあわせて確認できます。",
         f"{pref['name']}の{c['name']}", c["hub"]["lead"],
         crumbs([("ホーム", root), (c["name"], f"{root}{cat_id}/"), (pref["name"], None)]),
         content, url, ld(graph),
         ogp=f"{SITE}/assets/{hero}" if hero else None, hero=hero,
         cat_id=cat_id, area_id=pref_id, ptype="pref")



# ------------------------------------------------------------------ 404
def build_404():
    """GitHub Pages の 404 を自前のページに差し替える。

    URL を手で削って辿る利用者（/houmon-kaigo/tokyo/xxx/ を打ち間違えるなど）が
    素っ気ない標準404で離脱しないよう、その場から主要導線に戻れるようにする。
    パスの深さが読めないので、リンクはすべてルート絶対パスで書く。
    """
    live = []
    for cid in CATS:
        for c in S["cities"].get("tokyo", []):
            if has_data(cid, "tokyo", c["id"]):
                live.append((f'/{cid}/tokyo/{c["id"]}/',
                             f'{c["name"]}の{CATS[cid]["name"]}'))
    live.sort()
    content = (
        '  <h2 id="cat">サービスから探す</h2>\n'
        '  <div class="cats">'
        + "".join(f'<a class="cat" href="/{c["id"]}/"><b>{c["name"]}</b>'
                  f'<span>{c["tagline"]}</span></a>' for c in S["categories"])
        + '</div>\n'
        '  <h2 id="pages">公開中の市区町村ページ</h2>\n'
        '  <div class="areas">'
        + "".join(f'<a class="area live" href="{h}">{n}</a>' for h, n in live)
        + '</div>\n'
        '  <h2 id="help">それでも見つからないとき</h2>\n'
        '  <p>介護がはじめての方は、お住まいの地域の相談窓口が確実です。'
        '<a href="/guide/soudan-madoguchi/">相談窓口の探し方</a>をご覧ください。'
        'リンク切れを見つけた場合は<a href="/contact/">お問い合わせ</a>からお知らせいただけると助かります。</p>\n'
    )
    tpl = (BASE / "templates" / "hub.html").read_text(encoding="utf-8")
    repl = {
        "{{TITLE}}": "ページが見つかりません｜かいごのとなり",
        "{{DESCRIPTION}}": "お探しのページは見つかりませんでした。公開中のページ一覧からお探しください。",
        "{{OG_TITLE}}": "ページが見つかりません", "{{CANONICAL}}": f"{SITE}/404.html",
        "{{OG_IMAGE}}": OG, "{{JSONLD}}": ld([]), "{{ROOT}}": "/",
        "{{H1}}": "お探しのページが見つかりません",
        "{{LEAD}}": "URLが変わったか、まだ公開していないページの可能性があります。下の一覧からお探しください。", "{{HERO}}": "",
        "{{BREADCRUMB}}": '      <li><a href="/">ホーム</a></li>\n      <li>404</li>',
        "{{CAT_ID}}": "", "{{AREA_ID}}": "", "{{PTYPE}}": "404",
        "{{CONTENT}}": content,
    }
    html = tpl
    for k, v in repl.items():
        html = html.replace(k, v)
    html = html.replace("{{ROOT}}", "/")
    html = html.replace('<meta name="robots" content="index,follow,max-image-preview:large">',
                        '<meta name="robots" content="noindex,follow">')
    (BASE / "404.html").write_text(html, encoding="utf-8")
    print(f"built  404.html  ({(BASE / '404.html').stat().st_size:,} bytes)")


if __name__ == "__main__":
    build_top()
    build_static()
    build_404()
    for cid in CATS:
        build_hub(cid)
        for pref in S["prefs"]:
            if live_areas(cid, pref["id"]):
                build_pref(cid, pref["id"])
