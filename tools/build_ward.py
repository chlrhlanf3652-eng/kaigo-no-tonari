#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""収集済みキャッシュから、訪問介護の市区町村ページを組み立てる。

  tools/cache/<区>.json  →  data/houmon-kaigo_tokyo_<区>.json
                            content/houmon-kaigo_tokyo_<区>.html
                            data/site.json（status を live に、町域を登録）

掲載3件未満の区はページを作らない（薄いページを量産しないための最低線）。

使い方:
  python3 tools/build_ward.py            # キャッシュにある区すべて
  python3 tools/build_ward.py kita koto  # 指定した区だけ
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS
from counts import COUNTS, MADOGUCHI_OVERRIDE
from content_tpl import HOUMON_KAIGO

BASE = pathlib.Path(__file__).parent.parent
CACHE = pathlib.Path(__file__).parent / "cache"
TODAY = "2026-09-21"
MIN_ITEMS = 3

EXTRA_NAMES = {"komae": "狛江市", "mitaka": "三鷹市", "musashino": "武蔵野市"}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ward_name(wid):
    return WARDS[wid]["name"] if wid in WARDS else EXTRA_NAMES.get(wid, wid)


def to_items(rec, towns):
    """収集した生データを schema.org の LocalBusiness に整える。"""
    names = sorted([t["name"] for t in towns], key=len, reverse=True)
    out = []
    for r in rec["items"]:
        street = r.get("address", "").replace("東京都" + rec["name"], "").strip()
        town = next((t for t in names if street.startswith(t)), "")
        it = {"@type": "LocalBusiness", "name": r["name"]}
        if r.get("tel"):
            it["telephone"] = r["tel"]
        it["address"] = {"@type": "PostalAddress", "addressCountry": "JP",
                         "addressRegion": "東京都", "addressLocality": rec["name"],
                         "streetAddress": street}
        if r.get("org"):
            it["parentOrganization"] = r["org"]
        if r.get("identifier"):
            it["identifier"] = r["identifier"]
        if r.get("fax") and r["fax"] != "-":
            it["faxNumber"] = r["fax"]
        if r.get("hours"):
            it["_hours"] = r["hours"]
        closed = r.get("closed", "")
        if closed:
            it["_closed"] = closed
        it["_town"] = town
        tags = []
        if town:
            tags.append(town + "エリア")
        if "年中無休" in closed:
            tags.append("年中無休")
        elif closed and "土" not in closed and "日" not in closed:
            tags.append("土日も受付")
        tags.append("訪問介護")
        it["_tags"] = tags
        out.append(it)
    return out


def build(wid, site):
    rec = json.loads((CACHE / f"{wid}.json").read_text(encoding="utf-8"))
    towns, items = rec["towns"], None
    items = to_items(rec, towns)
    n = len(items)
    if n < MIN_ITEMS:
        print(f"  skip {wid}: 掲載{n}件（3件未満）")
        return False

    ward = rec["name"]
    madoguchi = MADOGUCHI_OVERRIDE.get(wid, rec["madoguchi"])
    total = COUNTS[wid]

    if madoguchi == "地域包括支援センター":
        note = f"{ward}では地域包括支援センターを区内各地に設置しています。"
    elif "（" in madoguchi:
        base, alias = madoguchi.split("（", 1)
        note = f"{ward}では{base}を「{alias.rstrip('）')}」の愛称で呼び、区内各地に設置しています。"
    else:
        note = f"{ward}では地域包括支援センターを「{madoguchi}」と呼び、区内各地に設置しています。"

    # 掲載事業所の所在町域を集計する（区ごとに必ず違う表になる）
    bucket, order = {}, []
    for it in items:
        t = it["_town"] or "その他"
        if t not in bucket:
            bucket[t] = []
            order.append(t)
        bucket[t].append(it["name"])
    order.sort(key=lambda t: (-len(bucket[t]), t))
    dist = "\n".join('        <tr><th>%s</th><td>%s</td></tr>'
                     % (esc(t), esc("、".join(bucket[t]))) for t in order)

    content = HOUMON_KAIGO % dict(ward=ward, id=wid, center=madoguchi, center_note=note,
                                  total=total, townc=len(towns), n=n, dist=dist)
    (BASE / "content" / f"houmon-kaigo_tokyo_{wid}.html").write_text(content, encoding="utf-8")

    faq = [
        {"q": f"{ward}で訪問介護を使うには、まず何をすればいいですか？",
         "a": f"お住まいの地区を担当する「{madoguchi}（地域包括支援センター）」に相談するのが最初の一歩です。"
              "要介護認定の申請方法から、ケアマネジャー（居宅介護支援事業所）の紹介まで無料で案内してもらえます。"},
        {"q": f"{ward}には訪問介護事業所が何件ありますか？",
         "a": f"2026年9月時点で、介護情報サイトの掲載ベースで約{total}件の訪問介護事業所が{ward}内にあります。"
              f"本ページではそのうち{n}件を連絡先つきで掲載しています。"
              "全件は厚生労働省「介護サービス情報公表システム」で確認できます。"},
        {"q": "訪問介護の自己負担はいくらくらいですか？",
         "a": f"{ward}は介護報酬の地域区分で1級地（1単位＝11.40円）にあたります。自己負担1割の場合、"
              "身体介護20分以上30分未満で約278円、生活援助20分以上45分未満で約204円が目安です（各種加算は別途）。"},
        {"q": "ヘルパーに家族の分の食事や庭の草むしりも頼めますか？",
         "a": "介護保険の訪問介護では頼めません。訪問介護は利用者本人の生活に必要な支援に限られ、"
              "家族分の家事、来客対応、庭の手入れ、大掃除などは対象外です。"
              "保険外の自費サービスや家事代行を併用する方法があります。"},
        {"q": "事業所は途中で変更できますか？",
         "a": "変更できます。担当のケアマネジャーに相談すれば、ケアプランを見直したうえで"
              "別の訪問介護事業所に切り替えられます。相性やシフトの都合で変更する方は珍しくありません。"},
        {"q": "要介護認定の結果が出る前でもサービスを使えますか？",
         "a": "申請日にさかのぼってサービスを利用できる「暫定ケアプラン」という仕組みがあります。"
              "ただし想定より低い介護度で認定された場合、超過分が全額自己負担になるリスクがあります。"
              "利用を急ぐ場合は、必ずケアマネジャーとリスクを確認したうえで進めてください。"},
    ]

    near = WARDS[wid]["near"][:6]
    nearby = "\n      ".join('<a href="{{ROOT}}houmon-kaigo/tokyo/%s/">%s</a>' % (x, ward_name(x))
                             for x in near)
    related = "\n      ".join([
        '<a href="{{ROOT}}takuhai-bento/tokyo/%s/">%sの宅配弁当<small>高齢者向け配食サービス</small></a>' % (wid, ward),
        '<a href="{{ROOT}}koreisha-chintai/tokyo/%s/">%sの高齢者可賃貸<small>断られない部屋探し</small></a>' % (wid, ward),
        '<a href="{{ROOT}}houmon-kango/tokyo/%s/">%sの訪問看護<small>医療ケアが必要な方へ</small></a>' % (wid, ward),
        '<a href="{{ROOT}}day-service/tokyo/%s/">%sのデイサービス<small>通所介護</small></a>' % (wid, ward),
        '<a href="{{ROOT}}mimamori/tokyo/%s/">%sの見守りサービス<small>ひとり暮らしの安否確認</small></a>' % (wid, ward),
        '<a href="{{ROOT}}kaigo-taxi/tokyo/%s/">%sの介護タクシー<small>通院・外出の送迎</small></a>' % (wid, ward),
    ])
    sidebar = (
        '<div class="side cta-side">\n'
        '        <h4>どこに相談すればいい？</h4>\n'
        '        <p>介護がはじめての方は、まず地域の相談窓口へ。無料で手続きを案内してもらえます。</p>\n'
        '        <a class="btn" href="{{ROOT}}guide/soudan-madoguchi/">相談窓口の探し方を見る</a>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>このページの要点</h4>\n'
        '        <ul>\n'
        f'          <li>{ward}内の訪問介護事業所は約{total}件</li>\n'
        f'          <li>{ward}は1級地（1単位11.40円）</li>\n'
        '          <li>身体介護30分未満で約278円（1割）</li>\n'
        f'          <li>最初の相談は{madoguchi}</li>\n'
        '        </ul>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>関連ガイド</h4>\n'
        '        <ul>\n'
        '          <li><a href="{{ROOT}}guide/youkaigo-nintei/">要介護認定の申請方法</a></li>\n'
        '          <li><a href="{{ROOT}}guide/caremanager/">ケアマネジャーの選び方</a></li>\n'
        '          <li><a href="{{ROOT}}guide/kubun-shikyu-gendo/">区分支給限度基準額とは</a></li>\n'
        '          <li><a href="{{ROOT}}guide/jihi-service/">介護保険外サービスの相場</a></li>\n'
        '        </ul>\n'
        '      </div>')

    d = {
        "slug": f"houmon-kaigo_tokyo_{wid}",
        "category": {"id": "houmon-kaigo", "name": "訪問介護", "path": "/houmon-kaigo/"},
        "area": {"pref_id": "tokyo", "pref_name": "東京都", "city_id": wid, "city_name": ward},
        "seo": {
            "title": f"{ward}の訪問介護{n}事業所｜料金と選び方【2026年9月更新】",
            "description": f"東京都{ward}の訪問介護（ホームヘルプ）事業所{n}件を連絡先つきで掲載。"
                           f"区内約{total}件の中から選ぶための料金の目安、頼めること・頼めないこと、"
                           f"{madoguchi}への相談から利用開始までの流れを解説します。",
            "canonical": f"https://kaigonotonari.com/houmon-kaigo/tokyo/{wid}/",
            "og_title": f"{ward}の訪問介護事業所一覧｜料金の目安と選び方",
            "og_description": f"{ward}の訪問介護事業所{n}件を掲載。料金の目安、できること・できないこと、"
                              "利用開始までの流れを解説します。",
            "og_image": "https://kaigonotonari.com/assets/ogp-houmon-kaigo.jpg",
        },
        "h1": f"{ward}の訪問介護事業所一覧｜料金の目安と選び方",
        "published": TODAY, "modified": TODAY,
        "count_label": f"掲載：{n}事業所",
        "lead": f"東京都{ward}で訪問介護（ホームヘルプ）を探している方へ。区内にある約{total}件の事業所から"
                f"{n}件を連絡先つきで掲載し、あわせて自己負担額の目安、ヘルパーに頼めること・頼めないこと、"
                f"相談から利用開始までの流れをまとめました。はじめて介護保険を使う方は、"
                f"まず「{madoguchi}」への相談から始めるのが近道です。",
        "listing_note": f"{ward}内の訪問介護事業所から{n}件を掲載しています（2026年9月時点）。"
                        f"区内には約{total}件の事業所があり、全件は厚生労働省"
                        "「介護サービス情報公表システム」で確認できます。掲載順は事業所の優劣を示すものではありません。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "近隣エリアの訪問介護", "nearby": nearby,
        "sources": [
            "厚生労働省「介護事業所・生活関連情報検索（介護サービス情報公表システム）」",
            f"{ward}「{madoguchi}一覧」",
            f"{ward}「要介護・要支援認定の申請からサービス利用までの流れ」",
            "令和6年度介護報酬改定 訪問介護 基本報酬単位数／介護報酬の地域区分（1級地・1単位11.40円）",
            f"日本郵便 郵便番号データにもとづく{ward}の町域一覧",
            "区内事業所数の目安：ハートページナビ／LIFULL介護 各掲載件数（2026年9月時点）",
        ],
        "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">事業所一覧</a>\n  <a class="m2" href="#s5">利用の流れ</a>',
        "hero_image": "assets/ogp-houmon-kaigo.jpg",
        "towns": {"pref": "tokyo", "city": wid},
    }
    (BASE / "data" / f"houmon-kaigo_tokyo_{wid}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    site.setdefault("towns", {}).setdefault("tokyo", {})[wid] = towns
    ids = [c["id"] for c in site["cities"]["tokyo"]]
    if wid not in ids:
        site["cities"]["tokyo"].append({"id": wid, "name": ward, "status": "live"})
    else:
        for c in site["cities"]["tokyo"]:
            if c["id"] == wid:
                c["status"] = "live"
    print(f"  {ward}: {n}事業所 / 町域{len(towns)} / 窓口「{madoguchi}」 / title {len(d['seo']['title'])}字")
    return True


if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(p.stem for p in CACHE.glob("*.json"))
    sp = BASE / "data" / "site.json"
    site = json.loads(sp.read_text(encoding="utf-8"))
    ok = sum(1 for t in targets if build(t, site))
    sp.write_text(json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8")
    live = [c["id"] for c in site["cities"]["tokyo"] if c["status"] == "live"]
    print(f"\n{ok} ページ分のデータを書き出しました。東京都の公開エリア: {len(live)}")
