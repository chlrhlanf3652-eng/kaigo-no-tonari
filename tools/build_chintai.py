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
from chintai_data import WARDS as C, NATIONWIDE, COVERS
import chintai_steps
from chintai_tpl import CHINTAI

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
    cov = COVERS[wid]
    covers = "\n".join(
        '        <tr><th>%s</th><td class="num">%s</td><td>%s</td></tr>' % (k, cov[k][0], cov[k][1])
        for k in ("家賃", "安否", "退去"))
    covers = (covers.replace("<th>家賃</th>", "<th>家賃を払い続けられるか</th>")
                    .replace("<th>安否</th>", "<th>室内で事故が起きないか</th>")
                    .replace("<th>退去</th>", "<th>退去時の対応ができるか</th>"))

    content = (CHINTAI.replace("@@COVERS@@", covers)
                      .replace("@@STEPS@@", chintai_steps.steps(ward, d["madoguchi"], cov))
                      .replace("@@LEAD@@", chintai_steps.lead(ward, d["madoguchi"], cov))
                      .replace("@@CLOSE@@", chintai_steps.close(ward, cov))
                      .replace("@@COVER_NOTE@@", cov["note"])
                      .replace("@@WARD@@", ward)
                      .replace("@@MADOGUCHI@@", d["madoguchi"])
                      .replace("@@NEIGHBORS@@", neighbors)
                      .replace("@@BODY@@", d["body"]))
    (BASE / "content" / f"koreisha-chintai_tokyo_{wid}.html").write_text(content, encoding="utf-8")

    faq = [
        {"q": f"{ward}で高齢者が賃貸を借りるには、まずどこに相談すればいいですか？",
         "a": f"{d['madoguchi']}が入口です。{ward}の街の不動産店を回る前にここへ相談すると、"
              f"年齢を理由に断られにくい物件と、{ward}が用意している制度を先に把握できます。"},
        {"q": f"{ward}で保証人がいなくても借りられますか？",
         "a": f"家賃債務保証会社を使えば保証人なしで契約できる物件があり、{ward}でも同じです。"
              + (f"しかも{ward}では{cov['家賃'][1]}ため、保証料の負担そのものを軽くできます。"
                 if cov["家賃"][0] == "◎" else
                 f"ただし{ward}に保証料の助成はないので、保証会社の初回保証料（家賃の30〜50%%程度）は自己負担になります。")
              + "一般財団法人高齢者住宅財団の家賃債務保証は公的性格のある制度で、高齢者世帯の利用を想定しています。"},
        {"q": f"{ward}で年齢を理由に断られるのは違法ではないのですか？",
         "a": f"民間の賃貸借契約では貸主に契約の自由があるため、{ward}に限らず年齢を理由とする入居拒否が"
              "直ちに違法とされるわけではありません。"
              f"国は住宅セーフティネット制度で高齢者等の入居を拒まない住宅の登録を進めており、"
              f"{d['madoguchi']}でも登録物件の有無を確認できます。"},
        {"q": f"ひとり暮らしで、{ward}に緊急連絡先になる親族がいません。",
         "a": "見守りサービスの導入を申し込み時に伝えると、貸主の不安に答える材料になります。"
              + (f"{ward}の場合、{cov['安否'][1]}ので、まずそちらを申し込んでください。"
                 if cov["安否"][0] in ("◎", "○") else
                 f"{ward}には区の安否確認がないため、センサー型・電話型・配食の手渡し型などから"
                 "自分で選ぶことになります。"),
         },
        {"q": f"{ward}では一般の賃貸と、サ高住のどちらがよいでしょうか？",
         "a": f"{ward}の区の制度で貸主の3つの不安を埋められるなら一般の賃貸で十分ですが、"
              + (f"{ward}は3つのうち{sum(1 for k in ('家賃','安否','退去') if cov[k][0] in ('◎','○'))}つしか"
                 "埋まらないため、" if sum(1 for k in ("家賃","安否","退去") if cov[k][0] in ("◎","○")) < 3
                 else f"{ward}は3つとも埋まるため、")
              + "ひとり暮らしへの不安が強い場合はサービス付き高齢者向け住宅も並行して検討してください。"
              "費用と入居条件の違いは「サ高住と老人ホームの違い」にまとめています。"},
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
        "mcta": '<a class="m1" href="#s2">区の居住支援</a>\n  <a class="m2" href="#s4">相談先一覧</a>',
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
