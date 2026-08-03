# screener.trgy.co.jp 公開手順（Xserver スタンダードプラン）

Vercelは使わず、既に契約しているエックスサーバー（サーバーID `eaexpo` / `sv8170` /
スタンダードプラン）のサブドメインとして公開する。`trgy.co.jp` は同サーバーに
ドメイン登録済みのため、サブドメインを1つ追加するだけでよく、追加費用は発生しない。

日次のデータ更新とデプロイは GitHub Actions が行うため、Macを起動しておく必要はない。

```
GitHub Actions（毎営業日 18:30 JST）
  → 株価・配当を取得して再判定 → サイトをビルド → FTPでXserverへ転送
```

サイトは完全な静的ファイル（HTML/CSS/JS）のみで、サーバー側の処理を持たない。

---

## 1. GitHubリポジトリの作成

`screening-site/` をそのままリポジトリのルートとして公開する。

```bash
cd ~/Desktop/project/screening-site
git init -b main
git add -A
git commit -m "初回コミット"
gh repo create ch8maejima-oss/screener-trgy --private --source=. --push
```

`gh` が使えない場合は GitHub 上で空のプライベートリポジトリ `screener-trgy` を作り、

```bash
git remote add origin https://github.com/ch8maejima-oss/screener-trgy.git
git push -u origin main
```

**必ずプライベートにすること。** `.env`（EDINET APIキー）は `.gitignore` で除外済みだが、
リポジトリ自体を公開する必要はない。

---

## 2. Xserver にサブドメインを追加

1. XServerアカウント → 対象サーバー（`eaexpo`）の **「サーバー管理」**（サーバーパネル）を開く
2. **「サブドメイン設定」** → ドメイン一覧から **`trgy.co.jp`** の「選択する」
3. **「サブドメイン設定追加」** タブ
   - サブドメイン: **`screener`**
   - 「無料独自SSLを利用する」に**チェックを入れる**
4. 確認画面へ進み、追加する（SSLの反映に最大1時間程度）

作成されるディレクトリは `/home/eaexpo/trgy.co.jp/public_html/screener/`。

## 3. GitHub Secrets の登録

リポジトリの Settings → Secrets and variables → Actions → New repository secret

| 名前 | 値 | 用途 |
|---|---|---|
| `XSERVER_FTP_HOST` | `sv8170.xserver.jp` | 日次デプロイ |
| `XSERVER_FTP_USER` | `eaexpo`（サーバーパネル「FTPアカウント設定」で確認） | 日次デプロイ |
| `XSERVER_FTP_PASSWORD` | 上記FTPアカウントのパスワード | 日次デプロイ |
| `XSERVER_FTP_REMOTE_DIR` | `/trgy.co.jp/public_html/screener` | 日次デプロイ |
| `EDINET_API_KEY` | EDINETのAPIキー | 財務データ再取得（年1回） |

> **`XSERVER_FTP_REMOTE_DIR` は必ず確認すること。**
> デプロイは `mirror --delete` で同期するため、誤ったディレクトリを指定すると
> その中身が削除される。同じサーバーには `ea-exposition.com` も同居しているため、
> 誤指定の影響が他サイトに及びうる。
>
> ワークフロー側にも防御を入れてあり、パスが `.../public_html/screener` で
> 終わっていない場合はデプロイせずに失敗する。

---

## 4. DNSの切り替え（ムームーDNS）

ムームードメインの「ムームーDNS」で `trgy.co.jp` のカスタム設定を開き、
サブドメイン `screener` に次のAレコードを設定する。

| 項目 | 値 |
|---|---|
| サブドメイン | `screener` |
| 種別 | `A` |
| 内容 | `183.181.89.11`（`sv8170.xserver.jp`） |

反映後、https://screener.trgy.co.jp が表示されることを確認する。

---

## 5. 初回デプロイ

GitHub の Actions タブ →「日次更新とデプロイ」→ Run workflow で手動実行する。

ワークフローには、空のディレクトリを転送して既存サイトを消す事故を防ぐため、
`out/index.html` の存在と本文の生成を確認する検証ステップを入れてある。

---

## 手元での確認

Node.js は `~/.local/opt/node22` にインストール済み（sudo不要のユーザー領域）。

```bash
cd ~/Desktop/project/screening-site
export PATH="$HOME/.local/bin:$PATH"

npm run dev     # http://localhost:3000 で確認
npm run build   # out/ に静的ファイルを書き出す
```

データを更新してから確認する場合:

```bash
python3 scripts/screen.py           # 株価・配当を取得して再判定
python3 scripts/build_site_data.py  # app/data/latest.json を更新
npm run build
```

---

## 運用サイクル

| 頻度 | 作業 | 実行方法 |
|---|---|---|
| 毎営業日 18:30 | 株価・配当の更新と再デプロイ | GitHub Actions（自動） |
| 年1回（7月頃） | 有価証券報告書の再取得 | Actions →「財務データの再取得」を手動実行 |

年1回の再取得では、EDINETのタクソノミ変更で抽出が壊れていないかを
取得率で自動検証している。想定を下回るとワークフローが失敗するので気づける。

---

## 外部公開する場合

現在は `app/layout.tsx` に `robots: "noindex"` を設定しており、検索エンジンには載らない。
社内利用の間はこのままにする。

外部公開に切り替える際は、事前に次を行う。

1. `compliance-reviewer` によるコンプライアンスチェック
2. 商号・登録番号（近畿財務局長（金商）第372号）・加入協会名の表示確認（フッターに実装済み）
3. 選定条件・除外基準の表示確認（実装済み）
4. `robots: "noindex"` の解除
