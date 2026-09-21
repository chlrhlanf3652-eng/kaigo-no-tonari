#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""既存キャッシュに、区ごとの相談窓口の設置数を足す。

地域包括支援センターが区内に何か所あるかは、その区の探し方を左右する。
（7か所の区と25か所の区では「担当窓口を調べる」の難易度が違う）
一覧ページの件数表示から取るだけなので、1区1リクエストで済む。

使い方: python3 tools/fetch_extra.py [区ID...]
"""
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS

CACHE = pathlib.Path(__file__).parent / "cache"
UA = ("kaigonotonari-bot/1.0 (+https://kaigonotonari.com/about/; "
      "contact: https://kaigonotonari.com/contact/)")
NUM = re.compile(r'class="num"[^>]*>(.*?)</div>', re.S)


def centers(hp):
    time.sleep(2.5)
    req = urllib.request.Request(f"https://www.heartpage.jp/{hp}/kaigo_soudan",
                                 headers={"User-Agent": UA, "Accept-Language": "ja"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    m = NUM.search(page)
    if not m:
        return None
    d = re.search(r"([\d,]+)", re.sub(r"<[^>]+>", "", m.group(1)))
    return int(d.group(1).replace(",", "")) if d else None


if __name__ == "__main__":
    targets = sys.argv[1:] or sorted(p.stem for p in CACHE.glob("*.json") if not p.stem.startswith("_"))
    for t in targets:
        f = CACHE / f"{t}.json"
        if not f.exists():
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        try:
            n = centers(WARDS[t]["hp"])
        except Exception as e:
            print(f"   × {t}: {e}")
            continue
        rec["centers"] = n
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"   {rec['name']}: {rec['madoguchi']} {n}か所")
