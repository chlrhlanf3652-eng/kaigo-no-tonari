#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""訪問介護の「区内件数」を、東京都の指定事業所一覧の実数に揃える。

訪問介護だけ、区内の件数に民間ポータルの掲載件数（LIFULL）を使っていた。
ほかの4カテゴリは東京都 CSV の実数なので、同じサイトの中で
「約181件」と「115件」が並ぶことになり、どちらが何なのか読者に分からない。

ここでは東京都 CSV を1回だけ読み、各区の訪問介護の指定件数を
cache/<区>.json の total_csv に書く。items も towns も触らない
（取り直すと相談窓口の呼び名や受付時間が失われるため）。

使い方:
  python3 tools/fill_totals.py
"""
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fetch_tokyo_opendata as T
from wards import WARDS

CACHE = pathlib.Path(__file__).parent / "cache"


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    rows = T.load_rows()
    changed = 0
    for wid, w in WARDS.items():
        f = CACHE / f"{wid}.json"
        if not f.exists():
            continue
        total, _ = T.to_records(rows, w["name"], "訪問介護", want=10**9)
        rec = json.loads(f.read_text(encoding="utf-8"))
        old = rec.get("total")
        rec["total_csv"] = total
        rec["total_csv_source"] = T.SOURCE
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                     encoding="utf-8")
        changed += 1
        print("  %-10s 都CSV %4d件   （キャッシュのtotal: %s）"
              % (w["name"], total, old))
    print(f"\n{changed}区に total_csv を書きました。")


if __name__ == "__main__":
    main()
