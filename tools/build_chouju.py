#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""長寿祝いの年齢早見表（/guide/chouju-iwai/）の本文を作る。

祝いの年齢は2つの公開資料で一致を確認（2026-11-16）:
  ベストカレンダー「長寿祝い 2027年」/ QUOカード「長寿祝い早見表」
満年齢で祝う場合: 生まれ年 = 年 - 満年齢（その年の誕生日に到達）
数え年で祝う場合: 生まれ年 = 年 - 数え年 + 1。還暦は数え61歳（＝満60歳）で、どちらでも同じ生まれ年。
"""
import pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent
YEARS = [2026, 2027, 2028]
# 名前, 読み, 満年齢, 名前の由来（字の成り立ちなど）
IWAI = [
    ("還暦", "かんれき", 60, "生まれた年の干支が60年でひと回りして戻ることから"),
    ("古希（古稀）", "こき", 70, "杜甫の詩「人生七十古来稀なり」から"),
    ("喜寿", "きじゅ", 77, "「喜」の草書体が七十七に見えることから"),
    ("傘寿", "さんじゅ", 80, "「傘」の略字が八十に見えることから"),
    ("米寿", "べいじゅ", 88, "「米」の字を分けると八十八になることから"),
    ("卒寿", "そつじゅ", 90, "「卒」の略字「卆」が九十に見えることから"),
    ("白寿", "はくじゅ", 99, "「百」から一を引くと「白」になることから"),
    ("百寿", "ひゃくじゅ・ももじゅ", 100, "100歳の祝い。紀寿ともいいます"),
]


def wareki(y):
    if y >= 1989:
        return f"平成{y - 1988 if y > 1989 else '元'}年"
    if y == 1926:
        return "大正15年・昭和元年"
    if y > 1926:
        return f"昭和{y - 1925}年"
    return f"大正{y - 1911}年"


def main():
    rows = "".join(
        f'      <tr><th class="nw">{n}</th><td>{r}</td><td class="num">{a}歳</td><td>{o}</td></tr>\n'
        for n, r, a, o in IWAI)
    years = ""
    for y in YEARS:
        body = ""
        for n, r, a, o in IWAI:
            man = y - a
            kazoe = y - (61 if a == 60 else a) + 1
            body += (f'      <tr><th class="nw">{n.split("（")[0]}（{a}歳）</th><td>{man}年（{wareki(man)}）</td>'
                     f'<td>{kazoe}年（{wareki(kazoe)}）</td></tr>\n')
        years += (f'  <h3 id="y{y}">{y}年に長寿祝いを迎える人の生まれ年</h3>\n'
                  '  <div class="tw">\n  <table>\n'
                  '    <thead><tr><th class="nw">お祝い</th><th>満年齢で祝う場合</th><th>数え年で祝う場合</th></tr></thead>\n'
                  f'    <tbody>\n{body}    </tbody>\n  </table>\n  </div>\n')
    html = f"""<p>親や祖父母の長寿祝いは、いつ・何歳で祝うのかが意外と分かりにくいものです。2026年から2028年に<strong>還暦・古希・喜寿・傘寿・米寿・卒寿・白寿・百寿</strong>を迎える人の生まれ年を、満年齢と数え年の両方で一覧にしました。</p>
  <div class="note"><strong>先に結論</strong>　いまは<strong>満年齢</strong>（その年の誕生日を迎えた年齢）で祝う家が多く、数え年で祝う家もあります。還暦は昔から数え年61歳（＝満60歳）の祝いなので、<strong>どちらで数えても同じ生まれ年</strong>です。</div>
  <h2 id="list">長寿祝いの名前と年齢</h2>
  <div class="tw">
  <table>
    <thead><tr><th class="nw">お祝い</th><th>読み方</th><th>満年齢</th><th>名前の由来</th></tr></thead>
    <tbody>
{rows}    </tbody>
  </table>
  </div>
  <h2 id="year">年ごとの早見表（2026・2027・2028年）</h2>
  <p>満年齢で祝う場合は「その年に誕生日を迎えて○歳になる人」、数え年で祝う場合は「生まれた年を1歳として数え、元日に1つ年をとる」数え方です。</p>
{years}
  <h2 id="kaigo">介護が始まっていても祝うときのポイント</h2>
  <ul class="check">
    <li><b>施設に入っている場合は、先に施設へ相談</b>面会の時間や人数、持ち込める食べ物（刻み食・とろみが必要かなど）は施設ごとに決まりがあります。</li>
    <li><b>体調に合わせて短く、日中に</b>長時間の外出や夜の会食は負担になることがあります。自宅や施設の部屋で、短い時間に集まるだけでも十分です。</li>
    <li><b>形に残るものを</b>家族写真、寄せ書き、名前入りの品などは、あとから何度も見返せます。</li>
  </ul>
  <div class="note"><strong>運営者のサービス（PR）</strong>　かいごのとなりの運営者は、生年月日から読む四柱推命（韓国式サジュ）の鑑定書サービス<a href="https://koyomikitsune.com/" rel="noopener" target="_blank">「こよみ狐」</a>も運営しています。長寿祝いの贈り物の候補として、生年月日からこれまでとこれからの流れを読む鑑定書があります。かいごのとなりの掲載内容とは関係ありません。</div>
  <div class="src"><strong>参考・出典</strong><ul>
    <li>ベストカレンダー「長寿祝い（2027年）」</li>
    <li>QUOカード「長寿祝い早見表」</li>
    <li>生まれ年は上の年齢から計算（和暦は昭和元年＝1926年として換算）</li>
  </ul></div>
"""
    (BASE / "content" / "page_guide_chouju-iwai.html").write_text(html, encoding="utf-8")
    print("chouju ok")


if __name__ == "__main__":
    main()
