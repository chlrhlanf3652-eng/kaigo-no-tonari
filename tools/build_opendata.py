# -*- coding: utf-8 -*-
"""掲載している事業所データを1本のCSVにまとめて公開する。

このサイトの値打ちは、東京都と厚生労働省の2つの公開データを事業所番号で
突き合わせたところにある。突き合わせた結果そのものを配れば、同じことを
やり直す人の手間が省けるし、引用もされやすい。作り方は /data-sources/ に、
配るものはここに置く。

出力: opendata/kaigonotonari-tokyo23-kaigo.csv
"""
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS

BASE = pathlib.Path(__file__).parent.parent
CACHE = pathlib.Path(__file__).parent / "cache"
OUT = BASE / "opendata" / "kaigonotonari-tokyo23-kaigo.csv"

# 出力順は「何のサービスか → どこか → どこの誰か → 中身」
COLS = [
    ("service", "サービス種類"),
    ("ward", "市区町村名"),
    ("ward_code", "団体コード"),
    ("name", "事業所名"),
    ("corporation", "法人名"),
    ("corporation_type", "法人種別"),
    ("office_id", "事業所番号"),
    ("address", "住所"),
    ("tel", "電話番号"),
    ("designated_on", "指定年月日"),
    ("facility_type", "事業所種別"),
    ("available_days", "利用可能曜日"),
    ("capacity", "定員"),
    ("url", "公式サイト"),
    ("lat", "緯度"),
    ("lng", "経度"),
]

CATS = [
    ("", "訪問介護"),
    ("kango_", "訪問看護"),
    ("day_", "通所介護"),
    ("short_", "短期入所生活介護"),
    ("yogu_", "福祉用具貸与・特定福祉用具販売"),
]


def rows():
    for prefix, service in CATS:
        for wid, w in WARDS.items():
            p = CACHE / f"{prefix}{wid}.json"
            if not p.exists():
                continue
            rec = json.loads(p.read_text(encoding="utf-8"))
            for it in rec["items"]:
                svcs = it.get("services") or [service]
                yield {
                    "service": "・".join(svcs),
                    "ward": w["name"],
                    "ward_code": w["code"],
                    "name": it.get("name", ""),
                    "corporation": it.get("org", ""),
                    "corporation_type": it.get("org_kind", ""),
                    "office_id": it.get("identifier", ""),
                    "address": it.get("address", ""),
                    "tel": it.get("tel", ""),
                    "designated_on": it.get("designated", ""),
                    "facility_type": it.get("facility_kind", ""),
                    # 曜日は厚労省側にしかない。無い事業所は空欄のままにする
                    # （「なし」と書くと、提供していないという別の意味になる）。
                    "available_days": "・".join(it.get("days") or []),
                    "capacity": it.get("capacity") or "",
                    "url": it.get("url", ""),
                    "lat": it.get("lat", ""),
                    "lng": it.get("lng", ""),
                }



def check_page(data):
    """配布ページに手で書いた件数が、実際のCSVとずれていないか確かめる。

    件数を本文にベタ書きしているので、データを取り直したときに黙ってずれる。
    同業サイトで「2021年1月22日時点44件」が5年半放置されている例を見たので、
    ずれたらビルドを止める。
    """
    page = BASE / "content" / "page_opendata.html"
    if not page.exists():
        return
    html = page.read_text(encoding="utf-8")
    pub, tot = {}, {}
    for prefix, service in CATS:
        for wid in WARDS:
            f = CACHE / f"{prefix}{wid}.json"
            if not f.exists():
                continue
            rec = json.loads(f.read_text(encoding="utf-8"))
            pub[service] = pub.get(service, 0) + len(rec["items"])
            tot[service] = tot.get(service, 0) + rec["total"]
    want = [f"{len(data):,}"] + [f"{v:,}" for v in pub.values()] + [f"{v:,}" for v in tot.values()]
    missing = [w for w in want if w not in html]
    if missing:
        raise SystemExit(
            "content/page_opendata.html の件数が古くなっています。\n"
            f"  本文に見当たらない数値: {missing}\n"
            f"  掲載: {pub}\n  区内全指定: {tot}\n  合計: {len(data):,}")
    print(f"\n件数の照合: 本文の数値はCSVと一致しています（合計 {len(data):,}）。")


def main():
    data = list(rows())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Excel でそのまま開けるように BOM つき UTF-8。
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        wtr = csv.writer(f)
        wtr.writerow([ja for _, ja in COLS])
        for r in data:
            wtr.writerow([r[en] for en, _ in COLS])

    filled = {en: sum(1 for r in data if str(r[en]).strip()) for en, _ in COLS}
    print(f"{OUT.relative_to(BASE)}  {len(data):,}行 / {OUT.stat().st_size:,}バイト\n")
    print("列ごとの記載あり件数:")
    for en, ja in COLS:
        print(f"  {ja:16} {filled[en]:5,} / {len(data):,}  ({filled[en]/len(data)*100:5.1f}%)")
    check_page(data)
    return len(data)


if __name__ == "__main__":
    main()
