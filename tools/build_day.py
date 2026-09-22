#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""東京都オープンデータのキャッシュから、デイサービスの市区町村ページを組み立てる。

  tools/cache/day_<区>.json  →  data/day-service_tokyo_<区>.json
                                content/day-service_tokyo_<区>.html

法人の種別は CSV の「法人種別名」をそのまま使う（事業所名から推測しない）。
開設からの年数は「指定年月日」から出す。訪問介護・訪問看護のページと軸を
変えるための集計で、この2つは CSV にしかない情報。

使い方:
  python3 tools/build_day.py             # キャッシュにある区すべて
  python3 tools/build_day.py chiyoda     # 指定した区だけ
"""
import datetime
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS

BASE = pathlib.Path(__file__).parent.parent
CACHE = pathlib.Path(__file__).parent / "cache"
TODAY = "2026-09-22"
MIN_ITEMS = 3

# CSV の「法人種別名」に対応する傾向の説明
# 東京都の CSV が使っている「法人種別名」の表記に合わせている
ORG_DESC = {
    "営利法人": "株式会社・有限会社など。住宅街の中の小規模な事業所が多い",
    "社会福祉法人（社協以外）": "特別養護老人ホームなどに併設されていることが多く、設備が整っている",
    "社会福祉協議会": "地域の社会福祉協議会が運営。公的性格が強い",
    "医療法人": "病院・診療所が母体。健康面の変化に気づいてもらいやすい",
    "社団・財団": "公益性の高い運営。地域の事情に通じているところが多い",
    "非営利法人（NPO）": "地域に密着した小規模な運営が中心",
    "生協": "生活協同組合。組合員向けの活動と一体で運営されている",
    "農協": "農業協同組合による運営",
    "地方公共団体（市町村）": "自治体が直接または委託して運営",
    "その他法人": "上記にあてはまらない法人格",
    "その他": "上記にあてはまらない法人格",
}

# 指定年月日をまとめる区切り（新しい順に判定する）
AGE_BUCKETS = [
    (3, "直近3年以内", "設備が新しく、空きがあることが多い"),
    (10, "3〜10年", "運営が固まってきた時期。空き状況は事業所ごとに差が大きい"),
    (20, "10〜20年", "利用者が定着している。空きは出にくい"),
    (999, "20年以上", "制度の初期から続いている。地域での評判を聞きやすい"),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ward_name(wid):
    return WARDS[wid]["name"] if wid in WARDS else wid


def years_since(ymd: str):
    """指定年月日（2001-01-01 形式）から経過年数を返す。読めなければ None。"""
    try:
        d = datetime.date.fromisoformat(ymd[:10])
    except Exception:
        return None
    ref = datetime.date.fromisoformat(TODAY)
    return (ref - d).days / 365.25


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
        d = r.get("designated") or ""
        it["_designated"] = d
        y = years_since(d)
        it["_years"] = y
        tags = []
        if town:
            tags.append(town + "エリア")
        if y is not None and y >= 20:
            tags.append("20年以上")
        elif y is not None and y < 3:
            tags.append("開設3年以内")
        tags.append("デイサービス")
        it["_tags"] = tags
        out.append(it)
    return out


def build(wid, site):
    src = CACHE / f"day_{wid}.json"
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

    # 法人の種別（CSV の値をそのまま集計）
    kinds = {}
    for it in items:
        kinds[it["_kind"]] = kinds.get(it["_kind"], 0) + 1
    kind_rows = sorted(kinds.items(), key=lambda x: (-x[1], x[0]))
    orgs = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (esc(k), v, ORG_DESC.get(k, "")) for k, v in kind_rows)
    top_kind, top_n = kind_rows[0]
    org_note = ("掲載%d件のうち%sが%d件と最も多くなっています。"
                % (n, top_kind, top_n))

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
        oldest = max(yrs)
        veteran = sum(1 for y in yrs if y >= 20)
        age_note = ("掲載%d件のうち、指定から20年以上たっている事業所は%d件、"
                    "最も古い事業所は約%d年前の指定です。"
                    % (n, veteran, int(oldest)))
    else:
        age_note = "指定年月日が読み取れる事業所がありませんでした。"

    scale_note = ("区内の数が多いぶん、送迎範囲と規模で絞れます。" if total >= 60
                  else "数が限られるため、送迎範囲に入るかどうかを先に確認してください。")

    from day_tpl import DAY_SERVICE
    content = DAY_SERVICE % dict(
        ward=ward, id=wid, center=madoguchi, scale_note=scale_note,
        total=total, townc=len(towns), n=n, dist=dist,
        orgs=orgs, org_note=org_note, ages=ages_rows, age_note=age_note)
    (BASE / "content" / f"day-service_tokyo_{wid}.html").write_text(content, encoding="utf-8")

    nonstop_note = ""
    faq = [
        {"q": f"{ward}でデイサービスを使うには、まず何をすればいいですか？",
         "a": f"担当のケアマネジャー、いなければ{madoguchi}に相談してください。"
              f"デイサービスはケアプランに位置づける必要があるため、{ward}の事業所に直接申し込むのではなく"
              "そこが入口になります。要介護認定を受けていない場合は、認定の申請から始まります。"},
        {"q": f"{ward}にデイサービスは何件ありますか？",
         "a": f"東京都が公表している指定事業所一覧では、2026年9月1日時点で{ward}内に{total}件の"
              f"通所介護事業所が指定を受けています。本ページではそのうち{n}件を連絡先つきで掲載しています。"
              "なお定員18人以下の地域密着型通所介護は区が指定するため、この件数には含まれていません。"},
        {"q": f"{ward}の掲載事業所は、どこを見て絞り込めばいいですか？",
         "a": f"まず送迎範囲に自宅が入るかで絞り、次に入浴設備（個浴か機械浴か）で絞るのが順番です。"
              f"{ward}の掲載{n}件では{top_kind}が{top_n}件と最も多く、"
              f"指定から20年以上の事業所も{sum(1 for y in yrs if y >= 20) if yrs else 0}件あります。"
              "長く続いているところは空きが出にくい一方、新しいところは空きがあります。"},
        {"q": f"{ward}で自己負担はいくらくらいですか？",
         "a": f"{ward}は介護報酬の地域区分で1級地（1単位＝11.40円）にあたるため、"
              "通常規模型・7時間以上8時間未満なら1割負担で要介護1が約750円、要介護3が約1,026円、"
              "要介護5が約1,309円が目安です。"
              f"ただし{ward}でもこれに昼食代などの保険外費用が加わるため、"
              "事業所から1か月の総額の目安を出してもらってください。"},
        {"q": f"本人が{ward}のデイサービスに行きたがりません。",
         "a": f"まず体験利用を試してください。{ward}内には{total}件あり、"
              f"掲載{n}件を見ても{top_kind}が{top_n}件と偏りがあるように、規模も雰囲気も事業所ごとに違います。"
              f"合わない理由別の対処（個浴のある事業所、小規模な事業所など）は"
              "デイサービスのしくみのページにまとめました。"
              f"{ward}でも週1回から始めて、慣れてから増やすのが定石です。"},
        {"q": f"{ward}の事業所は、途中で変更できますか？",
         "a": f"変更できます。ケアマネジャーに相談すればケアプランを見直したうえで"
              f"{ward}内の別の事業所に切り替えられます。"
              f"{ward}は区内{total}件と候補があるので、合わずに変える方は珍しくありません。"},
    ]

    near = WARDS[wid]["near"][:6]
    nearby = "\n      ".join('<a href="{{ROOT}}day-service/tokyo/%s/">%s</a>' % (x, ward_name(x))
                             for x in near)
    related = "\n      ".join([
        '<a href="{{ROOT}}houmon-kaigo/tokyo/%s/">%sの訪問介護<small>身体介護・生活援助</small></a>' % (wid, ward),
        '<a href="{{ROOT}}houmon-kango/tokyo/%s/">%sの訪問看護<small>医療ケアが必要な方へ</small></a>' % (wid, ward),
        '<a href="{{ROOT}}short-stay/tokyo/%s/">%sのショートステイ<small>短期入所</small></a>' % (wid, ward),
        '<a href="{{ROOT}}fukushi-yogu/tokyo/%s/">%sの福祉用具レンタル<small>介護ベッド・車いす</small></a>' % (wid, ward),
        '<a href="{{ROOT}}takuhai-bento/tokyo/%s/">%sの宅配弁当<small>高齢者向け配食サービス</small></a>' % (wid, ward),
        '<a href="{{ROOT}}mimamori/tokyo/%s/">%sの見守りサービス<small>ひとり暮らしの安否確認</small></a>' % (wid, ward),
    ])
    sidebar = (
        '<div class="side cta-side">\n'
        '        <h4>まず体験利用を</h4>\n'
        '        <p>合うかどうかは見学だけでは分かりません。制度と費用はハブにまとめています。</p>\n'
        '        <a class="btn" href="{{ROOT}}day-service/">デイサービスのしくみを見る</a>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>このページの要点</h4>\n'
        '        <ul>\n'
        f'          <li>{ward}内の通所介護は{total}件（都指定）</li>\n'
        '          <li>7〜8時間・要介護1で約750円（1割）</li>\n'
        '          <li>食費などは全額自己負担</li>\n'
        f'          <li>入口はケアマネか{madoguchi}</li>\n'
        '        </ul>\n'
        '      </div>\n'
        '      <div class="side">\n'
        '        <h4>関連ガイド</h4>\n'
        '        <ul>\n'
        '          <li><a href="{{ROOT}}guide/youkaigo-nintei/">要介護認定の申請方法</a></li>\n'
        '          <li><a href="{{ROOT}}guide/soudan-madoguchi/">相談窓口の探し方</a></li>\n'
        '          <li><a href="{{ROOT}}day-service/">デイサービスのしくみ</a></li>\n'
        '          <li><a href="{{ROOT}}short-stay/">ショートステイ</a></li>\n'
        '        </ul>\n'
        '      </div>')

    d = {
        "slug": f"day-service_tokyo_{wid}",
        "category": {"id": "day-service", "name": "デイサービス", "path": "/day-service/"},
        "area": {"pref_id": "tokyo", "pref_name": "東京都", "city_id": wid, "city_name": ward},
        "seo": {
            "title": f"{ward}のデイサービス{n}事業所｜送迎と費用の見方【2026年9月更新】",
            "description": f"東京都{ward}の通所介護（デイサービス）事業所{n}件を連絡先つきで掲載。"
                           f"区内{total}件の中から選ぶための所在町域・運営法人・開設年数の内訳と、"
                           "1級地での自己負担、見学で聞くことをまとめました。",
            "canonical": f"https://kaigonotonari.com/day-service/tokyo/{wid}/",
            "og_title": f"{ward}のデイサービス一覧｜送迎範囲と費用の見方",
            "og_description": f"{ward}の通所介護事業所{n}件を掲載。送迎範囲・入浴設備・開設年数から選ぶ順番と、"
                              "保険外費用を含めた費用の見方を解説します。",
            "og_image": "https://kaigonotonari.com/assets/ogp-day-service.jpg",
        },
        "h1": f"{ward}のデイサービス一覧｜送迎範囲と費用の見方",
        "published": TODAY, "modified": TODAY,
        "count_label": f"掲載：{n}事業所",
        "lead": f"東京都{ward}で通所介護（デイサービス）を探している方へ。"
                f"東京都の指定を受けた{total}件から{n}件を連絡先つきで掲載し、"
                f"所在町域・運営法人・開設からの年数の内訳と、1級地での自己負担をまとめました。"
                f"デイサービスでいちばん多い壁は<strong>本人が行きたがらないこと</strong>です。"
                "選ぶ順番は近い順ではなく、通い続けられる条件の順になります。",
        "listing_note": f"{ward}内の通所介護事業所から{n}件を掲載しています（東京都公表・2026年9月1日時点）。"
                        f"区内には{total}件が指定を受けており、"
                        + ("事業所番号の順に等間隔で抽出したため、開設の古い事業所と新しい事業所が混ざっています。"
                           if total > n else "そのすべてを掲載しています。")
                        + "定員18人以下の地域密着型通所介護は区が指定するため、この一覧には含まれていません。"
                        + "掲載順は事業所の優劣を示すものではありません。",
        "items": items, "faq": faq, "related": related,
        "nearby_heading": "近隣エリアのデイサービス", "nearby": nearby,
        "sources": [
            rec.get("source", "東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0）"),
            "厚生労働省「指定居宅サービス介護給付費単位数の算定構造」通所介護費（令和6年度改定）／"
            "介護報酬の地域区分（1級地・1単位11.40円）",
            f"{ward}「{madoguchi}一覧」",
            f"日本郵便 郵便番号データにもとづく{ward}の町域一覧",
        ],
        "sidebar": sidebar,
        "mcta": '<a class="m1" href="#s2">事業所一覧</a>\n  <a class="m2" href="#s4">自己負担の目安</a>',
        "hero_image": "assets/ogp-day-service.jpg",
        "towns": {"pref": "tokyo", "city": wid},
    }
    (BASE / "data" / f"day-service_tokyo_{wid}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    site.setdefault("towns", {}).setdefault("tokyo", {})[wid] = towns
    ids = [c["id"] for c in site["cities"]["tokyo"]]
    if wid not in ids:
        site["cities"]["tokyo"].append({"id": wid, "name": ward, "status": "live"})
    print(f"  {ward}: {n}事業所 / 区内{total}件 / {top_kind}{top_n}件 / title {len(d['seo']['title'])}字")
    return True


if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(
        p.stem[len("day_"):] for p in CACHE.glob("day_*.json"))
    sp = BASE / "data" / "site.json"
    site = json.loads(sp.read_text(encoding="utf-8"))
    ok = sum(1 for t in targets if build(t, site))
    sp.write_text(json.dumps(site, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{ok} ページ分のデータを書き出しました。")
