# -*- coding: utf-8 -*-
"""ビルド後の全ページを見て、出してはいけないものが出ていないか確かめる。"""
import io, re, sys, pathlib, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
B = pathlib.Path(r"C:\Users\pc\dev\kaigo-no-tonari")
CATS = ["houmon-kaigo", "houmon-kango", "day-service", "short-stay",
        "fukushi-yogu", "takuhai-bento", "koreisha-chintai"]
tot_ext = 0
bad = []
for c in CATS:
    d = B / c / "tokyo"
    if not d.exists():
        continue
    ext = days = caps = 0
    for p in sorted(d.glob("*/index.html")):
        t = p.read_text(encoding="utf-8")
        ext += len(re.findall(r'class="ext"', t))
        days += t.count("サービス提供日") + t.count("営業日") + t.count("対応日")
        caps += t.count("公表されている定員")
        probs = []
        if "%(" in t or "{{" in t:
            probs.append("未展開")
        if re.search(r"<td[^>]*>\s*</td>|<th[^>]*>\s*</th>", t):
            probs.append("空セル")
        if "None" in t:
            probs.append("None")
        # 「年中無休」は事務所の休業日の値として正しく出るので、
        # 旧・受付体制の表の見出しだけを見る。
        if "電話の受付体制" in t or "<th>土日も受付</th>" in t:
            probs.append("旧・受付体制の表")
        if probs:
            bad.append((c, p.parent.name, probs))
    print("%-18s 外部リンク%5d  曜日見出し%3d  定員見出し%3d" % (c, ext, days, caps))
    tot_ext += ext
print("\n外部リンク合計:", tot_ext)
print("問題:", len(bad))
for x in bad[:15]:
    print("  ", x)
