# -*- coding: utf-8 -*-
"""公式サイトURLに、URLとして壊れているものが混ざっていないか確かめる。

厚労省CSVの URL 列は人が入力した値で、`https;//` のように
コロンがセミコロンになっているものがある。startswith("http") だけで
通すと、相対リンク扱いになってサイト内に存在しないパスを生む。
"""
import io, json, pathlib, re, sys, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
B = pathlib.Path(r"C:\Users\pc\dev\kaigo-no-tonari")
OK = re.compile(r"^https?://[^\s/]+\.[^\s/]+", re.I)

bad = []
tot = 0
for f in sorted((B / "data").glob("*.json")):
    if f.name == "site.json":
        continue
    d = json.loads(f.read_text(encoding="utf-8"))
    for it in d.get("items", []):
        u = (it.get("url") or "").strip()
        if not u:
            continue
        tot += 1
        if not OK.match(u):
            bad.append((f.stem, it.get("name", ""), u))
print("URL総数", tot, " 壊れているもの", len(bad))
for x in bad:
    print("  ", x)

# キャッシュ側にも同じものが残っていないか
cbad = 0
for f in (B / "tools" / "cache").glob("*.json"):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    for it in d.get("items", []):
        u = (it.get("url") or "").strip()
        if u and not OK.match(u):
            cbad += 1
            print("   cache:", f.stem, it.get("name"), u)
print("キャッシュ側", cbad)
