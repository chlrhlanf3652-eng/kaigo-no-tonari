# -*- coding: utf-8 -*-
"""訪問介護の市区町村ページ本文テンプレート（v2）。

v1 では、料金のしくみ・頼めること・選び方・認定の流れを各区ページに
そのまま載せていた。区が変わっても中身は1文字も変わらないので、
20区に展開した時点で「地域名だけ差し替えた量産ページ」になっていた。
（実測でページ間の類似度は平均90.2％）

v2 では、区によって変わらない説明を /guide/ 配下の独立した記事に移し、
市区町村ページには「その区でしか成り立たない事実」だけを残す。

  - 掲載事業所の一覧（区ごとに別物）
  - 掲載事業所の所在町域・運営法人の種別・受付体制の内訳（集計値）
  - その区の相談窓口の呼び名と設置数
  - 区内の町域一覧

差し込み口は %(...)s。
"""

HOUMON_KAIGO = """<h2 id="s1">%(ward)sで訪問介護を探すとき、最初に押さえること</h2>
    <p>%(ward)sには訪問介護事業所が%(total)d件あります。%(scale_note)s絞り込みの軸は距離ではなく、<strong>希望する曜日・時間帯にヘルパーを確保できるか</strong>です。</p>
    <div class="note">
      <strong>%(ward)sの相談窓口は「%(center)s」%(center_count_label)s</strong><br>
      %(center_note)s要介護認定の申請方法、ケアマネジャー探し、事業所の選び方まで無料で相談できます。担当の窓口は<strong>お住まいの町名で決まります</strong>ので、連絡前にご自宅の町域を確認しておくと話が早く進みます。
    </div>
    <p class="tiny">はじめて介護保険を使う方は、<a href="{{ROOT}}guide/youkaigo-nintei/">要介護認定の申請から利用開始までの流れ</a>を先にご覧ください。申請から実際にサービスが始まるまで、1か月から1か月半かかります。</p>

    <h2 id="s2">%(ward)sの訪問介護事業所一覧</h2>
    {{LISTING}}

    <h2 id="s3">掲載%(n)d事業所の内訳</h2>
    %(facts)s

    <h3>所在町域</h3>
    <p>訪問介護は、事業所から車や自転車で行ける範囲が実質的な対応エリアになります。%(ward)s内は%(townc)dの町域に分かれており、</p>
    <div class="tw">
    <table>
      <thead><tr><th style="width:34%%">町域</th><th>掲載事業所</th></tr></thead>
      <tbody>
%(dist)s
      </tbody>
    </table>
    </div>

    <h3>運営法人の種別</h3>
    <p>%(org_note)s</p>
    <div class="tw">
    <table>
      <thead><tr><th style="width:34%%">法人の種別</th><th style="width:14%%">件数</th><th>傾向</th></tr></thead>
      <tbody>
%(orgs)s
      </tbody>
    </table>
    </div>
    <p class="tiny">詳しくは<a href="{{ROOT}}guide/jigyosho-erabikata/">訪問介護事業所の選び方</a>で解説しています。</p>

    <h3>ヘルパーが来られる曜日</h3>
    <p>%(recv_note)s最初に詰まるのは<strong>曜日が合うヘルパーを確保できるか</strong>で、%(ward)sでもここが合わないと事業所が近くても話が進みません。</p>
    <div class="tw">
    <table>
      <thead><tr><th style="width:34%%">サービス提供日</th><th style="width:14%%">件数</th><th>こんな方に</th></tr></thead>
      <tbody>
%(recv)s
      </tbody>
    </table>
    </div>
    <p class="tiny">%(hours_note)s</p>

    <h2 id="s4">%(ward)sでの自己負担の目安</h2>
    <p>東京23区は1単位11.40円の「1級地」。1割負担なら、身体介護20〜30分が約279円、生活援助20〜45分が約204円です。ほかの時間区分や2割・3割負担の金額は<a href="{{ROOT}}guide/houmon-kaigo-ryokin/">訪問介護の料金</a>に早見表でまとめました。</p>

    <h2 id="s5">問い合わせの前に確認しておくこと</h2>
    <p>%(ward)sの事業所に電話をかける前に、次の3点を手元に用意しておくと、1回の電話で話が決まります。</p>
    <ol class="steps">
      <li><b>ご自宅の町名・番地</b>同じ%(ward)s内でも、事業所によって対応する町域が違います。上の一覧の「対応エリア」は目安なので、住所を伝えて確認するのが確実です。</li>
      <li><b>必要な曜日と時間帯</b>朝の起床介助と夕方の食事介助は依頼が集中します。「火・木の朝7時台」のように具体的に伝えてください。</li>
      <li><b>要介護認定の状況</b>認定済みなら要介護度を、申請中ならその旨を。未申請なら、事業所より先に%(center)sへ相談してください。</li>
    </ol>
    <div class="note">ヘルパーに頼めるのは<strong>利用者本人の日常生活に必要な支援</strong>だけです。家族分の家事、草むしり、大掃除などは介護保険では頼めません。詳しくは<a href="{{ROOT}}guide/houmon-kaigo-dekirukoto/">ヘルパーに頼めること・頼めないこと</a>をご覧ください。保険外の用事は、<a href="{{ROOT}}kaji-daiko/tokyo/%(id)s/">家事代行</a>や<a href="{{ROOT}}takuhai-bento/tokyo/%(id)s/">宅配弁当</a>と組み合わせるのが現実的です。</div>

    <h2 id="s6">よくある質問</h2>
    {{FAQ}}
"""
