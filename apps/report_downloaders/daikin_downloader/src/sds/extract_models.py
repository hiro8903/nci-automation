import requests
from bs4 import BeautifulSoup
import re
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# ==============================================================================
# プロジェクトルートをPythonパスに追加（.env読み込みのため）
# ==============================================================================
current_file_path = os.path.abspath(__file__)
# apps/report_downloaders/daikin_downloader/src/sds/extract_models.py
# -> 6階層上がプロジェクトルート（automation_tools/）
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

def setup_environment():
    """download_sds.py と同様のロジックで .env を読み込む"""
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
        dotenv_path = os.path.join(os.path.dirname(base_path), '.env')
    else:
        dotenv_path = os.path.join(project_root, '.env')

    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
        return True
    return False

def extract_models():
    # .env の読み込みを試行
    setup_environment()
    
    # download_sds.py と共通の変数を使用
    target_url = os.getenv("DAIKIN_SDS_TARGET_URL")
    
    if not target_url:
        print("エラー: .env ファイルに 'DAIKIN_SDS_TARGET_URL' が設定されていません。")
        print("設定を確認してから再度実行してください。")
        return
    
    print(f"Accessing: {target_url}")
    
    try:
        response = requests.get(target_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    
    pdf_links = []
    # ページ内の全リンクを走査
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.lower().endswith(".pdf"):
            # URLから品番らしき部分を抽出 (例: sds-f-104-J_20240516.pdf -> F-104)
            match = re.search(r'sds-(.+)-[A-Z]_', href, re.IGNORECASE)
            model_name = ""
            if match:
                model_name = match.group(1).upper()
            else:
                match2 = re.search(r'sds-(.+)_\d{8}', href, re.IGNORECASE)
                if match2:
                    model_name = match2.group(1).upper()
            
            if model_name:
                pdf_links.append({
                    "model": model_name,
                    "href": href
                })

    # 重複を除去してソート
    unique_models = sorted(list(set([l["model"] for l in pdf_links])))
    
    print(f"\nFound {len(unique_models)} unique models.")
    
    # --- 実行環境に応じた保存先と時刻の決定 ---
    if getattr(sys, 'frozen', False):
        # EXE実行時: EXE本体があるフォルダに保存
        script_dir = os.path.dirname(sys.executable)
    else:
        # スクリプト実行時: ファイルと同じ場所に保存
        script_dir = os.path.dirname(os.path.abspath(__file__))

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    # レポート名を英文に変更
    filename = f"daikin_sds_available_models_{timestamp_str}.txt"
    report_path = os.path.join(script_dir, filename)
    
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"--- Daikin SDS Available Models Report ---\n")
            f.write(f"Date: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n")
            f.write(f"Target URL: {target_url}\n")
            f.write(f"Models Found: {len(unique_models)}\n")
            f.write("-" * 45 + "\n\n")
            for m in unique_models:
                f.write(f"{m}\n")
        print(f"Report saved to: {report_path}")
        
        if unique_models:
            print("\n--- 品番一覧（一部抜粋） ---")
            for m in unique_models[:10]:
                print(m)
            print("...")
    except Exception as e:
        print(f"ファイルの保存中にエラーが発生しました: {e}")

if __name__ == "__main__":
    extract_models()
