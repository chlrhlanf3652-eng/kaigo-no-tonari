# -*- coding: utf-8 -*-
"""掲載事業所から、その区だけの集計値を作る。

外から新しいデータを取ってこなくても、載せている20件を数え直すだけで
区ごとに違う事実が出てくる。法人の種別構成も、受付体制の厚みも、区によって
はっきり差がある。ここが市区町村ページを「地域名だけ違うページ」にしない支え。
"""
import re

# 法人名の接頭辞・接尾辞から種別を判定する。上から順に当てる。
ORG_RULES = [
    ("社会福祉法人", ("（社福）", "社会福祉法人"),
     "特別養護老人ホームなどを併設していることが多く、住み替えまで見据えて相談しやすい"),
    ("医療法人", ("（医社）", "（医財）", "医療法人"),
     "訪問看護や在宅医療と連携しやすく、医療的ケアが必要になったときに強い"),
    ("ＮＰＯ法人", ("ＮＰＯ法人", "NPO法人", "特定非営利活動法人"),
     "地域の助け合いから始まった事業所が多く、制度の隙間の相談にのってくれることがある"),
    ("協同組合・生協", ("協同組合", "生活協同組合", "労働者協同組合"),
     "組合員同士の支え合いが土台。地域に根を張った活動が長い"),
    ("一般社団・財団法人", ("（一社）", "（一財）", "一般社団法人", "一般財団法人"),
     "特定の分野に特化した事業所が多い"),
    ("株式会社", ("（株）", "株式会社"),
     "全国展開の事業所はサービスが標準化され自費プランも整う。地域密着の小規模は融通が利く"),
    ("有限会社", ("（有）", "有限会社"),
     "地域で長く続けている小規模事業所が多く、担当が変わりにくい"),
    ("合同会社", ("（同）", "合同会社"),
     "近年に開設された事業所が多く、新しい体制で運営している"),
]


def org_type(name: str) -> str:
    for label, keys, _ in ORG_RULES:
        if any(k in name for k in keys):
            return label
    return "その他"


ORG_DESC = {label: desc for label, _, desc in ORG_RULES}
ORG_DESC["その他"] = "上記にあてはまらない法人格"


def _hhmm(s):
    m = re.match(r"(\d{1,2}):(\d{2})", s or "")
    return (int(m.group(1)), int(m.group(2))) if m else None


def reception(closed: str) -> str:
    """受付休業日の書き方から、受付体制を3つに分ける。"""
    if "年中無休" in closed:
        return "年中無休"
    if "土" not in closed and "日" not in closed:
        return "土日も受付"
    return "平日中心"


RECV_DESC = {
    "年中無休": "急な依頼や体調の変化に、曜日を気にせず相談したい方",
    "土日も受付": "平日は仕事で電話できない家族が窓口になる場合",
    "平日中心": "日中に連絡が取れる方。土日の緊急連絡先は別途確認を",
}
RECV_ORDER = ["年中無休", "土日も受付", "平日中心"]


def summarize(items):
    """事業所リストから、ページに出す集計値をまとめて返す。"""
    orgs, recv = {}, {}
    starts, ends = [], []
    for it in items:
        o = it.get("parentOrganization") or ""
        o = o if isinstance(o, str) else o.get("name", "")
        orgs[org_type(o)] = orgs.get(org_type(o), 0) + 1
        r = reception(it.get("_closed", ""))
        recv[r] = recv.get(r, 0) + 1
        h = it.get("_hours", "")
        parts = re.split(r"[〜~]", h, 1)
        a = _hhmm(parts[0]) if parts else None
        b = _hhmm(parts[1]) if len(parts) > 1 else None
        if a:
            starts.append(a)
        if b:
            ends.append(b)
    fmt = lambda t: f"{t[0]}:{t[1]:02d}"
    return {
        "orgs": sorted(orgs.items(), key=lambda x: (-x[1], x[0])),
        "recv": [(k, recv[k]) for k in RECV_ORDER if k in recv],
        "open_min": fmt(min(starts)) if starts else "—",
        "open_max": fmt(max(ends)) if ends else "—",
    }
