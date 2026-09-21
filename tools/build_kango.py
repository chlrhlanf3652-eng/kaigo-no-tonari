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
from wardstats import summarize, ORG_DESC, RECV_DESC

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
        tags = []
        if town:
            tags.append(town + "エリア")
        if "年中無休" in closed:
            tags.append("年中無休")
        elif closed and "土" not in closed and "日" not in closed:
            tags.append("土日も受付")
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

    st = summarize(items)
    orgs = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (k, v, ORG_DESC.get(k, "")) for k, v in st["orgs"])
    recv = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (k, v, RECV_DESC.get(k, "")) for k, v in st["recv"])

    org_map = dict(st["orgs"])
    top_org, top_n = st["orgs"][0]
    iryo = org_map.get("医療法人", 0)
    org_note = ("掲載%d件のうち%sが%d件と最も多く、医療法人は%d件です。"
                % (n, top_org, top_n, iryo))

    nonstop = dict(st["recv"]).get("年中無休", 0)
    weekend = nonstop + dict(st["recv"]).get("土日も受付", 0)
    recv_note = ("掲載%d件のうち、年中無休が%d件、土日も電話を受けるところを含めると%d件です。"
                 % (n, nonstop, weekend))

    centers = rec.get("centers")
    center_count_label = f"（区内{centers}か所）" if centers else ""
    scale_note = (f"区内に訪問看護ステーションがこれだけある一方、"
                  f"対応できる医療処置はステーションごとに違います。" if total >= 60 else
                  f"数が限られるため、必要な医療処置に対応できるかを先に確認してください。")

    content = HOUMON_KANGO % dict(
        ward=ward, id=wid, center=madoguchi, center_note=note,
        center_count_label=center_count_label, scale_note=scale_note,
        total=total, townc=len(towns), n=n, dist=dist,
        orgs=orgs, org_note=org_note, recv=recv, recv_note=recv_note,
        open_min=st["open_min"], open_max=st["open_max"])
    (BASE / "content" / f"houmon-kango_tokyo_{wid}.html").write_text(content, encoding="utf-8")

    faq = [
        {"q": f"{ward}で訪問看護を使うには、まず何をすればいいですか？",
         "a": f"主治医に「自宅で訪問看護を使いたい」と伝えるのが最初の一歩です。"
              f"訪問看護は主治医の指示書がないと始められないため、{ward}のステーションに直接連絡しても"
              f"そこで止まります。入院中なら退院支援の窓口、主治医が決まっていなければ{madoguchi}が相談先です。"},
        {"q": f"{ward}には訪問看護ステーションが何件ありますか？",
         "a": f"2026年9月時点で、介護情報サイトの掲載ベースで約{total}件のステーションが{ward}内にあります。"
              f"本ページではそのうち{n}件を連絡先つきで掲載しています。"
              "全件は厚生労働省「介護サービス情報公表システム」で確認できます。"},
        {"q": f"{ward}の掲載事業所は、どこを見て絞り込めばいいですか？",
         "a": f"まず必要な医療処置に対応できるかで絞り、次に距離で絞るのが順番です。"
              f"{ward}の掲載{n}件では年中無休が{nonstop}件、土日も電話を受けるところを含めると{weekend}件あります。"
              f"そのうえで、ご自宅の町名を伝えて{ward}内の対応エリアに入っているかを確認してください。"},
        {"q": f"{ward}で夜間や休日に急変したら、来てもらえますか？",
         "a": f"24時間の緊急対応体制をとっているステーションなら、連絡して必要と判断されれば訪問してもらえます。"
              f"ただしこれは加算のかかる体制で、{ward}内でもすべてのステーションが対応しているわけではありません。"
              "上の受付体制の表は電話の受付時間であり、緊急対応の可否とは別ですので、契約前に必ず確認してください。"},
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
        f'          <li>掲載{n}件のうち年中無休は{nonstop}件</li>\n'
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
                           f"区内約{total}件の中から選ぶための所在町域・運営法人・受付体制の内訳と、"
                           "主治医の指示書から利用開始までの流れをまとめました。",
            "canonical": f"https://kaigonotonari.com/houmon-kango/tokyo/{wid}/",
            "og_title": f"{ward}の訪問看護ステーション一覧｜選び方と始め方",
            "og_description": f"{ward}の訪問看護ステーション{n}件を掲載。対応できる医療処置の確認と、"
                              "主治医の指示書から始める流れを解説します。",
            "og_image": "https://kaigonotonari.com/assets/ogp-houmon-kango.jpg",
        },
        "h1": f"{ward}の訪問看護ステーション一覧｜選び方と始め方",
        "published": TODAY, "modified": TODAY,
        "count_label": f"掲載：{n}事業所",
        "lead": f"東京都{ward}で訪問看護を探している方へ。区内にある約{total}件のステーションから"
                f"{n}件を連絡先つきで掲載し、あわせて所在町域・運営法人・受付体制の内訳と、"
                f"主治医の指示書から利用開始までの流れをまとめました。"
                f"訪問看護は事業所選びより先に<strong>主治医への相談</strong>が要ります。",
        "listing_note": f"{ward}内の訪問看護ステーションから{n}件を掲載しています（2026年9月時点）。"
                        f"区内には約{total}件のステーションがあり、全件は厚生労働省"
                        "「介護サービス情報公表システム」で確認できます。掲載順は事業所の優劣を示すものではありません。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "近隣エリアの訪問看護", "nearby": nearby,
        "sources": [
            "厚生労働省「介護事業所・生活関連情報検索（介護サービス情報公表システム）」",
            f"{ward}「{madoguchi}一覧」",
            "厚生労働大臣が定める疾病等（訪問看護で医療保険が適用される範囲）",
            f"日本郵便 郵便番号データにもとづく{ward}の町域一覧",
            "区内事業所数の目安：ハートページナビ 掲載件数（2026年9月時点）",
        ],
        "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">事業所一覧</a>\n  <a class="m2" href="#s4">問い合わせ前に</a>',
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
        st = summarize(to_items(rec, rec["towns"]))
        iryo = dict(st["orgs"]).get("医療法人", 0)
        nonstop = dict(st["recv"]).get("年中無休", 0)
        rows.append((rec["total"] or n, rec["name"], wid, n, iryo, nonstop))
    if not rows:
        return
    rows.sort(reverse=True)
    body = "\n".join(
        '        <tr><th><a href="{{ROOT}}houmon-kango/tokyo/%s/">%s</a></th>'
        '<td class="num">%d</td><td class="num">%d</td><td class="num">%d</td>'
        '<td class="num">%d</td></tr>' % (wid, name, total, n, iryo, nonstop)
        for total, name, wid, n, iryo, nonstop in rows)
    most = rows[0]
    least = rows[-1]
    total_all = sum(r[0] for r in rows)
    html = f"""
  <h2 id="kazu">東京23区の訪問看護ステーション数</h2>
  <p>掲載している{len(rows)}区だけで、区内のステーションは合わせて約{total_all}件あります。ただし<strong>区によって数が大きく違います</strong>。最も多い{most[1]}が約{most[0]}件、最も少ない{least[1]}が約{least[0]}件で、{most[0] / max(least[0], 1):.1f}倍の開きがあります。</p>
  <p>数が少ない区では、<strong>必要な医療処置に対応できるステーションがさらに絞られます</strong>。区内で見つからない場合、訪問看護は隣接する区から訪問してもらえることもあるので、区境にお住まいなら隣の区も当たってください。</p>
  <div class="tw">
  <table>
    <thead><tr><th style="width:26%">区</th><th>区内のステーション</th><th>本サイト掲載</th><th>うち医療法人</th><th>うち年中無休</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
  </div>
  <p class="tiny">区内のステーション数はハートページナビの掲載件数（2026年9月時点）。医療法人の件数と年中無休の件数は、本サイト掲載分についての集計です。年中無休は電話の受付体制であり、24時間の緊急対応体制の有無とは別です。</p>

  <h2 id="tsukaikata">この表の使い方</h2>
  <ul class="check">
    <li><b>まず自分の区の行を見る</b>ステーションが多い区なら、対応できる医療処置で絞っても候補が残ります。少ない区なら、最初から隣接区も視野に入れてください。</li>
    <li><b>医療法人の列は、主治医との連携のしやすさの目安</b>母体が医療機関のステーションは、指示書のやり取りや急変時の連絡が早いことがあります。ただし数が少ない区が多いので、決め手にはしないでください。</li>
    <li><b>年中無休の列は「電話がつながる日」</b>実際に夜間・休日に訪問してもらえるかは、24時間の緊急対応体制を取っているかどうかで決まります。契約前に必ず個別に確認してください。</li>
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
