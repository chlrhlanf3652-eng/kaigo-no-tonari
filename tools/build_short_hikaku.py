#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""東京23区のショートステイ比較ページ（/tokyo/short-stay-hikaku/）の本文とCSVを作る。

数は opendata/kaigonotonari-tokyo23-kaigo.csv（東京都の指定事業所一覧）から、
人口は tools/cache/stats/koreika.json（住民基本台帳）から、
区独自の緊急事業は tools/kinkyu_short.py（各区公式サイトで確認したもの）から取る。
定員は公表されている事業所が半分以下なので使わない。
"""
import collections
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kinkyu_short as KS
import koreika as KO
from wards import WARDS

BASE = pathlib.Path(__file__).resolve().parent.parent
SRC = BASE / "opendata" / "kaigonotonari-tokyo23-kaigo.csv"
KINDS = [("特養の併設事業所型", "特養に併設"), ("特養の空床利用型", "特養の空床利用"),
         ("単独型", "単独型"), ("特養以外の併設事業所型", "特養以外に併設")]


def pct(a, b):
    return f"{a / b * 100:.0f}%" if b else "—"


def main():
    rows = [r for r in csv.DictReader(open(SRC, encoding="utf-8-sig")) if r["サービス種類"] == "短期入所生活介護"]
    N = len(rows)
    byw = collections.defaultdict(list)
    for r in rows:
        byw[r["市区町村名"]].append(r)
    allk = collections.Counter(r["事業所種別"] for r in rows)
    body, csvrows, recs = [], [], []
    for wid, w in WARDS.items():
        L = byw.get(w["name"], [])
        st = KO.stats(wid)
        if not L or not st:
            continue
        k = collections.Counter(r["事業所種別"] for r in L)
        n = len(L)
        senyo = n - k["特養の空床利用型"]
        per = n / st["p65"] * 10000
        kin = "あり" if wid in KS.DATA else ("近い事業あり" if wid in KS.NEAR else "確認できず")
        recs.append((wid, w["name"], n, per, senyo, k, kin))
        cells = "".join(f'<td class="num">{k[a]}</td>' for a, _ in KINDS)
        body.append(f'      <tr><th class="nw"><a href="{{{{ROOT}}}}short-stay/tokyo/{wid}/">{w["name"]}</a></th>'
                    f'<td class="num">{n}</td><td class="num">{per:.1f}</td>{cells}'
                    f'<td class="num">{senyo}</td><td>{kin}</td></tr>\n')
        csvrows.append([w["name"], n, f"{per:.2f}"] + [k[a] for a, _ in KINDS] + [senyo, kin])
    hi = max(recs, key=lambda x: x[3]); lo = min(recs, key=lambda x: x[3])
    most = max(recs, key=lambda x: x[2])
    nk = sum(1 for r in recs if r[6] == "あり")
    tok = allk["特養の併設事業所型"] + allk["特養の空床利用型"]
    pts = [
        f'<li><b>23区のショートステイ（短期入所生活介護）は{N}件</b>最も多いのは{most[1]}の{most[2]}件。</li>',
        f'<li><b>{pct(tok, N)}が特別養護老人ホームと一体</b>特養の併設型が{allk["特養の併設事業所型"]}件、特養の空床利用型が{allk["特養の空床利用型"]}件、単独型は{allk["単独型"]}件です。</li>',
        f'<li><b>65歳以上1万人あたりの数は区で{hi[3] / lo[3]:.1f}倍の差</b>最も多いのは{hi[1]}（{hi[3]:.1f}件）、最も少ないのは{lo[1]}（{lo[3]:.1f}件）です。</li>',
        f'<li><b>区独自のショートステイ・一時保護の事業は{nk}区で確認</b>介護者の急病など、急な事情で在宅介護が難しいときなどに使える区の事業です（対象や日数は区ごとに大きく違います）。</li>',
    ]
    head = ["区", "事業所数", "65歳以上1万人あたり"] + [b for _, b in KINDS] + ["専用の床がある事業所", "区独自の事業"]
    table = ('  <div class="tw">\n  <table class="sortable">\n'
             '    <caption class="tiny" style="text-align:left;padding-bottom:6px">「専用の床がある事業所」は空床利用型以外の数。区名を押すとその区の一覧（全件）に移ります</caption>\n'
             '    <thead><tr>' + "".join(('<th class="nw">' if i == 0 else '<th>') + h + '</th>' for i, h in enumerate(head))
             + '</tr></thead>\n    <tbody>\n' + "".join(body) + '    </tbody>\n  </table>\n  </div>\n')
    kin_rows = "".join(
        f'      <tr><th class="nw"><a href="{{{{ROOT}}}}short-stay/tokyo/{wid}/#kinkyu">{WARDS[wid]["name"]}</a></th>'
        f'<td>{KS.DATA[wid][0]}</td><td>{KS.DATA[wid][2] or "—"}</td></tr>\n'
        for wid in WARDS if wid in KS.DATA)
    html = f"""<p class="upd">更新日：2026-11-16（事業所数は東京都の指定事業所一覧 2026年9月1日時点、区の事業は{KS.CHECKED}確認）</p>
  <p>東京23区のショートステイ（短期入所生活介護）{N}件を区ごとに数え、<strong>高齢者の人数あたりの数</strong>、<strong>特養との関係（併設・空床利用・単独）</strong>、<strong>区独自のショートステイ・一時保護の事業</strong>を一覧にしました。数字は事業所の良し悪しではなく、予約の取りやすさを考えるときの目安です。</p>
  <h2 id="point">要点</h2>
  <ul class="check">
    {"".join(pts)}
  </ul>
  <h2 id="ward">区ごとの比較</h2>
  <p>空床利用型は、特別養護老人ホームのベッドが空いているときだけ使える形です。定期的に使いたいときは「専用の床がある事業所」から当たると予約が取りやすくなります。表の見出しを押すと並べ替えられます。</p>
{table}
  <h2 id="kinkyu">区独自のショートステイ・一時保護の事業</h2>
  <p>介護保険のショートステイとは別に、区が独自に行っている事業です。各区の公式サイト・公式資料で確認できたものだけを載せています。費用・最新の条件は区の案内でご確認ください。</p>
  <div class="tw">
  <table>
    <thead><tr><th class="nw">区</th><th>事業名</th><th>日数のめやす</th></tr></thead>
    <tbody>
{kin_rows}    </tbody>
  </table>
  </div>
  <p class="tiny">千代田区・港区・台東区・墨田区・品川区・目黒区・板橋区は、緊急ショートステイにあたる区の事業を公式サイトで確認できませんでした（港区と目黒区には近い事業があり、各区のページで紹介しています）。区の事業がない場合でも、ケアマネジャーや地域包括支援センターが介護保険のショートステイの空きを探してくれます。</p>
  <h2 id="dl">データのダウンロード</h2>
  <p>区ごとの集計はCSVで自由に使えます（<a href="https://creativecommons.org/licenses/by/4.0/deed.ja" rel="noopener">CC BY 4.0</a>。出典「かいごのとなり（東京都・各区の公表データをもとに作成）」の表記をお願いします）。</p>
  <div class="lg"><a href="{{{{ROOT}}}}opendata/tokyo23-short-stay-hikaku.csv" download>ショートステイの区別集計（CSV）<small>23行</small></a><a href="{{{{ROOT}}}}guide/short-stay-hiyou/">ショートステイの費用は1日いくら？<small>要介護度別の自己負担</small></a><a href="{{{{ROOT}}}}tokyo/hikaku/">東京23区の介護サービス比較<small>5サービスの事業所数</small></a></div>
  <div class="src"><strong>参考・出典</strong><ul>
    <li>東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0／2026年9月1日時点／事業所種別）</li>
    {"".join(f"<li>{s}</li>" for s in KO.SOURCES)}
    <li>各区の公式サイト・公式資料（緊急ショートステイ等の事業。{KS.CHECKED}確認）</li>
  </ul></div>
  <script src="{{{{ROOT}}}}assets/sort.js" defer></script>
"""
    (BASE / "content" / "page_tokyo_short-stay-hikaku.html").write_text(html, encoding="utf-8")
    with open(BASE / "opendata" / "tokyo23-short-stay-hikaku.csv", "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["区", "事業所数", "65歳以上1万人あたり"] + [a for a, _ in KINDS] + ["専用の床がある事業所", "区独自の事業"])
        wr.writerows(csvrows)
    print(f"short-hikaku: {N} / kinkyu {nk}")
    for p in pts:
        print(" ", p.replace("<li>", "").replace("</li>", "").replace("<b>", "【").replace("</b>", "】"))


if __name__ == "__main__":
    main()
