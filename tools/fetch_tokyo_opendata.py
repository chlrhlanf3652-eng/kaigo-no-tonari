#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""東京都のオープンデータ（居宅サービス事業所一覧 CSV）から区ごとのデータを作る。

ハートページに掲載のない区（千代田・足立・葛飾）を埋めるために用意した。
民間ポータルではなく東京都が公表している一次情報で、ライセンスは
クリエイティブ・コモンズ 表示 4.0 国際（CC BY 4.0）。出所を明記すれば利用できる。

  出所: 東京都福祉局「居宅サービス事業所一覧」
       https://www.fukushi.metro.tokyo.lg.jp/kourei/hoken/kaigo_lib/jigyo/shitei/togetsu

CSV の列:
  項番 / サービス種類 / 事業所番号 / 事業所名 / 事業所種別名 / 事業所〒 /
  事業所住所 / 事業所電話 / 指定年月日 / 状態 / 法人名 / 法人種別名

ハートページ由来のキャッシュと同じ形で書き出すので、build_ward.py はそのまま動く。
電話受付時間と休業日は CSV に無いため空にする（無いものを推測して埋めない）。

使い方:
  python3 tools/fetch_tokyo_opendata.py chiyoda adachi katsushika
  python3 tools/fetch_tokyo_opendata.py --list      # CSV の列と件数を確認する
"""
import csv
import io
import json
import pathlib
import re
import sys
import time
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fetch_ward as F
from wards import WARDS

CACHE = pathlib.Path(__file__).parent / "cache"
INDEX = ("https://www.fukushi.metro.tokyo.lg.jp/kourei/hoken/kaigo_lib/"
         "jigyo/shitei/togetsu")
SERVICE = "訪問介護"
SOURCE = "東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0）"

# 区ごとの相談窓口の呼び名と設置数（各区公式サイトで確認：2026-09-22）
MADOGUCHI = {
    "chiyoda": ("高齢者あんしんセンター", 2),
    "adachi": ("地域包括支援センター（ホウカツ）", 23),
    "katsushika": ("高齢者総合相談センター", 14),
}


def csv_url() -> str:
    """一覧ページから CSV のリンクを見つける。月次でファイル名が変わるため。"""
    page = F.get(INDEX)
    m = re.search(r'href="([^"]*kyotaku_itiran_opendata[^"]*)"', page)
    if not m:
        raise SystemExit("CSV のリンクが見つかりません。ページ構成が変わった可能性があります。")
    href = m.group(1)
    return href if href.startswith("http") else "https://www.fukushi.metro.tokyo.lg.jp" + href


def load_rows():
    url = csv_url()
    print(f"  CSV: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": F.UA, "Accept-Language": "ja"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    text = raw.decode("utf-8-sig", "replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    print(f"  {len(rows)}行 読み込み")
    return rows


def to_records(rows, ward_name: str, want: int = 20):
    """その区・そのサービス種類・指定中のものだけを取り出す。"""
    out = []
    for r in rows:
        if (r.get("サービス種類") or "").strip() != SERVICE:
            continue
        if (r.get("状態") or "").strip() != "指定":
            continue
        addr = (r.get("事業所住所") or "").strip()
        if not addr.startswith("東京都" + ward_name):
            continue
        rec = {
            "name": (r.get("事業所名") or "").strip(),
            "identifier": (r.get("事業所番号") or "").strip(),
            "org": (r.get("法人名") or "").strip(),
            "address": addr,
            "tel": (r.get("事業所電話") or "").strip(),
            # CSV に無い項目は空のまま（推測で埋めない）
            "fax": "", "hours": "", "closed": "",
            "designated": (r.get("指定年月日") or "").strip(),
            "org_kind": (r.get("法人種別名") or "").strip(),
        }
        if rec["name"] and rec["identifier"]:
            out.append(rec)
    total = len(out)
    # 事業所番号順（=指定の古い順に近い）で安定させ、先頭 want 件を載せる
    out.sort(key=lambda x: x["identifier"])
    return total, out[:want]


def run(ward_id: str, rows):
    w = WARDS[ward_id]
    total, items = to_records(rows, w["name"])
    madoguchi, centers = MADOGUCHI.get(ward_id, ("地域包括支援センター", None))
    towns = F.fetch_towns(w["code"])
    rec = {"id": ward_id, "name": w["name"], "total": total,
           "madoguchi": madoguchi, "centers": centers,
           "items": items, "towns": towns,
           "source": SOURCE,
           "fetched": time.strftime("%Y-%m-%d")}
    CACHE.mkdir(exist_ok=True)
    (CACHE / f"{ward_id}.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"   {w['name']}: 掲載{len(items)}件 / 区内{total}件 / "
          f"窓口「{madoguchi}」{centers}か所 / 町域{len(towns)}")
    return rec


if __name__ == "__main__":
    args = sys.argv[1:]
    rows = load_rows()
    if args and args[0] == "--list":
        print("  列:", list(rows[0].keys()))
        import collections
        c = collections.Counter((r.get("サービス種類") or "").strip() for r in rows)
        for k, v in c.most_common(12):
            print(f"    {v:5}  {k}")
        raise SystemExit
    targets = args or list(MADOGUCHI)
    for t in targets:
        try:
            run(t, rows)
        except Exception as e:
            print(f"   × {t}: {e}")
