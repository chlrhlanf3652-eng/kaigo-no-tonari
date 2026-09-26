# -*- coding: utf-8 -*-
"""区ごとの高齢化・要介護認定の公的統計。

同業大手のうち、区ごとの統計を本文に書いているのは「みんなの介護」だけで、
LIFULL介護・ケアスル介護・さがしっくすはどこも書いていない。
素材は行政が公開していて無料なので、ここは小さいサイトでも取りにいける差。

出典（いずれも一次情報）:
  人口   … 東京都総務局統計部「住民基本台帳による東京都の世帯と人口」令和8年1月
           第3-1表（年齢3区分）/ 第7表（5歳階級）
  認定者 … 東京都福祉局「介護保険事業状況報告（月報）」令和8年6月分

作り方は tools/build_koreika.py。ここは読み出しだけ。
"""
import json
import pathlib

DATA = pathlib.Path(__file__).parent / "cache" / "stats" / "koreika.json"

SOURCES = [
    "東京都総務局統計部「住民基本台帳による東京都の世帯と人口」"
    "（令和8年1月1日現在／年齢3区分別人口・5歳階級別人口）",
    "東京都福祉局「介護保険事業状況報告（月報）」令和8年6月分"
    "（保険者別・第1号被保険者数／要介護認定者数）",
]

_d = None


def stats(wid: str):
    global _d
    if _d is None:
        _d = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {}
    return _d.get(wid)


def rank_note(wid: str, key: str, label: str):
    """23区の中での位置を一言で。順位そのものは優劣ではないので、
    「多いほう／少ないほう」と幅で書く。"""
    global _d
    if _d is None:
        stats(wid)
    vals = sorted((v[key] for v in _d.values() if v.get(key) is not None), reverse=True)
    me = _d[wid][key]
    r = vals.index(me) + 1
    if r <= 5:
        where = f"23区で{r}番目に高く"
    elif r >= 19:
        where = f"23区で{24 - r}番目に低く"
    else:
        where = f"23区のまん中あたり（{r}位）で"
    return where


CAT_LABEL = {
    "houmon-kaigo": "訪問介護",
    "houmon-kango": "訪問看護",
    "day-service": "デイサービス",
    "short-stay": "ショートステイ",
    "fukushi-yogu": "福祉用具の事業所",
}


def _avg(key):
    global _d
    return sum(v[key] for v in _d.values()) / len(_d)


def section(wid: str, ward: str, cat: str, total: int, sid: str = "s9") -> str:
    """区ごとの高齢化・認定者数のセクション。数字は全て一次統計から。"""
    d = stats(wid)
    if not d:
        return ""
    avg65 = _avg("rate65")
    avgnin = _avg("ninteiritsu")
    hi_lo = "高い" if d["rate65"] >= avg65 else "低い"
    label = CAT_LABEL.get(cat, "事業所")
    per = d["nintei"] / total if total else 0

    return f"""<h2 id="{sid}">{ward}の高齢化率は{d['rate65']}%、要介護認定を受けている人は{d['nintei']:,}人</h2>
    <p>{ward}の人口{d['pop']:,}人のうち、65歳以上は{d['p65']:,}人（{d['rate65']}%）です。23区の平均{avg65:.1f}%より{hi_lo}水準にあたります。65歳以上のうち{d['p75']:,}人は75歳以上で、介護が必要になる人が増えはじめる年代です。</p>
    <div class="tw">
    <table>
      <caption class="tiny" style="text-align:left;padding-bottom:6px">{ward}の高齢者人口と要介護認定（公的統計）</caption>
      <thead><tr><th style="width:46%">項目</th><th>{ward}</th></tr></thead>
      <tbody>
        <tr><td>総人口</td><td>{d['pop']:,}人</td></tr>
        <tr><td>65歳以上（高齢化率）</td><td>{d['p65']:,}人（{d['rate65']}%）</td></tr>
        <tr><td>うち75歳以上</td><td>{d['p75']:,}人（{d['rate75']}%）</td></tr>
        <tr><td>第1号被保険者（65歳以上）</td><td>{d['hihokensha']:,}人</td></tr>
        <tr><td>要支援1・2の認定</td><td>{d['shien']:,}人</td></tr>
        <tr><td>要介護1〜5の認定</td><td>{d['kaigo']:,}人</td></tr>
        <tr><td>認定率（認定者÷第1号被保険者）</td><td>{d['ninteiritsu']}%（23区平均{avgnin:.1f}%）</td></tr>
      </tbody>
    </table>
    </div>
    <p>{ward}で要介護・要支援の認定を受けているのは{d['nintei']:,}人、区内の{label}は{total}件なので、<strong>1事業所あたり{per:.0f}人</strong>という計算になります。認定者が全員このサービスを使うわけではないため、混み具合そのものではありません。</p>
    <p class="tiny">認定者数は第1号被保険者（65歳以上）の再掲値で、40〜64歳の方は含みません。出典はページ下部に記載しています。</p>"""
