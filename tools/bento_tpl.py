# -*- coding: utf-8 -*-
"""宅配弁当の市区町村ページ本文（v2）。

高齢者向け配食の一般論・食形態・チェックポイントは /guide/ に移し、
ここには「その区に配達できる店舗」「担当店の実際の価格」「区の配食事業」だけを残す。
"""

BENTO = """<h2 id="s1">%(ward)sに配達できるのは%(n)d件</h2>
    <p>高齢者向けの配食サービスは、事業者ごとに配達できる範囲が細かく分かれています。%(ward)sの場合、区内に配達を公表しているのは%(n)d件。%(brand_note)s</p>
    <div class="note">高齢者専門の配食が一般の宅食と違うのは、<strong>手渡しによる安否確認</strong>、<strong>やわらか食・ムース食</strong>、<strong>治療食への対応</strong>の3点です。この3つが要るかどうかで選び方が変わります。詳しくは<a href="{{ROOT}}guide/haishoku-erabikata/">配食サービスの選び方</a>をご覧ください。</div>

    <h2 id="s2">%(ward)sに配達するサービス一覧</h2>
    {{LISTING}}

    <h2 id="s3">掲載%(n)d件の内訳</h2>
    <p>%(inside_note)s%(ward)s内でも店舗によって「区内全域」と「一部地域を除く」が混在するため、番地まで伝えて確認するのが確実です。</p>
    <div class="tw">
    <table>
      <thead><tr><th style="width:38%%">サービス</th><th style="width:20%%">店舗の所在地</th><th>配達できる範囲</th></tr></thead>
      <tbody>
%(shoplist)s
      </tbody>
    </table>
    </div>
    <p class="tiny">※区外に店舗がある場合でも、配達エリアに入っていれば利用できます。逆に区内の店舗でも一部の町域に配達できないことがあります。</p>

    <h2 id="s4">%(ld)sの料金</h2>
    <p>まごころ弁当と宅配クック123は店舗ごとに料金が違い、%(ward)s担当店の価格は公式サイトに出ていません。料金を公開しているライフデリについて、%(ward)sを担当する<strong>%(ld)s</strong>の価格を掲載します。</p>
    <div class="note"><strong>専門食の価格はライフデリ全店共通ですが、普通食だけは店舗ごとに違います。</strong>%(ward)sは普通食のおかずのみが%(plain)d円、ごはんセットが%(rice)d円です。%(price_rank)s</div>
    <div class="tw">
    <table>
      <caption class="tiny" style="text-align:left;padding-bottom:6px">%(ld)s の料金（2026年9月時点・1食あたり・税込）</caption>
      <thead><tr><th>食形態</th><th>おかずのみ</th><th>ごはんセット</th><th>こんな方に</th></tr></thead>
      <tbody>
%(prices)s
      </tbody>
    </table>
    </div>
    <p class="tiny">※食形態の違いと選び分けは<a href="{{ROOT}}guide/kaigoshoku-keitai/">介護食の形態と選び方</a>で解説しています。夕食のみ（ごはんセット%(rice)d円）を週5回で、1か月およそ%(month)s円前後です。</p>

    <h2 id="s5">%(ward)sの配食サービス（区の事業）</h2>
    %(gov_body)s
    <p class="tiny">なお民間の宅配弁当は<strong>介護保険の給付対象外</strong>で全額自己負担ですが、要介護認定がなくても使え、区分支給限度基準額の枠を消費しません。</p>

    <h2 id="s6">申し込む前に</h2>
    <p>%(ward)sの事業者に連絡する前に、次の2点だけ決めておくと1回の電話で済みます。</p>
    <ol class="steps">
      <li><b>ご自宅の町名・番地</b>同じ%(ward)s内でも「一部地域を除く」店舗があります。上の一覧の配達エリアは目安です。</li>
      <li><b>必要な食形態</b>普通食か、やわらか食か、治療食か。迷うときは試食を申し込んで、本人が食べきれるか確かめてください。</li>
    </ol>

    <h2 id="s7">よくある質問</h2>
    {{FAQ}}
"""
