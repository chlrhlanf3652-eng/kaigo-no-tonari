#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""東京23区の介護事業所の運営法人・指定年の比較ページ（/tokyo/unei-hojin/）の本文とCSVを作る。

元データは opendata/kaigonotonari-tokyo23-kaigo.csv（東京都福祉局の指定事業所一覧＋厚労省オープンデータ）。
集計だけを行い、評価（良い・悪い）は書かない。法人名は全角半角の違いをNFKCでそろえて数える。
出力: content/page_tokyo_unei-hojin.html, opendata/tokyo23-kaigo-hojin.csv
"""
import collections
import csv
import pathlib
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS

BASE = pathlib.Path(__file__).resolve().parent.parent
SRC = BASE / "opendata" / "kaigonotonari-tokyo23-kaigo.csv"
NAME2ID = {v["name"]: k for k, v in WARDS.items()}
SVC = [("訪問介護", "訪問介護"), ("訪問看護", "訪問看護"), ("通所介護", "デイサービス"),
       ("短期入所生活介護", "ショートステイ"), ("福祉用具", "福祉用具")]
KINDS = ["営利法人", "社会福祉法人", "医療法人", "NPO法人", "その他"]
NEW_FROM, NEW_TO = "2025-09-02", "2026-09-01"   # 都の一覧の基準日（2026-09-01）から1年
OLD_BEFORE = "2016-09-02"                       # 基準日時点で指定から10年以上


def kind(s):
    if s == "営利法人":
        return "営利法人"
    if s.startswith("社会福祉法人"):
        return "社会福祉法人"
    if s == "医療法人":
        return "医療法人"
    if "NPO" in s:
        return "NPO法人"
    return "その他"


def svc(s):
    return "福祉用具" if "福祉用具" in s else s


def pct(a, b):
    return f"{a / b * 100:.0f}%" if b else "—"


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
    for r in rows:
        r["k"] = kind(r["法人種別"])
        r["s"] = svc(r["サービス種類"])
        r["h"] = unicodedata.normalize("NFKC", r["法人名"]).replace("　", " ").strip()
        r["d"] = r["指定年月日"]
    N = len(rows)

    # 1. サービス × 法人の種類
    by_s = collections.defaultdict(collections.Counter)
    for r in rows:
        by_s[r["s"]][r["k"]] += 1
    t1 = []
    for s, label in SVC:
        c = by_s[s]; n = sum(c.values())
        t1.append(f'      <tr><th class="nw">{label}</th><td class="num">{n:,}</td>'
                  + "".join(f'<td class="num">{pct(c[k], n)}</td>' for k in KINDS) + "</tr>\n")
    call = collections.Counter(r["k"] for r in rows)
    t1.append(f'      <tr><th class="nw">5サービス合計</th><td class="num">{N:,}</td>'
              + "".join(f'<td class="num">{pct(call[k], N)}</td>' for k in KINDS) + "</tr>\n")

    # 2. 事業所数の多い法人
    hc = collections.Counter(r["h"] for r in rows)
    top = hc.most_common(15)
    hs = collections.defaultdict(collections.Counter)
    hw = collections.defaultdict(set)
    for r in rows:
        hs[r["h"]][r["s"]] += 1
        hw[r["h"]].add(r["市区町村名"])
    t2 = []
    for i, (h, n) in enumerate(top, 1):
        mix = "・".join(f'{lab}{hs[h][s]}' for s, lab in SVC if hs[h][s])
        t2.append(f'      <tr><td class="num">{i}</td><th>{h}</th><td class="num">{n}</td>'
                  f'<td class="num">{len(hw[h])}</td><td class="tiny">{mix}</td></tr>\n')
    top10 = {h for h, _ in hc.most_common(10)}
    top10n = sum(hc[h] for h in top10)
    n_hojin = len(hc)

    # 3. 区ごと
    by_w = collections.defaultdict(list)
    for r in rows:
        by_w[r["市区町村名"]].append(r)
    wrow, csvrows = [], []
    for wid, w in WARDS.items():
        L = by_w.get(w["name"], [])
        if not L:
            continue
        n = len(L); kc = collections.Counter(r["k"] for r in L)
        t10 = sum(1 for r in L if r["h"] in top10)
        new = sum(1 for r in L if NEW_FROM <= r["d"] <= NEW_TO)
        old = sum(1 for r in L if r["d"] and r["d"] < OLD_BEFORE)
        nh = len({r["h"] for r in L})
        wrow.append(f'      <tr><th class="nw"><a href="{{{{ROOT}}}}tokyo/{wid}/">{w["name"]}</a></th>'
                    f'<td class="num">{n}</td><td class="num">{nh}</td><td class="num">{pct(kc["営利法人"], n)}</td>'
                    f'<td class="num">{pct(kc["社会福祉法人"], n)}</td><td class="num">{pct(kc["医療法人"], n)}</td>'
                    f'<td class="num">{pct(t10, n)}</td><td class="num">{new}</td><td class="num">{pct(old, n)}</td></tr>\n')
        csvrows.append([w["name"], n, nh, kc["営利法人"], kc["社会福祉法人"], kc["医療法人"], kc["NPO法人"], kc["その他"],
                        t10, new, old])

    # 4. 指定年の分布
    bands = [("〜2005年", "0000", "2006"), ("2006〜2015年", "2006", "2016"),
             ("2016〜2020年", "2016", "2021"), ("2021年〜", "2021", "9999")]
    t4 = []
    for s, label in SVC:
        L = [r for r in rows if r["s"] == s and r["d"]]
        t4.append(f'      <tr><th class="nw">{label}</th>'
                  + "".join(f'<td class="num">{pct(sum(1 for r in L if a <= r["d"][:4] < b), len(L))}</td>' for _, a, b in bands)
                  + "</tr>\n")

    new_all = sum(1 for r in rows if NEW_FROM <= r["d"] <= NEW_TO)
    new_by = collections.Counter(r["s"] for r in rows if NEW_FROM <= r["d"] <= NEW_TO)
    kaigo = by_s["訪問介護"]; kaigo_n = sum(kaigo.values())
    short = by_s["短期入所生活介護"]; short_n = sum(short.values())
    kango = by_s["訪問看護"]; kango_n = sum(kango.values())
    tokuyo = sum(1 for r in rows if r["s"] == "短期入所生活介護" and r["事業所種別"].startswith("特養の"))
    lead_w = max(csvrows, key=lambda x: x[3] / x[1])
    low_w = min(csvrows, key=lambda x: x[3] / x[1])

    pts = [
        f'<li><b>営利法人（株式会社など）が{pct(call["営利法人"], N)}</b>23区の5サービス{N:,}事業所のうち{call["営利法人"]:,}件。'
        f'訪問介護では{pct(kaigo["営利法人"], kaigo_n)}、訪問看護では{pct(kango["営利法人"], kango_n)}です。</li>',
        f'<li><b>ショートステイは社会福祉法人が中心</b>短期入所生活介護{short_n}件のうち社会福祉法人が{pct(short["社会福祉法人"], short_n)}。'
        f'事業所の{tokuyo}件（{pct(tokuyo, short_n)}）が特別養護老人ホームの併設型・空床利用型です。</li>',
        f'<li><b>運営しているのは{n_hojin:,}法人</b>事業所数の多い上位10法人で{top10n:,}件（全体の{pct(top10n, N)}）。'
        f'最も多いのは{top[0][0]}の{top[0][1]}件です。</li>',
        f'<li><b>直近1年で新しく指定されたのは{new_all}件</b>（{NEW_FROM[:4]}年9月〜{NEW_TO[:4]}年9月）。'
        f'訪問看護{new_by["訪問看護"]}件、訪問介護{new_by["訪問介護"]}件など（<a href="{{{{ROOT}}}}tokyo/houmon-kango-zouka/">訪問看護の指定年</a>）。</li>',
        f'<li><b>営利法人の割合は区で差がある</b>最も高いのは{lead_w[0]}（{pct(lead_w[3], lead_w[1])}）、'
        f'最も低いのは{low_w[0]}（{pct(low_w[3], low_w[1])}）です。</li>',
    ]

    def table(head, rows_, cap, sortable=True):
        return ('  <div class="tw">\n  <table' + (' class="sortable"' if sortable else "") + '>\n'
                f'    <caption class="tiny" style="text-align:left;padding-bottom:6px">{cap}</caption>\n'
                '    <thead><tr>' + "".join(('<th class="nw">' if i == 0 else '<th>') + h + '</th>' for i, h in enumerate(head))
                + '</tr></thead>\n    <tbody>\n' + "".join(rows_) + '    </tbody>\n  </table>\n  </div>\n')

    html = f"""<p class="upd">更新日：2026-11-10（東京都の指定事業所一覧 2026年9月1日時点）</p>
  <p>東京23区の介護サービス事業所{N:,}件（訪問介護・訪問看護・デイサービス・ショートステイ・福祉用具）を、<strong>運営している法人の種類</strong>と<strong>指定を受けた年</strong>で集計しました。株式会社が多いのか、社会福祉法人が多いのか、大手の事業所がどれくらいを占めるのかが、区ごとに分かります。数字は事業所の良し悪しを示すものではありません。</p>
  <h2 id="point">要点</h2>
  <ul class="check">
    {"".join(pts)}
  </ul>
  <h2 id="kind">サービス別：運営法人の種類</h2>
{table(["サービス", "事業所数"] + KINDS, t1, "割合は各サービスの事業所数に対するもの", sortable=False)}
  <p class="tiny">「その他」は社団・財団、生協、地方公共団体などです。社会福祉法人は社会福祉協議会以外の法人です（23区のこの5サービスに社会福祉協議会の事業所はありません）。</p>
  <h2 id="top">23区で事業所数の多い法人</h2>
  <p>同じ法人が複数の区・複数のサービスで事業所を開いている場合は、すべて合計しています。法人名は東京都の公表にもとづき、全角・半角の表記だけそろえています。</p>
{table(["順位", "法人名", "事業所数", "展開している区", "内訳"], t2, "上位15法人（5サービス合計）", sortable=False)}
  <h2 id="ward">区ごとの比較</h2>
  <p>表の見出しを押すと並べ替えられます。「上位10法人」は上の表の1〜10位の法人が運営する事業所の割合です。</p>
{table(["区", "事業所数", "法人数", "営利法人", "社会福祉法人", "医療法人", "上位10法人", "直近1年の新規指定", "指定から10年以上"], wrow, "5サービス合計。新規指定は2025年9月2日〜2026年9月1日、10年以上は2016年9月1日以前の指定")}
  <h2 id="year">指定を受けた年の分布</h2>
  <p>事業所が介護保険の指定を受けた年です。開設年の目安になりますが、運営法人が変わった事業所は新しい年になっていることがあります。</p>
{table(["サービス"] + [b[0] for b in bands], t4, "各サービスの事業所数に対する割合", sortable=False)}
  <h2 id="dl">データのダウンロード</h2>
  <p>区ごとの集計はCSVで自由に使えます（<a href="https://creativecommons.org/licenses/by/4.0/deed.ja" rel="noopener">CC BY 4.0</a>。出典「かいごのとなり（東京都・厚生労働省の公表データをもとに作成）」の表記をお願いします）。</p>
  <div class="lg"><a href="{{{{ROOT}}}}opendata/tokyo23-kaigo-hojin.csv" download>運営法人の区別集計（CSV）<small>23行・法人の種類と指定年</small></a><a href="{{{{ROOT}}}}tokyo/hikaku/">東京23区の介護サービス比較<small>高齢者1万人あたりの事業所数</small></a><a href="{{{{ROOT}}}}opendata/">事業所データ（CSV）<small>事業所1件ずつの一覧</small></a></div>
  <div class="src"><strong>参考・出典</strong><ul>
    <li>東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0／2026年9月1日時点／法人名・法人種別・指定年月日）</li>
    <li>集計：かいごのとなり（法人名は全角・半角の違いをそろえて数えています）</li>
  </ul></div>
  <script src="{{{{ROOT}}}}assets/sort.js" defer></script>
"""
    (BASE / "content" / "page_tokyo_unei-hojin.html").write_text(html, encoding="utf-8")
    with open(BASE / "opendata" / "tokyo23-kaigo-hojin.csv", "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["区", "事業所数", "法人数", "営利法人", "社会福祉法人", "医療法人", "NPO法人", "その他",
                     "上位10法人の事業所", "直近1年の新規指定", "指定から10年以上"])
        wr.writerows(csvrows)
    print(f"unei: {N:,}件 / {n_hojin:,}法人 / 新規{new_all} / 上位10 {top10n}")
    for p in pts:
        print(" ", p.replace("<li>", "").replace("</li>", "").replace("<b>", "【").replace("</b>", "】"))


if __name__ == "__main__":
    main()
