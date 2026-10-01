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
import urllib.parse
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


# ------------------------------------------------------------- 一覧の絞り込み
# 60件の一覧はスマホで27画面ぶんある。持っているデータ（町域・提供曜日・
# 法人種別など）で絞れるようにする。選択肢はビルド時に件数つきで作り、
# JS はカードの表示・非表示を切り替えるだけ。JS が無効なら全件がそのまま見える。
DAY_OPTS = [("sat", "土曜も対応"), ("sun", "日曜も対応")]
DAY_WORD = {"sat": "土曜日", "sun": "日曜日"}
# (data属性名, 項目キー, 短い見出し)。スマホで横に3つ並ぶよう見出しは2文字前後。
FACET_ATTRS = [("fk", "_fkind", "型"), ("mix", "_mix", "扱い"), ("kind", "_kind", "法人")]
VISITING = ("houmon-kaigo", "houmon-kango")


def _count(vals):
    c = {}
    for v in vals:
        if v:
            c[v] = c.get(v, 0) + 1
    return sorted(c.items(), key=lambda x: (-x[1], x[0]))


def _facets(items):
    """絞り込みの選択肢。2種類以上あり、1つの値が9割を占めないものだけ出す
    （ショートステイの法人種別は9割が社会福祉法人で、選んでも絞れない）。"""
    n = len(items)
    out = []
    towns = _count(it.get("_town") for it in items)
    if len(towns) >= 2:
        out.append(("town", "場所", [(v, f"{v}（{k}）") for v, k in towns]))
    if any(it.get("_days") for it in items):
        opts = []
        for key, lab in DAY_OPTS:
            k = sum(1 for it in items if DAY_WORD[key] in (it.get("_days") or []))
            if k:
                opts.append((key, f"{lab}（{k}）"))
        if opts:
            out.append(("day", "曜日", opts))
    for key, attr, lab in FACET_ATTRS:
        vals = _count(it.get(attr) for it in items)
        if len(vals) >= 2 and vals[0][1] < n * 0.9:
            out.append((key, lab, [(v, f"{v}（{k}）") for v, k in vals]))
    return out


# 地図を出す一覧（利用者が通う・泊まるサービスだけ）。訪問系は事務所の場所なので地図は出さない
MAP_CATS = ("day-service", "short-stay")
_COORDS = None


def _coords(ident):
    """事業所番号 → (緯度, 経度)。厚労省オープンデータ由来で、tools/cache の各区ファイルに入っている。"""
    global _COORDS
    if _COORDS is None:
        _COORDS = {}
        for f in (BASE / "tools" / "cache").glob("*.json"):
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for it in rec.get("items", []) if isinstance(rec, dict) else []:
                if isinstance(it, dict) and it.get("identifier") and it.get("lat") and it.get("lng"):
                    _COORDS[it["identifier"]] = (float(it["lat"]), float(it["lng"]))
    return _COORDS.get(ident)


def _gmap_url(it, city):
    """Googleマップの検索URL（APIキー不要の公式URL形式）。住所＋名前で検索する。"""
    addr = it.get("address") or {}
    q = " ".join(x for x in ("東京都", addr.get("addressLocality") or city,
                             addr.get("streetAddress", ""), it.get("name", "")) if x)
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q)


def _card_attrs(it):
    a = []
    c = _coords(it.get("identifier")) if it.get("identifier") else None
    if c:
        a.append(("lat", f"{c[0]:.6f}"))
        a.append(("lng", f"{c[1]:.6f}"))
    if it.get("_town"):
        a.append(("town", it["_town"]))
    days = [k for k, _ in DAY_OPTS if DAY_WORD[k] in (it.get("_days") or [])]
    if days:
        a.append(("day", "|".join(days)))
    for key, attr, _ in FACET_ATTRS:
        if it.get(attr):
            a.append((key, it[attr]))
    return "".join(f' data-{k}="{esc(v)}"' for k, v in a)


def _filter_bar(d):
    items = d["items"]
    facets = _facets(items)
    if not facets or len(items) < 6:
        return ""
    sel = []
    for key, lab, opts in facets:
        sel.append(f'        <select data-f="{key}" aria-label="{lab}で絞り込む">'
                   # スマホ幅(390px)で3つ並べると「場所：すべて」は切れる。見出しだけにする
                   f'<option value="">{lab}</option>'
                   + "".join(f'<option value="{esc(v)}">{esc(t)}</option>' for v, t in opts)
                   + "</select>")
    notes = []
    if any(k == "town" for k, _, _ in facets) and d["category"]["id"] in VISITING:
        notes.append('      <p class="flt-note">「場所」は事務所の所在地です。'
                     '訪問サービスは近くの町からも来てもらえます。</p>')
    if any(k == "day" for k, _, _ in facets):
        nod = sum(1 for it in items if not it.get("_days"))
        if nod:
            notes.append(f'      <p class="flt-note" id="flt-daynote" hidden>'
                         f'提供曜日の記載がない{nod}件は、曜日で絞ると表示されません。</p>')
    return (
        '    <div id="flt-top"></div>\n'
        '    <div class="flt" id="flt" hidden>\n'
        '      <div class="flt-row">\n' + "\n".join(sel) + '\n      </div>\n'
        f'      <p class="flt-n" aria-live="polite"><span><b id="flt-n">{len(items)}</b>'
        f' / {len(items)}件を表示</span>'
        '<button type="button" id="flt-reset" hidden>条件をクリア</button></p>\n'
        '    </div>'
        # 注記は上に貼りつかせない（スマホでバーが高くなりすぎるため）
        + "".join("\n" + x for x in notes)
    )


# 住所の「１－３９－１７」は全角で幅を取り、スマホではほぼ必ず2行に折り返す。
# 表示だけ半角にする（JSON-LD とCSVは元の表記のまま）。長音「ー」には触らない。
_HALF = {**{chr(0xFF10 + i): str(i) for i in range(10)},
         **{chr(0xFF21 + i): chr(0x41 + i) for i in range(26)},
         **{chr(0xFF41 + i): chr(0x61 + i) for i in range(26)},
         "\uff0d": "-", "\u3000": " "}


def _half(s: str) -> str:
    return "".join(_HALF.get(ch, ch) for ch in s)


def render_listing(d: dict) -> str:
    """掲載事業者カードを描画する。住所・電話は data の値をそのまま使う。"""
    out = []
    if d.get("listing_note"):
        out.append(f'    <p class="cnt">{d["listing_note"]}</p>')
    # 「事業所一覧へ」ボタンの飛び先。絞り込みバーと地図を含めた一覧全体の先頭
    out.append('    <div id="jigyosho"></div>')
    bar = _filter_bar(d)
    if bar:
        out.append(bar)
    if d["category"]["id"] in MAP_CATS:
        pins = sum(1 for it in d["items"] if it.get("identifier") and _coords(it["identifier"]))
        if pins:
            out.append(
                '    <div class="kmap-wrap">\n'
                f'      <button type="button" class="kmap-btn" id="kmap-btn" hidden>地図で見る<small>（{pins}件の場所）</small></button>\n'
                '      <div id="kmap" class="kmap" hidden></div>\n'
                '      <p class="kmap-n" id="kmap-n" hidden>地図：<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">国土地理院（地理院タイル）</a>を加工して作成。'
                '位置は厚生労働省の公表データの座標で、建物の入口とずれることがあります。</p>\n'
                '    </div>')
    out.append('    <div class="bizlist">')
    city = d["area"]["city_name"]
    cat_name = d["category"]["name"]
    for i, it in enumerate(d["items"], 1):
        # --- 1行目: 住所（区名まではページで分かるので番地から）と、名前と違うときだけ運営法人
        sub = []
        addr = it.get("address")
        if addr:
            loc = addr.get("addressLocality", "")
            street = addr.get("streetAddress", "")
            sub.append(esc(_half(street if loc == city else " ".join(x for x in (loc, street) if x))))
        org = it.get("parentOrganization")
        org = org if isinstance(org, str) else (org or {}).get("name", "")
        if org and re.sub(r"\s", "", org) != re.sub(r"\s", "", it["name"]):
            sub.append(f'<span class="c-org">{esc(org)}</span>')

        # --- 2行目: ひと目で分かる事実だけ。カテゴリ名と「〇〇エリア」は住所・ページと重複するので外す
        chips = [f'<span class="tag">{esc(t)}</span>' for t in it.get("_tags", [])
                 if t != cat_name and not t.endswith("エリア")]
        if it.get("_capacity"):
            chips.append(f'<span class="tag">定員{int(it["_capacity"])}人</span>')
        if it.get("_days"):
            short = {"土曜日": "土", "日曜日": "日", "祝日": "祝"}
            chips.append('<span class="c-days">提供日 %s</span>'
                         % esc("・".join(short.get(x, x) for x in it["_days"])))

        # --- 数の少ない項目（宅配弁当・賃貸などにだけある）は従来どおり表で
        rows = []
        if it.get("faxNumber"):
            rows.append(f'<dt>FAX</dt><dd>{esc(it["faxNumber"])}</dd>')
        if it.get("_hours"):
            rows.append(f'<dt>電話受付</dt><dd>{esc(it["_hours"])}</dd>')
        if it.get("_closed"):
            rows.append(f'<dt>事務所の休業日</dt><dd>{esc(it["_closed"])}</dd>')
        if it.get("areaServed"):
            rows.append(f'<dt>対応エリア</dt><dd>{esc(it["areaServed"])}</dd>')
        if it.get("description"):
            rows.append(f'<dt>特徴</dt><dd>{esc(it["description"])}</dd>')

        # --- 電話を主役に。ここが利用者にとっての「次の一歩」で、tel_tap で計測している
        act = []
        if it.get("telephone"):
            tel = re.sub(r"[^0-9]", "", it["telephone"])
            act.append(f'<a class="tel" href="tel:{tel}"><span class="tel-l">電話する</span>'
                       f'{esc(it["telephone"])}</a>')
        if it.get("address"):
            act.append(f'<a class="ext map" href="{esc(_gmap_url(it, city))}" target="_blank" rel="noopener">'
                       '地図<span class="sr">（Googleマップが開きます）</span></a>')
        if it.get("url"):
            act.append(f'<a class="ext" href="{esc(it["url"])}" target="_blank" rel="noopener">'
                       '公式サイト<span class="exti" aria-hidden="true">↗</span>'
                       '<span class="sr">（外部サイトが開きます）</span></a>')

        out.append(
            f'    <div class="card" id="b{i}"{_card_attrs(it)}>\n'
            f'      <h3><span class="no">{i}</span>{esc(it["name"])}</h3>\n'
            + (f'      <p class="c-sub">{"".join(sub)}</p>\n' if sub else "")
            + (f'      <div class="c-tags">{"".join(chips)}</div>\n' if chips else "")
            + (f'      <dl class="dl">{"".join(rows)}</dl>\n' if rows else "")
            + (f'      <div class="c-act">{"".join(act)}</div>\n' if act else "")
            # 事業所番号は利用者の判断材料ではないが、厚労省の公表システムで
            # 照合するときの手がかりなので、消さずに小さく残す
            + (f'      <p class="c-id">事業所番号 {esc(it["identifier"])}</p>\n'
               if it.get("identifier") else "")
            + "    </div>"
        )
    if bar:
        out.append('    <p class="flt-empty" id="flt-empty" hidden>条件に合う事業所はありません。'
                   '条件を1つ外してみてください。</p>')
    out.append('    </div>')
    out.append(
        '    <div class="warn"><strong>掲載情報についてのお願い</strong><br>'
        f'上記{len(d["items"])}件は、{d["modified"]}に{city}および各事業者の公表情報で確認した内容です。'
        '営業時間・対応エリア・空き状況は変動しますので、連絡の前に必ず公式情報をご確認ください。'
        '掲載内容の訂正・削除は、'
        '<a href="{{ROOT}}contact/">お問い合わせ</a>からご依頼いただければ'
        '<strong>理由の説明なしで削除します</strong>。</div>'
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
    # 行ごとの件数から、その市区町村でいちばん厚い行を出す（ページごとに必ず変わる一文）
    counts = [(label, len([t for t in towns if t["kana"] and t["kana"][0] in heads]))
              for label, heads in GYO]
    counts = [c for c in counts if c[1]]
    top_row, top_n = max(counts, key=lambda x: x[1])
    lead = (f'    <p>{city}の町域は{len(towns)}。五十音では{len(counts)}行にわたり、'
            f'最も多いのは<strong>{top_row}</strong>の{top_n}件です。'
            f'掲載事業者の対応範囲は町域単位で分かれているため、'
            f'問い合わせのときは「{city}{towns[0]["name"]}」のように町名まで伝えてください。</p>\n')
    return (f'    <h2 id="towns">{city}の町域一覧（対応エリアの目安）</h2>\n'
            + lead
            + '    <div class="towns-wrap">\n' + "\n".join(rows) + "\n    </div>\n"
            '    <p class="tiny">※町域ごとの事業者ページは、掲載できる事業者が3件以上そろった町域から順次公開します。</p>')


def render_toc(content: str) -> str:
    """本文中の <h2 id="..."> から目次を組み立てる。"""
    rows = []
    for anchor, text in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', content, re.S):
        label = re.sub(r"<[^>]+>", "", text).strip()
        rows.append('        <li><a href="#%s">%s</a></li>' % (anchor, label))
    return "\n".join(rows)


_TOWN_TABLE = re.compile(
    r'(?P<tw><div class="tw">\s*<table>\s*<thead><tr><th[^>]*>町域</th><th>掲載事業所</th></tr></thead>.*?</table>\s*</div>)',
    re.S)


def _mobile_tweaks(content: str, d: dict) -> str:
    """スマホで一覧にたどり着くまでが長いので、2つだけ手当てする。
    ① 冒頭の「事業所一覧へ」ボタンは build() でテンプレートの見出し直下に入れる
    ② 町域ごとの事業所名の表（一覧と同じ情報で、スマホだと2,000px超）を折りたたむ"""

    def fold(m):
        rows = m.group("tw").count("<tr>") - 1
        return ('<details class="more"><summary>町域ごとの事業所名を見る'
                f'<small>（{rows}町域）</small></summary>\n    {m.group("tw")}\n    </details>')
    return _TOWN_TABLE.sub(fold, content, count=1)


def build(slug: str) -> pathlib.Path:
    d = json.loads((BASE / "data" / f"{slug}.json").read_text(encoding="utf-8"))
    content = (BASE / "content" / f"{slug}.html").read_text(encoding="utf-8")
    tpl = (BASE / "templates" / "city.html").read_text(encoding="utf-8")
    n_items = len(d.get("items") or [])
    if n_items:
        # スマホでは一覧が4画面ほど下から始まるので、見出しのすぐ下に飛ぶボタンを置く（CSSでスマホ幅だけ表示）
        tpl = tpl.replace("    {{HERO_IMAGE}}",
                          f'    <a class="jump" href="#jigyosho">事業所一覧へ<small>（{n_items}件）</small></a>\n    {{{{HERO_IMAGE}}}}', 1)

    cat, area = d["category"], d["area"]
    out_dir = BASE / cat["id"] / area["pref_id"] / area["city_id"]
    root = "../" * 3  # /<cat>/<pref>/<city>/ からサイトルートまで

    content = content.replace("{{LISTING}}", render_listing(d))
    content = _mobile_tweaks(content, d)
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
