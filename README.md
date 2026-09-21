# かいごのとなり — サイト構成とビルド手順

日本の高齢者向け地域サービスディレクトリ。市区町村 × カテゴリのページを、データ（JSON）と本文（HTML断片）からビルドして生成する。

---

## 1. ディレクトリ

```
kaigo-no-tonari/
├─ index.html                     サイトトップ          ← build_hubs.py が生成
├─ <cat>/index.html               カテゴリハブ（全国）   ← build_hubs.py が生成
├─ <cat>/<pref>/index.html        都道府県ページ         ← build_hubs.py が生成
├─ <cat>/<pref>/<city>/index.html 市区町村ページ         ← build.py が生成
├─ assets/
│   ├─ style.css                  全ページ共通スタイル
│   └─ ogp-houmon-kaigo.png       OGP / ヒーロー画像
├─ data/
│   ├─ site.json                  カテゴリ・都道府県・市区町村の一覧（公開状態つき）
│   └─ <cat>_<pref>_<city>.json   市区町村ページのデータ
├─ content/
│   ├─ hub_top.html               サイトトップの本文
│   ├─ hub_<cat>.html             カテゴリハブの本文
│   ├─ pref_<cat>_<pref>.html     都道府県ページの本文
│   └─ <cat>_<pref>_<city>.html   市区町村ページの本文（{{LISTING}} / {{FAQ}} を含む）
├─ templates/
│   ├─ city.html                  市区町村ページの骨組み
│   └─ hub.html                   トップ / ハブ / 都道府県ページの骨組み
├─ build.py                       市区町村ページ生成
├─ build_hubs.py                  トップ・ハブ・都道府県ページ生成
├─ build_sitemap.py               sitemap.xml / robots.txt 生成
├─ postprocess.py                 未作成ページへのリンクを「準備中」表示に落とす
├─ CNAME                          GitHub Pages のカスタムドメイン
├─ .github/workflows/deploy.yml   push で生成→検証→公開
├─ dist-artifact/                 プレビュー配信用のコピー（ディレクトリ index を明示パスに書き換えたもの）
└─ docs/
    ├─ crawler-design.md          事業者データ収集パイプライン設計書
    └─ deploy.md                  ドメイン取得・本番公開・検索登録の手順
```

## 2. ビルド

依存ライブラリなし。Python 3.9 以上。

```bash
python3 build_hubs.py                          # トップ・ハブ・都道府県ページ
python3 build.py                               # data/ 配下すべての市区町村ページ
python3 postprocess.py                         # 未作成ページへのリンクを「準備中」表示に
                                               # （リンク切れが残ると終了コード1で止まる）
python3 build_sitemap.py                       # sitemap.xml / robots.txt
```

**必ずこの順番で実行する。** `postprocess.py` は生成済みHTMLを書き換えるため、`build_*.py` のあとに走らせる。
ページを作れば、そのリンクは次のビルドで自動的にリンクへ戻る。

## 3. URL 設計

| 階層 | URL | 検索意図 | 役割 |
|---|---|---|---|
| トップ | `/` | ブランド | 入口 |
| カテゴリ | `/houmon-kaigo/` | 「訪問介護 とは」 | 制度解説と都道府県への導線 |
| 都道府県 | `/houmon-kaigo/tokyo/` | 「東京都 訪問介護」 | 地域区分・窓口の解説と市区町村への導線 |
| **市区町村** | `/houmon-kaigo/tokyo/setagaya/` | **「世田谷区 訪問介護」** | **事業者一覧。検索流入と収益の主戦場** |

日本のユーザーは市区町村単位で検索する。最終的な勝負はこの4階層目。

## 4. データスキーマ（`data/<cat>_<pref>_<city>.json`）

| キー | 型 | 説明 |
|---|---|---|
| `slug` | string | `<cat>_<pref>_<city>`。ファイル名と一致させる |
| `category.id` / `.name` / `.path` | string | カテゴリID・表示名・URLパス |
| `area.pref_id` / `.pref_name` | string | 都道府県のIDと表示名 |
| `area.city_id` / `.city_name` | string | 市区町村のIDと表示名 |
| `seo.title` | string | `<title>`。全角32字以内に収める |
| `seo.description` | string | meta description。全角90〜120字 |
| `seo.canonical` | string | 正規URL（絶対URL） |
| `seo.og_title` / `.og_description` / `.og_image` | string | OGP |
| `h1` | string | 見出し。title とは別文言にする |
| `published` / `modified` | string | `YYYY-MM-DD` |
| `count_label` | string | ヘッダーに出す件数表示（例: `掲載：12事業所`） |
| `lead` | string | 導入文（HTML可） |
| `listing_note` | string | 一覧の直前に出す注記 |
| `items[]` | array | 掲載事業者。**schema.org の LocalBusiness 形式をそのまま持つ**（下記） |
| `faq[]` | array | `{q, a}`。本文の FAQ と JSON-LD の FAQPage を同時に生成 |
| `related` / `nearby` | string | 内部リンクブロック（HTML）。`{{ROOT}}` でサイトルートを表す |
| `nearby_heading` | string | 近隣エリア見出し |
| `sources[]` | array | 出典。各ページ下部に表示 |
| `sidebar` / `mcta` | string | サイドバー・モバイル固定CTA（HTML） |
| `hero_image` | string | 任意。サイトルートからの相対パス |

### `items[]` の形

`items` は schema.org の `LocalBusiness`（自治体窓口なら `GovernmentOffice`、民間サービスなら `Organization`）をそのまま格納する。**JSON-LD と表示カードの両方がこの1か所から生成される**ので、二重管理が起きない。

```json
{
  "@type": "LocalBusiness",
  "name": "玉川ケアサービス",
  "telephone": "03-3709-6776",
  "address": {
    "@type": "PostalAddress",
    "addressCountry": "JP",
    "addressRegion": "東京都",
    "addressLocality": "世田谷区",
    "streetAddress": "玉川台1-13-14 用賀武井ビル301、302"
  },
  "areaServed": "世田谷区中心部",
  "_tags": ["用賀・玉川エリア", "訪問介護"]
}
```

`_` で始まるキー（`_tags`）は表示専用で、JSON-LD には出力されない。

### `content/<slug>.html` のプレースホルダ

| 記法 | 差し込まれるもの |
|---|---|
| `{{LISTING}}` | `items[]` から生成した事業者カード一覧＋掲載情報の注記 |
| `{{FAQ}}` | `faq[]` から生成した `<details>` 群 |
| `{{ROOT}}` | サイトルートへの相対パス（階層に応じて `../` の数が変わる） |

目次は本文中の `<h2 id="...">` から自動生成される。手で書かない。

## 5. 新しい市区町村ページを追加する手順

1. `data/site.json` の `cities` に市区町村を追加し、`status` を `"planned"` にする
2. 事業者データを集める（`docs/crawler-design.md` 参照）
3. **掲載3件以上**を満たしたら `data/<cat>_<pref>_<city>.json` を作成
4. `content/<cat>_<pref>_<city>.html` に本文を書く（800字以上）
5. `data/site.json` の `status` を `"live"` に変更
6. `python3 build_hubs.py && python3 build.py` を実行
7. Search Console でインデックス登録をリクエスト

掲載3件未満のエリアはページを作らない。都道府県ページに「準備中」と表示されるだけで、リンクも張られない。

## 6. 公開前チェックリスト

- [ ] `<title>` 全角32字以内 / meta description 90〜120字
- [ ] canonical が本番URLになっているか
- [ ] JSON-LD が構文エラーなくパースできるか（リッチリザルトテストで確認）
- [ ] 目次アンカーがすべて本文の `id` に対応しているか
- [ ] 内部リンクの相対パスが切れていないか
- [ ] 出典と最終確認日が入っているか
- [ ] 広告（PR）表記がページ上部にあるか — 2023年10月施行のステマ規制対応
- [ ] 掲載事業者の訂正・削除の受付導線（`/contact/`）が機能しているか

## 7. 日本市場向けに入れてある仕掛け

上位競合（ハートページナビ／LIFULL介護／みんなの介護／シニアのあんしん相談室）を実地調査して取り込んだもの。

| 仕掛け | 実装 |
|---|---|
| 文字サイズ切替（ふつう／大きい） | ユーティリティバー。localStorage に保存、描画前に復元してちらつきを防止 |
| タイトルに更新月と件数 | `世田谷区の訪問介護12事業所｜料金と選び方【2026年9月更新】` |
| 町域一覧 | 五十音の行ごとに全町域を掲載。ロングテール検索語をページ内に持たせる |
| 事業者情報の密度 | 運営法人・事業所番号・FAX・電話受付時間・休業日まで掲載 |
| 図解 | 料金の計算式／食形態の段階／貸主の不安と対策をインラインSVGで |
| 相談窓口の常時表示 | ユーティリティバーに固定 |
| リンク切れゼロ運用 | `postprocess.py` が未作成ページへのリンクを自動で「準備中」表示に落とす。ページを作れば次のビルドで自動的にリンクへ戻る |

## 8. 未実装（次にやること）

| 項目 | 内容 |
|---|---|
| 実ページ | `/shukatsu/` と `/guide/` 配下の個別ガイド。現在「準備中」表示 |
| 見守りの市区町村ページ | `/mimamori/` はハブのみ。事業者データがそろい次第、市区町村ページを追加 |
| 町域ページ | 掲載3件以上そろった町域から公開 |
| 町域ページ | 掲載3件以上そろった町域から `/houmon-kaigo/tokyo/setagaya/sangenjaya/` 形式で |
| 計測 | 電話タップ・外部リンククリックのイベント計測（収益判定に必須） |
| 事業者写真 | 提供を受けたもの、または自前で撮影・購入したもののみ |
