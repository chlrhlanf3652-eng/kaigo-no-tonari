#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""東京23区の訪問看護ステーションの指定年を集計するページ（/tokyo/houmon-kango-zouka/）。

元データは opendata/kaigonotonari-tokyo23-kaigo.csv。2026年9月1日時点で指定を受けている事業所だけが
入っているため、廃止・休止した事業所は数えられない。本文でもそう書き、増えた理由は推測で書かない。
出力: content/page_tokyo_houmon-kango-zouka.html, opendata/tokyo23-houmon-kango-shitei.csv
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
NEW_FROM, NEW_TO = "2025-09-02", "2026-09-01"


def pct(a, b):
    return f"{a / b * 100:.0f}%" if b else "—"


def main():
    rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8-sig")) if r["サービス種類"] == "訪問看護"]
    N = len(rows)
    new = [r for r in rows if r["指定年月日"] >= "2021"]
    old = [r for r in rows if r["指定年月日"] < "2021"]
    nn, no = len(new), len(old)
    yc = collections.Counter(r["指定年月日"][:4] for r in rows)
    peak = max((y for y in yc if y != "2026"), key=lambda y: yc[y])

    def eiri(L):
        return sum(1 for r in L if r["法人種別"] == "営利法人")

    def iryo(L):
        return sum(1 for r in L if r["法人種別"] == "医療法人")

    def sun(L):
        d = [r for r in L if r["利用可能曜日"]]
        return sum(1 for r in d if "日曜日" in r["利用可能曜日"]), len(d)

    sn, sd = sun(new); so, sod = sun(old)
    last = sum(1 for r in rows if NEW_FROM <= r["指定年月日"] <= NEW_TO)

    # 年ごとの棒（2000年は制度開始時にまとめて指定された分なので、そのまま示して注記）
    mx = max(yc.values())
    bars = []
    for y in sorted(yc):
        n = yc[y]
        lab = y + ("年（9月1日まで）" if y == "2026" else "年")
        bars.append(f'      <tr><th class="nw">{lab}</th><td class="num">{n}</td>'
                    f'<td style="width:60%"><span style="display:block;height:12px;border-radius:3px;'
                    f'background:{"#14705f" if y >= "2021" else "#9bb8b0"};width:{n / mx * 100:.0f}%"></span></td></tr>\n')

    # 区ごと
    byw = collections.defaultdict(list)
    for r in rows:
        byw[r["市区町村名"]].append(r)
    wrows, csvrows = [], []
    for wid, w in WARDS.items():
        L = byw.get(w["name"], [])
        if not L:
            continue
        a = sum(1 for r in L if r["指定年月日"] >= "2021")
        l1 = sum(1 for r in L if NEW_FROM <= r["指定年月日"] <= NEW_TO)
        wrows.append(f'      <tr><th class="nw"><a href="{{{{ROOT}}}}houmon-kango/tokyo/{wid}/">{w["name"]}</a></th>'
                     f'<td class="num">{len(L)}</td><td class="num">{a}</td><td class="num">{pct(a, len(L))}</td>'
                     f'<td class="num">{l1}</td></tr>\n')
        csvrows.append([w["name"], len(L), a, round(a / len(L), 3), l1])
    hiw = max(csvrows, key=lambda x: x[2])
    hir = max(csvrows, key=lambda x: x[3])

    hc = collections.Counter(unicodedata.normalize("NFKC", r["法人名"]).replace("　", " ") for r in new)
    toph = hc.most_common(5)
    trows = [f'      <tr><td class="num">{i}</td><th>{h}</th><td class="num">{n}</td></tr>\n'
             for i, (h, n) in enumerate(toph, 1)]

    pts = [
        f'<li><b>いまある訪問看護の{pct(nn, N)}が2021年以降の指定</b>23区で指定を受けている{N:,}件のうち{nn}件が、2021年1月以降に指定を受けたステーションです。</li>',
        f'<li><b>いちばん多かったのは{peak}年の{yc[peak]}件</b>直近1年（2025年9月〜2026年9月）でも{last}件が新しく指定されています。</li>',
        f'<li><b>新しいステーションの{pct(eiri(new), nn)}が株式会社など</b>2020年以前に指定されたところでは{pct(eiri(old), no)}で、'
        f'医療法人は2020年以前の{pct(iryo(old), no)}に対し、2021年以降は{pct(iryo(new), nn)}です。</li>',
        f'<li><b>日曜も訪問するところは新しいほど多い</b>サービス提供日が登録されている事業所のうち、日曜を含むのは2021年以降の指定で{pct(sn, sd)}（{sn}/{sd}件）、'
        f'2020年以前の指定で{pct(so, sod)}（{so}/{sod}件）です。</li>',
        f'<li><b>2021年以降の数が最も多いのは{hiw[0]}（{hiw[2]}件）</b>区内の割合が最も高いのは{hir[0]}（{hir[1]}件中{hir[2]}件、{pct(hir[2], hir[1])}）です。</li>',
    ]

    def table(head, body, cap, sortable=False):
        return ('  <div class="tw">\n  <table' + (' class="sortable"' if sortable else "") + '>\n'
                f'    <caption class="tiny" style="text-align:left;padding-bottom:6px">{cap}</caption>\n'
                '    <thead><tr>' + "".join(('<th class="nw">' if i == 0 else '<th>') + h + '</th>' for i, h in enumerate(head))
                + '</tr></thead>\n    <tbody>\n' + "".join(body) + '    </tbody>\n  </table>\n  </div>\n')

    d0401 = sum(1 for r in rows if r["指定年月日"] == "2000-04-01")
    html = f"""<p class="upd">更新日：2026-11-11（東京都の指定事業所一覧 2026年9月1日時点）</p>
  <p>東京23区で指定を受けている訪問看護ステーション{N:,}件を、<strong>介護保険の指定を受けた年</strong>で数えました。いま23区にあるステーションの約半分は、2021年以降に指定されたところです。新しいステーションほど株式会社の運営が多く、日曜にも訪問するところが多いという違いも見えます。</p>
  <div class="note"><strong>このデータで分かること・分からないこと</strong>　数えているのは2026年9月1日時点で指定を受けている事業所だけです。廃止・休止したステーションは入っていないため、「その年に開設された数」そのものではありません。また、増えた理由はこのデータからは分かりません。</div>
  <h2 id="point">要点</h2>
  <ul class="check">
    {"".join(pts)}
  </ul>
  <h2 id="year">指定を受けた年ごとの数</h2>
  <p>濃い色が2021年以降です。2000年のうち{d0401}件は、介護保険制度が始まった2000年4月1日の指定です。</p>
{table(["年", "件数", ""], bars, "いま23区で指定を受けている訪問看護ステーションを、指定年月日の年で数えたもの")}
  <h2 id="ward">区ごとの比較</h2>
  <p>区名を押すと、その区の訪問看護ステーション一覧（全件・電話番号つき）に移ります。表の見出しを押すと並べ替えられます。</p>
{table(["区", "ステーション数", "2021年以降の指定", "割合", "直近1年の指定"], wrows, "直近1年は2025年9月2日〜2026年9月1日", sortable=True)}
  <h2 id="hojin">2021年以降に指定が多い法人</h2>
  <p>2021年以降に指定を受けたステーションを、運営法人ごとに数えました（法人名は東京都の公表にもとづき、全角・半角の表記だけそろえています）。</p>
{table(["順位", "法人名", "2021年以降の指定"], trows, "上位5法人")}
  <h2 id="next">訪問看護を探すときは</h2>
  <p>新しいか古いかは、ステーションの良し悪しとは関係ありません。日曜の訪問、対応できる医療処置、緊急時の連絡体制は事業所ごとに違うので、主治医やケアマネジャーと相談しながら、候補のステーションに直接確認してください。</p>
  <div class="lg"><a href="{{{{ROOT}}}}houmon-kango/tokyo/">東京23区の訪問看護<small>区を選んで全件を見る</small></a><a href="{{{{ROOT}}}}guide/houmon-kango-chigai/">訪問介護と訪問看護の違い<small>頼めること・保険・料金</small></a><a href="{{{{ROOT}}}}tokyo/unei-hojin/">介護事業所の運営法人<small>株式会社の割合と大手15法人</small></a></div>
  <h2 id="dl">データのダウンロード</h2>
  <p>区ごとの集計はCSVで自由に使えます（<a href="https://creativecommons.org/licenses/by/4.0/deed.ja" rel="noopener">CC BY 4.0</a>。出典「かいごのとなり（東京都・厚生労働省の公表データをもとに作成）」の表記をお願いします）。</p>
  <div class="lg"><a href="{{{{ROOT}}}}opendata/tokyo23-houmon-kango-shitei.csv" download>訪問看護の指定年・区別集計（CSV）<small>23行</small></a><a href="{{{{ROOT}}}}opendata/">事業所データ（CSV）<small>事業所1件ずつの一覧</small></a></div>
  <div class="src"><strong>参考・出典</strong><ul>
    <li>東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0／2026年9月1日時点／指定年月日・法人種別・法人名）</li>
    <li>厚生労働省「介護サービス情報公表システム」オープンデータ（2026年6月30日時点／サービス提供日）</li>
  </ul></div>
  <script src="{{{{ROOT}}}}assets/sort.js" defer></script>
"""
    (BASE / "content" / "page_tokyo_houmon-kango-zouka.html").write_text(html, encoding="utf-8")
    with open(BASE / "opendata" / "tokyo23-houmon-kango-shitei.csv", "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["区", "訪問看護ステーション数", "2021年以降の指定", "2021年以降の割合", "直近1年の指定"])
        wr.writerows(csvrows)
    print(f"kango-zouka: {N} / 2021+ {nn} / peak {peak}:{yc[peak]} / last1y {last}")
    for p in pts:
        print(" ", p.replace("<li>", "").replace("</li>", "").replace("<b>", "【").replace("</b>", "】"))


if __name__ == "__main__":
    main()
