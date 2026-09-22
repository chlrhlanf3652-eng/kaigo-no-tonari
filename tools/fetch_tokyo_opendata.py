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
  python3 tools/fetch_tokyo_opendata.py --cat day-service          # 通所介護を全区
  python3 tools/fetch_tokyo_opendata.py --list                     # 列と件数を確認

なお 地域密着型通所介護（定員18人以下）は市町村が指定するため、
この都の一覧には含まれない。ページ側でその旨を明記している。
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
SOURCE = "東京都福祉局「居宅サービス事業所一覧」（CC BY 4.0）"

# カテゴリ → (CSV のサービス種類, キャッシュの接頭辞)
# 接頭辞が空のものは cache/<区>.json（訪問介護の既定の置き場）に書く。
SERVICES = {
    "houmon-kaigo": ("訪問介護", ""),
    "houmon-kango": ("訪問看護", "kango_"),
    "day-service": ("通所介護", "day_"),
    "short-stay": ("短期入所生活介護", "short_"),
    # 福祉用具は「貸与」と「販売」が別のサービス種類として登録されている。
    # 実際には同じ事業所番号で両方を扱っているところが大半（都内579事業所）で、
    # 入浴・排泄用具は販売でしか手に入らないため、利用者にとっては
    # 「両方扱うか、片方だけか」が実務上いちばん効く違いになる。まとめて取る。
    "fukushi-yogu": (("福祉用具貸与", "特定福祉用具販売"), "yogu_"),
}

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


def to_records(rows, ward_name: str, service, want: int = 20):
    """その区・そのサービス種類・指定中のものだけを取り出す。

    service には文字列のほか、複数のサービス種類をまとめたタプルも渡せる。
    複数渡したときは事業所番号で名寄せし、その事業所が扱う種類を services に
    並べる（福祉用具の貸与と販売は別行だが、同じ事業所であることが多いため）。
    """
    svcs = (service,) if isinstance(service, str) else tuple(service)
    out, seen = [], {}
    for r in rows:
        svc = (r.get("サービス種類") or "").strip()
        if svc not in svcs:
            continue
        if (r.get("状態") or "").strip() != "指定":
            continue
        addr = (r.get("事業所住所") or "").strip()
        if not addr.startswith("東京都" + ward_name):
            continue
        ident = (r.get("事業所番号") or "").strip()
        name = (r.get("事業所名") or "").strip()
        if not (name and ident):
            continue
        if ident in seen:
            if svc not in seen[ident]["services"]:
                seen[ident]["services"].append(svc)
            continue
        rec = {
            "name": name,
            "identifier": ident,
            "org": (r.get("法人名") or "").strip(),
            "address": addr,
            "tel": (r.get("事業所電話") or "").strip(),
            # CSV に無い項目は空のまま（推測で埋めない）
            "fax": "", "hours": "", "closed": "",
            "designated": (r.get("指定年月日") or "").strip(),
            "org_kind": (r.get("法人種別名") or "").strip(),
            # 短期入所生活介護では「特養の併設事業所型」「特養の空床利用型」
            # 「単独型」などが入る。ほかのサービスでは空。
            "facility_kind": (r.get("事業所種別名") or "").strip(),
            "services": [svc],
        }
        seen[ident] = rec
        out.append(rec)
    total = len(out)
    out.sort(key=lambda x: x["identifier"])
    if total <= want:
        return total, out
    # 先頭から want 件を取ると事業所番号の若い＝古い事業所ばかりになり、
    # その区を代表しない一覧になる（開設年数の内訳も1区分に潰れる）。
    # 並び順を保ったまま等間隔で抜き、新旧が混ざるようにする。
    step = total / want
    picked = [out[min(int(i * step), total - 1)] for i in range(want)]
    return total, picked


def run(ward_id: str, rows, cat: str = "houmon-kaigo"):
    service, prefix = SERVICES[cat]
    w = WARDS[ward_id]
    total, items = to_records(rows, w["name"], service)

    base = CACHE / f"{ward_id}.json"
    if prefix:
        # 町域と相談窓口は訪問介護のキャッシュを使い回す（同じものを取り直さない）
        if not base.exists():
            print(f"   - {ward_id}: 基礎キャッシュがないためスキップ")
            return None
        src = json.loads(base.read_text(encoding="utf-8"))
        madoguchi = src.get("madoguchi", "地域包括支援センター")
        centers = src.get("centers")
        towns = src.get("towns", [])
    else:
        madoguchi, centers = MADOGUCHI.get(ward_id, ("地域包括支援センター", None))
        towns = F.fetch_towns(w["code"])

    rec = {"id": ward_id, "name": w["name"], "total": total,
           "madoguchi": madoguchi, "centers": centers,
           "items": items, "towns": towns,
           "source": SOURCE,
           "service": service if isinstance(service, str) else "・".join(service),
           "fetched": time.strftime("%Y-%m-%d")}
    CACHE.mkdir(exist_ok=True)
    (CACHE / f"{prefix}{ward_id}.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    flag = "" if len(items) >= 3 else "   ※ 3件未満"
    print(f"   {w['name']}: 掲載{len(items)}件 / 区内{total}件{flag}")
    return rec


if __name__ == "__main__":
    args = sys.argv[1:]
    cat = "houmon-kaigo"
    if args and args[0] == "--cat":
        cat = args[1]
        args = args[2:]
    rows = load_rows()
    if args and args[0] == "--list":
        print("  列:", list(rows[0].keys()))
        import collections
        c = collections.Counter((r.get("サービス種類") or "").strip() for r in rows)
        for k, v in c.most_common(12):
            print(f"    {v:5}  {k}")
        raise SystemExit
    service, prefix = SERVICES[cat]
    print(f"  カテゴリ: {cat}（サービス種類「{service}」）")
    # 訪問介護は3区だけ、それ以外は基礎キャッシュのある全区
    if args:
        targets = args
    elif prefix:
        targets = sorted(p.stem for p in CACHE.glob("*.json")
                         if not p.stem.startswith(("_", "kango_", "day_",
                                                   "short_", "yogu_")))
    else:
        targets = list(MADOGUCHI)
    ok = 0
    for t in targets:
        try:
            if run(t, rows, cat):
                ok += 1
        except Exception as e:
            print(f"   × {t}: {e}")
    print(f"\n{ok}/{len(targets)} 区を取得しました。")
