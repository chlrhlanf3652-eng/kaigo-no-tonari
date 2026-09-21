# -*- coding: utf-8 -*-
"""高齢者可賃貸の市区町村ページ本文（v3）。

「なぜ断られるのか」「5つの準備」「サ高住との比較」は区が変わっても同じ内容なので
/guide/ に移し、ここには「その区が用意している居住支援」と
「その区の制度の穴をどう埋めるか」だけを残す。
差し込み口は @@WARD@@ / @@MADOGUCHI@@ / @@NEIGHBORS@@ / @@BODY@@ /
@@COVERS@@ / @@COVER_NOTE@@ / @@STEPS@@ / @@LEAD@@ / @@CLOSE@@。
"""

CHINTAI = """<h2 id="s1">@@WARD@@で高齢の親の部屋を探すとき</h2>
    <p>@@LEAD@@</p>
    <div class="note">年齢を理由に断られる仕組みと、申し込み前にそろえる5つの準備は<a href="{{ROOT}}guide/koreisha-chintai-kotowarareru/">高齢者が賃貸を断られる理由と対策</a>にまとめました。街の不動産店を回る前に読んでおくと、断られる回数が減ります。</div>

    <h2 id="s2">@@WARD@@の居住支援</h2>
    @@BODY@@

    <h2 id="s3">@@WARD@@の支援は、貸主の不安のどこに届くか</h2>
    <p>@@COVER_NOTE@@</p>
    <div class="tw">
    <table>
      <thead><tr><th style="width:26%">貸主の不安</th><th style="width:10%">@@WARD@@</th><th>区の制度でどこまで手当てできるか</th></tr></thead>
      <tbody>
@@COVERS@@
      </tbody>
    </table>
    </div>
    <p class="tiny">◎＝区の制度で直接手当てできる／○＝窓口経由で手当てできる／△＝個別相談／×＝自分で用意する必要がある。区の公表情報をもとに当サイトが整理したものです。</p>

    <h2 id="s4">@@WARD@@での進め方</h2>
    <p>上の表の埋まり方で、動く順番が変わります。@@WARD@@の場合はこうなります。</p>
    <ol class="steps">
@@STEPS@@
    </ol>

    <h2 id="s5">相談先・サービス一覧</h2>
    {{LISTING}}

    <h2 id="s6">@@WARD@@で見つからないとき</h2>
    <p>@@CLOSE@@</p>
    <p>一般の賃貸にこだわらない場合は<a href="{{ROOT}}guide/sakoju-toha/">サ高住と老人ホームの違い</a>もご覧ください。地域を広げるなら@@NEIGHBORS@@まで範囲を伸ばすと選択肢が増えますが、@@WARD@@の居住支援は@@WARD@@内の物件が対象なので、区を越えるときは転居先の区の窓口にも相談してください。</p>
    <div class="note">引っ越し前に家財を減らしておくと、内見時の印象も退去時の不安材料も軽くなります。<a href="{{ROOT}}shukatsu/#seizen">生前整理の進め方</a>もあわせてどうぞ。</div>

    <h2 id="s7">よくある質問</h2>
    {{FAQ}}
"""
