#!/usr/bin/env python3
"""
かいごのとなり — IndexNow でのURL送信

新しいページを公開しても、検索エンジンが自分でクロールしに来るまでには時間がかかる。
IndexNow は「このURLを更新した」と直接通知する仕組みで、Bing・Yandex・Naver・Seznam
などが対応している（Google は非対応なので、Google 側は sitemap と Search Console を使う）。

事前準備はサイト直下に <key>.txt を置き、その中身をキーと同じ文字列にしておくだけ。
検索エンジンはそのファイルを取りに来て、送信者がサイトの所有者か確認する。

使い方:
  python3 indexnow.py                # sitemap.xml の全URLを送信
  python3 indexnow.py /houmon-kaigo/tokyo/nerima/   # 個別に送信
"""
import json
import pathlib
import re
import sys
import urllib.request

BASE = pathlib.Path(__file__).parent
KEY = "ea66b52cf36712654f39c6b036c8b3d5"
ORIGIN = json.loads((BASE / "data" / "site.json")
                    .read_text(encoding="utf-8"))["site"]["url"].rstrip("/")
HOST = ORIGIN.split("//", 1)[1]
ENDPOINT = "https://api.indexnow.org/IndexNow"


def urls_from_sitemap():
    xml = (BASE / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>(.*?)</loc>", xml)


def main():
    args = sys.argv[1:]
    urls = [a if a.startswith("http") else ORIGIN + a for a in args] or urls_from_sitemap()
    # 1リクエスト1万件まで。念のため500件ずつに分ける。
    for i in range(0, len(urls), 500):
        chunk = urls[i:i + 500]
        body = json.dumps({"host": HOST, "key": KEY,
                           "keyLocation": f"{ORIGIN}/{KEY}.txt",
                           "urlList": chunk}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                # 200 = 受理 / 202 = 受理（キー確認待ち）
                print(f"IndexNow {r.status} {r.reason}  {len(chunk)} URLs")
        except Exception as e:
            print(f"IndexNow 送信失敗: {e}")
            return 1
    for u in urls:
        print("  " + u)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
