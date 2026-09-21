#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""訪問看護ステーションの一覧を区ごとに収集して tools/cache/kango_<区>.json に保存する。

訪問介護（fetch_ward.py）と同じ一覧ページの仕組みなので、取得と解析はそちらを再利用し、
ここではサービス種別を visit_nursing に差し替えるだけにしてある。

町域と相談窓口の呼び名は訪問介護のキャッシュに入っているものを使い回す。
同じものを取り直さないぶん、相手のサーバーへのリクエストが減る。

使い方:
  python3 tools/fetch_kango.py nerima itabashi   # 指定した区だけ
  python3 tools/fetch_kango.py --all             # キャッシュのある区すべて
"""
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fetch_ward as F
from wards import WARDS

CACHE = pathlib.Path(__file__).parent / "cache"
TYPE = "visit_nursing"


def fetch_facilities(hp: str, want: int = 20):
    """fetch_ward.fetch_facilities のサービス種別違い。"""
    url = f"https://www.heartpage.jp/{hp}/list?type={TYPE}"
    page = F.get(url)
    total = None
    m = F.TOTAL.search(page)
    if m:
        import re
        d = re.search(r"([\d,]+)", F.text(m.group(1)))
        if d:
            total = int(d.group(1).replace(",", ""))
    items = F.parse_list(page)
    n = 2
    while len(items) < want and f"page={n}" in page and n <= 3:
        page = F.get(f"{url}&page={n}")
        items += F.parse_list(page)
        n += 1
    return total, items[:want]


def run(ward_id: str):
    w = WARDS[ward_id]
    base = CACHE / f"{ward_id}.json"
    if not base.exists():
        print(f"   - {ward_id}: 訪問介護のキャッシュがないためスキップ")
        return None
    src = json.loads(base.read_text(encoding="utf-8"))
    total, items = fetch_facilities(w["hp"])
    rec = {"id": ward_id, "name": w["name"], "total": total,
           "madoguchi": src.get("madoguchi", "地域包括支援センター"),
           "centers": src.get("centers"),
           "items": items, "towns": src.get("towns", []),
           "fetched": time.strftime("%Y-%m-%d")}
    (CACHE / f"kango_{ward_id}.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    flag = "" if len(items) >= 3 else "   ※ 3件未満。ページは作れません。"
    print(f"   {w['name']}: 掲載 {len(items)}件 / 区内 {total}件{flag}")
    return rec


if __name__ == "__main__":
    args = sys.argv[1:]
    have = [p.stem for p in sorted(CACHE.glob("*.json"))
            if not p.stem.startswith(("_", "kango_"))]
    targets = have if (not args or args[0] == "--all") else args
    ok = 0
    for t in targets:
        try:
            if run(t):
                ok += 1
        except Exception as e:
            print(f"   × {t}: {e}")
    print(f"\n{ok}/{len(targets)} 区を取得しました。")
