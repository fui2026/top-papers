# Top Papers Weekly Digest - セットアップガイド

トップジャーナル（Nature, Science, Cell 等）の最新論文を毎週自動収集し、
GitHub Pages で公開 & X（Twitter）にスレッド投稿するシステム。

---

## 1. GitHub リポジトリの作成と push

### 1-1. Git 初期化

```bash
cd C:\Users\fui58\agent\top-papers

git init
git config user.name "YOUR_GITHUB_USERNAME"
git config user.email "YOUR_EMAIL@example.com"
```

### 1-2. .gitignore の作成

```bash
# 以下の内容で .gitignore を作成
cat <<'EOF' > .gitignore
__pycache__/
*.pyc
venv/
.venv/
.env
EOF
```

### 1-3. 初回コミット

```bash
git add -A
git commit -m "Initial commit: Top Papers Weekly Digest"
```

### 1-4. GitHub にリポジトリ作成

1. https://github.com/new にアクセス
2. **Repository name**: `top-papers`（任意）
3. **Public** を選択（GitHub Pages を無料で使うため）
4. 「Create repository」をクリック
5. **他のオプション（README, .gitignore 等）は全てオフ** のまま作成

### 1-5. push

```bash
git remote add origin https://github.com/YOUR_USERNAME/top-papers.git
git branch -M main
git push -u origin main
```

---

## 2. GitHub Pages の有効化

1. リポジトリの **Settings** タブを開く
2. 左メニューの **Pages** をクリック
3. **Source**: 「Deploy from a branch」を選択
4. **Branch**: `main`、フォルダは `/docs` を選択
5. 「Save」をクリック

数分後に `https://YOUR_USERNAME.github.io/top-papers/` でダイジェストが閲覧可能になります。

---

## 3. GitHub Actions の動作確認

ワークフローは毎週月曜 09:00 JST に自動実行されますが、
手動でもテストできます。

1. リポジトリの **Actions** タブを開く
2. 左メニューから「Weekly Paper Digest」を選択
3. 「Run workflow」ボタンをクリック
4. 実行が完了すると：
   - `output/` に `digest_YYYY-MM-DD.md` と `.json` がコミットされる
   - `docs/` にも同じファイルがコピーされ、`index.md` が更新される

---

## 4. X（Twitter）連携の設定

### 4-1. X Developer アカウントの作成

1. https://developer.x.com にアクセス
2. 投稿に使いたい X アカウントでログイン
3. **Sign up for Free Account** を選択
4. 利用規約に同意し、用途の説明を記入（例: "Automated weekly digest of top academic papers"）

### 4-2. App の作成と API キー取得

1. Developer Portal で **Projects & Apps** → **+ Create App**
2. App name を入力（例: `top-papers-digest`）
3. **User authentication settings** で以下を設定：
   - App permissions: **Read and Write**
   - Type of App: **Web App, Automated App or Bot**
   - Callback URL: `https://example.com`（使わないがフィールドは必須）
   - Website URL: `https://github.com/YOUR_USERNAME/top-papers`
4. **Keys and Tokens** タブから以下の4つをメモ：

| 項目 | Developer Portal での表記 |
|------|--------------------------|
| API Key | Consumer Keys → API Key |
| API Key Secret | Consumer Keys → API Key Secret |
| Access Token | Authentication Tokens → Access Token |
| Access Token Secret | Authentication Tokens → Access Token Secret |

> **注意**: Access Token と Secret は生成時に一度しか表示されません。必ずメモしてください。
> 表示されなかった場合は「Regenerate」で再生成できます。

### 4-3. GitHub Secrets に登録

1. リポジトリの **Settings** → **Secrets and variables** → **Actions**
2. 「New repository secret」で以下の4つを登録：

| Name | Value |
|------|-------|
| `X_API_KEY` | API Key の値 |
| `X_API_SECRET` | API Key Secret の値 |
| `X_ACCESS_TOKEN` | Access Token の値 |
| `X_ACCESS_SECRET` | Access Token Secret の値 |

### 4-4. X 投稿のテスト

1. Actions タブから「Run workflow」で手動実行
2. X アカウントにスレッドが投稿されたことを確認
3. 投稿内容は以下の形式：
   - Tweet 1: ヘッダー（期間、総論文数、GitHub Pages URL）
   - Tweet 2-N: カテゴリ別ハイライト（タイトル・著者・DOI リンク）
   - 最終 Tweet: フッター（フルダイジェスト URL、ハッシュタグ）

> X API キーが未設定の場合、投稿ステップは自動的にスキップされます。
> まず GitHub Actions + Pages だけで運用し、後から X 連携を追加しても OK です。

---

## 5. カスタマイズ

### ジャーナルの追加・変更

`config.yaml` を編集して、対象ジャーナルを変更できます。

```yaml
journals:
  - name: Nature Reviews Neuroscience
    issn: "1471-0048"
    category: nature_family
```

ISSN は https://portal.issn.org で検索できます。
CrossRef に登録されているか確認するには：

```bash
curl -s "https://api.crossref.org/journals/ISSN_HERE" | python -c "
import sys, json
data = json.load(sys.stdin)
print(data['message']['title'])
"
```

### 検索期間の変更

`config.yaml` の `lookback_days` を変更するか、実行時に `--days` オプションを使用：

```bash
python fetch_papers.py --days 7    # 過去7日間
python fetch_papers.py --days 30   # 過去30日間
```

### 実行スケジュールの変更

`.github/workflows/weekly-digest.yml` の cron 式を変更：

```yaml
# 毎週月曜 09:00 JST
- cron: '0 0 * * 1'

# 毎週金曜 18:00 JST
- cron: '0 9 * * 5'

# 毎日 09:00 JST
- cron: '0 0 * * *'
```

> cron は UTC 基準です。JST = UTC + 9 時間。

---

## プロジェクト構成

```
top-papers/
├── .github/workflows/
│   └── weekly-digest.yml    # GitHub Actions ワークフロー
├── docs/                    # GitHub Pages 公開ディレクトリ
│   ├── _config.yml          # Jekyll 設定
│   ├── index.md             # ダイジェスト一覧ページ
│   └── digest_*.md          # 各週のダイジェスト
├── output/                  # ローカル出力ディレクトリ
│   ├── digest_*.md          # Markdown レポート
│   └── digest_*.json        # JSON サマリー（X 投稿用）
├── config.yaml              # ジャーナル設定
├── fetch_papers.py          # 論文取得スクリプト（CrossRef API）
├── post_to_x.py             # X スレッド投稿スクリプト
├── generate_index.py        # GitHub Pages インデックス生成
└── SETUP_GUIDE.md           # このファイル
```

---

## トラブルシューティング

### GitHub Actions が失敗する

- **Actions タブ** で失敗したワークフローをクリックし、ログを確認
- `pip install` で失敗する場合: `requirements.txt` が必要かもしれません
  ```bash
  echo -e "requests\npyyaml\ntweepy" > requirements.txt
  ```

### 特定のジャーナルで 0 件になる

- CrossRef のインデックス遅延の可能性があります（特に Cell 系）
- `config.yaml` の ISSN が正しいか確認してください
- ローカルで `python fetch_papers.py --dry-run` で設定を確認

### X 投稿が失敗する

- GitHub Secrets の4つの値が正しいか確認
- X Developer Portal で App の権限が **Read and Write** になっているか確認
- Free tier の月間上限（1,500 ツイート）に達していないか確認
