#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""東京都オープンデータのキャッシュから、福祉用具の市区町村ページを組み立てる。

  tools/cache/yogu_<区>.json  →  data/fukushi-yogu_tokyo_<区>.json
                                 content/fukushi-yogu_tokyo_<区>.html

このページの軸は「借りるのか買うのか」。介護保険で福祉用具を買う場合、
指定を受けた販売事業者から買ったものにしか支給されないので、
その事業所が販売の指定も持っているかどうかが利用者にとっていちばん効く。
東京都の CSV は貸与と販売を別行で持つため、事業所番号で名寄せして判定する。

使い方:
  python3 tools/build_yogu.py             # キャッシュにある区すべて
  python3 tools/build_yogu.py chiyoda     # 指定した区だけ
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import koreika as KO
import linkgrid as LG
from wards import WARDS
from build_day import ORG_DESC, AGE_BUCKETS, years_since, esc, ward_name
from build_short import age_table
import mhlw_fields as MF

BASE = pathlib.Path(__file__).parent.parent
CACHE = pathlib.Path(__file__).parent / "cache"
TODAY = "2026-09-22"
MIN_ITEMS = 3

LEND = "福祉用具貸与"
SELL = "特定福祉用具販売"

MIX_DESC = {
    "両方": "借りるのも買うのも、この1社で完結する。"
            "入浴用いすやポータブルトイレも保険を使って買える",
    "貸与のみ": "介護ベッドや車いすのレンタルは頼めるが、"
                "保険を使った購入はここではできない",
    "販売のみ": "ポータブルトイレや入浴用いすなどの購入は頼めるが、"
                "レンタルは別の事業所を当たることになる",
}
MIX_ORDER = ["両方", "貸与のみ", "販売のみ"]


def mix_of(services):
    s = set(services or [])
    if LEND in s and SELL in s:
        return "両方"
    if SELL in s:
        return "販売のみ"
    return "貸与のみ"


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
        it["_town"] = town
        it["_kind"] = r.get("org_kind") or "その他"
        mix = mix_of(r.get("services"))
        it["_mix"] = mix
        d = r.get("designated") or ""
        it["_designated"] = d
        it["_years"] = years_since(d)
        if r.get("url"):
            it["url"] = r["url"]
        if r.get("days"):
            it["_days"] = r["days"]
        tags = []
        if town:
            tags.append(town + "エリア")
        tags.append("貸与と販売" if mix == "両方" else mix)
        if "土曜日" in (r.get("days") or []):
            tags.append("土曜日も対応")
        if it["_years"] is not None and it["_years"] >= 20:
            tags.append("20年以上")
        it["_tags"] = tags
        out.append(it)
    return out


def stats(items, ward):
    n = len(items)
    mx = {}
    for it in items:
        mx[it["_mix"]] = mx.get(it["_mix"], 0) + 1
    labels = [k for k in MIX_ORDER if k in mx]
    mixes = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (k if k != "両方" else "貸与と販売の両方", mx[k], MIX_DESC[k])
        for k in labels)
    both = mx.get("両方", 0)
    sell_only = mx.get("販売のみ", 0)
    lend_only = mx.get("貸与のみ", 0)
    if both == n:
        mix_note = ("%sの掲載%d件は、すべて貸与と販売の両方の指定を持っています。"
                    % (ward, n))
    else:
        mix_note = ("%sの掲載%d件のうち、貸与と販売の両方を扱うのが%d件、"
                    "貸与だけが%d件、販売だけが%d件です。"
                    % (ward, n, both, lend_only, sell_only))

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

    ok = {}
    for it in items:
        ok[it["_kind"]] = ok.get(it["_kind"], 0) + 1
    krows = sorted(ok.items(), key=lambda x: (-x[1], x[0]))
    orgs = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (esc(k), v, ORG_DESC.get(k, "")) for k, v in krows)
    top_kind, top_n = krows[0]
    org_note = "掲載%d件のうち%sが%d件と最も多くなっています。" % (n, top_kind, top_n)
    return mixes, mix_note, both, lend_only, sell_only, dist, orgs, org_note, top_kind, top_n


_TOTALS = None
_BOTH_AVG = None


def bucket_sizes(items):
    b = {}
    for it in items:
        t = it["_town"] or "その他"
        b[t] = b.get(t, 0) + 1
    return b


def both_avg():
    """23区ぶんの掲載分に占める「貸与と販売の両方」の割合（％）。"""
    global _BOTH_AVG
    if _BOTH_AVG is None:
        tot = bo = 0
        for f in CACHE.glob("yogu_*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            tot += len(r["items"])
            bo += sum(1 for x in r["items"]
                      if mix_of(x.get("services")) == "両方")
        _BOTH_AVG = (bo / tot * 100) if tot else 0.0
    return _BOTH_AVG


def ward_totals():
    """区ごとの (区名, 区内件数, 掲載件数, 貸与と販売の両方の件数)。"""
    global _TOTALS
    if _TOTALS is None:
        _TOTALS = {}
        for f in CACHE.glob("yogu_*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            both = sum(1 for x in r["items"] if mix_of(x.get("services")) == "両方")
            _TOTALS[f.stem[len("yogu_"):]] = (
                r["name"], r.get("total") or 0, len(r["items"]), both)
    return _TOTALS


def neighbours(wid):
    """隣接区の事業所数。福祉用具は配送範囲が区をまたぐので、
    隣の区の事業所にも頼める。買う予定があるなら「両方」の列で選ぶ。"""
    t = ward_totals()
    near = [x for x in WARDS[wid]["near"][:5] if x in t]
    rows = "\n".join(
        '        <tr><th><a href="{{ROOT}}fukushi-yogu/tokyo/%s/">%s</a></th>'
        '<td class="num">%d</td><td class="num">%d</td><td class="num">%d</td></tr>'
        % (x, t[x][0], t[x][1], t[x][2], t[x][3]) for x in near)
    return rows, sum(t[x][1] for x in near), len(near)


def build(wid, site):
    src = CACHE / f"yogu_{wid}.json"
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
    madoguchi = rec.get("madoguchi", "地域包括支援センター")
    total = rec.get("total") or n
    (mixes, mix_note, both, lend_only, sell_only,
     dist, orgs, org_note, top_kind, top_n) = stats(items, ward)
    ages, age_note, veteran = age_table(items)
    near_rows, near_total, near_cnt = neighbours(wid)

    scale_note = ("数が多いので、価格と品ぞろえで比べる余地があります。"
                  if total >= 20 else
                  "数が限られますが、福祉用具の配送範囲は区をまたぐため、"
                  "隣接区の事業所にも頼めます。")
    if sell_only or lend_only:
        sell_note = ("%sの掲載%d件のうち%d件が販売の指定を持っています。"
                     % (ward, n, both + sell_only))
    else:
        sell_note = "%sの掲載%d件はいずれも販売の指定を持っています。" % (ward, n)

    avg = both_avg()
    mine = both / n * 100
    if mine >= avg + 5:
        ratio_note = ("両方を扱う事業所は掲載分の%.0f%%で、23区平均の%.0f%%より多く、"
                      "%sは買うほうの相談がしやすい区です。" % (mine, avg, ward))
    elif mine <= avg - 5:
        ratio_note = ("両方を扱う事業所は掲載分の%.0f%%で、23区平均の%.0f%%より少なめです。"
                      "%sで買う予定があるなら、隣の区も見てください。" % (mine, avg, ward))
    else:
        ratio_note = ("両方を扱う事業所は掲載分の%.0f%%で、23区平均の%.0f%%と同じくらいです。"
                      % (mine, avg))
    top_town = max(bucket_sizes(items).items(), key=lambda x: (x[1], x[0]))
    town_note = "掲載分がいちばん多いのは%s（%d件）です。" % (top_town[0], top_town[1])

    day_rows, day_note, sunday, weekend = MF.day_table(items)

    from yogu_tpl import FUKUSHI_YOGU
    content = FUKUSHI_YOGU % dict(
        days=day_rows, day_note=day_note,
        ratio_note=ratio_note, town_note=town_note,
        ward=ward, id=wid, center=madoguchi, scale_note=scale_note,
        total=total, townc=len(towns), n=n, dist=dist,
        mixes=mixes, mix_note=mix_note, both=both, sell_note=sell_note,
        orgs=orgs, org_note=org_note, ages=ages, age_note=age_note,
        near=near_rows, neart=near_total, nearc=near_cnt)
    # 区ごとの公的統計（高齢化率・要介護認定者数）を本文の最後に足す
    content += "\n\n    " + KO.section(wid, ward, "fukushi-yogu", total)
    (BASE / "content" / f"fukushi-yogu_tokyo_{wid}.html").write_text(
        content, encoding="utf-8")

    faq = [
        {"q": f"{ward}で福祉用具を借りるには、まず何をすればいいですか？",
         "a": f"担当のケアマネジャー、いなければ{madoguchi}に相談してください。"
              f"福祉用具貸与もケアプランに位置づける必要があるため、{ward}の事業所に"
              "直接申し込むのではなくそこが入口になります。"
              "要介護認定を受けていない場合は、認定の申請から始まります。"},
        {"q": f"{ward}に福祉用具の事業所は何件ありますか？",
         "a": f"東京都が公表している指定事業所一覧では、2026年9月1日時点で{ward}内に{total}件の"
              "福祉用具の事業所（貸与または特定販売の指定を受けたもの）があります。"
              f"本ページではそのうち{n}件を連絡先つきで掲載し、"
              f"うち{both}件が貸与と販売の両方を扱っています。"},
        {"q": f"{ward}でポータブルトイレや入浴用のいすは、レンタルできますか？",
         "a": "できません。これらは購入（特定福祉用具販売）の対象で、"
              "同一年度に10万円までが保険の対象になります。"
              f"{ward}の掲載{n}件のうち販売の指定を持つのは{both + sell_only}件なので、"
              "買う予定があるならその中から選んでください。"},
        {"q": f"ネット通販で買っても、{ward}から保険は出ますか？",
         "a": f"出ません。{ward}の掲載{n}件のうち{both + sell_only}件が販売の指定を持っているので、"
              f"その中から選んでください。購入前に{ward}の介護保険担当か"
              "ケアマネジャーに相談するのが確実です。"},
        {"q": f"{ward}で介護ベッドを借りたいのですが、要介護1でも借りられますか？",
         "a": "原則として対象外です。ただし医師の所見などをもとに例外的に認められる場合があり、"
              f"判断するのは{ward}です。{ward}のケアマネジャー経由で相談してください。"
              "対象外になる用具の一覧は福祉用具のしくみのページにまとめています。"},
        {"q": f"{ward}でレンタル料金が事業所によって違うのはなぜですか？",
         "a": "福祉用具貸与だけは単位数が決まっておらず、事業所が商品ごとに価格を"
              f"設定するしくみだからです。{ward}の掲載{n}件は{top_kind}が{top_n}件と"
              "大半を占めますが、価格も品ぞろえも事業所ごとに差があるので、"
              "複数から見積もりを取ってください。"},
    ]

    nearby = LG.area_links("fukushi-yogu", wid)
    related = LG.service_links(
        "fukushi-yogu", wid,
        [("takuhai-bento", "の宅配弁当", "高齢者向け配食サービス"),
         ("mimamori", "の見守りサービス", "ひとり暮らしの安否確認")])
    sidebar = (
        '<div class="side cta-side">\n'
        '        <h4>買う前に確認を</h4>\n'
        '        <p>指定のない店で買うと保険は出ません。対象種目と手続きはハブにまとめています。</p>\n'
        '        <a class="btn" href="{{ROOT}}fukushi-yogu/">福祉用具のしくみを見る</a>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>このページの要点</h4>\n'
        '        <ul>\n'
        f'          <li>{ward}内の福祉用具事業所は{total}件（都指定）</li>\n'
        f'          <li>掲載{n}件のうち貸与と販売の両方が{both}件</li>\n'
        '          <li>購入は年度内10万円まで（1〜3割負担）</li>\n'
        '          <li>指定事業所以外で買うと支給されません</li>\n'
        f'          <li>入口はケアマネか{madoguchi}</li>\n'
        '        </ul>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>関連ガイド</h4>\n'
        '        <ul>\n'
        '          <li><a href="{{ROOT}}guide/youkaigo-nintei/">要介護認定の申請方法</a></li>\n'
        '          <li><a href="{{ROOT}}guide/soudan-madoguchi/">相談窓口の探し方</a></li>\n'
        '          <li><a href="{{ROOT}}fukushi-yogu/">福祉用具のしくみ</a></li>\n'
        '          <li><a href="{{ROOT}}houmon-kaigo/">訪問介護</a></li>\n'
        '        </ul>\n'
        '      </div>')

    d = {
        "slug": f"fukushi-yogu_tokyo_{wid}",
        "category": {"id": "fukushi-yogu", "name": "福祉用具",
                     "path": "/fukushi-yogu/"},
        "area": {"pref_id": "tokyo", "pref_name": "東京都",
                 "city_id": wid, "city_name": ward},
        "seo": {
            "title": f"{ward}の福祉用具{n}事業所｜レンタルと購入【2026年9月更新】",
            "description": f"東京都{ward}の福祉用具貸与・特定福祉用具販売の指定事業所{n}件を連絡先つきで掲載。"
                           f"区内{total}件のうち貸与と販売の両方を扱う事業所がどれかを示し、"
                           "年10万円までの購入費と、指定事業所から買う必要がある理由を解説します。",
            "canonical": f"https://kaigonotonari.com/fukushi-yogu/tokyo/{wid}/",
            "og_title": f"{ward}の福祉用具一覧｜借りるか買うかで事業所が変わります",
            "og_description": f"{ward}の福祉用具事業所{n}件を掲載。ポータブルトイレや入浴用いすは"
                              "購入しかできません。指定のない店で買うと保険は出ません。",
            "og_image": "https://kaigonotonari.com/assets/ogp-fukushi-yogu.jpg",
        },
        "h1": f"{ward}の福祉用具一覧｜借りるか買うかで事業所が変わります",
        "published": TODAY, "modified": TODAY,
        "count_label": f"掲載：{n}事業所",
        "lead": f"東京都{ward}で福祉用具のレンタルや購入を考えている方へ。"
                f"東京都の指定を受けた{total}件から{n}件を連絡先つきで掲載し、"
                f"そのうち<strong>貸与と販売の両方を扱う事業所が{both}件</strong>あることまで示しました。"
                "介護保険で福祉用具を買う場合、"
                "<strong>指定を受けた事業者から買ったものにしか支給されません</strong>。"
                "同じ商品をネット通販で買っても1円も戻らないので、ここが最初の分かれ目になります。",
        "listing_note": f"{ward}内の福祉用具貸与・特定福祉用具販売の指定事業所から{n}件を"
                        "掲載しています（東京都公表・2026年9月1日時点）。"
                        f"区内には{total}件が指定を受けており、"
                        + ("事業所番号の順に等間隔で抽出したため、開設の古い事業所と新しい事業所が"
                           "混ざっています。" if total > n else "そのすべてを掲載しています。")
                        + "「貸与と販売」「貸与のみ」「販売のみ」の表示は、"
                        + "東京都の一覧でその事業所がどちらのサービス種類で指定を受けているかによります。"
                        + "取扱商品や価格は事業所ごとに違い、この一覧では扱っていません。"
                        + "掲載順は事業所の優劣を示すものではありません。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "東京23区から福祉用具を探す", "nearby": nearby,
        "sources": [
            rec.get("source", "東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0）"),
            "厚生労働省「介護サービス情報公表システム」オープンデータ"
            "（2026年6月30日時点／対応曜日・公式サイト）",
            "江東区「介護保険特定福祉用具購入費の支給」（支給限度額・対象種目・指定事業者要件）",
            "厚生労働省「令和6年度介護報酬改定」福祉用具貸与・特定福祉用具販売の選択制",
            f"{ward}「{madoguchi}一覧」",
            f"日本郵便 郵便番号データにもとづく{ward}の町域一覧",
            *KO.SOURCES,
        ],
        "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">事業所一覧</a>\n  <a class="m2" href="#s4">費用のしくみ</a>',
        "hero_image": "assets/ogp-fukushi-yogu.jpg",
        "towns": {"pref": "tokyo", "city": wid},
    }
    (BASE / "data" / f"fukushi-yogu_tokyo_{wid}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    site.setdefault("towns", {}).setdefault("tokyo", {})[wid] = towns
    ids = [c["id"] for c in site["cities"]["tokyo"]]
    if wid not in ids:
        site["cities"]["tokyo"].append({"id": wid, "name": ward, "status": "live"})
    print(f"  {ward}: {n}事業所 / 区内{total}件 / 両方{both}件 / "
          f"title {len(d['seo']['title'])}字")
    return True


def build_pref_partial():
    """東京都ページ（/fukushi-yogu/tokyo/）の本文。

    区ごとに「区内の件数」と「掲載のうち貸与と販売の両方／貸与のみ」を並べる。
    買う予定がある人にとっては、この列がそのまま当たる順番になる。
    """
    rows = []
    for f in sorted(CACHE.glob("yogu_*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        wid = f.stem[len("yogu_"):]
        its = to_items(rec, rec["towns"])
        n = len(its)
        if n < MIN_ITEMS:
            continue
        both = sum(1 for it in its if it["_mix"] == "両方")
        lend = sum(1 for it in its if it["_mix"] == "貸与のみ")
        rows.append((rec["total"] or n, rec["name"], wid, n, both, lend))
    if not rows:
        return
    rows.sort(reverse=True)
    body = "\n".join(
        '        <tr><th><a href="{{ROOT}}fukushi-yogu/tokyo/%s/">%s</a></th>'
        '<td class="num">%d</td><td class="num">%d</td><td class="num">%d</td>'
        '<td class="num">%d</td></tr>' % (wid, name, total, n, both, lend)
        for total, name, wid, n, both, lend in rows)
    most, least = rows[0], rows[-1]
    total_all = sum(r[0] for r in rows)
    shown = sum(r[3] for r in rows)
    both_all = sum(r[4] for r in rows)
    html = f"""
  <h2 id="kazu">東京23区の福祉用具事業所数と、販売も扱う事業所</h2>
  <p>掲載している{len(rows)}区だけで、区内の福祉用具事業所は合わせて{total_all}件あります。最も多い{most[1]}が{most[0]}件、最も少ない{least[1]}が{least[0]}件で、{most[0] / max(least[0], 1):.1f}倍の開きがあります。ただし<strong>福祉用具は配送範囲が区をまたぐため、事業所数の少なさはほかのサービスほど不利になりません</strong>。隣の区の事業所にも頼めます。</p>
  <p>それよりも見てほしいのが<strong>販売も扱っているか</strong>です。介護保険で福祉用具を買う場合、指定を受けた事業者から買ったものにしか支給されません。本サイト掲載分{shown}件のうち{both_all}件が貸与と販売の両方を扱っています。ポータブルトイレや入浴用いすを買う予定があるなら、最初からこちらを当たってください。</p>
  <div class="tw">
  <table>
    <thead><tr><th style="width:26%">区</th><th>区内の事業所</th><th>本サイト掲載</th><th>うち貸与と販売</th><th>うち貸与のみ</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
  </div>
  <p class="tiny">区内の事業所数は東京都が公表している指定事業所一覧の実数（2026年9月1日時点）で、福祉用具貸与または特定福祉用具販売の指定を受けたものを事業所番号で名寄せした件数です。貸与と販売の内訳は、本サイト掲載分についての集計です。取扱商品や価格は公表データに含まれないため、事業所へ直接ご確認ください。</p>

  <h2 id="tsukaikata">この表の使い方</h2>
  <ul class="check">
    <li><b>買う予定があるなら「貸与と販売」の列から</b>腰掛便座・入浴補助用具・簡易浴槽は購入しかできません。貸与だけの事業所では保険を使って買えないので、先にここで絞ります。</li>
    <li><b>借りるだけなら区の数は気にしなくてよい</b>福祉用具は自宅まで運んで組み立てるサービスで、配送範囲は区をまたぎます。事業所数の少ない区でも、隣接区から来てもらえます。</li>
    <li><b>複数の事業所から見積もりを取る</b>福祉用具貸与は単位数が決まっておらず、事業所が価格を設定します。同じ介護ベッドでも金額が違うので、1社で決めないでください。</li>
  </ul>
"""
    (BASE / "content" / "pref_fukushi-yogu_tokyo.html").write_text(html, encoding="utf-8")
    print(f"  東京都ページ本文: {len(rows)}区の表を書き出しました。")


if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(
        p.stem[len("yogu_"):] for p in CACHE.glob("yogu_*.json"))
    sp = BASE / "data" / "site.json"
    site = json.loads(sp.read_text(encoding="utf-8"))
    ok = sum(1 for t in targets if build(t, site))
    sp.write_text(json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8")
    build_pref_partial()
    print(f"\n{ok} ページ分のデータを書き出しました。")
