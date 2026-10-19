#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""東京23区の介護サービス比較ページ（/tokyo/hikaku/）の本文とCSVを作る。

区ページに散らばっている「23区中○位」の元になる表を、1ページにまとめて公開する。
数字はすべて一次統計（東京都の指定事業所一覧・住民基本台帳・介護保険事業状況報告）と
厚労省オープンデータ（サービス提供日）から計算し、推測で埋めない。
出力: content/page_tokyo_hikaku.html, opendata/tokyo23-kaigo-hikaku.csv
"""
import csv
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import facts as FX
import koreika as KO
import linkgrid as LG
from wards import WARDS

BASE = pathlib.Path(__file__).resolve().parent.parent
CATS = list(LG.CATS)
NAME = {c: LG.CATS[c][1] for c in CATS}
SUN_CATS = ["houmon-kaigo", "houmon-kango", "day-service"]


def main():
    cnt = {c: LG.counts(c) for c in CATS}
    st = {w: KO.stats(w) for w in WARDS}
    per = {c: {w: cnt[c][w] / st[w]["p65"] * 10000 for w in cnt[c] if st.get(w)} for c in CATS}
    sun = {c: FX._sunday_share(c) for c in SUN_CATS}
    wids = [w for w in WARDS if st.get(w)]
    total_all = sum(sum(cnt[c].values()) for c in CATS)

    def rank(d, w):
        return KO._rank(d, w)

    def link(w):
        return f'<a href="{{{{ROOT}}}}tokyo/{w}/">{WARDS[w]["name"]}</a>'

    # 要点（各サービスで1万人あたり最多・最少）
    pts = []
    for c in CATS:
        d = per[c]
        hi = max(d, key=d.get); lo = min(d, key=d.get)
        pts.append(f'<li><b>{NAME[c]}</b>65歳以上1万人あたり最も多いのは{WARDS[hi]["name"]}（{d[hi]:.1f}件）、'
                   f'最も少ないのは{WARDS[lo]["name"]}（{d[lo]:.1f}件）。差は{d[hi]/d[lo]:.1f}倍です。</li>')
    r65 = {w: st[w]["rate65"] for w in wids}
    hi = max(r65, key=r65.get); lo = min(r65, key=r65.get)
    pts.insert(0, f'<li><b>高齢化率</b>最も高いのは{WARDS[hi]["name"]}（{r65[hi]}%）、最も低いのは{WARDS[lo]["name"]}（{r65[lo]}%）。</li>')

    def table(head, rows, cap):
        return ('  <div class="tw">\n  <table class="sortable">\n'
                f'    <caption class="tiny" style="text-align:left;padding-bottom:6px">{cap}</caption>\n'
                '    <thead><tr>' + "".join(('<th class="nw">' if i == 0 else '<th>') + h + '</th>' for i, h in enumerate(head)) + '</tr></thead>\n    <tbody>\n'
                + "".join(rows) + '    </tbody>\n  </table>\n  </div>\n')

    t1 = [f'      <tr><th class="nw">{link(w)}</th><td class="num">{st[w]["p65"]:,}</td><td class="num">{st[w]["rate65"]}</td>'
          f'<td class="num">{st[w]["rate75"]}</td><td class="num">{st[w]["nintei"]:,}</td><td class="num">{st[w]["ninteiritsu"]}</td></tr>\n'
          for w in wids]
    t2 = [f'      <tr><th class="nw">{link(w)}</th>' + "".join(
              f'<td class="num"><a href="{{{{ROOT}}}}{c}/tokyo/{w}/">{cnt[c].get(w, 0)}</a></td>' for c in CATS) + '</tr>\n'
          for w in wids]
    t3 = [f'      <tr><th class="nw">{link(w)}</th>' + "".join(
              f'<td class="num">{per[c][w]:.1f}</td>' if w in per[c] else '<td class="num">—</td>' for c in CATS) + '</tr>\n'
          for w in wids]
    t4 = [f'      <tr><th class="nw">{link(w)}</th>' + "".join(
              f'<td class="num">{sun[c][w]*100:.0f}%</td>' if w in sun[c] else '<td class="num">—</td>' for c in SUN_CATS) + '</tr>\n'
          for w in wids]

    html = f"""<p class="upd">更新日：2026-10-19（事業所数は2026年9月1日時点）</p>
  <p>東京23区の介護サービス事業所{total_all:,}件（訪問介護・訪問看護・デイサービス・ショートステイ・福祉用具）を区ごとに数え、高齢者人口と並べました。<strong>「65歳以上1万人あたり」の事業所数</strong>を見ると、高齢者の数に対してサービスが多い区・少ない区がわかります。表の見出しを押すと並べ替えられます。数字は優劣ではなく、事業所の探しやすさの目安です。</p>
  <h2 id="point">要点</h2>
  <ul class="check">
    {"".join(pts)}
  </ul>
  <h2 id="koreika">23区の高齢化率と要介護認定</h2>
{table(["区","65歳以上（人）","高齢化率（%）","75歳以上の割合（%）","要支援・要介護の認定（人）","認定率（%）"], t1, "人口は2026年1月1日、認定者数は2026年6月分")}
  <h2 id="kensu">23区の介護サービス事業所数</h2>
  <p>数字を押すと、その区の事業所一覧（全件・電話番号つき）に移ります。デイサービスは東京都が指定する通所介護（定員19人以上）の数で、区が指定する地域密着型通所介護は含みません。</p>
{table(["区"] + [NAME[c] for c in CATS], t2, "東京都の指定を受けている事業所数（2026年9月1日時点）")}
  <h2 id="per">65歳以上1万人あたりの事業所数</h2>
  <p>区内の事業所数を、65歳以上の人口1万人あたりに直した数です。区の外の事業所を使うこともできるため、少ない区でも利用できないという意味ではありません。</p>
{table(["区"] + [NAME[c] for c in CATS], t3, "事業所数 ÷ 65歳以上人口 × 10,000")}
  <h2 id="sunday">日曜日もサービスを提供している事業所の割合</h2>
  <p>厚生労働省のオープンデータで「サービスを提供する曜日」が登録されている事業所のうち、日曜日を含む事業所の割合です。週末にも来てほしい・通いたい場合の探しやすさの目安になります。</p>
{table(["区"] + [NAME[c] for c in SUN_CATS], t4, "曜日の登録がある事業所が3件未満の区は「—」")}
  <h2 id="dl">データのダウンロード</h2>
  <p>この表のもとになった数字は、CSVで自由に使えます（<a href="https://creativecommons.org/licenses/by/4.0/deed.ja" rel="noopener">CC BY 4.0</a>。出典「かいごのとなり（東京都・厚生労働省の公表データをもとに作成）」の表記をお願いします）。</p>
  <div class="lg"><a href="{{{{ROOT}}}}opendata/tokyo23-kaigo-hikaku.csv" download>23区比較データ（CSV）<small>23行・区ごとの件数と人口</small></a><a href="{{{{ROOT}}}}opendata/">事業所データ（CSV）<small>事業所1件ずつの一覧</small></a></div>
  <div class="src"><strong>参考・出典</strong><ul>
    <li>東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0／2026年9月1日時点）</li>
    {"".join(f"<li>{s}</li>" for s in KO.SOURCES)}
    <li>厚生労働省「介護サービス情報公表システム」オープンデータ（2026年6月30日時点／サービス提供日）</li>
  </ul></div>
  <script src="{{{{ROOT}}}}assets/sort.js" defer></script>
"""
    (BASE / "content" / "page_tokyo_hikaku.html").write_text(html, encoding="utf-8")

    with open(BASE / "opendata" / "tokyo23-kaigo-hikaku.csv", "w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["区", "65歳以上人口", "高齢化率", "75歳以上割合", "要支援要介護認定者数", "認定率"]
                    + [f"{NAME[c]}_事業所数" for c in CATS]
                    + [f"{NAME[c]}_65歳以上1万人あたり" for c in CATS]
                    + [f"{NAME[c]}_日曜提供割合" for c in SUN_CATS])
        for w in wids:
            s = st[w]
            wr.writerow([WARDS[w]["name"], s["p65"], s["rate65"], s["rate75"], s["nintei"], s["ninteiritsu"]]
                        + [cnt[c].get(w, "") for c in CATS]
                        + [f"{per[c][w]:.2f}" if w in per[c] else "" for c in CATS]
                        + [f"{sun[c][w]:.3f}" if w in sun[c] else "" for c in SUN_CATS])
    print(f"hikaku: {len(wids)}区 / 事業所{total_all:,}件")


if __name__ == "__main__":
    main()
