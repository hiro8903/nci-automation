# 🤖 NCI Automation Tools

本プロジェクトは、業務におけるルーチンワーク（ダウンロード、ログイン、レポート収集等）を Python (Selenium, Requests 等) で自動化するためのツール群です。

---

## 📖 利用者ガイド (For Users)

実行ファイル（EXE）を使用して、すぐにツールを利用したい方向けのガイドです。

### 1. ツールのダウンロード
GitHub の [Releases](./releases) ページから、利用したいツールの最新版（EXEファイル）をダウンロードしてください。

### 2. フォルダ構成と配置
ダウンロードした EXE ファイルは、以下の構成で配置してください。**設定ファイル（.env）は、EXE本体が含まれるフォルダの「一つ上の階層」に置く必要があります。**

```text
作業フォルダ（名前は自由）/
├── .env                          (設定ファイル：IDやパスワードを記入)
└── app/                          (名前は自由：ここにEXEを置く)
    └── Daikin_SDS_Downloader.exe
```

### 3. 環境設定 (.env) の作成
プロジェクトの共通ガイドラインとして、`.env` ファイルには以下の共通項目が必要です。各ツール固有の設定値（保存パス等）については、各ツールの仕様書（SPECIFICATION.md）を参照してください。

> [!IMPORTANT]
> 値を記入する際は、原則としてダブルクォーテーション `"` で囲むことを推奨しますが、**保存先フォルダパスなどの一部の項目では不要です。**

#### 📋 共通設定テンプレート (.env)
```text
# --- デスクネッツ認証共通 (desknets) ---
DESKNETS_LOGIN_URL="https://www.example.com/login"
DESKNETS_ORG_ID="1234"
DESKNETS_NAME_VALUE="1234"
DESKNETS_PASSWORD="password"
```

### 4. 自動化の設定（Windows タスクスケジューラ）
ツールを定期的に自動実行させるには、Windows の「タスクスケジューラ」を使用します。

**起動方法**: Windows キーを押して「タスク」と入力し、検索結果から **[タスク スケジューラ]** をクリックして開きます。

1. **タスクの作成**: [基本タスクの作成] または [タスクの作成] を選択。
2. **トリガー**: 実行したい頻度（毎日、毎週など）を設定。
3. **操作**: [プログラムの開始] を選択。
4. **プログラム/スクリプト**: EXEファイルへの**絶対パス**を入力。
   - 例: `C:\Users\Target\Desktop\automation\app\Daikin_SDS_Downloader.exe`
5. **開始 (オプション)**: EXEファイルが置かれているフォルダのパスを入力してください。
   - **重要**: ここを空欄にすると、プログラムが設定ファイル（.env）を見つけられず、エラーになる可能性があります。
   - 例: `C:\Users\Target\Desktop\automation\app`

---

## 🏗 開発者ガイド (For Developers)

本リポジトリのコードを編集、デバッグ、または新たにビルドしたい方向けのガイドです。

### 1. 開発環境のセットアップ
リポジトリをクローンした後、以下のコマンドで必要な依存ライブリをインストールしてください。
```bash
pip install -r requirements.txt
```

### 2. 開発・協業のルール
AIとのペアプログラミングや、チームでの品質維持のために以下のドキュメントを必ず一読してください。
- **[GEMINI.md (協業・実装指針)](./GEMINI.md)**: AIとの協業ルールと、エラーハンドリング等の実装規約。
- **[DEVELOPMENT.md (開発プロセス)](./DEVELOPMENT.md)**: Git運用（ブランチ、コミット）やPR作成の標準フロー。

### 3. ローカルでのビルド (EXE化)
コード修正後の動作確認や、GitHub を介さずに即座に実行ファイルを作成したい場合は、ローカル環境でビルドを行うことができます。

```bash
# SDSダウンローダーのビルド例
pyinstaller --onefile --paths . --name Daikin_SDS_Downloader apps/report_downloaders/daikin_downloader/src/sds/download_sds.py
```

動作確認が完了し、他のユーザーへ配布できる状態（正式版）になった場合は、GitHub の **[Releases](./releases)** から新規リリースを作成し、最新の成果物を公開・共有するようにしてください。

---

## 📚 ツールの一覧 (Tool Inventory)

各ツールの詳細な仕様や、設定すべき `.env` の項目については以下を参照してください。

### 🛠 自動化ツール (Apps)
- **[Daikin Inspection Report (検査成績書取得ツール)](./apps/report_downloaders/daikin_downloader/src/inspection_report/SPECIFICATION.md)**
  - 概要：検査成績書の自動取得・解凍・整理。
  - 💾 [EXE ダウンロード](https://github.com/hiro8903/nci-automation/releases/tag/daikin-build-2026-02-27)

- **[Daikin SDS Downloader Group (SDS取得ツール群)](./apps/report_downloaders/daikin_downloader/src/sds/SPECIFICATION.md)**
  - 概要：最新のSDSを動的に取得する「Downloader」と、対象品番を調査する「Model Extractor」のセット。
  - 💾 [EXE ダウンロード (Downloader)](https://github.com/hiro8903/nci-automation/releases/tag/daikin-sds-build-2026-03-04)
  - 💾 [EXE ダウンロード (Model Extractor)](https://github.com/hiro8903/nci-automation/releases) (※最新の Actions 成果物を参照)

### 📦 共通部品 (Common Utilities)
- **[Desknets Login Module (デスクネッツ共通認証)](./common_utils/desknets/SPECIFICATION.md)**
  - 役割：共通の認証とメール更新を担う部品。
  - 💾 [EXE ダウンロード](https://github.com/hiro8903/nci-automation/releases/tag/desknets-login-build-2026-02-27)

---
*Developed by N-Client Automation Team*
