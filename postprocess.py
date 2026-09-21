#!/usr/bin/env python3
"""
かいごのとなり — 生成後の後処理：未作成ページへのリンクを「準備中」表示に落とす

サイト構造としては先に置いておきたいが、中身がまだ無いページがある。
そこへリンクを張ったままにすると 404 を量産し、検索評価にも利用者にも悪い。
かといってリンクごと消すと、構造を作り直すたびに手で戻すことになる。

そこで、生成された HTML を走査し、
  「サイト内のディレクトリへのリンクで、その index.html が存在しないもの」
だけを <span class="soon-link"> に置き換える。ページを作れば自動でリンクに戻る。

使い方（ビルドの最後に実行する）:
  python3 build_hubs.py && python3 build.py && python3 postprocess.py && python3 build_sitemap.py
"""
import pathlib
import posixpath
import re
import sys

BASE = pathlib.Path(__file__).parent
SKIP = {"dist-artifact", "node_modules", ".git", ".github"}

A_TAG = re.compile(r'<a\b([^>]*?)href="([^"#:]*?/)"([^>]*)>(.*?)</a>', re.S)


def pages():
    for p in BASE.rglob("index.html"):
        if not (set(p.relative_to(BASE).parts) & SKIP):
            yield p


def main():
    built = {str(p.parent.relative_to(BASE)).replace("\\", "/").strip(".").strip("/")
             for p in pages()}
    changed = total = fallbacks = 0
    missing = set()

    for p in pages():
        here = str(p.parent.relative_to(BASE)).replace("\\", "/").strip(".").strip("/")
        html = p.read_text(encoding="utf-8")

        def repl(m):
            nonlocal total, fallbacks
            before, href, after, inner = m.groups()
            target = posixpath.normpath(posixpath.join(here, href)).lstrip("./")
            target = "" if target == "." else target
            if target in built:
                return m.group(0)
            missing.add(target)
            total += 1
            cls = re.search(r'class="([^"]*)"', before + after)
            extra = f' {cls.group(1)}' if cls else ""

            # 市区町村ページが未作成でも、上位（都道府県 → カテゴリ）が
            # あるならそこへ逃がす。行き止まりにせず、必ずどこかに着地させる。
            up = target.split("/")
            while len(up) > 1:
                up.pop()
                cand = "/".join(up)
                if cand in built and cand != here:
                    rel = posixpath.relpath(cand, here or ".")
                    rel = "" if rel == "." else rel + "/"
                    fallbacks += 1
                    return (f'<a class="soon-link{extra}" href="{rel}">{inner}'
                            f'<em class="soon-tag">エリア準備中</em></a>')

            return (f'<span class="soon-link{extra}" aria-disabled="true">{inner}'
                    f'<em class="soon-tag">準備中</em></span>')

        out = A_TAG.sub(repl, html)
        if out != html:
            p.write_text(out, encoding="utf-8")
            changed += 1

    print(f"postprocess: {changed} pages updated, {total} links marked 準備中 "
          f"({fallbacks} は上位ページへ誘導)")
    if missing:
        print("\n未作成（リンクを準備中表示にしたページ）:")
        for m in sorted(missing):
            print(f"  /{m}/")

    # 念のため、置換後にサイト内リンク切れが残っていないか確認する
    left = []
    for p in pages():
        here = str(p.parent.relative_to(BASE)).replace("\\", "/").strip(".").strip("/")
        for m in A_TAG.finditer(p.read_text(encoding="utf-8")):
            t = posixpath.normpath(posixpath.join(here, m.group(2))).lstrip("./")
            t = "" if t == "." else t
            if t not in built:
                left.append(f"{p}: {m.group(2)}")
    if left:
        print("\n残っているリンク切れ:")
        print("\n".join(left))
        sys.exit(1)
    print("\nリンク切れ: なし")


if __name__ == "__main__":
    main()
