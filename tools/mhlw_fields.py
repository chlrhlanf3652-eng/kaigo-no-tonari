# -*- coding: utf-8 -*-
"""厚労省オープンデータ由来の項目を、ページの表に整える共通部分。

5つのカテゴリで同じ言い方をするために、ここに集める。

【言い切らないための注意】
  利用可能曜日は「サービスを提供する曜日」であって、事務所の電話が
  つながる曜日ではない。ハートページ由来の休業日とは食い違うことが多く
  （掲載分で246件）、両者は別のものとして別の見出しで出す。

  定員は、通所介護と短期入所では人数・床数として読めるが、訪問介護や
  訪問看護では意味が揃っていない（300などの値が入る）ので使わない。

  通所介護の介護報酬上の規模区分（通常規模型・大規模型）は前年度の
  平均利用延人員で決まるもので、定員とは別物。混同させない書き方にする。
"""

DAY_BUCKETS = [
    ("日曜日も", "週末も家族が休めない場合の受け皿"),
    ("土曜日まで", "日曜だけ別の手段が要る"),
    ("平日のみ", "土日はほかと組み合わせる"),
    ("記載なし", "公表データに記載なし。直接ご確認を"),
]
DAY_ORDER = [b[0] for b in DAY_BUCKETS]
DAY_DESC = dict(DAY_BUCKETS)


def day_bucket(days):
    if not days:
        return "記載なし"
    if "日曜日" in days:
        return "日曜日も"
    if "土曜日" in days:
        return "土曜日まで"
    return "平日のみ"


def day_label(days):
    """一覧の1件ぶんの表示。「平日・土曜日・祝日」のように出す。"""
    return "・".join(days) if days else ""


def day_table(items):
    """サービス提供日の内訳を表の行にする。戻り値は (行HTML, 説明文, 日曜件数)。"""
    cnt = {}
    for it in items:
        b = day_bucket(it.get("_days"))
        cnt[b] = cnt.get(b, 0) + 1
    rows = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (lab, cnt[lab], DAY_DESC[lab]) for lab in DAY_ORDER if lab in cnt)
    n = len(items)
    sun = cnt.get("日曜日も", 0)
    sat = sun + cnt.get("土曜日まで", 0)
    none = cnt.get("記載なし", 0)
    if none == n:
        note = "公表データにサービス提供日の記載がある事業所がありませんでした。"
    else:
        note = ("掲載%d件のうち、日曜日も対応するところが%d件、"
                "土曜日まで含めると%d件です。" % (n, sun, sat))
        if none:
            note += "残る%d件は公表データに記載がありません。" % none
    return rows, note, sun, sat


CAP_BUCKETS_DAY = [
    (25, "25人以下", "顔ぶれが固定されやすい"),
    (40, "26〜40人", "都内でいちばん多い規模"),
    (9999, "41人以上", "種類は多いがにぎやか"),
]
CAP_BUCKETS_SHORT = [
    (10, "10床以下", "連休はすぐ埋まる"),
    (20, "11〜20床", "都内で標準的な規模"),
    (9999, "21床以上", "直前でも空きが出ることがある"),
]


def cap_table(items, buckets):
    """定員の内訳。記載のあるものだけを数え、無い件数は別に返す。"""
    cnt, known = {}, 0
    for it in items:
        c = it.get("_capacity")
        if not c:
            continue
        known += 1
        for lim, label, _ in buckets:
            if c <= lim:
                cnt[label] = cnt.get(label, 0) + 1
                break
    desc = {b[1]: b[2] for b in buckets}
    rows = "\n".join(
        '        <tr><th>%s</th><td class="num">%d件</td><td>%s</td></tr>'
        % (b[1], cnt[b[1]], desc[b[1]]) for b in buckets if b[1] in cnt)
    return rows, known
