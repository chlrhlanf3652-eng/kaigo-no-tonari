#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""区ごとの掲載データを収集して tools/cache/<区>.json に保存する。

収集するもの（すべて公表されている一覧ページから）:
  1. 訪問介護事業所の一覧（事業所名・法人名・事業所番号・所在地・電話・FAX・受付）
  2. その区が地域包括支援センターを何と呼んでいるか
  3. 区内の町域一覧（五十音の読みつき）

クロールの作法（docs/crawler-design.md のとおり）:
  - robots.txt で許可されている経路だけを取る（2026-09-21 確認済み）
  - 1リクエストずつ、2.5秒あける
  - 連絡先のわかる User-Agent を名乗る
  - 3回続けて 403/429 が返ったら、その回の収集を打ち切る

使い方:
  python3 tools/fetch_ward.py nerima itabashi      # 指定した区だけ
  python3 tools/fetch_ward.py --all                # 23区すべて
  python3 tools/fetch_ward.py --labels nerima      # th のラベル一覧を確認する（下見用）
"""
import html as htmllib
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS, TOWN_EXCLUDE

BASE = pathlib.Path(__file__).parent.parent
CACHE = pathlib.Path(__file__).parent / "cache"
UA = ("kaigonotonari-bot/1.0 (+https://kaigonotonari.com/about/; "
      "contact: https://kaigonotonari.com/contact/)")
WAIT = 2.5
_last = [0.0]
_fails = [0]


def get(url: str) -> str:
    """作法を守って1ページ取る。"""
    gap = WAIT - (time.time() - _last[0])
    if gap > 0:
        time.sleep(gap)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ja,en;q=0.5"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            _last[0] = time.time()
            _fails[0] = 0
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        _last[0] = time.time()
        if e.code in (403, 429):
            _fails[0] += 1
            if _fails[0] >= 3:
                raise SystemExit("403/429 が3回続いたため収集を中止します。時間をおいてください。")
        raise


def text(s: str) -> str:
    """タグを落として、全角の約物を見出しに使える形にそろえる。"""
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s)
    s = s.replace("　", " ").replace("：", ":").replace("～", "〜")
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------ 事業所一覧
STORE = re.compile(r'<div class="store item[^"]*">(.*?)(?=<div class="store item|<div id="facility_list_bottom"|</section>)', re.S)
NAME = re.compile(r'<a class="list_facility_name[^"]*"[^>]*>\s*<h3>(.*?)</h3>', re.S)
CELL = re.compile(r"<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>", re.S)
TOTAL = re.compile(r'class="num"[^>]*>(.*?)</div>', re.S)

# ハートページ側のラベル → こちらのキー
FIELD = {
    "事業所番号": "identifier", "法人名": "org", "運営法人": "org",
    "所在地": "address", "住所": "address",
    "電話番号": "tel", "電話": "tel", "FAX番号": "fax", "FAX": "fax",
    "電話受付時間": "hours", "受付時間": "hours",
    "受付休業日": "closed", "休業日": "closed", "定休日": "closed",
}


def parse_list(page: str):
    items = []
    for block in STORE.findall(page):
        m = NAME.search(block)
        if not m:
            continue
        rec = {"name": text(m.group(1))}
        for th, td in CELL.findall(block):
            key = FIELD.get(text(th).replace(" ", ""))
            if key and key not in rec:
                rec[key] = text(td)
        if rec.get("identifier"):
            items.append(rec)
    return items


def fetch_facilities(hp: str, want: int = 60):
    url = f"https://www.heartpage.jp/{hp}/list?type=visit_care"
    page = get(url)
    m = TOTAL.search(page)
    total = None
    if m:
        d = re.search(r"([\d,]+)", text(m.group(1)))
        if d:
            total = int(d.group(1).replace(",", ""))
    items = parse_list(page)
    n = 2
    while len(items) < want and f"page={n}" in page and n <= 3:
        page = get(f"{url}&page={n}")
        items += parse_list(page)
        n += 1
    return total, items[:want]


# ------------------------------------------------------- 相談窓口の呼び名
SOUDAN = re.compile(r"<title>[^<]*?の介護の相談窓口｜(.+?)の一覧")


def fetch_madoguchi(hp: str, fallback="地域包括支援センター"):
    try:
        page = get(f"https://www.heartpage.jp/{hp}/kaigo_soudan")
    except Exception:
        return fallback
    m = SOUDAN.search(page)
    return htmllib.unescape(m.group(1)).strip() if m else fallback


# ------------------------------------------------------------- 町域一覧
# 町名はリンク、読みはすぐ後ろの span に入っている
ROW = re.compile(r'<a href="[^"]*?list\.php[^"]*?&amp;id=[^"]*">(.*?)</a>'
                 r'\s*<span class="choikikobetsuyomi">（(.*?)）</span>', re.S)


def fetch_towns(code: str):
    page = get(f"https://chimei.jitenon.jp/data/list.php?pref=13&town={code}")
    out, seen = [], set()
    for a, b in ROW.findall(page):
        name, kana = text(a), text(b)
        kana = re.sub(r"[^぀-ゟ]", "", kana)
        if not name or not kana or name in seen:
            continue
        if any(x in name for x in TOWN_EXCLUDE):
            continue
        seen.add(name)
        out.append({"name": name, "kana": kana})
    return out


def run(ward_id: str):
    w = WARDS[ward_id]
    print(f"— {w['name']} ({ward_id})")
    total, items = fetch_facilities(w["hp"])
    madoguchi = fetch_madoguchi(w["hp"])
    towns = fetch_towns(w["code"])
    rec = {"id": ward_id, "name": w["name"], "total": total, "madoguchi": madoguchi,
           "items": items, "towns": towns, "fetched": time.strftime("%Y-%m-%d")}
    CACHE.mkdir(exist_ok=True)
    (CACHE / f"{ward_id}.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"   事業所 {len(items)}件 / 区内 {total}件 / 窓口「{madoguchi}」/ 町域 {len(towns)}")
    if len(items) < 3:
        print("   ※ 掲載3件未満。このままではページを作れません。")
    return rec


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--towns":
        # 町域だけ取り直して、既存のキャッシュに差し込む
        targets = list(WARDS) if len(args) == 1 else args[1:]
        for t in targets:
            f = CACHE / f"{t}.json"
            if not f.exists():
                print(f"   - {t}: キャッシュなし、スキップ")
                continue
            rec = json.loads(f.read_text(encoding="utf-8"))
            rec["towns"] = fetch_towns(WARDS[t]["code"])
            f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"   {WARDS[t]['name']}: 町域 {len(rec['towns'])}")
        raise SystemExit
    if args and args[0] == "--labels":
        page = get(f"https://www.heartpage.jp/{WARDS[args[1]]['hp']}/list?type=visit_care")
        blocks = STORE.findall(page)
        print(f"{len(blocks)} blocks")
        if blocks:
            for th, td in CELL.findall(blocks[0]):
                print(f"  [{text(th)}] = {text(td)[:60]}")
        raise SystemExit
    targets = list(WARDS) if (not args or args[0] == "--all") else args
    ok = 0
    for t in targets:
        try:
            run(t)
            ok += 1
        except Exception as e:
            print(f"   × {t}: {e}")
    print(f"\n{ok}/{len(targets)} 区を取得しました。")
