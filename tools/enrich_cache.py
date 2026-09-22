#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""取り込み済みのキャッシュに、厚労省オープンデータの項目を足す。

再取得はしない。既存のキャッシュ（町域・相談窓口の呼び名・受付時間など、
取り直すと失われるものが入っている）はそのままに、事業所番号で
突き合わせて 公式サイトURL・利用可能曜日・定員・緯度経度 だけを足す。

  cache/<区>.json          訪問介護
  cache/kango_<区>.json    訪問看護
  cache/day_<区>.json      通所介護
  cache/short_<区>.json    短期入所生活介護
  cache/yogu_<区>.json     福祉用具

使い方:
  python3 tools/enrich_cache.py
"""
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import mhlw

CACHE = pathlib.Path(__file__).parent / "cache"
PREFIX = {"": "houmon-kaigo", "kango_": "houmon-kango", "day_": "day-service",
          "short_": "short-stay", "yogu_": "fukushi-yogu"}


def files_for(prefix):
    if prefix:
        return sorted(CACHE.glob(f"{prefix}*.json"))
    return sorted(p for p in CACHE.glob("*.json")
                  if "_" not in p.stem and not p.stem.startswith("."))


def closed_days(s: str):
    """ハートページ由来の休業日「土・日・祝・年末年始」を曜日の集合にする。"""
    s = s or ""
    out = set()
    if "土" in s:
        out.add("土曜日")
    if "日" in s:
        out.add("日曜日")
    if "祝" in s:
        out.add("祝日")
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    grand = clash = 0
    for prefix, cat in PREFIX.items():
        idx = mhlw.index(cat)
        tot = hit = nurl = nday = ncap = 0
        for f in files_for(prefix):
            rec = json.loads(f.read_text(encoding="utf-8"))
            items = rec.get("items") or []
            tot += len(items)
            h = mhlw.enrich(items, cat)
            hit += h
            for it in items:
                if it.get("url"):
                    nurl += 1
                if it.get("days"):
                    nday += 1
                    # 既存の休業日と食い違わないかを数える（両方は出さない判断材料）
                    cl = closed_days(it.get("closed", ""))
                    if cl & set(it["days"]):
                        clash += 1
                if it.get("capacity"):
                    ncap += 1
            rec["source2"] = mhlw.SOURCE
            rec["mhlw_hit"] = h
            f.write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                         encoding="utf-8")
        grand += tot
        print("  %-14s %3d区 掲載%4d件 / 一致%4d / URL%4d / 曜日%4d / 定員%4d"
              % (cat, len(files_for(prefix)), tot, hit, nurl, nday, ncap))
    print(f"\n合計 {grand}件。休業日と利用可能曜日が食い違う件数: {clash}")


if __name__ == "__main__":
    main()
