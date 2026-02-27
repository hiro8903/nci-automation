import sys
import traceback

# 一瞬で閉じるのを防ぐための全体ガード
try:
    """
    ダイキン工業のウェブサイトから検査レポートを自動でダウンロードするスクリプト。
    """
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import TimeoutException, NoSuchElementException 
    import time
    import os
    from dotenv import load_dotenv
    import logging

    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # --- .envファイルのパス解決と読み込み ---
    dotenv_path = None
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        executable_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        parent_dir = os.path.abspath(os.path.join(executable_dir, os.pardir))
        dotenv_path = os.path.join(parent_dir, '.env')
        logger.info(f"実行可能ファイルモード: .envファイルを '{parent_dir}' から探します。")
    else:
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.normpath(os.path.join(current_script_dir, *([os.pardir] * 5)))
        dotenv_path = os.path.join(project_root, '.env')
        logger.info(f"スクリプト実行モード: .envファイルを '{project_root}' から探します。")

    if dotenv_path and os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f".envファイルを '{dotenv_path}' から正常に読み込みました。")
    else:
        logger.warning(f"警告: .envファイルが見つかりませんでした。指定されたパス: '{dotenv_path}'。")

    # --- パス設定 ---
    current_script_dir_run = os.path.dirname(os.path.abspath(__file__))
    project_root_mod = os.path.normpath(os.path.join(current_script_dir_run, *([os.pardir] * 5))) 
    if project_root_mod not in sys.path:
        sys.path.insert(0, project_root_mod)

    # --- カスタムモジュールのインポート ---
    from apps.report_downloaders.daikin_downloader.src.common.auth_code_fetcher import fetch_auth_code 
    from common_utils.file_processing.unzip_files import unzip_and_delete_zips 

    # --- 環境変数取得 ---
    DOWNLOAD_PAGE_URL = os.getenv("DAIKIN_CHEM_TRANSPRINT_URL")
    AUTH_PAGE_URL = os.getenv("DAIKIN_CHEM_TRANSPRINT_AUTH_PAGE_URL") 
    USER_ID = os.getenv("DAIKIN_CHEM_TRANSPRINT_USER_ID")
    PASSWORD = os.getenv("DAIKIN_CHEM_TRANSPRINT_PASSWORD")
    DESKNETS_EMAIL_ADDRESS = os.getenv("DESKNETS_MY_EMAIL_ADDRESS") 

    def perform_auth_code_entry_and_submit(driver) -> bool:
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
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "download_list_select_all")) 
            )
            return True
        except Exception as e:
            logger.error(f"認証プロセスでエラーが発生しました: {e}")
            return False

    def daikin_download_inspection_report():
        driver = None
        try:
            download_dir = os.getenv("DAIKIN_INSPECTION_REPORT_DIR")
            if not download_dir:
                logger.error("エラー: 環境変数 'DAIKIN_INSPECTION_REPORT_DIR' が未設定です。")
                return
            
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)

            options = webdriver.ChromeOptions()
            prefs = {"download.default_directory": download_dir, "download.prompt_for_download": False}
            options.add_experimental_option("prefs", prefs)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options) 
            driver.maximize_window()

            max_retries = 3
            login_successful = False

            for attempt in range(max_retries):
                driver.get(DOWNLOAD_PAGE_URL)
                user_id_input = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='ユーザーID']"))
                )
                user_id_input.send_keys(USER_ID)
                password_input = driver.find_element(By.XPATH, "//input[@placeholder='パスワード']")
                password_input.send_keys(PASSWORD)
                login_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ログイン')]")))
                login_button.click()

                email_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='メールアドレス']")))
                email_input.send_keys(DESKNETS_EMAIL_ADDRESS)
                send_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '送信')]")))
                send_button.click()

                ok_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "complete_dialog_ok_btn")))
                ok_button.click()
                time.sleep(2)

                if perform_auth_code_entry_and_submit(driver):
                    login_successful = True
                    break
            
            if not login_successful:
                logger.error("ログインに失敗しました。")
                return

            # ダウンロード処理
            select_all_checkbox = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "download_list_select_all")))
            if not select_all_checkbox.is_selected():
                select_all_checkbox.click()
            
            download_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='buttonText' and text()='一括ダウンロード']")))
            download_button.click()
            confirm_ok_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "confirm_dialog_ok_btn")))
            confirm_ok_button.click()
            
            time.sleep(10) # 完了待ち

            # 解凍処理
            unzip_and_delete_zips(download_dir)

        finally:
            if driver:
                input("\n処理が完了しました。Enterキーを押すとブラウザを閉じます...")
                driver.quit()

    if __name__ == "__main__":
        daikin_download_inspection_report()

except Exception:
    print("\n" + "!"*60)
    print("【致命的なエラー】プログラムの起動に失敗しました。")
    print("!"*60)
    traceback.print_exc()
    print("!"*60)
    input("\n上記のエラー内容を確認し、Enterキーを押して終了してください...")