#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""東京都オープンデータのキャッシュから、ショートステイの市区町村ページを組み立てる。

  tools/cache/short_<区>.json  →  data/short-stay_tokyo_<区>.json
                                  content/short-stay_tokyo_<区>.html

このページの軸は「予約が取れるか」。東京都の CSV の「事業所種別名」に
特養の併設事業所型／特養の空床利用型／単独型 が入っているので、そこを使う。
空床利用型は本体の特養が埋まっていると使えないため、利用者にとっての
差がいちばん大きい。ほかのポータルはこの列を出していない。

使い方:
  python3 tools/build_short.py             # キャッシュにある区すべて
  python3 tools/build_short.py chiyoda     # 指定した区だけ
"""
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS
from build_day import ORG_DESC, AGE_BUCKETS, years_since, esc, ward_name

BASE = pathlib.Path(__file__).parent.parent
CACHE = pathlib.Path(__file__).parent / "cache"
TODAY = "2026-09-22"
MIN_ITEMS = 3
TANKA = 11.40  # 東京23区＝1級地

# 東京都 CSV の「事業所種別名」ごとの、予約するうえでの意味
KIND_DESC = {
    "特養の併設事業所型":
        "特別養護老人ホームに併設され、ショートステイ専用の床を持つ。"
        "定期的に使う予定が立てやすい",
    "特養の空床利用型":
        "特養の入所者用ベッドの空きを使う。本体が満床だとその分使えず、"
        "直前の予約は取りにくい",
    "単独型":
        "ショートステイ単独で運営。専用の床を持つが、基本報酬は併設型より高い",
    "特養以外の併設事業所型":
        "老人保健施設や有料老人ホームなどに併設されている",
    "": "東京都の一覧に型の記載がないもの",
}
KIND_ORDER = ["特養の併設事業所型", "特養以外の併設事業所型", "単独型",
              "特養の空床利用型", ""]

# 短期入所生活介護費（1日あたり単位数／令和6年度改定後、令和8年6月改定を経て有効）
# 従来型個室と多床室は同額、ユニット型個室とユニット型個室的多床室も同額。
# 出典が独立した2社以上で一致することを確認したうえで載せている。
UNITS_STD = {1: (603, 645), 2: (672, 715), 3: (745, 787),
             4: (815, 856), 5: (884, 926)}          # (併設型, 単独型)
UNITS_UNIT = {1: (704, 746), 2: (772, 815), 3: (847, 891),
              4: (918, 959), 5: (987, 1028)}


def yen1(units: int) -> int:
    """単位数から1割負担の円を出す。費用総額を1円未満切り捨て、その1割。"""
    return int(math.floor(math.floor(units * TANKA) / 10))


def fee_rows(table):
    out = []
    for lv in sorted(table):
        h, s = table[lv]
        out.append(
            '        <tr><th>要介護%d</th><td class="num">%d単位</td>'
            '<td class="num">約%s円</td><td class="num">%d単位</td>'
            '<td class="num">約%s円</td></tr>'
            % (lv, h, f"{yen1(h):,}", s, f"{yen1(s):,}"))
    return "\n".join(out)


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
        fk = r.get("facility_kind") or ""
        it["_fkind"] = fk
        d = r.get("designated") or ""
        it["_designated"] = d
        y = years_since(d)
        it["_years"] = y
        tags = []
        if town:
            tags.append(town + "エリア")
        if fk == "特養の空床利用型":
            tags.append("特養の空床利用")
        elif fk == "単独型":
            tags.append("単独型")
        elif fk:
            tags.append("併設・専用床")
        if y is not None and y < 3:
            tags.append("開設3年以内")
        tags.append("ショートステイ")
        it["_tags"] = tags
        out.append(it)
    return out


def stats(items):
    """内訳の表に使う集計をまとめて出す。"""
    n = len(items)
    # 事業所の型
    fk = {}
    for it in items:
        fk[it["_fkind"]] = fk.get(it["_fkind"], 0) + 1
    labels = [k for k in KIND_ORDER if k in fk] + \
             [k for k in fk if k not in KIND_ORDER]
    kinds = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (esc(k or "記載なし"), fk[k], KIND_DESC.get(k, "")) for k in labels)
    kuushou = fk.get("特養の空床利用型", 0)
    heisetsu = sum(v for k, v in fk.items() if "併設" in k) + kuushou
    top_fk = max(fk.items(), key=lambda x: (x[1], x[0] != ""))[0]
    kind_note = ("掲載%d件のうち%sが%d件と最も多く、特養の空床を使う空床利用型は%d件です。"
                 % (n, top_fk or "型の記載がないもの", fk[top_fk], kuushou))

    # 所在町域
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

    # 法人の種別
    ok = {}
    for it in items:
        ok[it["_kind"]] = ok.get(it["_kind"], 0) + 1
    krows = sorted(ok.items(), key=lambda x: (-x[1], x[0]))
    orgs = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (esc(k), v, ORG_DESC.get(k, "")) for k, v in krows)
    top_kind, top_n = krows[0]
    org_note = "掲載%d件のうち%sが%d件と最も多くなっています。" % (n, top_kind, top_n)
    return (kinds, kind_note, kuushou, heisetsu, top_fk, fk,
            dist, orgs, org_note, top_kind, top_n)


def age_table(items):
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
    rows = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (lab, ages[lab], desc[lab]) for lab in labels if lab in ages)
    yrs = [it["_years"] for it in items if it["_years"] is not None]
    veteran = sum(1 for y in yrs if y >= 20)
    if yrs:
        note = ("掲載%d件のうち、指定から20年以上たっている事業所は%d件、"
                "最も古い事業所は約%d年前の指定です。"
                % (len(items), veteran, int(max(yrs))))
    else:
        note = "指定年月日が読み取れる事業所がありませんでした。"
    return rows, note, veteran


_TOTALS = None
_KUUSHOU_AVG = None


def bucket_sizes(items):
    b = {}
    for it in items:
        t = it["_town"] or "その他"
        b[t] = b.get(t, 0) + 1
    return b


def kuushou_avg():
    """23区ぶんの掲載分に占める空床利用型の割合（％）。区ごとの比較に使う。"""
    global _KUUSHOU_AVG
    if _KUUSHOU_AVG is None:
        tot = ku = 0
        for f in CACHE.glob("short_*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            tot += len(r["items"])
            ku += sum(1 for x in r["items"]
                      if (x.get("facility_kind") or "") == "特養の空床利用型")
        _KUUSHOU_AVG = (ku / tot * 100) if tot else 0.0
    return _KUUSHOU_AVG


def ward_totals():
    """区ごとの (区名, 区内件数, 掲載件数) を一度だけ読み込む。"""
    global _TOTALS
    if _TOTALS is None:
        _TOTALS = {}
        for f in CACHE.glob("short_*.json"):
            r = json.loads(f.read_text(encoding="utf-8"))
            _TOTALS[f.stem[len("short_"):]] = (
                r["name"], r.get("total") or 0, len(r["items"]))
    return _TOTALS


def neighbours(wid):
    """隣接区の事業所数。ショートステイは区外の事業所も使えるので、
    その区で埋まったときに次にどこを当たるかの材料になる。"""
    t = ward_totals()
    near = [x for x in WARDS[wid]["near"][:5] if x in t]
    rows = "\n".join(
        '        <tr><th><a href="{{ROOT}}short-stay/tokyo/%s/">%s</a></th>'
        '<td class="num">%d</td><td class="num">%d</td></tr>'
        % (x, t[x][0], t[x][1], t[x][2]) for x in near)
    return rows, sum(t[x][1] for x in near), len(near)


def build(wid, site):
    src = CACHE / f"short_{wid}.json"
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
    (kinds, kind_note, kuushou, heisetsu, top_fk, fk,
     dist, orgs, org_note, top_kind, top_n) = stats(items)
    ages, age_note, veteran = age_table(items)
    near_rows, near_total, near_cnt = neighbours(wid)

    scale_note = ("区内の数が多いので、空床利用型を外しても候補が残ります。"
                  if total >= 20 else
                  "数が限られるため、隣接する区の事業所も早めに視野に入れてください。")
    if kuushou:
        kuushou_note = "%sの掲載%d件のうち%d件がこの型です。" % (ward, n, kuushou)
    elif total > n:
        kuushou_note = ("%sの掲載%d件にこの型は含まれていませんが、"
                        "区内%d件の中にはある場合があります。" % (ward, n, total))
    else:
        kuushou_note = ("%s内の%d件にこの型はありませんが、"
                        "区外の事業所に申し込むときはあてはまります。" % (ward, total))

    # 23区平均と比べた空床利用型の割合。その区が平均より当たりにくいかが分かる。
    avg = kuushou_avg()
    mine = kuushou / n * 100
    if kuushou == 0:
        ratio_note = ("%sの掲載分はすべて専用の床を持つ事業所で、23区平均（掲載分の%.0f%%が空床利用型）"
                      "と比べると押さえやすいほうです。" % (ward, avg))
    elif mine >= avg + 5:
        ratio_note = ("空床利用型は掲載分の%.0f%%にあたり、23区平均の%.0f%%より高めです。"
                      "%sでは専用の床を持つ事業所から先に当たってください。"
                      % (mine, avg, ward))
    else:
        ratio_note = ("空床利用型は掲載分の%.0f%%で、23区平均の%.0f%%と同じくらいです。"
                      % (mine, avg))

    top_town = max(bucket_sizes(items).items(), key=lambda x: (x[1], x[0]))
    town_note = ("掲載分がいちばん多いのは%s（%d件）です。"
                 % (top_town[0], top_town[1]))

    from short_tpl import SHORT_STAY
    content = SHORT_STAY % dict(
        senyo=n - kuushou, ratio_note=ratio_note, town_note=town_note,
        ward=ward, id=wid, center=madoguchi, scale_note=scale_note,
        total=total, townc=len(towns), n=n, dist=dist,
        kinds=kinds, kind_note=kind_note, kuushou=kuushou,
        kuushou_note=kuushou_note, heisetsu=heisetsu,
        orgs=orgs, org_note=org_note, ages=ages, age_note=age_note,
        fee_std=fee_rows(UNITS_STD),
        near=near_rows, neart=near_total, nearc=near_cnt,
        unit3=f"{yen1(UNITS_UNIT[3][0]):,}")
    (BASE / "content" / f"short-stay_tokyo_{wid}.html").write_text(
        content, encoding="utf-8")

    y3 = f"{yen1(UNITS_STD[3][0]):,}"
    y5 = f"{yen1(UNITS_STD[5][0]):,}"
    faq = [
        {"q": f"{ward}でショートステイを使うには、まず何をすればいいですか？",
         "a": f"担当のケアマネジャー、いなければ{madoguchi}に相談してください。"
              f"ショートステイもケアプランに位置づける必要があるため、{ward}の事業所に"
              "直接申し込むのではなくそこが入口になります。"
              "要介護認定を受けていない場合は、認定の申請から始まります。"},
        {"q": f"{ward}にショートステイは何件ありますか？",
         "a": f"東京都が公表している指定事業所一覧では、2026年9月1日時点で{ward}内に{total}件の"
              f"短期入所生活介護事業所が指定を受けています。本ページではそのうち{n}件を"
              f"連絡先つきで掲載しています。掲載分のうち{kuushou}件が特養の空床利用型です。"},
        {"q": f"{ward}で予約が取れないときはどうすればいいですか？",
         "a": f"まず空床利用型以外を当たってください。{ward}の掲載{n}件のうち"
              f"{n - kuushou}件は専用の床を持つ事業所です。"
              f"それでも埋まっていれば、日程をずらすか、{ward}に隣接する区の事業所を当たります。"
              f"{ward}でもお盆・年末年始・連休は数か月前から埋まります。"},
        {"q": f"{ward}で自己負担はいくらくらいですか？",
         "a": f"{ward}は介護報酬の地域区分で1級地（1単位＝11.40円）にあたります。"
              f"従来型個室・多床室の併設型なら1割負担で要介護3が1日約{y3}円、"
              f"要介護5が1日約{y5}円が目安です。"
              f"ただし{ward}でもこれとは別に食費と滞在費が全額自己負担で加わるため、"
              "総額はこの倍以上になることがあります。"
              "住民税非課税世帯などは負担限度額認定で上限をつけられます。"},
        {"q": f"{ward}のショートステイは何日まで連続で使えますか？",
         "a": f"{ward}でも全国共通で、連続利用は30日までです。"
              "日数の管理はケアマネジャーがしてくれます。"
              "上限の詳しい決まりはショートステイのしくみのページにまとめています。"},
        {"q": f"認知症があっても{ward}のショートステイを使えますか？",
         "a": f"使えます。{ward}の掲載{n}件のうち{heisetsu}件は特別養護老人ホームなどに"
              "併設されており、認知症の方の受け入れに慣れているところが多くなります。"
              f"ただし環境が変わると混乱が強く出る方もいるため、{ward}でもまず1泊2日から"
              "試してください。夜間の見守り体制は事業所ごとに違います。"},
    ]

    near = WARDS[wid]["near"][:6]
    nearby = "\n      ".join(
        '<a href="{{ROOT}}short-stay/tokyo/%s/">%s</a>' % (x, ward_name(x))
        for x in near)
    related = "\n      ".join([
        '<a href="{{ROOT}}day-service/tokyo/%s/">%sのデイサービス<small>日中の預け先</small></a>' % (wid, ward),
        '<a href="{{ROOT}}houmon-kaigo/tokyo/%s/">%sの訪問介護<small>身体介護・生活援助</small></a>' % (wid, ward),
        '<a href="{{ROOT}}houmon-kango/tokyo/%s/">%sの訪問看護<small>医療ケアが必要な方へ</small></a>' % (wid, ward),
        '<a href="{{ROOT}}fukushi-yogu/tokyo/%s/">%sの福祉用具レンタル<small>介護ベッド・車いす</small></a>' % (wid, ward),
        '<a href="{{ROOT}}takuhai-bento/tokyo/%s/">%sの宅配弁当<small>高齢者向け配食サービス</small></a>' % (wid, ward),
        '<a href="{{ROOT}}mimamori/tokyo/%s/">%sの見守りサービス<small>ひとり暮らしの安否確認</small></a>' % (wid, ward),
    ])
    sidebar = (
        '<div class="side cta-side">\n'
        '        <h4>まず1泊2日から</h4>\n'
        '        <p>連続利用の上限や緊急時の預け先は、ハブにまとめています。</p>\n'
        '        <a class="btn" href="{{ROOT}}short-stay/">ショートステイのしくみを見る</a>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>このページの要点</h4>\n'
        '        <ul>\n'
        f'          <li>{ward}内の短期入所生活介護は{total}件（都指定）</li>\n'
        f'          <li>掲載{n}件のうち空床利用型が{kuushou}件</li>\n'
        f'          <li>併設型・要介護3で1日約{y3}円（1割）</li>\n'
        '          <li>食費・滞在費は全額自己負担</li>\n'
        f'          <li>入口はケアマネか{madoguchi}</li>\n'
        '        </ul>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>関連ガイド</h4>\n'
        '        <ul>\n'
        '          <li><a href="{{ROOT}}guide/youkaigo-nintei/">要介護認定の申請方法</a></li>\n'
        '          <li><a href="{{ROOT}}guide/soudan-madoguchi/">相談窓口の探し方</a></li>\n'
        '          <li><a href="{{ROOT}}short-stay/">ショートステイのしくみ</a></li>\n'
        '          <li><a href="{{ROOT}}day-service/">デイサービス</a></li>\n'
        '        </ul>\n'
        '      </div>')

    d = {
        "slug": f"short-stay_tokyo_{wid}",
        "category": {"id": "short-stay", "name": "ショートステイ",
                     "path": "/short-stay/"},
        "area": {"pref_id": "tokyo", "pref_name": "東京都",
                 "city_id": wid, "city_name": ward},
        "seo": {
            "title": f"{ward}のショートステイ{n}事業所｜予約と費用【2026年9月更新】",
            "description": f"東京都{ward}の短期入所生活介護（ショートステイ）事業所{n}件を連絡先つきで掲載。"
                           f"区内{total}件のうち特養の空床利用型がどれかを含め、"
                           "予約の取りやすさ・1級地での自己負担・食費と滞在費の見方をまとめました。",
            "canonical": f"https://kaigonotonari.com/short-stay/tokyo/{wid}/",
            "og_title": f"{ward}のショートステイ一覧｜予約が取れる事業所の見分け方",
            "og_description": f"{ward}の短期入所生活介護{n}件を掲載。空床利用型かどうかで予約の取りやすさが"
                              "変わります。費用は食費・滞在費まで含めて解説します。",
            "og_image": "https://kaigonotonari.com/assets/ogp-short-stay.jpg",
        },
        "h1": f"{ward}のショートステイ一覧｜予約が取れる事業所の見分け方",
        "published": TODAY, "modified": TODAY,
        "count_label": f"掲載：{n}事業所",
        "lead": f"東京都{ward}で短期入所生活介護（ショートステイ）を探している方へ。"
                f"東京都の指定を受けた{total}件から{n}件を連絡先つきで掲載し、"
                f"そのうち特養の空床を使う<strong>空床利用型が{kuushou}件</strong>あることまで示しました。"
                f"ショートステイでいちばん多い壁は<strong>予約が取れないこと</strong>です。"
                "同じ区の事業所でも、専用の床を持つところと特養の空きベッドを使うところでは、"
                "押さえやすさがまったく違います。",
        "listing_note": f"{ward}内の短期入所生活介護事業所から{n}件を掲載しています"
                        "（東京都公表・2026年9月1日時点）。"
                        f"区内には{total}件が指定を受けており、"
                        + ("事業所番号の順に等間隔で抽出したため、開設の古い事業所と新しい事業所が"
                           "混ざっています。" if total > n else "そのすべてを掲載しています。")
                        + "「特養の空床利用」「単独型」などの表示は東京都の一覧の事業所種別名です。"
                        + "空き状況は日々変わるため、この一覧では扱っていません。"
                        + "掲載順は事業所の優劣を示すものではありません。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "近隣エリアのショートステイ", "nearby": nearby,
        "sources": [
            rec.get("source", "東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0）"),
            "厚生労働省「指定居宅サービス介護給付費単位数等」短期入所生活介護費"
            "（令和6年度改定後・令和8年6月改定を経て有効）／介護報酬の地域区分（1級地・1単位11.40円）",
            f"{ward}「{madoguchi}一覧」",
            f"日本郵便 郵便番号データにもとづく{ward}の町域一覧",
        ],
        "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">事業所一覧</a>\n  <a class="m2" href="#s4">自己負担の目安</a>',
        "hero_image": "assets/ogp-short-stay.jpg",
        "towns": {"pref": "tokyo", "city": wid},
    }
    (BASE / "data" / f"short-stay_tokyo_{wid}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    site.setdefault("towns", {}).setdefault("tokyo", {})[wid] = towns
    ids = [c["id"] for c in site["cities"]["tokyo"]]
    if wid not in ids:
        site["cities"]["tokyo"].append({"id": wid, "name": ward, "status": "live"})
    print(f"  {ward}: {n}事業所 / 区内{total}件 / 空床利用{kuushou}件 / "
          f"title {len(d['seo']['title'])}字")
    return True


def build_pref_partial():
    """東京都ページ（/short-stay/tokyo/）の本文。

    区ごとに「区内の件数」と「うち空床利用型」を並べる。空床利用型の比率は
    区によって差があり、その区で予約がどれくらい取りにくいかの目安になる。
    """
    rows = []
    for f in sorted(CACHE.glob("short_*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        wid = f.stem[len("short_"):]
        its = to_items(rec, rec["towns"])
        n = len(its)
        if n < MIN_ITEMS:
            continue
        ku = sum(1 for it in its if it["_fkind"] == "特養の空床利用型")
        tan = sum(1 for it in its if it["_fkind"] == "単独型")
        rows.append((rec["total"] or n, rec["name"], wid, n, ku, tan))
    if not rows:
        return
    rows.sort(reverse=True)
    body = "\n".join(
        '        <tr><th><a href="{{ROOT}}short-stay/tokyo/%s/">%s</a></th>'
        '<td class="num">%d</td><td class="num">%d</td><td class="num">%d</td>'
        '<td class="num">%d</td></tr>' % (wid, name, total, n, ku, tan)
        for total, name, wid, n, ku, tan in rows)
    most, least = rows[0], rows[-1]
    total_all = sum(r[0] for r in rows)
    ku_all = sum(r[4] for r in rows)
    html = f"""
  <h2 id="kazu">東京23区のショートステイ事業所数と、空床利用型の数</h2>
  <p>掲載している{len(rows)}区だけで、区内の短期入所生活介護は合わせて{total_all}件あります。ただし<strong>区によって数が大きく違います</strong>。最も多い{most[1]}が{most[0]}件、最も少ない{least[1]}が{least[0]}件で、{most[0] / max(least[0], 1):.1f}倍の開きがあります。</p>
  <p>ショートステイで見るべきはそれだけではありません。<strong>特養の空床利用型は、本体の特別養護老人ホームが満床だとその分使えません。</strong>本サイト掲載分{sum(r[3] for r in rows)}件のうち{ku_all}件がこの型です。お住まいの区で空床利用型の割合が高ければ、最初から隣接区も視野に入れたほうが早く決まります。</p>
  <div class="tw">
  <table>
    <thead><tr><th style="width:26%">区</th><th>区内の事業所</th><th>本サイト掲載</th><th>うち空床利用型</th><th>うち単独型</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
  </div>
  <p class="tiny">区内の事業所数は東京都が公表している指定事業所一覧の実数（2026年9月1日時点）。空床利用型と単独型の件数は、本サイト掲載分についての集計です。事業所の型は東京都の一覧の「事業所種別名」をそのまま使っています。空き状況は日々変わるため、この表では扱っていません。</p>

  <h2 id="tsukaikata">この表の使い方</h2>
  <ul class="check">
    <li><b>まず自分の区の行を見る</b>事業所が多い区なら、空床利用型を外しても候補が残ります。少ない区なら、最初から隣接区も当たってください。ショートステイは区外の事業所も使えます。</li>
    <li><b>空床利用型の列は、予約の取りにくさの目安</b>この型は特養の入所者用ベッドの空きを使うため、直前の予約が読めません。定期的に預けたいなら、専用の床を持つ事業所を先に当たります。</li>
    <li><b>単独型の列は、費用がわずかに上がる目安</b>単独型は併設型より基本報酬が高く設定されています。要介護3なら1日あたり{UNITS_STD[3][1] - UNITS_STD[3][0]}単位、1割負担で約{yen1(UNITS_STD[3][1]) - yen1(UNITS_STD[3][0])}円の差です。決め手にはなりませんが、長期で使うなら効いてきます。</li>
  </ul>
"""
    (BASE / "content" / "pref_short-stay_tokyo.html").write_text(html, encoding="utf-8")
    print(f"  東京都ページ本文: {len(rows)}区の表を書き出しました。")


if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(
        p.stem[len("short_"):] for p in CACHE.glob("short_*.json"))
    sp = BASE / "data" / "site.json"
    site = json.loads(sp.read_text(encoding="utf-8"))
    ok = sum(1 for t in targets if build(t, site))
    sp.write_text(json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8")
    build_pref_partial()
    print(f"\n{ok} ページ分のデータを書き出しました。")
