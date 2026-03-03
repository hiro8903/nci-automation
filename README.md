# 🤖 CI Automation Tools (nci-automation)

本プロジェクトは、業務におけるルーチンワーク（ダウンロード、ログイン、レポート収集等）を Python と Selenium で自動化するためのツール群です。

---

## 🚀 共通の実行環境ガイド

本プロジェクトの全てのツールは、以下の共通ルールに従って実行されます。

### 1. 依存ライブラリのインストール
```bash
pip install -r requirements.txt
```

### 2. 環境設定 (.env) の作成
全てのツールは、**プロジェクトルート（本ファイルと同じ階層）にある `.env` ファイル** を共通して参照します。
以下の「全項目コピペ用テンプレート」をコピーして `.env` ファイルを作成し、必要な値を記入してください。

> [!IMPORTANT]
> 値を記入する際は、ダブルクォーテーション `"` で囲むようにしてください。

#### 📋 .env 用コピペ・テンプレート
```text
# --- デスクネッツ認証共通 (desknets) ---
DESKNETS_LOGIN_URL="https://..."
DESKNETS_ORG_ID="1234"
DESKNETS_NAME_VALUE="1234"
DESKNETS_PASSWORD="password"

# --- 検査成績書設定 (daikin_inspection_report) ---
DAIKIN_INSPECTION_LOGIN_URL="https://..."
DAIKIN_INSPECTION_SAVE_PATH="C:/downloads/inspection"
```

### 3. 実行方法
各ツールの実行ファイル（EXE）またはスクリプトを起動します。

- **EXE実行時の注意**: 「Windows によって PC が保護されました」という青い画面が出た場合は、[詳細情報] をクリックしてから [実行] を押してください。
- **必須要件**: PC に **Google Chrome** ブラウザがインストールされている必要があります。
- **エラー時の挙動**: `GEMINI.md` の規定により、実行中にエラーが発生してもウィンドウは即座に閉じず、内容を表示したまま待機します。

### 4. 配布・運用時のフォルダ構成 (EXE)
ツールを EXE 形式で配布・運用する場合は、以下の階層構造で配置する必要があります。
**重要：実行ファイル本体が含まれるフォルダの「一つ上の階層」に `.env` ファイルを置いてください。**

```text
作業フォルダ（名前は自由）/
├── .env                          (設定ファイル：IDやパスワードを記入)
└── app/                          (名前は自由：ここにEXEをまとめる)
    └── download_inspection_report.exe
```

---

> [!IMPORTANT]
> **セキュリティに関する注意**
> `.env` ファイルには重要なログイン情報が含まれています。このファイルをメールに添付して送信したり、共有ストレージで不特定多数に公開したりしないでください。

---

## 📚 ツールの一覧 (Tool Inventory)

各ツールの具体的な仕様や詳細な利用手順については、それぞれのリンク先を参照してください。
プロジェクト全体の目録は **[SPECIFICATION.md (Index)](./SPECIFICATION.md)** にまとめられています。

### 🛠 自動化ツール (Apps)
- **[Daikin Inspection Report](./apps/report_downloaders/daikin_downloader/src/inspection_report/SPECIFICATION.md)**: 検査成績書の自動取得・解凍・整理。

### 📦 共通部品 (Common Utilities)
- **[Desknets Login Module](./common_utils/desknets/SPECIFICATION.md)**: デスクネッツ認証とメール更新を担う共有部品。

---

## 🏗 プロジェクト構成と指針 (Architecture)

- **[GEMINI.md](./GEMINI.md)**: AIアシスタントのための動作指針。
- **[DEVELOPMENT.md](./DEVELOPMENT.md)**: 開発・運用の標準化プロセス。
- **[SPECIFICATION.md (Index)](./SPECIFICATION.md)**: プロジェクト全体の仕様目録。
