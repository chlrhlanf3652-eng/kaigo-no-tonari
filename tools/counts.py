# -*- coding: utf-8 -*-
"""区内の訪問介護事業所数の目安。

複数の介護情報サイトで件数が違うため、区ごとに別々のソースを混ぜると
「23区の比較表」が成り立たなくなる。そこで全区を LIFULL介護 の掲載件数で
そろえ、ページ上は「約○件」と書いて出典を明記する。
出典: LIFULL介護 各区の訪問介護一覧（2026-09-21 確認）
"""
COUNTS = {
    "chiyoda": 17, "chuo": 33, "minato": 65, "shinjuku": 76, "bunkyo": 31,
    "taito": 54, "sumida": 58, "koto": 76, "shinagawa": 53, "meguro": 48,
    "ota": 125, "setagaya": 219, "shibuya": 44, "nakano": 72, "suginami": 132,
    "toshima": 61, "kita": 82, "arakawa": 48, "itabashi": 143, "nerima": 180,
    "adachi": 194, "katsushika": 136, "edogawa": 137,
}

# 区が独自の愛称を使っていて、一覧サイトの表記だけでは足りないもの
MADOGUCHI_OVERRIDE = {
    "ota": "地域包括支援センター（さわやかサポート）",
}
