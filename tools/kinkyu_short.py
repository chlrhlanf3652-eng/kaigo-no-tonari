# -*- coding: utf-8 -*-
"""区が独自に行っている「緊急ショートステイ」「緊急一時保護」などの事業（介護保険の外）。

各区の公式サイト・公式PDFで確認したものだけを載せる（2026-11-16 確認）。
費用・電話番号は載せない（変わりやすく、区の案内で確認してもらう）。
日数は公式ページの記載をそのまま写せたものだけ入れる。
公式に見つからなかった区は None（「確認できなかった」と正直に書く）。
"""

CHECKED = "2026年11月16日"

# wid: (事業名, 対象のめやす, 日数, 申込・相談先, 公式URL)
DATA = {
    "chuo": ("緊急生活支援宿泊サービス（緊急ショートステイ）",
             "介護者の急な入院や葬儀への出席などで、ほかに介護する人がいない方など",
             "原則として1週間以内", "中央区役所（閉庁時は区立の特別養護老人ホームに直接）",
             "https://www.city.chuo.lg.jp/a0029/kenkouiryou/koureikaigo/zaitakuiryou/zaitakushienservice/nintei/syortosutei.html"),
    "shinjuku": ("高齢者緊急ショートステイ",
                 "区内在住の要支援・要介護認定者などで、介護する家族の急病・けが・親族の葬儀などで介護できない方",
                 "7日間", "高齢者支援課（ふだんはケアマネジャーを通して）",
                 "https://www.city.shinjuku.lg.jp/fukushi/file05_02_00023.html"),
    "bunkyo": ("緊急ショートステイ事業",
               "区内在住の要支援・要介護認定者などで、介護者が特別な理由で一時的に介護できなくなった方",
               "理由により5日・7日・30日", "区の案内に載っている施設に直接",
               "https://www.city.bunkyo.lg.jp/b020/p007738.html"),
    "koto": ("高齢者緊急ショートステイ「シルバーステイ」",
             "区内在住の65歳以上の方など（介護認定は不要。医療処置・感染症のある方は対象外）",
             "1回につき原則7日間（6泊7日）まで", "区の案内に載っている施設に直接",
             "https://www.city.koto.lg.jp/211103/fukushi/koresha/service/jisshi/67944.html"),
    "ota": ("高齢者緊急ショートステイ事業",
            "介護者の急病などで一時的に在宅生活が難しくなった要支援・要介護の方など（区が緊急性を認めた場合）",
            "原則7日以内", "担当のケアマネジャー（いなければ地域包括支援センター）を通して区へ",
            "https://www.city.ota.tokyo.jp/seikatsu/fukushi/kourei/handbook.files/R8handbook.pdf"),
    "setagaya": ("高齢者緊急一時宿泊",
                 "65歳以上で、介護保険では対応できない緊急の事情で家族が介護できない方",
                 "", "あんしんすこやかセンター、または総合支所保健福祉課",
                 "https://www.city.setagaya.lg.jp/02082/2410.html"),
    "shibuya": ("短期入所緊急利用",
                "要支援・要介護の認定を受けていて、切迫した事情で短期間の利用が必要になった方",
                "1回6日まで", "区の案内に載っている施設に直接（問い合わせは高齢者福祉課）",
                "https://www.city.shibuya.tokyo.jp/kenko/koreisha-seikatsu/kaigo/s_short.html"),
    "nakano": ("高齢者緊急一時宿泊事業",
               "区内在住のおおむね65歳以上で、介護者の急病や災害などで在宅生活が難しく、ほかのサービスが使えない方",
               "", "担当区域の地域包括支援センター",
               "https://www.city.tokyo-nakano.lg.jp/kenko_hukushi/kourei/hokenhukushi/kinkyu-syukuhaku.html"),
    "suginami": ("緊急ショートステイ（医療型）",
                 "要介護1以上で、経管栄養や在宅酸素などの医療行為が必要な方。家族の急な入院などで介護を受けられない場合",
                 "10日間", "ケアマネジャーから区役所（高齢者在宅支援課）へ事前に相談",
                 "https://www.city.suginami.tokyo.jp/guide/koureisha/enjo/1004634.html"),
    "toshima": ("緊急ショートステイ",
                "区内在住のおおむね65歳以上で、介護者の急病・けが、急な葬儀などで介護できない方",
                "原則7日以内", "区の案内に載っている施設に予約（問い合わせは高齢者福祉課）",
                "https://www.city.toshima.lg.jp/166/kenko/koresha/kinkyushortstay/kinkyushortstay.html"),
    "kita": ("高齢者緊急生活支援事業",
             "おおむね65歳以上で一時的に在宅生活が難しい方（要支援・要介護認定を受けている方は除く）",
             "", "高齢福祉課 高齢相談係",
             "https://www.city.kita.lg.jp/socialcare-health/elderly/1008607/1008608.html"),
    "arakawa": ("荒川区高齢者緊急一時保護事業",
                "介護認定の有無を問わず、おおむね65歳以上で家庭の事情などで一時的に在宅生活が難しい方",
                "原則14日以内", "区の高齢者福祉の窓口",
                "https://www.city.arakawa.tokyo.jp/reiki_int/reiki_honbun/p800RG00000856.html"),
    "nerima": ("緊急一時宿泊",
               "要支援・要介護認定者などで、家族の病気・けが・冠婚葬祭などで介護できず、介護保険のショートステイに空きがない方など",
               "原則9泊10日以内", "お近くの地域包括支援センター",
               "https://www.city.nerima.tokyo.jp/hokenfukushi/koreisha/oshirase/koreisya-guide.files/fukushisa-bisu2024.pdf"),
    "katsushika": ("家族等介護支援事業",
                   "区内で家族などの介護を受けている65歳以上の方など（以前の高齢者生活支援ショートステイは2024年4月にこの事業へ統合）",
                   "", "高齢者支援課 相談係",
                   "https://www.city.katsushika.lg.jp/kenkou/1000052/1030186/1002141/1017015.html"),
    "adachi": ("高齢者生活支援型緊急ショートステイ事業",
               "", "", "",
               "https://www.city.adachi.tokyo.jp/documents/50787/adachikuhukushijigyogaiyor7_1_1.pdf"),
    "edogawa": ("熟年者緊急短期入所実施事業",
                "", "", "",
                "https://www.city.edogawa.tokyo.jp/documents/6871/keikaku9.pdf"),
}

# 区独自の緊急ショートステイは見つからなかったが、近い区の事業があるもの
NEAR = {
    "meguro": ("短期入院病床確保事業「病院ショートステイ」",
               "医療的な管理が必要な要支援・要介護の方が、ケアマネジャーを通して病院に短期入院できる区の事業です（緊急専用ではありません）。",
               "https://www.city.meguro.tokyo.jp/koureifukushi/kenkoufukushi/koureisha/tanki.html"),
    "minato": ("港区高齢者緊急一時介護人派遣",
               "介護者が急に介護できなくなったときに、自宅へ介護人を派遣する区の事業です（宿泊ではありません）。相談は高齢者相談センターへ。",
               "https://www.city.minato.tokyo.jp/documents/10616/kinnkyuu.pdf"),
}


def section(wid, ward, center):
    d = DATA.get(wid)
    head = f'<h2 id="kinkyu">{ward}で急にショートステイが必要になったら</h2>\n'
    tail = (f'    <p class="tiny">各区の公式サイト・公式資料で確認（{CHECKED}）。費用や空き状況、最新の条件は必ず区の案内でご確認ください。'
            '介護保険のショートステイでも、ケアマネジャーに「緊急」と伝えると空きを探してもらえることがあります。</p>\n')
    if d:
        name, who, days, apply, url = d
        rows = f'      <tr><th>事業名</th><td>{name}</td></tr>\n'
        if who:
            rows += f'      <tr><th>対象のめやす</th><td>{who}</td></tr>\n'
        if days:
            rows += f'      <tr><th>利用できる日数</th><td>{days}</td></tr>\n'
        if apply:
            rows += f'      <tr><th>申込・相談</th><td>{apply}</td></tr>\n'
        rows += f'      <tr><th>区の案内</th><td><a href="{url}" rel="noopener" target="_blank">{ward}の公式ページ</a></td></tr>\n'
        lead = f"    <p>{ward}では、介護保険のショートステイとは別に、区の事業として次のものがあります。対象や日数は事業ごとに違います。"
        if not who:
            lead += f"区の資料で事業名は確認できましたが、対象や手続きの詳しい案内は見つかりませんでした。まず{center}に相談してください。"
        lead += "</p>\n"
        return (head + lead + '    <div class="tw">\n    <table>\n    <tbody>\n' + rows
                + '    </tbody>\n    </table>\n    </div>\n' + tail)
    n = NEAR.get(wid)
    body = (f"    <p>{ward}の公式サイトでは、区独自の緊急ショートステイの案内を確認できませんでした（{CHECKED}時点）。"
            f"急いで預け先が必要なときは、ケアマネジャー、いなければ{center}にすぐ相談してください。下の一覧から空きを直接問い合わせることもできます。</p>\n")
    if n:
        body += (f'    <div class="note"><strong>{ward}の近い事業：{n[0]}</strong>　{n[1]}'
                 f'（<a href="{n[2]}" rel="noopener" target="_blank">区の案内</a>）</div>\n')
    return head + body + tail
