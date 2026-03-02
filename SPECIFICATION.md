# 📚 ツール仕様書一覧 (Master Index)

本プロジェクトに含まれる自動化ツールの仕様書一覧です。詳細は各リンク先を参照してください。

## 🛠 稼働中・開発中のツール

- **Daikin Inspection Report (検査成績書ツール)**
    - [詳細仕様はこちら](./apps/report_downloaders/daikin_downloader/src/inspection_report/SPECIFICATION.md)
    - 概要：検査成績書（ZIP）をダウンロードし、自動解凍・整理を行う。

---

## 📦 共通ユーティリティ (Common Utilities)

- **Desknets Login Module**
    - [詳細仕様はこちら](./common_utils/desknets/SPECIFICATION.md)
    - 役割：デスクネッツの認証を代行し、他のツールへログイン済みドライバを提供する「部品」。

---

## 🏗 プロジェクト共通規約

本プロジェクトの開発および運用は、以下のガイドラインに準拠して行われます。

- **[GEMINI.md (協業・実装指針)](./GEMINI.md)**
    - AIを「バーチャル・チームメンバー」として迎えるための協業指針と、実務レベルの実装規律。
- **[DEVELOPMENT.md (開発プロセス)](./DEVELOPMENT.md)**
    - チーム開発を想定した標準開発フロー（SDLC）に加え、Git運用や品質管理の「思考の点検リスト」を定義。
- **[SPECIFICATION.md (Index)](./SPECIFICATION.md)**
    - プロジェクト全体の仕様目録（Master Index）。
