# 📝 プロジェクト仕様書 (SPECIFICATION)

本ドキュメントは、プロジェクト内で開発される各ツールの確定済み仕様を記録するものです。

---

## 🛠 新機能：型番別PDF自動巡回取得ツール（仮称）

### 概要
特定のWebページから、指定された型番（品番）に対応するPDFドキュメントを自動で巡回・保存するツール。取得日ごとのスナップショット管理を目的とする。

### ① 要件定義 (確定済み)

#### 1-A. 要求分析 (Demand Analysis)
- **ユーザー要求**: 特定URLから品番指定でPDFを表示・保存。
- **ビジネス目的**: 取得日ごとの最新版管理（スナップショット）。更新有無に関わらず実行時の最新を保存。

#### 1-B. 要件策定 (Requirement Specification)
- **入力**: 
    - `DAIKIN_SDS_TARGET_URL`: SDS一覧ページのURL
    - `DAIKIN_SDS_BASE_URL`: 相対パスを解決するためのベースドメイン (例: `https://www.daikinchemicals.com`)
    - `DAIKIN_SDS_MODEL_LIST`: 型番リスト（カンマ区切り）
    - `DAIKIN_SDS_SAVE_ROOT_DIR`: 保存先フォルダのルート
- **出力**: 
    - `DAIKIN_SDS_SAVE_ROOT_DIR/yyyy-mm-dd/` フォルダへのPDF保存。
    - `download_result_yyyy-mm-dd.txt`: 
        - 成功セクション: `品番名,yyyy/m/d` (URLから抽出したSDS更新日)
        - 失敗セクション: `品番名`
- **正常系フロー**: 
    - ターゲットURLのHTMLを `requests` で取得。
    - `BeautifulSoup` を使用し、リンク(`<a>`タグ)の中から品番名を含むPDFリンクを動的に特定。
    - 最新のPDFを `requests` で直接取得し、ファイルに保存。
- **異常系・アラート**: 
    - 型番未発見時、結果レポートに記録。
    - コンソール画面にてユーザーへ視覚的な警告を行い、キー入力まで画面を維持する。

#### 1-C. デプロイメント戦略
- **提供形式**: Route A (EXE化)
- **実行形式**: Windowsタスクスケジューラ等による定期実行。

#### 1-D. 開発スタイル
- **推奨規模**: [Team] スタイル。

#### 1-E. 制約条件
- **非機能要件**: 
    - Seleniumへの依存を排除し、軽量・高速化を実現。
    - 日本語ログ表示、失敗時のウィンドウ維持（エラーガード）。
- **環境要件**: Python 3.9+ (requests, beautifulsoup4, python-dotenv)。

## ② 利用手順 (Usage)

### 1. セットアップ
プロジェクトルートにある `.env` ファイルに、以下の項目を設定してください。
```text
DAIKIN_SDS_TARGET_URL="https://www.daikinchemicals.com/jp/downloads/safety-data-sheets.html"
DAIKIN_SDS_BASE_URL="https://www.daikinchemicals.com"
DAIKIN_SDS_MODEL_LIST="F-104,D-210C"
DAIKIN_SDS_SAVE_ROOT_DIR="/Users/dev/Desktop"
```

### 2. 実行
スクリプト `download_sds.py` を起動します。
プログラムは最新のリンクを動的に発見し、PDFを日付フォルダに保存します。

### 3. 結果の確認
設定した保存場所に、実行日の日付フォルダ、PDFファイル、および詳細な結果レポート（`download_result_...txt`）が生成されます。

---

## 💡 技術的メモ
- 品番検索は「大文字小文字を区別せず」「ハイフンの有無」も考慮してマッチングを行う。
- PDFのURLに含まれる `_YYYYMMDD.pdf` のパターンを正規表現で解析し、レポート用の更新日を抽出する。
- Seleniumを使用しないため、ブラウザやドライバの更新による影響を受けにくい。
