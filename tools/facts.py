# -*- coding: utf-8 -*-
"""区ごとの「その区でしか成り立たない事実」を文章にする（一覧ページの内訳の冒頭）。

テンプレートの説明文は区が変わっても同じなので、区ページどうしの本文がよく似てしまう。
ここでは掲載事業所の集計（町域・運営法人・日曜の提供）と、同じサービスの23区比較から
その区だけの文を作る。数字はすべて tools/cache の掲載データから数える。
"""
import collections
import json
import pathlib

import linkgrid as LG

CACHE = pathlib.Path(__file__).parent / "cache"
_sun = {}


def _sunday_share(cat):
    """23区それぞれの「曜日が分かる掲載事業所のうち日曜も提供する割合」。"""
    if cat not in _sun:
        prefix = LG.CATS[cat][0]
        out = {}
        for p in CACHE.glob(f"{prefix}*.json"):
            wid = p.stem[len(prefix):]
            if wid not in LG.counts(cat):
                continue
            rec = json.loads(p.read_text(encoding="utf-8"))
            known = [it for it in rec.get("items", []) if it.get("days")]
            if len(known) >= 3:
                out[wid] = sum("日曜日" in it["days"] for it in known) / len(known)
        _sun[cat] = out
    return _sun[cat]


def facts(cat, wid, ward, items, label):
    n = len(items)
    towns = collections.Counter(it.get("_town") for it in items if it.get("_town"))
    kinds = collections.Counter(it.get("_kind") for it in items if it.get("_kind"))
    parts = []
    top = [(t, c) for t, c in towns.most_common(3) if c >= 2]
    if len(top) >= 2:
        listed = "、".join(f"{t}（{c}件）" for t, c in top)
        parts.append(f"掲載している{n}件を町域別に見ると、多いのは{listed}です。")
    elif towns:
        parts.append(f"掲載している{n}件は、{len(towns)}つの町域に分かれています。")
    if kinds:
        k, c = kinds.most_common(1)[0]
        if c == n:
            parts.append(f"{n}件すべてを{k}が運営しています。")
        else:
            parts.append(f"運営法人は{k}が{c}件で最も多くなっています。")
    known = [it for it in items if it.get("_days")]
    share = _sunday_share(cat)
    if len(known) >= 3 and wid in share:
        sun = sum("日曜日" in it["_days"] for it in known)
        rank = 1 + sum(1 for v in share.values() if v > share[wid])
        pct = round(share[wid] * 100)
        if rank <= 5:
            where = f"23区の{label}のなかで{rank}番目に高い割合です。"
        elif rank >= len(share) - 5:
            where = f"23区の{label}のなかでは低いほうです（{len(share)}区中{rank}位）。"
        else:
            where = f"23区のなかでは{rank}番目の割合になります。"
        parts.append(f"日曜日もサービスを提供しているのは、曜日が分かる{len(known)}件のうち{sun}件（{pct}％）で、{where}")
    return "<p>" + "".join(parts) + "</p>" if parts else ""
