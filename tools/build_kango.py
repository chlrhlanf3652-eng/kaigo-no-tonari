#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""収集済みキャッシュから、訪問看護の市区町村ページを組み立てる。

  tools/cache/kango_<区>.json  →  data/houmon-kango_tokyo_<区>.json
                                  content/houmon-kango_tokyo_<区>.html
                                  data/site.json（町域を登録）

掲載3件未満の区はページを作らない。

使い方:
  python3 tools/build_kango.py            # キャッシュにある区すべて
  python3 tools/build_kango.py kita koto  # 指定した区だけ
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS
from counts import MADOGUCHI_OVERRIDE
from kango_tpl import HOUMON_KANGO
from build_day import ORG_DESC, AGE_BUCKETS, years_since
import mhlw_fields as MF

BASE = pathlib.Path(__file__).parent.parent
CACHE = pathlib.Path(__file__).parent / "cache"
TODAY = "2026-09-21"
MIN_ITEMS = 3


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ward_name(wid):
    return WARDS[wid]["name"] if wid in WARDS else wid


def to_items(rec, towns):
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
        it["_kind"] = r.get("org_kind") or "その他"
        it["_designated"] = r.get("designated") or ""
        it["_years"] = years_since(it["_designated"])
        if r.get("url"):
            it["url"] = r["url"]
        if r.get("days"):
            it["_days"] = r["days"]
        tags = []
        if town:
            tags.append(town + "エリア")
        if "日曜日" in (r.get("days") or []):
            tags.append("日曜日も訪問")
        elif "土曜日" in (r.get("days") or []):
            tags.append("土曜日も訪問")
        y = it["_years"]
        if y is not None and y >= 20:
            tags.append("20年以上")
        elif y is not None and y < 3:
            tags.append("開設3年以内")
        tags.append("訪問看護")
        it["_tags"] = tags
        out.append(it)
    return out


def build(wid, site):
    src = CACHE / f"kango_{wid}.json"
    if not src.exists():
        return False
    rec = json.loads(src.read_text(encoding="utf-8"))
    towns = rec["towns"]
    items = to_items(rec, towns)
    n = len(items)
    if n < MIN_ITEMS:
        print(f"  skip {wid}: 掲載{n}件（3件未満）")
        return False

    ward = rec["name"]
    madoguchi = MADOGUCHI_OVERRIDE.get(wid, rec["madoguchi"])
    total = rec.get("total") or n

    if madoguchi == "地域包括支援センター":
        note = f"{ward}では地域包括支援センターを区内各地に設置しています。"
    elif "（" in madoguchi:
        base, alias = madoguchi.split("（", 1)
        note = f"{ward}では{base}を「{alias.rstrip('）')}」の愛称で呼び、区内各地に設置しています。"
    else:
        note = f"{ward}では地域包括支援センターを「{madoguchi}」と呼び、区内各地に設置しています。"

    bucket, order = {}, []
    for it in items:
        t = it["_town"] or "その他"
        bucket.setdefault(t, [])
        if t not in order:
            order.append(t)
        bucket[t].append(it["name"])
    order.sort(key=lambda t: (-len(bucket[t]), t))
    dist = "\n".join('        <tr><th>%s</th><td>%s</td></tr>'
                     % (esc(t), esc("、".join(bucket[t]))) for t in order)

    # 法人の種別は東京都の「法人種別名」をそのまま集計する
    kinds = {}
    for it in items:
        kinds[it["_kind"]] = kinds.get(it["_kind"], 0) + 1
    kind_rows = sorted(kinds.items(), key=lambda x: (-x[1], x[0]))
    orgs = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (esc(k), v, ORG_DESC.get(k, "")) for k, v in kind_rows)
    top_org, top_n = kind_rows[0]
    iryo = kinds.get("医療法人", 0)
    org_note = ("掲載%d件のうち%sが%d件と最も多く、母体が医療機関である医療法人は%d件です。"
                % (n, top_org, top_n, iryo))

    # 開設からの年数
    ages = {}
    for it in items:
        y = it["_years"]
        if y is None:
            ages["不明"] = ages.get("不明", 0) + 1
            continue
        for lim, label, _ in AGE_BUCKETS:
            if y < lim:
                ages[label] = ages.get(label, 0) + 1
                break
    labels = [b[1] for b in AGE_BUCKETS] + ["不明"]
    desc = {b[1]: b[2] for b in AGE_BUCKETS}
    desc["不明"] = "指定年月日が読み取れなかったもの"
    ages_rows = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (lab, ages[lab], desc[lab]) for lab in labels if lab in ages)
    yrs = [it["_years"] for it in items if it["_years"] is not None]
    if yrs:
        veteran = sum(1 for y in yrs if y >= 20)
        newbie = sum(1 for y in yrs if y < 3)
        age_note = ("掲載%d件のうち、指定から20年以上の事業所は%d件、直近3年以内に指定を受けた事業所は%d件です。"
                    % (n, veteran, newbie))
    else:
        age_note = "指定年月日が読み取れる事業所がありませんでした。"
        veteran = newbie = 0

    centers = rec.get("centers")
    center_count_label = f"（区内{centers}か所）" if centers else ""
    scale_note = ("区内の数が多い一方、対応できる医療処置はステーションごとに違います。"
                  if total >= 60 else
                  "数が限られるため、必要な医療処置に対応できるかを先に確認してください。")

    # 定期訪問の曜日（厚労省オープンデータ）。24時間の緊急対応とは別もの。
    day_rows, day_note, sunday, weekend = MF.day_table(items)

    content = HOUMON_KANGO % dict(
        ward=ward, id=wid, center=madoguchi, center_note=note,
        center_count_label=center_count_label, scale_note=scale_note,
        total=total, townc=len(towns), n=n, dist=dist,
        orgs=orgs, org_note=org_note, ages=ages_rows, age_note=age_note,
        days=day_rows, day_note=day_note)
    (BASE / "content" / f"houmon-kango_tokyo_{wid}.html").write_text(content, encoding="utf-8")

    faq = [
        {"q": f"{ward}で訪問看護を使うには、まず何をすればいいですか？",
         "a": f"主治医に「自宅で訪問看護を使いたい」と伝えるのが最初の一歩です。"
              f"訪問看護は主治医の指示書がないと始められないため、{ward}のステーションに直接連絡しても"
              f"そこで止まります。入院中なら退院支援の窓口、主治医が決まっていなければ{madoguchi}が相談先です。"},
        {"q": f"{ward}には訪問看護ステーションが何件ありますか？",
         "a": f"東京都が公表している指定事業所一覧では、2026年9月1日時点で{ward}内に{total}件の"
              f"訪問看護ステーションが指定を受けています。"
              f"本ページではそのうち{n}件を連絡先つきで掲載しています。"},
        {"q": f"{ward}の掲載事業所は、どこを見て絞り込めばいいですか？",
         "a": f"まず必要な医療処置に対応できるかで絞り、次に距離で絞るのが順番です。"
              f"{ward}の掲載{n}件では{top_org}が{top_n}件、医療法人が{iryo}件、"
              f"指定から20年以上の事業所が{veteran}件です。"
              f"そのうえで、ご自宅の町名を伝えて{ward}内の対応エリアに入っているかを確認してください。"},
        {"q": f"{ward}で夜間や休日に急変したら、来てもらえますか？",
         "a": f"24時間の緊急対応体制をとっているステーションなら、連絡して必要と判断されれば訪問してもらえます。"
              f"ただしこれは加算のかかる体制で、{ward}内でもすべてのステーションが対応しているわけではありません。"
              f"上のサービス提供日の表は定期訪問の曜日で、{ward}の掲載{n}件では日曜日も訪問するところが"
              f"{sunday}件ありますが、これは緊急対応ができるという意味ではありません。契約前に必ず確認してください。"},
        {"q": f"{ward}で訪問看護の自己負担はいくらくらいですか？",
         "a": f"{ward}は介護報酬の地域区分で1級地（1単位＝11.40円）にあたるため、介護保険で使う場合、"
              "訪問看護ステーションからの訪問は20分未満で約358円、30分未満で約537円、"
              "30分以上1時間未満で約938円が1割負担の目安です。"
              f"これは基本報酬だけの金額で、緊急時訪問看護加算などが上乗せされます。"
              f"医療保険で使う場合は計算が別になるため、{ward}の事業所に実額を確認してください。"},
        {"q": "医療保険と介護保険のどちらになりますか？",
         "a": f"要介護認定を受けていれば原則として介護保険、受けていなければ医療保険です。"
              f"ただし国が定める疾病等に当てはまる場合や、急に状態が悪くなって特別訪問看護指示書が出た場合は、"
              f"認定があっても医療保険になります。{ward}に限らず全国共通の分岐で、判断は主治医とステーションが行います。"},
        {"q": f"{ward}で訪問介護（ヘルパー）と両方使えますか？",
         "a": f"使えます。医療的なケアは訪問看護、身体介護や家事は訪問介護と役割が分かれており、"
              f"両方を併用する方は珍しくありません。{ward}の訪問介護事業所は同じサイト内にまとめています。"
              "介護保険で使う場合は、どちらも区分支給限度基準額の範囲内で組むことになります。"},
    ]

    near = WARDS[wid]["near"][:6]
    nearby = "\n      ".join('<a href="{{ROOT}}houmon-kango/tokyo/%s/">%s</a>' % (x, ward_name(x))
                             for x in near)
    related = "\n      ".join([
        '<a href="{{ROOT}}houmon-kaigo/tokyo/%s/">%sの訪問介護<small>身体介護・生活援助</small></a>' % (wid, ward),
        '<a href="{{ROOT}}day-service/tokyo/%s/">%sのデイサービス<small>通所介護</small></a>' % (wid, ward),
        '<a href="{{ROOT}}short-stay/tokyo/%s/">%sのショートステイ<small>短期入所</small></a>' % (wid, ward),
        '<a href="{{ROOT}}fukushi-yogu/tokyo/%s/">%sの福祉用具レンタル<small>介護ベッド・車いす</small></a>' % (wid, ward),
        '<a href="{{ROOT}}takuhai-bento/tokyo/%s/">%sの宅配弁当<small>高齢者向け配食サービス</small></a>' % (wid, ward),
        '<a href="{{ROOT}}mimamori/tokyo/%s/">%sの見守りサービス<small>ひとり暮らしの安否確認</small></a>' % (wid, ward),
    ])
    sidebar = (
        '<div class="side cta-side">\n'
        '        <h4>まず主治医に相談を</h4>\n'
        '        <p>訪問看護は主治医の指示書が起点です。制度の分岐はハブにまとめています。</p>\n'
        '        <a class="btn" href="{{ROOT}}houmon-kango/">訪問看護のしくみを見る</a>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>このページの要点</h4>\n'
        '        <ul>\n'
        f'          <li>{ward}内のステーションは約{total}件</li>\n'
        '          <li>起点は主治医の訪問看護指示書</li>\n'
        '          <li>30分未満の訪問で約537円（1割）</li>\n'
        f'          <li>掲載{n}件のうち医療法人は{iryo}件</li>\n'
        f'          <li>主治医が未定なら{madoguchi}へ</li>\n'
        '        </ul>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>関連ガイド</h4>\n'
        '        <ul>\n'
        '          <li><a href="{{ROOT}}guide/youkaigo-nintei/">要介護認定の申請方法</a></li>\n'
        '          <li><a href="{{ROOT}}guide/soudan-madoguchi/">相談窓口の探し方</a></li>\n'
        '          <li><a href="{{ROOT}}guide/houmon-kaigo-dekirukoto/">ヘルパーに頼めること</a></li>\n'
        '          <li><a href="{{ROOT}}houmon-kango/">訪問看護のしくみ</a></li>\n'
        '        </ul>\n'
        '      </div>')

    d = {
        "slug": f"houmon-kango_tokyo_{wid}",
        "category": {"id": "houmon-kango", "name": "訪問看護", "path": "/houmon-kango/"},
        "area": {"pref_id": "tokyo", "pref_name": "東京都", "city_id": wid, "city_name": ward},
        "seo": {
            "title": f"{ward}の訪問看護{n}事業所｜主治医の指示書から始める【2026年9月更新】",
            "description": f"東京都{ward}の訪問看護ステーション{n}件を連絡先つきで掲載。"
                           f"区内{total}件の中から選ぶための所在町域・運営法人・開設年数・"
                           "定期訪問の曜日の内訳と、主治医の指示書から利用開始までの流れをまとめました。",
            "canonical": f"https://kaigonotonari.com/houmon-kango/tokyo/{wid}/",
            "og_title": f"{ward}の訪問看護ステーション一覧｜選び方と始め方",
            "og_description": f"{ward}の訪問看護ステーション{n}件を掲載。対応できる医療処置の確認と、"
                              "主治医の指示書から始める流れを解説します。",
            "og_image": "https://kaigonotonari.com/assets/ogp-houmon-kango.jpg",
        },
        "h1": f"{ward}の訪問看護ステーション一覧｜選び方と始め方",
        "published": TODAY, "modified": TODAY,
        "count_label": f"掲載：{n}事業所",
        "lead": f"東京都{ward}で訪問看護を探している方へ。区内にある{total}件のステーションから"
                f"{n}件を連絡先つきで掲載し、そのうち<strong>日曜日も定期訪問があるのは"
                f"{sunday}件</strong>であることまで示しました。"
                f"主治医の指示書から利用開始までの流れもまとめています。"
                f"訪問看護は事業所選びより先に<strong>主治医への相談</strong>が要ります。",
        "listing_note": f"{ward}内の訪問看護ステーションから{n}件を掲載しています"
                        "（東京都公表・2026年9月1日時点）。"
                        + (f"区内には{total}件が指定を受けており、事業所番号の順に等間隔で抽出したため、"
                           "開設の古い事業所と新しい事業所が混ざっています。"
                           if total > n else f"区内には{total}件が指定を受けており、そのすべてを掲載しています。")
                        + "掲載順は事業所の優劣を示すものではありません。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "近隣エリアの訪問看護", "nearby": nearby,
        "sources": [
            rec.get("source", "東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0）"),
            "厚生労働省「介護サービス情報公表システム」オープンデータ"
            "（2026年6月30日時点／サービス提供日・公式サイト）",
            f"{ward}「{madoguchi}一覧」",
            "厚生労働大臣が定める疾病等（訪問看護で医療保険が適用される範囲）",
            "厚生労働省「指定居宅サービス介護給付費単位数の算定構造」訪問看護費／"
            "介護報酬の地域区分（1級地・1単位11.40円）",
            f"日本郵便 郵便番号データにもとづく{ward}の町域一覧",
            "区内事業所数：東京都公表の指定事業所一覧にもとづく実数（2026年9月1日時点）",
        ],
        "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">事業所一覧</a>\n  <a class="m2" href="#s4">自己負担の目安</a>',
        "hero_image": "assets/ogp-houmon-kango.jpg",
        "towns": {"pref": "tokyo", "city": wid},
    }
    (BASE / "data" / f"houmon-kango_tokyo_{wid}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    site.setdefault("towns", {}).setdefault("tokyo", {})[wid] = towns
    ids = [c["id"] for c in site["cities"]["tokyo"]]
    if wid not in ids:
        site["cities"]["tokyo"].append({"id": wid, "name": ward, "status": "live"})
    print(f"  {ward}: {n}事業所 / 区内{total}件 / 医療法人{iryo}件 / title {len(d['seo']['title'])}字")
    return True


def build_pref_partial():
    """東京都ページ用の本文。区ごとのステーション数を1枚の表にする。

    区によって数が4倍以上違うので、この表そのものが「どこから当たるか」の材料になる。
    """
    rows = []
    for f in sorted(CACHE.glob("kango_*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        wid = f.stem[len("kango_"):]
        n = len(rec["items"])
        if n < MIN_ITEMS:
            continue
        its = to_items(rec, rec["towns"])
        iryo = sum(1 for it in its if it["_kind"] == "医療法人")
        veteran = sum(1 for it in its
                      if it["_years"] is not None and it["_years"] >= 20)
        rows.append((rec["total"] or n, rec["name"], wid, n, iryo, veteran))
    if not rows:
        return
    rows.sort(reverse=True)
    body = "\n".join(
        '        <tr><th><a href="{{ROOT}}houmon-kango/tokyo/%s/">%s</a></th>'
        '<td class="num">%d</td><td class="num">%d</td><td class="num">%d</td>'
        '<td class="num">%d</td></tr>' % (wid, name, total, n, iryo, veteran)
        for total, name, wid, n, iryo, veteran in rows)
    most = rows[0]
    least = rows[-1]
    total_all = sum(r[0] for r in rows)
    html = f"""
  <h2 id="kazu">東京23区の訪問看護ステーション数</h2>
  <p>掲載している{len(rows)}区だけで、区内のステーションは合わせて約{total_all}件あります。ただし<strong>区によって数が大きく違います</strong>。最も多い{most[1]}が約{most[0]}件、最も少ない{least[1]}が約{least[0]}件で、{most[0] / max(least[0], 1):.1f}倍の開きがあります。</p>
  <p>数が少ない区では、<strong>必要な医療処置に対応できるステーションがさらに絞られます</strong>。区内で見つからない場合、訪問看護は隣接する区から訪問してもらえることもあるので、区境にお住まいなら隣の区も当たってください。</p>
  <div class="tw">
  <table>
    <thead><tr><th style="width:26%">区</th><th>区内のステーション</th><th>本サイト掲載</th><th>うち医療法人</th><th>うち20年以上</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
  </div>
  <p class="tiny">区内のステーション数は東京都が公表している指定事業所一覧の実数（2026年9月1日時点）。医療法人の件数と指定から20年以上の件数は、本サイト掲載分についての集計です。24時間の緊急対応体制を取っているかは公表データに含まれないため、事業所へ直接ご確認ください。</p>

  <h2 id="tsukaikata">この表の使い方</h2>
  <ul class="check">
    <li><b>まず自分の区の行を見る</b>ステーションが多い区なら、対応できる医療処置で絞っても候補が残ります。少ない区なら、最初から隣接区も視野に入れてください。</li>
    <li><b>医療法人の列は、主治医との連携のしやすさの目安</b>母体が医療機関のステーションは、指示書のやり取りや急変時の連絡が早いことがあります。ただし数が少ない区が多いので、決め手にはしないでください。</li>
    <li><b>20年以上の列は、地域での評判を聞けるかどうかの目安</b>長く続いているステーションは、近所のケアマネジャーや利用者から実際の様子を聞ける可能性が高いです。ただし利用者が定着していて、すぐに空きが出ないこともあります。</li>
  </ul>
"""
    (BASE / "content" / "pref_houmon-kango_tokyo.html").write_text(html, encoding="utf-8")
    print(f"  東京都ページ本文: {len(rows)}区の表を書き出しました。")


if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(
        p.stem[len("kango_"):] for p in CACHE.glob("kango_*.json"))
    sp = BASE / "data" / "site.json"
    site = json.loads(sp.read_text(encoding="utf-8"))
    ok = sum(1 for t in targets if build(t, site))
    sp.write_text(json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8")
    build_pref_partial()
    print(f"\n{ok} ページ分のデータを書き出しました。")
