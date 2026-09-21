#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高齢者向け宅配弁当の市区町村ページを組み立てる。

区ごとに必ず違うのは次の3点で、ここがページの中身の差になる。
  - その区に配達できる店舗（まごころ弁当・ライフデリ・宅配クック123）
  - 担当ライフデリ店の普通食の価格（専門食は全店共通だが、普通食だけ店舗ごとに違う）
  - 区が配食事業をやっているか、やっていないか

使い方: python3 tools/build_bento.py [区ID...]
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS as W
from bento_data import WARDS as B, COMMON_PRICES
from bento_tpl import BENTO

BASE = pathlib.Path(__file__).parent.parent
TODAY = "2026-09-21"
EXTRA = {"komae": "狛江市", "mitaka": "三鷹市", "musashino": "武蔵野市"}


def wname(wid):
    return W[wid]["name"] if wid in W else EXTRA.get(wid, wid)


def price_rows(ld_plain):
    rows = [("普通食", ld_plain[0], ld_plain[1], "食事づくりが負担になってきた方")]
    who = {"やわらか食": "噛む力が落ちてきた方", "ムース食": "飲み込みに不安がある方",
           "カロリー調整食": "糖尿病などでカロリー管理が必要な方",
           "腎臓食": "たんぱく質・塩分制限がある方", "透析食": "人工透析を受けている方"}
    for k, (a, b) in COMMON_PRICES.items():
        rows.append((k, a, b, who[k]))
    return "\n".join(
        '        <tr><th>%s</th><td class="num">%s円</td><td class="num">%s円</td><td>%s</td></tr>'
        % r for r in rows)


def items_of(wid, ward):
    d = B[wid]
    out = []
    for name, tel, loc, street, area, tags in d["shops"]:
        it = {"@type": "LocalBusiness", "name": name}
        if tel:
            it["telephone"] = tel
        if loc:
            it["address"] = {"@type": "PostalAddress", "addressCountry": "JP",
                             "addressRegion": "東京都", "addressLocality": loc,
                             "streetAddress": street}
        it["areaServed"] = area
        it["_tags"] = tags
        out.append(it)
    g = d["gov"]
    if g:
        it = {"@type": "GovernmentOffice", "name": g["name"]}
        if g.get("tel"):
            it["telephone"] = g["tel"]
        if g.get("fax"):
            it["faxNumber"] = g["fax"]
        it["areaServed"] = ward
        it["description"] = g["desc"] + f"（窓口: {g['dept']}）"
        it["_tags"] = g["tags"]
        out.append(it)
    return out




def build(wid, site):
    ward = wname(wid)
    d = B[wid]
    items = items_of(wid, ward)
    n = len(items)
    rice = d["ld_plain"][1]
    month = f"{rice * 5 * 4.3:,.0f}"

    # 普通食の値段が23区の中でどのあたりかを言い添える（区ごとに必ず変わる一文）
    plains = sorted(v["ld_plain"][0] for v in B.values())
    rank = plains.index(d["ld_plain"][0]) + 1
    if rank == 1:
        price_rank = f"当サイト掲載{len(plains)}区のなかで最も安い設定です。"
    elif rank == len(plains):
        price_rank = f"当サイト掲載{len(plains)}区のなかでは高めの設定です。"
    else:
        price_rank = (f"当サイト掲載{len(plains)}区のなかでは安いほうから{rank}番目で、"
                      f"最も安い区より{d['ld_plain'][0] - plains[0]}円高い設定です。")

    brands = sorted({("まごころ弁当" if "まごころ" in x[0] else
                      "ライフデリ" if "ライフデリ" in x[0] else
                      "宅配クック123" if "クック" in x[0] else "その他") for x in d["shops"]})
    mago = sum(1 for x in d["shops"] if "まごころ" in x[0])
    brand_note = (f"まごころ弁当が{mago}店舗と最も多く、"
                  if mago >= 2 else "") + \
                 ("ライフデリと宅配クック123も配達エリアに入っています。"
                  if len(brands) >= 3 else "複数のブランドが配達エリアに入っています。")

    def esc(x):
        return x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    rows, inside = [], 0
    for name, tel, loc, street, area, tags in d["shops"]:
        where = loc if loc else "—"
        if loc == ward:
            inside += 1
        rows.append('        <tr><th>%s</th><td>%s</td><td>%s</td></tr>'
                    % (esc(name), esc(where), esc(area)))
    if d["gov"]:
        rows.append('        <tr><th>%s</th><td>%s</td><td>%s</td></tr>'
                    % (esc(d["gov"]["name"]), ward + "（行政）", "区が定める対象者"))
    shoplist = "\n".join(rows)
    outside = len(d["shops"]) - inside
    inside_note = (f"{ward}に店舗があるのは{inside}件で、"
                   f"残り{outside}件は区外の店舗またはエリア対応です。"
                   if outside else f"掲載している店舗はすべて{ward}内にあります。")

    content = BENTO % dict(shoplist=shoplist, inside_note=inside_note,
                           ward=ward, n=n, ld=d["ld_shop"], prices=price_rows(d["ld_plain"]),
                           plain=d["ld_plain"][0], rice=rice, month=month,
                           price_rank=price_rank, brand_note=brand_note,
                           gov_body=d["gov_body"])
    (BASE / "content" / f"takuhai-bento_tokyo_{wid}.html").write_text(content, encoding="utf-8")

    gov = d["gov"]
    faq = [
        {"q": f"{ward}で高齢者向けの宅配弁当を頼むには、どこに連絡すればいいですか？",
         "a": f"上の一覧にある事業者へ直接お電話ください。まずは配達エリアにご自宅の町名が入っているかを確認し、"
              "無料試食を申し込むのが確実です。どれを選ぶか迷う場合は、地域包括支援センターでも相談できます。"},
        {"q": "宅配弁当は介護保険で安くなりますか？",
         "a": "民間の配食サービスは介護保険の給付対象外で、全額自己負担です。"
              "そのかわり要介護認定がなくても使え、区分支給限度基準額を圧迫しないという利点があります。"
              + (f"{ward}の区の事業を利用できる場合は、自己負担の条件が変わることがあります。" if gov else "")},
        {"q": "やわらか食やムース食は普通食よりどのくらい高いですか？",
         "a": f"{d['ld_shop']}の公表価格では、ごはんセットで普通食{rice}円に対し、"
              f"やわらか食830円、ムース食760円です。治療食（腎臓食940円・透析食950円）はさらに上がります。"
              "価格は改定されることがあるため、申し込み前に公式情報をご確認ください。"},
        {"q": "毎日でなくても頼めますか？",
         "a": f"週に数回、夕食だけという使い方が一般的で、{ward}に配達する{n}件はいずれも食数と曜日を選べます。"
              f"ただし変更・休止の締め切り時間は事業者ごとに違うため、{ward}で複数を比べるときはここも聞いておいてください。"},
        {"q": "留守のときはどうなりますか？",
         "a": f"{ward}に配達する事業者の多くは手渡しが原則で、応答がないときは再訪問するか、登録した緊急連絡先へ連絡します。"
              f"この手順こそが安否確認の中身なので、{ward}で申し込む前に「何分待つか」「誰に連絡するか」まで確認してください。"
              f"日中の不在が多いご家庭は、{ward}の見守りサービスと組み合わせたほうが確実です。"},
    ]

    near = W[wid]["near"][:6]
    nearby = "\n      ".join('<a href="{{ROOT}}takuhai-bento/tokyo/%s/">%s</a>' % (x, wname(x))
                             for x in near)
    related = "\n      ".join([
        '<a href="{{ROOT}}houmon-kaigo/tokyo/%s/">%sの訪問介護<small>ホームヘルプ</small></a>' % (wid, ward),
        '<a href="{{ROOT}}koreisha-chintai/tokyo/%s/">%sの高齢者可賃貸<small>断られない部屋探し</small></a>' % (wid, ward),
        '<a href="{{ROOT}}mimamori/tokyo/%s/">%sの見守りサービス<small>ひとり暮らしの安否確認</small></a>' % (wid, ward),
        '<a href="{{ROOT}}kaimono-daiko/tokyo/%s/">%sの買い物代行<small>食材の調達</small></a>' % (wid, ward),
        '<a href="{{ROOT}}kaji-daiko/tokyo/%s/">%sの家事代行<small>調理・掃除</small></a>' % (wid, ward),
        '<a href="{{ROOT}}day-service/tokyo/%s/">%sのデイサービス<small>昼食つきの通所</small></a>' % (wid, ward),
    ])
    sidebar = (
        '<div class="side cta-side">\n'
        '        <h4>迷ったら試食から</h4>\n'
        '        <p>本人が「これなら食べられる」と感じるかが続くかどうかを決めます。多くの事業者が無料試食を用意しています。</p>\n'
        '        <a class="btn" href="#s2">配達するサービスを見る</a>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>このページの要点</h4>\n'
        '        <ul>\n'
        f'          <li>{ward}に配達できるのは{n}件</li>\n'
        f'          <li>普通食ごはんセット{rice}円（{d["ld_shop"]}）</li>\n'
        '          <li>専門食の価格はライフデリ全店共通</li>\n'
        f'          <li>{"区の配食事業あり" if gov else "区の配食事業は確認できず"}</li>\n'
        '        </ul>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>関連ガイド</h4>\n'
        '        <ul>\n'
        '          <li><a href="{{ROOT}}guide/kaigoshoku-keitai/">介護食の食形態とは</a></li>\n'
        '          <li><a href="{{ROOT}}guide/goen-yobou/">誤嚥を防ぐ食事の工夫</a></li>\n'
        '          <li><a href="{{ROOT}}guide/hitorigurashi-shokuji/">ひとり暮らしの食事の整え方</a></li>\n'
        '          <li><a href="{{ROOT}}guide/soudan-madoguchi/">介護の相談窓口の探し方</a></li>\n'
        '        </ul>\n'
        '      </div>')

    sources = [
        "まごころ弁当 公式サイト「東京都 %sの配食サービス店舗」" % ward,
        "ライフデリ 公式サイト「%s」（料金表を含む）" % d["ld_shop"],
        "宅配クック123 公式サイト「店舗検索（東京都%s）」" % ward,
    ]
    if gov:
        sources.append(f"{ward}「{gov['name']}」（{gov['dept']}）")
    else:
        sources.append(f"{ward} 公式ホームページ 高齢者向けサービス一覧（区の配食事業の記載なし・2026年9月確認）")

    d2 = {
        "slug": f"takuhai-bento_tokyo_{wid}",
        "category": {"id": "takuhai-bento", "name": "宅配弁当・配食サービス", "path": "/takuhai-bento/"},
        "area": {"pref_id": "tokyo", "pref_name": "東京都", "city_id": wid, "city_name": ward},
        "seo": {
            "title": f"{ward}の高齢者向け宅配弁当{n}社｜料金比較【2026年9月更新】",
            "description": f"東京都{ward}に配達する高齢者向け宅配弁当・配食サービス{n}件を連絡先つきで掲載。"
                           f"やわらか食・ムース食・治療食の料金比較、手渡しの安否確認、"
                           f"{'区の配食事業' if gov else '区の支援状況'}まで解説します。",
            "canonical": f"https://kaigonotonari.com/takuhai-bento/tokyo/{wid}/",
            "og_title": f"{ward}の高齢者向け宅配弁当｜料金比較と選び方",
            "og_description": f"{ward}に配達する高齢者向け配食サービス{n}件を掲載。"
                              "食形態別の料金、安否確認、区の事業をまとめました。",
            "og_image": "https://kaigonotonari.com/assets/ogp-takuhai-bento.jpg",
        },
        "h1": f"{ward}の高齢者向け宅配弁当・配食サービス｜料金比較と選び方",
        "published": TODAY, "modified": TODAY,
        "count_label": f"掲載：{n}サービス",
        "lead": f"東京都{ward}で高齢者向けの宅配弁当を探している方へ。"
                f"区内に配達できるサービス{n}件を連絡先つきで掲載し、"
                f"やわらか食・ムース食・治療食の料金、手渡しによる安否確認、"
                f"{'区の配食事業' if gov else '区の支援状況'}までまとめました。",
        "listing_note": f"2026年9月時点で{ward}への配達を公表しているサービスを掲載しています。"
                        f"配達エリアは町域単位で細かく分かれているため、{ward}内でも申し込み前に必ずご自宅の住所で確認してください。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "近隣エリアの宅配弁当", "nearby": nearby,
        "sources": sources, "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">サービス一覧</a>\n  <a class="m2" href="#s4">料金を見る</a>',
        "hero_image": "assets/ogp-takuhai-bento.jpg",
        "towns": {"pref": "tokyo", "city": wid},
    }
    (BASE / "data" / f"takuhai-bento_tokyo_{wid}.json").write_text(
        json.dumps(d2, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {ward}: {n}サービス / 普通食ごはん{rice}円 / title {len(d2['seo']['title'])}字")
    return True


if __name__ == "__main__":
    targets = sys.argv[1:] or list(B)
    sp = BASE / "data" / "site.json"
    site = json.loads(sp.read_text(encoding="utf-8"))
    ok = sum(1 for t in targets if build(t, site))
    print(f"\n{ok} ページ分のデータを書き出しました。")
