#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""厚生労働省「介護サービス情報公表システム オープンデータ」の読み込み。

東京都の CSV には無い列を補うために使う。突き合わせのキーは事業所番号。

  東京都 CSV から取るもの: 指定年月日 / 事業所種別名（空床利用型など）/ 法人種別名
  厚労省 CSV から取るもの: 利用可能曜日 / 定員 / 公式サイトURL / 緯度・経度

  出所: 厚生労働省「介護サービス情報公表システム」オープンデータ
       https://www.mhlw.go.jp/stf/kaigo-kouhyou_opendata.html
  営利・非営利を問わず二次利用可。出典を明記して使う。
  基準日は年2回（6月末・12月末）なので、東京都の月次 CSV より少し古い。
  そのため「区内に何件あるか」の数は東京都 CSV を正とし、
  厚労省 CSV は掲載する事業所の中身を厚くするためだけに使う。

使い方:
  python3 tools/mhlw.py --refresh      # CSV を取り直す
  python3 tools/mhlw.py --list         # 取得済みの件数と列を表示
"""
import csv
import io
import json
import pathlib
import re
import sys
import urllib.request

INDEX = "https://www.mhlw.go.jp/stf/kaigo-kouhyou_opendata.html"
SOURCE = "厚生労働省「介護サービス情報公表システム」オープンデータ"
UA = ("Mozilla/5.0 (compatible; kaigonotonari-bot/1.0; "
      "+https://kaigonotonari.com/)")
CACHE = pathlib.Path(__file__).parent / "cache" / "mhlw"

# サイトのカテゴリ → 厚労省のサービス種類コード
CODES = {
    "houmon-kaigo": "110",
    "houmon-kango": "130",
    "day-service": "150",
    "short-stay": "210",
    "fukushi-yogu": ("170", "410"),   # 貸与 と 特定販売
}


def _get(url: str, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "ja"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def csv_urls() -> dict:
    """一覧ページから サービス種類コード → CSV の URL を拾う。

    ファイル名に出力日時が入っていて年2回変わるため、直書きしない。
    """
    page = _get(INDEX, timeout=120).decode("utf-8", "replace")
    out = {}
    for m in re.finditer(r'href="([^"]*jigyosho_(\d{3})_all_[^"]*\.csv)"', page):
        href, code = m.group(1), m.group(2)
        if not href.startswith("http"):
            href = "https://www.mhlw.go.jp" + href
        out.setdefault(code, href)
    if not out:
        raise SystemExit("厚労省 CSV のリンクが見つかりません。ページ構成が変わった可能性があります。")
    return out


def refresh(codes=None):
    """必要なサービス種類ぶんだけ CSV を取り直す。"""
    want = set(codes or [c for v in CODES.values()
                         for c in ((v,) if isinstance(v, str) else v)])
    urls = csv_urls()
    CACHE.mkdir(parents=True, exist_ok=True)
    got = []
    for code in sorted(want):
        if code not in urls:
            print(f"   × {code}: 一覧にリンクがありません")
            continue
        raw = _get(urls[code])
        (CACHE / f"{code}.csv").write_bytes(raw)
        got.append(code)
        print(f"   {code}: {len(raw) / 1e6:.1f}MB  {urls[code].rsplit('/', 1)[-1]}")
    (CACHE / "_urls.json").write_text(
        json.dumps(urls, ensure_ascii=False, indent=1), encoding="utf-8")
    return got


def _rows(code: str):
    p = CACHE / f"{code}.csv"
    if not p.exists():
        return []
    return list(csv.DictReader(io.StringIO(
        p.read_text(encoding="utf-8-sig"))))


DAY_ORDER = ["平日", "土曜日", "日曜日", "祝日"]


def _days(s: str):
    """「平日,土曜日,祝日」→ ['平日','土曜日','祝日']。順序をそろえる。"""
    got = [d.strip() for d in (s or "").split(",") if d.strip()]
    known = [d for d in DAY_ORDER if d in got]
    return known


def _cap(s: str):
    """定員。0 は「該当なし・未記載」の意味で使われているので空にする。"""
    s = (s or "").strip()
    if not s.isdigit():
        return None
    n = int(s)
    return n if n > 0 else None


def _url(s: str):
    s = (s or "").strip()
    return s if s.startswith("http") else ""


_INDEX_CACHE = {}


def index(cat: str) -> dict:
    """カテゴリの 事業所番号 → 補える項目 の辞書を返す。

    福祉用具のように2つのサービス種類を束ねる場合は、両方を重ねる
    （同じ事業所番号なら後勝ちではなく、埋まっているほうを残す）。
    """
    if cat in _INDEX_CACHE:
        return _INDEX_CACHE[cat]
    codes = CODES.get(cat)
    if not codes:
        _INDEX_CACHE[cat] = {}
        return {}
    if isinstance(codes, str):
        codes = (codes,)
    out = {}
    for code in codes:
        for r in _rows(code):
            ident = (r.get("事業所番号") or "").strip()
            if not ident:
                continue
            cur = out.setdefault(ident, {})
            for key, val in (("url", _url(r.get("URL"))),
                             ("days", _days(r.get("利用可能曜日"))),
                             ("capacity", _cap(r.get("定員"))),
                             ("lat", (r.get("緯度") or "").strip()),
                             ("lng", (r.get("経度") or "").strip())):
                if val and not cur.get(key):
                    cur[key] = val
    _INDEX_CACHE[cat] = out
    return out


def enrich(items, cat: str):
    """取り込み済みのレコード配列に、厚労省 CSV の項目を足す。

    突き合わせは事業所番号。厚労省側の基準日が数か月古いため、
    新しい事業所は一致しないことがある。その場合は足さずに空のままにする
    （推測で埋めない）。戻り値は一致した件数。
    """
    idx = index(cat)
    hit = 0
    for it in items:
        add = idx.get((it.get("identifier") or "").strip())
        if not add:
            continue
        hit += 1
        if add.get("url"):
            it["url"] = add["url"]
        if add.get("days"):
            it["days"] = add["days"]
        if add.get("capacity"):
            it["capacity"] = add["capacity"]
        if add.get("lat") and add.get("lng"):
            it["lat"], it["lng"] = add["lat"], add["lng"]
    return hit


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--refresh" in args:
        print("厚労省 オープンデータを取得します。")
        refresh()
    for cat in CODES:
        idx = index(cat)
        n_url = sum(1 for v in idx.values() if v.get("url"))
        n_day = sum(1 for v in idx.values() if v.get("days"))
        n_cap = sum(1 for v in idx.values() if v.get("capacity"))
        print(f"  {cat:14} {len(idx):6}件  URL {n_url:6}  曜日 {n_day:6}  定員 {n_cap:6}")
