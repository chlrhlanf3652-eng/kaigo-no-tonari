# -*- coding: utf-8 -*-
"""CSV の中身を見て、どの列が使えるかを確かめるための下見用。"""
import collections, io, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import fetch_tokyo_opendata as T

rows = T.load_rows()
for svc in ["短期入所生活介護", "福祉用具貸与", "特定福祉用具販売"]:
    sub = [r for r in rows if (r.get("サービス種類") or "").strip() == svc
           and (r.get("状態") or "").strip() == "指定"]
    print("\n===", svc, len(sub), "件（指定中）")
    for col in ["事業所種別名", "法人種別名"]:
        c = collections.Counter((r.get(col) or "").strip() for r in sub)
        print("  ", col, dict(c.most_common(12)))
    print("   例:", [(r["事業所名"], r.get("事業所種別名"), r.get("指定年月日")) for r in sub[:3]])

# 貸与と販売で同じ事業所番号が重なるか
lend = {(r.get("事業所番号") or "").strip() for r in rows
        if (r.get("サービス種類") or "").strip() == "福祉用具貸与"
        and (r.get("状態") or "").strip() == "指定"}
sell = {(r.get("事業所番号") or "").strip() for r in rows
        if (r.get("サービス種類") or "").strip() == "特定福祉用具販売"
        and (r.get("状態") or "").strip() == "指定"}
print("\n貸与のみ", len(lend - sell), "／販売のみ", len(sell - lend), "／両方", len(lend & sell))
