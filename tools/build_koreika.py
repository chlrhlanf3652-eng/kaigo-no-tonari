# -*- coding: utf-8 -*-
"""公的統計から区ごとの高齢化データを組み立てて cache/stats/koreika.json に書く。

入力（tools/cache/stats/ に置く。取得は手元のPCから）:
  age3.csv        東京都統計部 第3-1表 区市町村、年齢3区分別人口
  age5.csv        東京都統計部 第7表  区市町村、年齢(5歳階級)別人口
  geppou0806.xls  東京都福祉局 介護保険事業状況報告（月報）令和8年6月分

23区の抽出は地域コード 13101〜13123 で行う（合計行 13000/13100 を巻き込まない）。
"""
import csv
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from wards import WARDS

STATS = pathlib.Path(__file__).parent / "cache" / "stats"
CODE2ID = {int(w["code"]): wid for wid, w in WARDS.items()}


def _read_csv(name):
    raw = (STATS / name).read_bytes()
    for enc in ("utf-8-sig", "cp932"):
        try:
            t = raw.decode(enc)
            if "千代田区" in t:
                return list(csv.reader(io.StringIO(t)))
        except UnicodeDecodeError:
            pass
    raise SystemExit(f"{name}: 文字コードを判定できません")


def population():
    """65歳以上人口・総人口（第3-1表）と75歳以上人口（第7表）。"""
    out = {}
    for r in _read_csv("age3.csv"):
        if len(r) < 10 or r[0] != "4" or not r[1].isdigit():
            continue
        code = int(r[1])
        if code not in CODE2ID:
            continue
        young, work, old = int(r[3]), int(r[6]), int(r[9])
        out[CODE2ID[code]] = {"pop": young + work + old, "p65": old}

    OLD5 = ("75～79", "80～84", "85～89", "90～94", "95～99", "100以上")
    p75 = {}
    for r in _read_csv("age5.csv"):
        if len(r) < 6 or r[0] != "4" or not r[1].isdigit():
            continue
        code = int(r[1])
        if code not in CODE2ID or r[4] not in OLD5:
            continue
        p75[CODE2ID[code]] = p75.get(CODE2ID[code], 0) + int(r[5])
    for wid, v in out.items():
        v["p75"] = p75.get(wid)
    return out


def ninteisha():
    """第1号被保険者数と、第1号被保険者の要介護・要支援認定者数（月報）。"""
    import xlrd
    b = xlrd.open_workbook(str(STATS / "geppou0806.xls"))
    name2id = {w["name"]: wid for wid, w in WARDS.items()}

    hihokensha = {}
    sh = b.sheet_by_name("第１号被保険者数")
    for r in range(sh.nrows):
        nm = str(sh.cell_value(r, 0)).strip()
        if nm in name2id:
            hihokensha[name2id[nm]] = int(sh.cell_value(r, 4))   # 当月末現在 合計

    nintei = {}
    sh = b.sheet_by_name("要介護認定者数（男女計）")
    for r in range(sh.nrows):
        nm = str(sh.cell_value(r, 0)).strip()
        if nm not in name2id:
            continue
        # 列9〜15 =（再掲）第1号被保険者の 要支援1〜要介護5
        parts = [sh.cell_value(r, c) for c in range(9, 16)]
        light = sum(int(v) for v in parts[:2])       # 要支援1・2
        heavy = sum(int(v) for v in parts[2:])       # 要介護1〜5
        nintei[name2id[nm]] = {"shien": light, "kaigo": heavy,
                               "nintei": light + heavy}
    return hihokensha, nintei


def main():
    pop = population()
    hi, ni = ninteisha()
    out = {}
    for wid in WARDS:
        if wid not in pop or wid not in hi or wid not in ni:
            print(f"   × {wid}: データ不足のため除外")
            continue
        d = dict(pop[wid])
        d.update(ni[wid])
        d["hihokensha"] = hi[wid]
        d["rate65"] = round(d["p65"] / d["pop"] * 100, 1)
        d["rate75"] = round(d["p75"] / d["pop"] * 100, 1) if d["p75"] else None
        d["ninteiritsu"] = round(d["nintei"] / d["hihokensha"] * 100, 1)
        out[wid] = d

    STATS.mkdir(parents=True, exist_ok=True)
    (STATS / "koreika.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{len(out)}区 書き出し\n")
    print(f"{'区':10}{'総人口':>10}{'65歳以上':>10}{'高齢化率':>8}"
          f"{'75歳以上':>10}{'1号被保険':>10}{'認定者':>9}{'認定率':>8}")
    for wid, d in out.items():
        print(f"{WARDS[wid]['name']:10}{d['pop']:10,}{d['p65']:10,}"
              f"{d['rate65']:7.1f}%{d['p75']:10,}{d['hihokensha']:10,}"
              f"{d['nintei']:9,}{d['ninteiritsu']:7.1f}%")


if __name__ == "__main__":
    main()
