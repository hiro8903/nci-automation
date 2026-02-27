import sys
import traceback
import os

# =========================================================================================
# 【重要】エラー発生時にウィンドウが即座に閉じるのを防ぐための全体ガード
# =========================================================================================
try:
    """
    Daikin工業のウェブサイトから検査レポートを自動でダウンロードするスクリプト。
    
    このファイルは、以下の主要な機能を持ちます：
    1. Seleniumを活用したブラウザ自動操作とログイン
    2. メール経由での2要素認証（認証コード）の自動解決
    3. ZIPファイルのダウンロードと、その後の自動解凍・整理
    """
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import TimeoutException, NoSuchElementException 
    import time
    from dotenv import load_dotenv
    import logging

    # -------------------------------------------------------------------------------------
    # ロギング設定：実行状況をコンソールに表示するための設定です。
    # -------------------------------------------------------------------------------------
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # -------------------------------------------------------------------------------------
    # 【最重要】インポートパスの解決ロジック
    # 実行ファイル（.exe）にした後でも、自作の部品（apps.やcommon_utils.）を
    # Pythonが正しく見つけられるように、住所録（sys.path）にプロジェクトのルートを登録します。
    # -------------------------------------------------------------------------------------
    if getattr(sys, 'frozen', False):
        # 実行ファイル（EXE）として動いている場合
        # PyInstallerが展開した一時フォルダ（_MEIPASS）がプロジェクトのルートになります。
        project_root = sys._MEIPASS
        logger.info(f"EXE実行モード：内部ルートを '{project_root}' に設定しました。")
    else:
        # 通常のPythonスクリプトとして動いている場合
        # このファイル（download_inspection_report.py）から5階層上のディレクトリがルートです。
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.normpath(os.path.join(current_script_dir, *([os.pardir] * 5)))
        logger.info(f"スクリプトモード：ルートを '{project_root}' に設定しました。")

    # Pythonの住所検索リストの先頭に、このプロジェクトのルートを追加します。
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        logger.info("プロジェクトのルートを住所検索リストに追加しました。")

    # -------------------------------------------------------------------------------------
    # 自作モジュールのインポート：住所を登録した後に実行することで、エラーを防ぎます。
    # -------------------------------------------------------------------------------------
    from apps.report_downloaders.daikin_downloader.src.common.auth_code_fetcher import fetch_auth_code 
    from common_utils.file_processing.unzip_files import unzip_and_delete_zips 

    # -------------------------------------------------------------------------------------
    # .envファイルの読み込み
    # 実行ファイルの場合は、.exeと同じフォルダ（または1つ上）に置かれた.envを探します。
    # -------------------------------------------------------------------------------------
    if getattr(sys, 'frozen', False):
        executable_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        # ユーザーに配布する際は dist フォルダの中身を出すため、
        # .exe と同じ場所、またはその親フォルダに .env があることを想定します。
        dotenv_path = os.path.join(executable_dir, '.env')
        if not os.path.exists(dotenv_path):
            dotenv_path = os.path.join(os.path.dirname(executable_dir), '.env')
    else:
        dotenv_path = os.path.join(project_root, '.env')

    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f".envファイルを読み込みました：{dotenv_path}")
    else:
        logger.warning(f"警告：.envファイルが見つかりません。パス：{dotenv_path}")

    # -------------------------------------------------------------------------------------
    # 設定値の取得（環境変数から）
    # -------------------------------------------------------------------------------------
    DOWNLOAD_PAGE_URL = os.getenv("DAIKIN_CHEM_TRANSPRINT_URL")
    AUTH_PAGE_URL = os.getenv("DAIKIN_CHEM_TRANSPRINT_AUTH_PAGE_URL") 
    USER_ID = os.getenv("DAIKIN_CHEM_TRANSPRINT_USER_ID")
    PASSWORD = os.getenv("DAIKIN_CHEM_TRANSPRINT_PASSWORD")
    DESKNETS_EMAIL_ADDRESS = os.getenv("DESKNETS_MY_EMAIL_ADDRESS") 

    def perform_auth_code_entry_and_submit(driver) -> bool:
        """ブラウザ上で認証コードを入力してログインを完成させる関数"""
        logger.info("\n--- 認証コード入力と送信処理を開始します ---")
        auth_code = fetch_auth_code() 
        if not auth_code:
            logger.error("認証コードの取得に失敗しました。")
            return False

        try:
            auth_code_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='認証コード']"))
            )
            auth_code_input.send_keys(auth_code)
            auth_send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '送信')]"))
            )
            auth_send_button.click()
            
            # ログイン成功の証拠（チェックボックス）が出るのを待つ
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "download_list_select_all")) 
            )
            return True
        except Exception as e:
            logger.error(f"認証プロセスでエラーが発生しました: {e}")
            return False

    def daikin_download_inspection_report():
        """ダイキン様のサイトからレポートをDLするメインフロー"""
        driver = None
        try:
            download_dir = os.getenv("DAIKIN_INSPECTION_REPORT_DIR")
            if not download_dir:
                logger.error("エラー：環境変数 'DAIKIN_INSPECTION_REPORT_DIR' が未設定です。")
                return
            
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)

            options = webdriver.ChromeOptions()
            prefs = {"download.default_directory": download_dir, "download.prompt_for_download": False}
            options.add_experimental_option("prefs", prefs)

            # Chromeブラウザの起動
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options) 
            driver.maximize_window()

            max_retries = 3
            login_successful = False

            for attempt in range(max_retries):
                logger.info(f"ログイン試行中 ({attempt+1}/{max_retries})...")
                driver.get(DOWNLOAD_PAGE_URL)
                
                # ID/パスワード入力
                user_id_input = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='ユーザーID']")))
                user_id_input.send_keys(USER_ID)
                password_input = driver.find_element(By.XPATH, "//input[@placeholder='パスワード']")
                password_input.send_keys(PASSWORD)
                driver.find_element(By.XPATH, "//button[contains(text(), 'ログイン')]").click()

                # メールアドレス認証
                email_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='メールアドレス']")))
                email_input.send_keys(DESKNETS_EMAIL_ADDRESS)
                driver.find_element(By.XPATH, "//button[contains(text(), '送信')]").click()

                WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "complete_dialog_ok_btn"))).click()
                time.sleep(2)

                # 認証コード入力
                if perform_auth_code_entry_and_submit(driver):
                    login_successful = True
                    break
            
            if not login_successful:
                logger.error("ログインに失敗しました。")
                return

            # 一括ダウンロード実行
            logger.info("レポートを選択してダウンロードを開始します...")
            WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "download_list_select_all"))).click()
            WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='buttonText' and text()='一括ダウンロード']"))).click()
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "confirm_dialog_ok_btn"))).click()
            
            # ダウンロード時間を考慮して長めに待機
            logger.info("ファイルを待機中（15秒）...")
            time.sleep(15)

            # ダウンロードフォルダ内のZIPを解凍して整理
            logger.info("ZIPファイルの解凍・削除処理を行います。")
            unzip_and_delete_zips(download_dir)

        finally:
            if driver:
                input("\nすべての処理が完了しました。Enterキーを押すとブラウザを閉じます...")
                driver.quit()

    if __name__ == "__main__":
        daikin_download_inspection_report()

except Exception:
    # -------------------------------------------------------------------------------------
    # 【救済措置】起動直後にエラーが出た場合でも、画面を止めます
    # -------------------------------------------------------------------------------------
    print("\n" + "!"*60)
    print("【致命的なエラー】プログラムの起動に失敗しました。")
    print("!"*60)
    traceback.print_exc()
    print("!"*60)
    input("\n上記のエラー内容を確認し、Enterキーを押して終了してください...")