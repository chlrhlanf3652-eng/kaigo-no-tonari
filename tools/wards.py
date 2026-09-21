# -*- coding: utf-8 -*-
"""東京23区の基礎データ（収集・生成の共通レジストリ）

  id       … サイト内のURLに使う識別子
  name     … 表示名
  hp       … ハートページナビのエリアslug（区名と一致しないものがある）
  code     … 全国地方公共団体コードの下3桁ではなく5桁（町域一覧の取得に使う）
  near     … 近隣エリアの内部リンク先。地理的に隣接する区を並べる
"""

WARDS = {
    "chiyoda":   dict(name="千代田区",  hp="chiyoda",     code="13101",
                      near=["chuo", "minato", "shinjuku", "bunkyo", "taito"]),
    "chuo":      dict(name="中央区",    hp="tokyochuo",   code="13102",
                      near=["chiyoda", "minato", "taito", "sumida", "koto"]),
    "minato":    dict(name="港区",      hp="minato",      code="13103",
                      near=["chiyoda", "chuo", "shinagawa", "shibuya", "shinjuku"]),
    "shinjuku":  dict(name="新宿区",    hp="shinjuku",    code="13104",
                      near=["chiyoda", "minato", "shibuya", "nakano", "toshima", "bunkyo"]),
    "bunkyo":    dict(name="文京区",    hp="bunkyo",      code="13105",
                      near=["chiyoda", "shinjuku", "toshima", "kita", "arakawa", "taito"]),
    "taito":     dict(name="台東区",    hp="taito",       code="13106",
                      near=["chiyoda", "chuo", "bunkyo", "arakawa", "sumida", "adachi"]),
    "sumida":    dict(name="墨田区",    hp="sumida",      code="13107",
                      near=["chuo", "taito", "koto", "arakawa", "adachi", "katsushika"]),
    "koto":      dict(name="江東区",    hp="koto",        code="13108",
                      near=["chuo", "sumida", "edogawa", "shinagawa", "katsushika"]),
    "shinagawa": dict(name="品川区",    hp="shinagawa",   code="13109",
                      near=["minato", "meguro", "ota", "koto", "setagaya"]),
    "meguro":    dict(name="目黒区",    hp="meguro",      code="13110",
                      near=["shinagawa", "ota", "setagaya", "shibuya"]),
    "ota":       dict(name="大田区",    hp="tokyoota",    code="13111",
                      near=["shinagawa", "meguro", "setagaya", "minato", "shibuya", "koto"]),
    "setagaya":  dict(name="世田谷区",  hp="setagaya",    code="13112",
                      near=["meguro", "shibuya", "suginami", "nakano", "ota", "komae"]),
    "shibuya":   dict(name="渋谷区",    hp="shibuya",     code="13113",
                      near=["shinjuku", "minato", "meguro", "setagaya", "nakano"]),
    "nakano":    dict(name="中野区",    hp="tokyonakano", code="13114",
                      near=["shinjuku", "shibuya", "setagaya", "suginami", "nerima", "toshima"]),
    "suginami":  dict(name="杉並区",    hp="suginami",    code="13115",
                      near=["nakano", "setagaya", "nerima", "shibuya", "mitaka", "musashino"]),
    "toshima":   dict(name="豊島区",    hp="toshima",     code="13116",
                      near=["shinjuku", "bunkyo", "kita", "itabashi", "nerima", "nakano"]),
    "kita":      dict(name="北区",      hp="tokyokita",   code="13117",
                      near=["bunkyo", "toshima", "itabashi", "arakawa", "adachi"]),
    "arakawa":   dict(name="荒川区",    hp="arakawa",     code="13118",
                      near=["bunkyo", "taito", "kita", "sumida", "adachi"]),
    "itabashi":  dict(name="板橋区",    hp="itabashi",    code="13119",
                      near=["nerima", "kita", "toshima", "adachi", "shinjuku", "bunkyo"]),
    "nerima":    dict(name="練馬区",    hp="nerima",      code="13120",
                      near=["itabashi", "toshima", "nakano", "suginami", "kita", "shinjuku"]),
    "adachi":    dict(name="足立区",    hp="adachi",      code="13121",
                      near=["kita", "arakawa", "sumida", "katsushika", "itabashi", "taito"]),
    "katsushika": dict(name="葛飾区",   hp="katsushika",  code="13122",
                      near=["adachi", "sumida", "edogawa", "koto", "arakawa"]),
    "edogawa":   dict(name="江戸川区",  hp="edogawa",     code="13123",
                      near=["koto", "katsushika", "sumida", "adachi", "chuo", "taito"]),
}

# 町域一覧に混ざる、人が住んでいない区画。長尾のキーワードとして意味がないので落とす。
TOWN_EXCLUDE = ("公園", "空港", "ふ頭", "埠頭")
