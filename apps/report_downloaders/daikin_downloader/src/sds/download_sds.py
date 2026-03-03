# apps/report_downloaders/daikin_downloader/src/sds/download_sds.py
#
# 概要:
#   ダイキン工業の安全データシート（SDS）ページから、
#   指定した品番の PDF を自動的に取得・保存するスクリプト。
#
# 設計方針:
#   - ターゲットURLに毎回アクセスし、最新のPDFリンクを動的に発見する。
#   - 品番名（例: "f-104"）をキーとして、href属性にその文字列を含む
#     <a>タグを検索することで、URL末尾の日付が変わっても対応可能。
#   - Seleniumへの依存を排除し、requestsとBeautifulSoupによる
#     軽量・高速なHTTPアクセスに統一している。
#   - ログイン処理は不要（SDS公開ページはログイン不要のため）。

import os
import re
import sys
import logging
import traceback
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import Optional

# ==============================================================================
# プロジェクトルートをPythonパスに追加（絶対インポートのため）
# apps/report_downloaders/daikin_downloader/src/sds/download_sds.py
# -> 6階層上がプロジェクトルート（automation_tools/）
# ==============================================================================
current_file_path = os.path.abspath(__file__)
project_root = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(current_file_path)
                )
            )
        )
    )
)
if project_root not in sys.path:
    sys.path.append(project_root)

# ロギング設定（日本語メッセージ）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_environment() -> Optional[dict]:
    """.envファイルを読み込み、設定値を辞書で返す。失敗時はNoneを返す。"""
    # EXE環境（frozen）ではexeの親フォルダを、スクリプト環境ではプロジェクトルートを探す
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        dotenv_path = os.path.join(os.path.dirname(base_path), '.env')
    else:
        dotenv_path = os.path.join(project_root, '.env')

    if not os.path.exists(dotenv_path):
        logger.error(f".env ファイルが見つかりません。パス: {dotenv_path}")
        return None

    load_dotenv(dotenv_path)
    logger.info(f".env を読み込みました: {dotenv_path}")

    config = {
        "target_url": os.getenv("DAIKIN_SDS_TARGET_URL", ""),
        "base_url": os.getenv("DAIKIN_SDS_BASE_URL", ""),
        "model_list": [
            m.strip()
            for m in os.getenv("DAIKIN_SDS_MODEL_LIST", "").split(",")
            if m.strip()
        ],
        "save_root": os.getenv("DAIKIN_SDS_SAVE_ROOT_DIR", ""),
    }

    # 必須項目のチェック
    if not all([config["target_url"], config["base_url"], config["model_list"], config["save_root"]]):
        logger.error(".env に必要な設定（URL, ベースURL, 品番リスト, 保存先）が不足しています。")
        return None

    return config


def fetch_pdf_links(target_url: str) -> list:
    """
    ターゲットURLのHTMLを取得し、全てのPDFリンクを抽出して返す。

    Returns:
        list of dict: [{"href": "...pdf", "text": "...", "lower_href": "..."}]
    """
    logger.info(f"SDSページにアクセスします: {target_url}")
    try:
        response = requests.get(target_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"ページへのアクセスに失敗しました: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # href属性が ".pdf" で終わる全リンクを取得
    pdf_links = []
    for tag in soup.find_all("a", href=True):
        href: str = tag["href"]
        if href.lower().endswith(".pdf"):
            pdf_links.append({
                "href": href,
                "lower_href": href.lower(),  # 大文字小文字を無視した検索用
            })

    logger.info(f"ページ上で {len(pdf_links)} 件のPDFリンクを発見しました。")
    return pdf_links


def find_pdf_for_model(model: str, pdf_links: list, base_url: str) -> Optional[str]:
    """
    品番名を含むPDFリンクを検索して返す。

    品番は大文字小文字を区別しない（例: "F-104" -> "f-104" で検索）。
    ハイフンの有無を考慮し、"f104"・"f-104" 両方のパターンで試みる。

    Returns:
        str | None: 発見されたPDFの絶対URL。見つからない場合はNone。
    """
    # 品番をURL照合用に正規化（例: "F-104" -> "f-104"）
    model_lower = model.lower()
    # ハイフンなしバージョンも用意（例: "f104"）
    model_no_hyphen = model_lower.replace("-", "")

    for link in pdf_links:
        lower_href = link["lower_href"]
        if model_lower in lower_href or model_no_hyphen in lower_href:
            # 相対パスの場合は絶対URLに変換
            href = link["href"]
            if href.startswith("http"):
                return href
            else:
                return base_url.rstrip("/") + "/" + href.lstrip("/")

    return None


def extract_date_from_url(pdf_url: str) -> str:
    """
    PDFのURLから更新日付を抽出し、yyyy/m/d 形式で返す。

    例:
        .../sds-f-104-J_20240516.pdf -> "2024/5/16"
        .../sds-d-210c-J_20250702.pdf -> "2025/7/2"

    日付の抽出に失敗した場合は空文字列を返す。
    """
    # "_" に続く8桁の数字（YYYYMMDD）を検索
    match = re.search(r'_(\d{8})\.pdf', pdf_url, re.IGNORECASE)
    if not match:
        return ""

    date_str = match.group(1)  # 例: "20240516"
    try:
        date_obj = datetime.strptime(date_str, "%Y%m%d")
        # ゼロ埋めなしのyyyy/m/d形式（%-mはmacOS/Linux対応）
        return f"{date_obj.year}/{date_obj.month}/{date_obj.day}"
    except ValueError:
        return ""


def download_pdf(url: str, save_path: str) -> bool:
    """
    指定されたURLからPDFをダウンロードし、save_pathに保存する。

    Returns:
        bool: 成功時True、失敗時False。
    """
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    except requests.RequestException as e:
        logger.error(f"PDFのダウンロード中にエラーが発生しました ({url}): {e}")
        return False


def main() -> None:
    """メイン処理フロー"""
    logger.info("--- SDS 自動取得処理を開始します ---")

    # --- Step 1: 設定の読み込み ---
    config = setup_environment()
    if not config:
        return

    # --- Step 2: 保存先フォルダの作成 ---
    today_str = datetime.now().strftime("%Y-%m-%d")
    save_dir = os.path.join(config["save_root"], today_str)
    os.makedirs(save_dir, exist_ok=True)
    logger.info(f"保存先フォルダ: {save_dir}")

    # --- Step 3: ページからPDFリンクを一括取得 ---
    # ページへのアクセスは1回のみ。品番ごとに繰り返すより効率的。
    pdf_links = fetch_pdf_links(config["target_url"])
    if not pdf_links:
        logger.error("PDFリンクの取得に失敗しました。処理を中断します。")
        return

    # --- Step 4: 品番ごとにPDFを検索・ダウンロード ---
    # 成功: [(品番, 日付文字列), ...]
    # 失敗: [品番, ...]
    success_models: list = []  # [(model, date_str), ...]
    missing_models: list = []  # [model, ...]

    for model in config["model_list"]:
        logger.info(f"品番処理中: {model}")

        pdf_url = find_pdf_for_model(model, pdf_links, config["base_url"])

        if not pdf_url:
            logger.warning(f"  → 品番 '{model}' のPDFが見つかりませんでした。スキップします。")
            missing_models.append(model)
            continue

        logger.info(f"  → PDFリンクを発見: {pdf_url}")

        save_path = os.path.join(save_dir, f"{model}.pdf")
        if download_pdf(pdf_url, save_path):
            date_str = extract_date_from_url(pdf_url)
            logger.info(f"  → 保存完了: {save_path} (SDS更新日: {date_str or '不明'})")
            success_models.append((model, date_str))
        else:
            logger.error(f"  → 品番 '{model}' のダウンロードに失敗しました。")
            missing_models.append(model)

    # --- Step 5: ダウンロード結果レポートの書き出し ---
    total = len(config["model_list"])
    success_count = len(success_models)
    logger.info(f"--- 処理完了: {success_count}/{total} 件取得成功 ---")

    result_log_path = os.path.join(save_dir, f"download_result_{today_str}.txt")
    with open(result_log_path, "w", encoding="utf-8") as f:
        f.write(f"実行日: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n\n")
        # --- 成功セクション ---
        f.write("【ダウンロード成功】\n")
        if success_models:
            for model, date_str in success_models:
                f.write(f"{model},{date_str}\n")
        else:
            f.write("（なし）\n")

        f.write("\n")

        # --- 失敗セクション ---
        f.write("【ダウンロード失敗】\n")
        if missing_models:
            for m in missing_models:
                f.write(f"{m}\n")
        else:
            f.write("（なし）\n")

    logger.info(f"結果レポートを保存しました: {result_log_path}")

    # 失敗があった場合のみコンソールで警告
    if missing_models:
        print("\n" + "!" * 60)
        print(f"警告: 以下の {len(missing_models)} 件の品番が見つかりませんでした。")
        for m in missing_models:
            print(f"  - {m}")
        print("!" * 60 + "\n")


if __name__ == "__main__":
    # グローバルエラーガード (GEMINI.md 準拠)
    # EXE化後にウィンドウが即座に閉じるのを防ぐため、必ずtry/finallyで囲む
    try:
        main()
    except Exception:
        print("\n" + "=" * 60)
        print("致命的なエラーによりプログラムが中断されました。")
        traceback.print_exc()
        print("=" * 60)
    finally:
        print("\n" + "-" * 60)
        input("エンターキーを押すと終了します（ウィンドウを維持中）...")
