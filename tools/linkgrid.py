# -*- coding: utf-8 -*-
"""区ページどうしを結ぶリンクグリッドを作る（全カテゴリ共通）。

同業大手（LIFULL介護・安心介護紹介センター）は一覧ページの下に
「23区すべて＋件数」「他サービスすべて＋件数」のリンクを並べている。
件数つきにするのは、0件や極端に少ないエリアを踏ませないため。
件数はすべて各カテゴリのキャッシュ（東京都福祉局CSV由来の区内実数）から取る。
"""
import json
import pathlib

from wards import WARDS

CACHE = pathlib.Path(__file__).parent / "cache"

# カテゴリID → (キャッシュの接頭辞, 表示名, 一覧の説明)
CATS = {
    "houmon-kaigo":  ("",        "訪問介護",       "自宅に来てもらう"),
    "houmon-kango":  ("kango_",  "訪問看護",       "医療ケアが必要な方へ"),
    "day-service":   ("day_",    "デイサービス",   "日帰りで通う"),
    "short-stay":    ("short_",  "ショートステイ", "数日あずける"),
    "fukushi-yogu":  ("yogu_",   "福祉用具",       "借りる・買う"),
}

_cache = {}


def counts(cat: str) -> dict:
    """そのカテゴリの区ごとの区内件数。キャッシュが無い区は入らない。"""
    if cat not in _cache:
        prefix = CATS[cat][0]
        out = {}
        for wid in WARDS:
            p = CACHE / f"{prefix}{wid}.json"
            if p.exists():
                rec = json.loads(p.read_text(encoding="utf-8"))
                if rec.get("total"):
                    out[wid] = rec["total"]
        _cache[cat] = out
    return _cache[cat]


def area_links(cat: str, cur: str) -> str:
    """同じサービスの他の22区へのリンク（区コード順・件数つき）。"""
    c = counts(cat)
    rows = []
    for wid, w in WARDS.items():
        if wid == cur or wid not in c:
            continue
        rows.append('<a href="{{ROOT}}%s/tokyo/%s/">%s<small>%d件</small></a>'
                    % (cat, wid, w["name"], c[wid]))
    return "\n      ".join(rows)


def service_links(cur_cat: str, wid: str, extra=()) -> str:
    """同じ区の他サービスへのリンク（件数つき）。

    extra には件数を持たないサービス（宅配弁当・高齢者可賃貸など）を
    (パス, 表示名, 説明) の形で渡す。ページが無いものは
    postprocess が「準備中」に変換する。
    """
    ward = WARDS[wid]["name"]
    rows = []
    for cat, (_prefix, name, desc) in CATS.items():
        if cat == cur_cat:
            continue
        n = counts(cat).get(wid)
        if not n:
            continue
        rows.append('<a href="{{ROOT}}%s/tokyo/%s/">%sの%s<small>%s・区内%d件</small></a>'
                    % (cat, wid, ward, name, desc, n))
    for path, name, desc in extra:
        rows.append('<a href="{{ROOT}}%s/tokyo/%s/">%s%s<small>%s</small></a>'
                    % (path, wid, ward, name, desc))
    return "\n      ".join(rows)
