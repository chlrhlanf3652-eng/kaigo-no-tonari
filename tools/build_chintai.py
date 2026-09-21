#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高齢者可賃貸の市区町村ページを組み立てる。

貸主の不安と答え方は区が変わっても同じなので共通テンプレートに置き、
区ごとに違う「その区が用意している居住支援」だけを差し込む。

使い方: python3 tools/build_chintai.py [区ID...]
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS as W
from chintai_data import WARDS as C, NATIONWIDE
from chintai_tpl import HEAD, TAIL

BASE = pathlib.Path(__file__).parent.parent
TODAY = "2026-09-21"
EXTRA = {"komae": "狛江市", "mitaka": "三鷹市", "musashino": "武蔵野市"}


def wname(wid):
    return W[wid]["name"] if wid in W else EXTRA.get(wid, wid)


def build(wid):
    ward = wname(wid)
    d = C[wid]
    items = []
    for g in d["gov"]:
        it = {"@type": "GovernmentOffice", "name": g["name"]}
        if g.get("tel"):
            it["telephone"] = g["tel"]
        if g.get("fax"):
            it["faxNumber"] = g["fax"]
        if g.get("street"):
            it["address"] = {"@type": "PostalAddress", "addressCountry": "JP",
                             "addressRegion": "東京都", "addressLocality": ward,
                             "streetAddress": g["street"]}
        it["areaServed"] = ward
        it["description"] = g["desc"]
        it["_tags"] = g["tags"]
        items.append(it)
    for s in NATIONWIDE:
        items.append({"@type": "Organization", "name": s["name"], "url": s["url"],
                      "description": s["desc"], "_tags": s["tags"]})
    n = len(items)

    neighbors = "・".join(wname(x) for x in W[wid]["near"][:3])
    def fill(t):
        return (t.replace("@@WARD@@", ward)
                 .replace("@@MADOGUCHI@@", d["madoguchi"])
                 .replace("@@NEIGHBORS@@", neighbors))

    content = (fill(HEAD)
               + f'\n\n    <h2 id="s2">{ward}の居住支援</h2>\n    ' + d["body"] + "\n\n"
               + '    <h2 id="s3">相談先・サービス一覧</h2>\n    {{LISTING}}\n\n    '
               + fill(TAIL)
               + '\n\n    <h2 id="s6">よくある質問</h2>\n    {{FAQ}}\n')
    (BASE / "content" / f"koreisha-chintai_tokyo_{wid}.html").write_text(content, encoding="utf-8")

    faq = [
        {"q": f"{ward}で高齢者が賃貸を借りるには、まずどこに相談すればいいですか？",
         "a": f"{d['madoguchi']}が入口です。街の不動産店を回る前にここへ相談すると、"
              "年齢を理由に断られにくい物件や制度を先に把握できます。"},
        {"q": "保証人がいなくても借りられますか？",
         "a": "家賃債務保証会社を利用すれば、保証人なしでも契約できる物件があります。"
              "一般財団法人高齢者住宅財団の家賃債務保証は公的性格のある制度で、"
              "高齢者世帯の利用を想定しています。"
              + ("杉並区では保証料の一部（最大30,000円）が助成されます。" if wid == "suginami" else "")},
        {"q": "年齢を理由に断られるのは違法ではないのですか？",
         "a": "民間の賃貸借契約では貸主に契約の自由があり、年齢を理由とする入居拒否が直ちに"
              "違法とされるわけではありません。一方で国は住宅セーフティネット制度により、"
              "高齢者等の入居を拒まない賃貸住宅の登録を進めています。"},
        {"q": "ひとり暮らしで緊急連絡先になる親族がいません。",
         "a": "見守りサービスの導入を申し込み時に伝えると、貸主の不安に答える材料になります。"
              + ("杉並区の高齢者等入居支援事業には、週1回の電話による安否確認が無料で付きます。"
                 if wid == "suginami" else
                 "センサー型・電話型・配食の手渡し型などがあり、費用も方式によって差があります。"),
         },
        {"q": "一般の賃貸ではなく、サ高住のほうがよいでしょうか？",
         "a": "ひとり暮らしに不安があるが自立して生活できる段階なら、安否確認と生活相談が"
              "必ず付くサービス付き高齢者向け住宅（サ高住）が合う場合があります。"
              "費用は家賃にサービス費が上乗せされます。上の比較表をご覧ください。"},
    ]

    nearby = "\n      ".join('<a href="{{ROOT}}koreisha-chintai/tokyo/%s/">%s</a>' % (x, wname(x))
                             for x in W[wid]["near"][:6])
    related = "\n      ".join([
        '<a href="{{ROOT}}houmon-kaigo/tokyo/%s/">%sの訪問介護<small>ホームヘルプ</small></a>' % (wid, ward),
        '<a href="{{ROOT}}takuhai-bento/tokyo/%s/">%sの宅配弁当<small>手渡しで安否確認</small></a>' % (wid, ward),
        '<a href="{{ROOT}}mimamori/tokyo/%s/">%sの見守りサービス<small>入居審査の材料になる</small></a>' % (wid, ward),
        '<a href="{{ROOT}}sakoju/tokyo/%s/">%sのサービス付き高齢者向け住宅<small>安否確認つきの住まい</small></a>' % (wid, ward),
        '<a href="{{ROOT}}ihinseiri/tokyo/%s/">%sの生前整理・不用品処分<small>引っ越し前の荷物減らし</small></a>' % (wid, ward),
        '<a href="{{ROOT}}jikka-baikyaku/tokyo/%s/">%sの実家売却<small>住み替えの資金</small></a>' % (wid, ward),
    ])
    sidebar = (
        '<div class="side cta-side">\n'
        '        <h4>不動産店より先に、区の窓口へ</h4>\n'
        f'        <p>{ward}では{d["madoguchi"]}が入口です。断られる回数を減らすための近道になります。</p>\n'
        '        <a class="btn" href="#s2">区の居住支援を見る</a>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>このページの要点</h4>\n'
        '        <ul>\n'
        '          <li>断られる理由は年齢ではなく3つの不安</li>\n'
        f'          <li>{ward}の入口は{d["madoguchi"]}</li>\n'
        '          <li>保証会社＋見守りで審査が通りやすくなる</li>\n'
        '          <li>緊急連絡先は2名分そろえる</li>\n'
        '        </ul>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>関連ガイド</h4>\n'
        '        <ul>\n'
        '          <li><a href="{{ROOT}}guide/housing-safety-net/">住宅セーフティネット制度とは</a></li>\n'
        '          <li><a href="{{ROOT}}guide/kachin-hosho/">家賃債務保証のしくみ</a></li>\n'
        '          <li><a href="{{ROOT}}guide/sakoju-toha/">サ高住と老人ホームの違い</a></li>\n'
        '          <li><a href="{{ROOT}}guide/seizen-seiri/">生前整理の進め方</a></li>\n'
        '        </ul>\n'
        '      </div>')

    sources = [f"{ward}「{g['name']}」" for g in d["gov"]] + [
        "一般財団法人高齢者住宅財団「家賃債務保証」",
        "株式会社R65「高齢者向け賃貸に関する実態調査（賃貸オーナー向け）」プレスリリース",
        "国土交通省 住宅セーフティネット制度",
        "CHINTAI「シニア・高齢者相談可の賃貸物件」",
    ]

    d2 = {
        "slug": f"koreisha-chintai_tokyo_{wid}",
        "category": {"id": "koreisha-chintai", "name": "高齢者可の賃貸", "path": "/koreisha-chintai/"},
        "area": {"pref_id": "tokyo", "pref_name": "東京都", "city_id": wid, "city_name": ward},
        "seo": {
            "title": f"{ward}の高齢者可賃貸｜相談窓口{n}件【2026年9月更新】",
            "description": f"東京都{ward}で高齢者が賃貸を断られないための進め方。"
                           f"{d['madoguchi']}など区の居住支援と全国対応サービス{n}件を連絡先つきで掲載し、"
                           "貸主の不安に先回りする5つの準備、サ高住との比較までまとめました。",
            "canonical": f"https://kaigonotonari.com/koreisha-chintai/tokyo/{wid}/",
            "og_title": f"{ward}の高齢者可賃貸｜断られないための進め方",
            "og_description": f"{ward}の居住支援と相談先{n}件を掲載。"
                              "断られる理由と、審査を通すための準備をまとめました。",
            "og_image": "https://kaigonotonari.com/assets/ogp-koreisha-chintai.jpg",
        },
        "h1": f"{ward}で高齢者が借りられる賃貸の探し方｜相談先と準備",
        "published": TODAY, "modified": TODAY,
        "count_label": f"相談窓口・サービス{n}件",
        "lead": f"東京都{ward}で高齢の親の部屋探しをしている方へ。"
                "年齢を理由に断られるのは、年齢そのものではなく年齢にひもづく3つの不安が理由です。"
                f"{ward}が用意している居住支援と、貸主の不安に先回りする準備をまとめました。"
                f"街の不動産店を回る前に、まず{d['madoguchi']}に相談するのが近道です。",
        "listing_note": f"{ward}で高齢者の部屋探しに使える窓口・サービスです（2026年9月時点）。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "近隣エリアの高齢者可賃貸", "nearby": nearby,
        "sources": sources, "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">区の居住支援</a>\n  <a class="m2" href="#s4">断られない準備</a>',
        "hero_image": "assets/ogp-koreisha-chintai.jpg",
        "towns": {"pref": "tokyo", "city": wid},
    }
    (BASE / "data" / f"koreisha-chintai_tokyo_{wid}.json").write_text(
        json.dumps(d2, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {ward}: {n}件 / 入口「{d['madoguchi']}」 / title {len(d2['seo']['title'])}字")
    return True


if __name__ == "__main__":
    targets = sys.argv[1:] or list(C)
    ok = sum(1 for t in targets if build(t))
    print(f"\n{ok} ページ分のデータを書き出しました。")
