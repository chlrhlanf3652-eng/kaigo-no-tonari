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


CONTENT = """<h2 id="s1">高齢者向け宅配弁当が「ふつうの宅食」と違う3点</h2>
    <p>スーパーの惣菜や一般的な宅食サービスでも食事はまかなえます。それでも高齢者専門の配食サービスが選ばれるのは、次の3点が理由です。</p>
    <ul class="check">
      <li><b>手渡しで安否確認になる</b>毎日決まった時間に顔を見て手渡すため、異変にいち早く気づけます。ひとり暮らしの方にとっては、食事そのものより大きな価値になることがあります。</li>
      <li><b>やわらか食・ムース食がある</b>噛む力や飲み込む力が落ちた方でも食べられる形態が用意されています。一般の宅食にはほとんどありません。</li>
      <li><b>治療食に対応できる</b>塩分・たんぱく質・カロリーを調整した腎臓食、透析食、カロリー調整食を継続して届けられます。</li>
    </ul>

    <h2 id="s2">%(ward)sに配達するサービス一覧</h2>
    {{LISTING}}

    <h2 id="s3">料金の比較（%(ld)sの公表価格）</h2>
    <p>高齢者向け配食サービスは「おかずのみ」と「ごはんセット」で料金が分かれています。
    ライフデリは料金を公開しているので、%(ward)sを担当する<strong>%(ld)s</strong>の価格を掲載します。
    専門食（やわらか食・ムース食・治療食）の価格は全店共通ですが、<strong>普通食だけは店舗ごとに違います</strong>。</p>

    <div class="tw">
    <table>
      <caption class="tiny" style="text-align:left;padding-bottom:6px">%(ld)s の料金（2026年9月時点・1食あたり・税込）</caption>
      <thead><tr><th>食形態</th><th>おかずのみ</th><th>ごはんセット</th><th>こんな方に</th></tr></thead>
      <tbody>
%(prices)s
      </tbody>
    </table>
    </div>
    <p class="tiny">※まごころ弁当・宅配クック123は店舗ごとに料金が異なり、公式サイトに一律の価格表示がありません。お住まいの担当店舗に直接お問い合わせください。</p>

    <div class="note"><strong>1か月あたりの目安。</strong>夕食のみ（普通食のごはんセット%(rice)d円）を週5回利用した場合、1か月でおよそ<strong>%(month)s円前後</strong>です。毎日の買い物と調理の負担、食材の廃棄を考えると、必ずしも割高ではありません。</div>

    <h2 id="s4">食形態の選び方</h2>
    <p>「食べられる形」を間違えると、本人が食べきれずに残してしまい、結局続きません。迷ったら、下の順に考えてください。</p>

    <figure class="fig">
      <svg viewBox="0 0 900 200" role="img" aria-label="食形態の段階。普通食、やわらか食、ムース食の順にやわらかくなる。">
        <rect width="900" height="200" fill="#fcfdfd"/>
        <g font-family="Hiragino Sans, Yu Gothic, Meiryo, sans-serif" text-anchor="middle">
          <text x="450" y="30" font-size="15" font-weight="700" fill="#1d2b2a">噛む力・飲み込む力で選ぶ3段階</text>
          <rect x="40" y="55" width="240" height="96" rx="10" fill="#e9f3f1" stroke="#bcd6cf"/>
          <text x="160" y="85" font-size="18" font-weight="700" fill="#0d5344">普通食</text>
          <text x="160" y="110" font-size="13" fill="#55636a">見た目も味も普段どおり</text>
          <text x="160" y="132" font-size="12" fill="#55636a">食事づくりだけが負担な方</text>
          <text x="300" y="108" font-size="24" fill="#8a9793">›</text>
          <rect x="330" y="55" width="240" height="96" rx="10" fill="#e9f3f1" stroke="#bcd6cf"/>
          <text x="450" y="85" font-size="18" font-weight="700" fill="#0d5344">やわらか食</text>
          <text x="450" y="110" font-size="13" fill="#55636a">箸やスプーンでほぐれる</text>
          <text x="450" y="132" font-size="12" fill="#55636a">硬いものを残すようになった方</text>
          <text x="590" y="108" font-size="24" fill="#8a9793">›</text>
          <rect x="620" y="55" width="240" height="96" rx="10" fill="#fdf1ea" stroke="#f0d0bc"/>
          <text x="740" y="85" font-size="18" font-weight="700" fill="#a9491a">ムース食</text>
          <text x="740" y="110" font-size="13" fill="#55636a">舌でつぶせるやわらかさ</text>
          <text x="740" y="132" font-size="12" fill="#55636a">むせる・飲み込みにくい方</text>
          <text x="450" y="180" font-size="12" fill="#55636a">※むせが続くときは、自己判断せず医師・歯科医師・言語聴覚士に相談してください</text>
        </g>
      </svg>
      <figcaption>食形態は「噛む力」と「飲み込む力」で選びます。無料試食を使い、本人が食べきれるかを必ず確認してください。</figcaption>
    </figure>

    <h2 id="s5">%(ward)sの配食サービス（区の事業）</h2>
    %(gov_body)s
    <p class="tiny">なお、民間の宅配弁当は<strong>介護保険の給付対象外</strong>で、全額自己負担です。介護保険の限度額を気にせず使えるという利点もあります。</p>

    <h2 id="s6">失敗しない5つのチェックポイント</h2>
    <ul class="check">
      <li><b>1. 置き配か、手渡しか</b>安否確認を目的にするなら手渡し一択です。応答がないときに緊急連絡先へ連絡してもらえるかも確認してください。</li>
      <li><b>2. ご自宅の町域が配達エリアに入っているか</b>同じ%(ward)sでも、店舗によって対応する町域が異なります。「一部地域を除く」と書かれている店舗が多いので、住所を伝えて必ず確認を。</li>
      <li><b>3. 日曜・祝日も配達があるか</b>日曜が定休の店舗もあります。毎日必要な方は、日曜分をどうするか事前に決めておきましょう。</li>
      <li><b>4. 無料試食ができるか</b>多くの事業者が試食を用意しています。本人が「これなら食べられる」と感じるかが、続けられるかどうかを決めます。</li>
      <li><b>5. 休止・キャンセルの締め切り時間</b>入院や外出で急に不要になることがあります。前日何時までキャンセルできるかを契約前に確認してください。</li>
    </ul>

    <h2 id="s7">よくある質問</h2>
    {{FAQ}}
"""


def build(wid, site):
    ward = wname(wid)
    d = B[wid]
    items = items_of(wid, ward)
    n = len(items)
    rice = d["ld_plain"][1]
    month = f"{rice * 5 * 4.3:,.0f}"

    content = CONTENT % dict(ward=ward, ld=d["ld_shop"], prices=price_rows(d["ld_plain"]),
                             rice=rice, month=month, gov_body=d["gov_body"])
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
         "a": "週に数回、夕食だけといった使い方が一般的です。曜日や食数の変更、休止にも対応している事業者が"
              "ほとんどですが、変更の締め切り時間は事業者ごとに違うので契約前に確認してください。"},
        {"q": "留守のときはどうなりますか？",
         "a": "手渡しを原則とする事業者では、応答がない場合に再訪問したり、"
              "あらかじめ登録した緊急連絡先へ連絡したりする運用をとっています。"
              "この対応こそが安否確認の中身なので、契約前に手順を必ず確認してください。"},
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
                        "配達エリアは町域単位で細かく分かれているため、申し込み前に必ずご自宅の住所で確認してください。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "近隣エリアの宅配弁当", "nearby": nearby,
        "sources": sources, "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">サービス一覧</a>\n  <a class="m2" href="#s3">料金を見る</a>',
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
