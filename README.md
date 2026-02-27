# Automation Tools for NCI

このリポジトリは、業務効率化のための自動化ツールを管理・ビルドするためのプロジェクトです。

---

## 📦 最新のリリース (Latest Releases)

ビルド済みの実行ファイル（Windows用）は以下のリンクからダウンロードできます。

| ツール名 | 最新リリースへのリンク |
| :--- | :--- |
| **Desknet's 自動ログインツール** | [リリースを開く](https://github.com/hiro8903/nci-automation/releases/tag/desknets-login-build-2026-02-27) |
| **ダイキン検査成績書 DLツール** | [リリースを開く](https://github.com/hiro8903/nci-automation/releases/tag/daikin-build-2026-02-27) |

---

## 🚀 公開中のツール概要

### 1. Desknet's 自動ログインツール
Desknet's NEO に自動でログインし、ポータル画面を表示します。毎朝のログイン操作を短縮します。

### 2. ダイキン検査成績書ダウンロードツール
ダイキン工業のサイトから検査成績書を自動で一括ダウンロードし、ZIPファイルの解凍・整理まで行います。
デスクネッツのメールから認証コードを自動取得する機能を備えています。

---

## 📖 利用者向け：実行方法

Windows環境でツールを使用する方は、以下の手順に従ってください。

### 1. 実行ファイルのダウンロード
上記の [最新のリリース](#-最新のリリース-latest-releases) セクションから、必要なツールの EXE ファイルをダウンロードしてください。

### 2. フォルダ構成と配置
ツールを正常に動かすには、以下の階層構造でファイルを配置する必要があります。
**重要：実行ファイル本体が含まれるフォルダの「一つ上の階層」に `.env` ファイルを置いてください。**

```text
作業フォルダ（名前は自由）/
├── .env                          (設定ファイル：IDやパスワードを記述)
└── app/                          (名前は自由)
    ├── login.exe                 (自動ログインツール)
    └── Daikin_Report_Downloader.exe (ダイキンDLツール)
```

### 3. 設定ファイル（.env）の準備
`.env` ファイルを新規作成し、使用するツールに合わせて以下の項目を設定してください。

#### 共通・デスクネッツ関連設定
| 項目名 | 設定内容 |
| :--- | :--- |
| **DESKNETS_LOGIN_URL** | Desknet's NEO ログイン画面のURL |
| **DESKNETS_ORG_ID** | 組織（部署）の内部ID（数字） |
| **DESKNETS_NAME_VALUE** | 氏名の選択値（数字/コード） |
| **DESKNETS_PASSWORD** | Desknet's パスワード |
| **DESKNETS_MY_EMAIL_ADDRESS** | 認証用メールを受け取るアドレス |

#### ダイキンツール専用設定
| 項目名 | 設定内容 |
| :--- | :--- |
| **DAIKIN_CHEM_TRANSPRINT_URL** | ダイキン ログインURL |
| **DAIKIN_CHEM_TRANSPRINT_USER_ID** | ダイキン ユーザーID |
| **DAIKIN_CHEM_TRANSPRINT_PASSWORD** | ダイキン パスワード |
| **DAIKIN_INSPECTION_REPORT_DIR** | 保存先フォルダのフルパス |
| **DAIKIN_AUTH_CODE_SENDER_NAME** | 認証メールの差出人名 |
| **DAIKIN_AUTH_CODE_SUBJECT_KEYWORD** | 認証メールの件名キーワード |

---

### 💡 コピペ用サンプル (.env)
以下をコピーして `.env` ファイルに貼り付け、各自の環境に合わせて右側の値を書き換えてください。

```text
# --- Desknet's 共通設定 ---
DESKNETS_LOGIN_URL=https://...
DESKNETS_ORG_ID=110
DESKNETS_NAME_VALUE=1234
DESKNETS_PASSWORD=your_password
DESKNETS_MY_EMAIL_ADDRESS=your_email@example.com

# --- ダイキンツール専用設定 ---
DAIKIN_CHEM_TRANSPRINT_URL=https://...
DAIKIN_CHEM_TRANSPRINT_USER_ID=your_id
DAIKIN_CHEM_TRANSPRINT_PASSWORD=your_password
DAIKIN_INSPECTION_REPORT_DIR=C:\Users\Documents\Reports
DAIKIN_AUTH_CODE_SENDER_NAME=ダイキン工業株式会社_配信システム
DAIKIN_AUTH_CODE_SUBJECT_KEYWORD=認証コードのお知らせ
```

---

### 4. 実行
`app/` フォルダ内の各ファイルをダブルクリックして起動します。

- **初回起動時**: 「Windows によって PC が保護されました」という青い画面が出た場合は、[詳細情報] をクリックしてから [実行] を押してください。
- **要件**: PC に **Google Chrome** ブラウザがインストールされている必要があります。
- **デバッグ**: 実行中に問題が発生した場合、ウィンドウが閉じずにエラー内容を表示します。その画面を開発者に共有してください。

---

> [!IMPORTANT]
> **セキュリティに関する注意**
> `.env` ファイルには重要なログイン情報が含まれています。このファイルをメールに添付して送信したり、共有ストレージで不特定多数に公開したりしないでください。

---

## 🛠 開発者向けセットアップ (Mac)

### 依存ライブラリのインストール
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 自動ビルド
各スクリプトを更新して GitHub へ push すると、GitHub Actions により Windows 用の `.exe` が自動ビルドされます。
- **Desknet's**: `common_utils/desknets/login.py`
- **Daikin**: `apps/report_downloaders/daikin_downloader/src/inspection_report/download_inspection_report.py`
