# 公開手順（ドメイン取得 → 本番公開 → 検索登録）

かいごのとなり / 2026-09-21

---

## 0. ドメインの状況

| ドメイン | 状態 | 備考 |
|---|---|---|
| `kaigo-tonari.com` | **取得済み（他者）** | 2026-07-12 登録／GMO（お名前.com）／Vercel のDNS／client hold |
| `kaigonotonari.com` | **取得済み（当方）✅** | 本番ドメイン。設定済み |
| `kaigotonari.com` | **空きあり** | 短い。「の」を省いた形 |
| `kaigonotonari.jp` ほか `.jp` | **未確認** | `.jp` は RDAP が外部から引けなかったため、レジストラの検索窓で要確認 |

> **`kaigonotonari.com` を取得済みです。** `data/site.json` の `site.url`、`CNAME`、各ページデータの絶対URLはすべてこのドメインに反映済みで、追加の置換作業はありません。

### 購入先の選択肢

| レジストラ | 向き | 備考 |
|---|---|---|
| Cloudflare Registrar | おすすめ | 原価販売・更新料が上がらない。DNSも同じ画面で完結 |
| お名前.com（GMO） | 日本語サポート重視 | 初年度が安い反面、更新料は高め。`.jp` も扱う |
| Google Domains 後継（Squarespace） | 手軽さ重視 | 管理画面が簡単 |

---

## 1. 反映状況（対応済み）

| 項目 | 値 |
|---|---|
| `data/site.json` の `site.url` | `https://kaigonotonari.com` |
| `CNAME` | `kaigonotonari.com` |
| 各ページの canonical / OGP / JSON-LD | 反映済み |
| `sitemap.xml` / `robots.txt` | 反映済み（16URL） |

再生成するときは、必ずこの順番で実行します。

```bash
python3 build_hubs.py
python3 build.py
python3 postprocess.py
python3 build_sitemap.py
```

`canonical` / OGP / JSON-LD / `sitemap.xml` / `robots.txt` はすべて `site.url` から組み立てられるので、これで全ページが新ドメインに揃います。

> 将来ドメインを変える場合は、`data/site.json` の `site.url`、`CNAME`、`data/*_*.json` の絶対URL（`seo.canonical` / `seo.og_image`）の3か所を置換してから再生成してください。

---

## 2. GitHub Pages で公開する

```bash
cd kaigo-no-tonari
git init
git add .
git commit -m "かいごのとなり 初期公開"
git branch -M main
git remote add origin git@github.com:<あなたのアカウント>/kaigo-no-tonari.git
git push -u origin main
```

リポジトリの **Settings → Pages → Build and deployment → Source** を **GitHub Actions** にします。`.github/workflows/deploy.yml` が動き、次を自動で行います。

1. `build_hubs.py` / `build.py` / `build_sitemap.py` を実行してページを生成
2. **検証**：JSON-LD の構文エラー、目次アンカー切れがあればデプロイを中止
3. 生成物だけを `_site/` に集めて公開（`data/` `content/` `templates/` `docs/` `*.py` は公開されません）

以後は `git push` するだけで反映されます。

### DNS 設定（GitHub Pages）

| 種別 | ホスト | 値 |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `<あなたのアカウント>.github.io` |

設定後、Settings → Pages で **Enforce HTTPS** にチェック。証明書の発行に数分〜1時間かかります。

### Cloudflare Pages を使う場合

GitHub Pages の代わりに Cloudflare Pages でも動きます（日本からの表示は速くなる傾向）。

- Build command: `python3 build_hubs.py && python3 build.py && python3 build_sitemap.py`
- Build output directory: `/`
- 環境変数: `PYTHON_VERSION = 3.12`

---

## 3. 公開直後にやること

| # | 作業 | 場所 |
|---|---|---|
| 1 | Search Console にプロパティ追加（ドメイン単位） | search.google.com/search-console |
| 2 | `sitemap.xml` を送信 | Search Console → サイトマップ |
| 3 | 市区町村ページ3本を個別にインデックス登録リクエスト | Search Console → URL検査 |
| 4 | Bing Webmaster Tools にも登録（Yahoo! JAPAN の検索結果に効く） | bing.com/webmasters |
| 5 | 問い合わせメールの受信確認 | `chlrhlanf3652@gmail.com` を記載済み。迷惑メールに振り分けられないよう、フィルタで「かいごのとなり」関連を受信トレイに固定しておく |
| 6 | 電話タップ・外部リンククリックの計測を入れる | 収益判定に必須 |

> **AdSense はまだ申請しないでください。** 現状3ページで、`/about/` などの必須ページも未作成です。市区町村ページが15〜20本たまり、必須ページが揃ってからの申請が通りやすくなります。

---

## 4. 法務・表記まわり（公開前チェック）

| 項目 | 状態 |
|---|---|
| 広告（PR）表記 | ✅ 全ページ上部に固定表示済み（2023年10月施行のステマ規制対応） |
| 出典・最終確認日 | ✅ 全ページ下部に表示済み |
| 掲載事業者の訂正・削除の受付 | ✅ `/contact/` 作成済み。削除は理由不要・5営業日以内と明記 |
| 運営者情報 | ✅ `/about/` 作成済み（運営者・所在地・事業者登録番号・掲載方針） |
| プライバシーポリシー / 免責事項 / 広告について | ✅ 作成済み |
| 問い合わせ用メールアドレス | ✅ `chlrhlanf3652@gmail.com` を記載済み。将来 `info@kaigonotonari.com` に移す場合は `content/page_contact.html` の1か所だけ直せば済みます |
| 事業者の写真・ロゴ | ✅ 未使用（提供を受けたものだけを使う方針） |
