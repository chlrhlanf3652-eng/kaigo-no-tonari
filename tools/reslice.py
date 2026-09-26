# -*- coding: utf-8 -*-
"""既存キャッシュの items だけを、手元の都 CSV から取り直して差し替える。

掲載件数の上限を 20 → 60 に上げたときに、町域・相談窓口・都の実数といった
取り直す必要のない項目まで作り直さないための一時スクリプト。
CSV は tools/cache/tokyo_kyotaku.csv（都の月次オープンデータ）を使う。
"""
import csv
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fetch_tokyo_opendata as F
import mhlw
from wards import WARDS

CSV = pathlib.Path(__file__).parent / "cache" / "tokyo_kyotaku.csv"
CACHE = pathlib.Path(__file__).parent / "cache"
WANT = 60


def main():
    rows = list(csv.DictReader(io.StringIO(
        CSV.read_bytes().decode("utf-8-sig", "replace"))))
    print(f"CSV {len(rows)}行")
    changed = 0
    for cat, (service, prefix) in F.SERVICES.items():
        for wid in sorted(WARDS):
            path = CACHE / f"{prefix}{wid}.json"
            if not path.exists():
                continue
            rec = json.loads(path.read_text(encoding="utf-8"))
            total, items = F.to_records(rows, WARDS[wid]["name"], service, want=WANT)
            hit = mhlw.enrich(items, cat)
            before = len(rec.get("items", []))
            rec["items"] = items
            rec["total"] = total
            rec["mhlw_hit"] = hit
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                            encoding="utf-8")
            changed += 1
            nurl = sum(1 for i in items if i.get("url"))
            print(f"  {cat:14} {WARDS[wid]['name']:5} "
                  f"掲載{before:3}→{len(items):3} / 区内{total:3} / "
                  f"厚労省一致{hit:3}（公式サイト{nurl}）")
    print(f"\n{changed}件のキャッシュを更新しました。")


if __name__ == "__main__":
    main()
