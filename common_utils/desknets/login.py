# common_utils/desknets/login.py

import os
import time
import logging

import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# .envファイルの読み込み
current_dir = os.path.dirname(os.path.abspath(__file__))
# .env は automation_tools/ にあるため、common_utils/desknets/ からは ../../.env
dotenv_path = os.path.join(current_dir, os.pardir, os.pardir, '.env')

# PyInstallerでパッケージ化された場合の.envパスも考慮
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    base_path_for_frozen = os.path.abspath(os.path.join(os.path.dirname(sys.executable), os.pardir))
    dotenv_path = os.path.join(base_path_for_frozen, '.env')
    logger.info(f"PyInstaller実行検知 (login.py)。dotenv_path: {dotenv_path}")
elif not os.path.exists(dotenv_path): # 通常のスクリプト実行パスが間違っていた場合のフォールバック
    project_root_for_fallback = os.path.abspath(os.path.join(current_dir, os.pardir, os.pardir, os.pardir))
    dotenv_path = os.path.join(project_root_for_fallback, '.env')
    logger.info(f"フォールバックパス (login.py)。dotenv_path: {dotenv_path}")

if not os.path.exists(dotenv_path):
    logger.error(f"エラー: .envファイルが見つかりません。login.py からのパス: {dotenv_path}")
else:
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f".envファイルを '{dotenv_path}' から正常に読み込みました (login.py)。")

# 環境変数の読み込み
LOGIN_URL = os.getenv("DESKNETS_LOGIN_URL")
ORG_ID_TO_SELECT = os.getenv("DESKNETS_ORG_ID")
NAME_VALUE = os.getenv("DESKNETS_NAME_VALUE")
PASSWORD = os.getenv("DESKNETS_PASSWORD")

def login_and_get_driver(download_directory=None):
    """
    desknet's NEOにログインし、成功すればWebDriverオブジェクトを返す。
    download_directory が指定された場合はそのディレクトリをダウンロード先として設定する。
    指定が無い場合は、ブラウザのデフォルトダウンロードディレクトリを使用する。
    失敗した場合はNoneを返す。
    """
    if not all([LOGIN_URL, ORG_ID_TO_SELECT, NAME_VALUE, PASSWORD]):
        logger.error("エラー: .envファイルに必要なログイン情報が設定されていません。login.pyで確認してください。")
        return None

    service = Service(ChromeDriverManager().install())
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3") # INFO, WARNING, ERRORのみ表示

    # --- ダウンロードディレクトリの設定ロジックを修正 ---
    # ⭐ download_directory が指定された場合のみ prefs を設定 ⭐
    if download_directory:
        # 指定されたディレクトリが存在しなければ作成
        os.makedirs(download_directory, exist_ok=True)
        prefs = {
            "download.default_directory": download_directory,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safeBrowse.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        logger.info(f"ダウンロードパスを '{download_directory}' に設定しました。")
    else:
        logger.info("ダウンロードパスは明示的に設定されませんでした。ブラウザのデフォルトダウンロードディレクトリが使用されます。")
    # -------------------------------------------------------------------

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("WebDriverを正常に初期化しました。")

        main_window_handle = driver.current_window_handle
        logger.debug(f"初期メインウィンドウハンドル: {main_window_handle}")

        driver.get(LOGIN_URL)
        logger.info(f"ログインページを開きました: {LOGIN_URL}")

        org_select_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "jco-sel-btn")))
        org_select_button.click()
        logger.info("「組織選択」ボタンをクリックしました。")
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "co-listview-tree")))

        organization_link = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, f"//li[@data-id='{ORG_ID_TO_SELECT}']/a")))
        organization_link.click()
        logger.info(f"モーダル内で組織 (data-id='{ORG_ID_TO_SELECT}') をクリックしました。")
        WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.CLASS_NAME, "co-listview-tree")))

        uid_select_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "uid")))
        time.sleep(0.5)
        select = Select(uid_select_element)
        select.select_by_value(NAME_VALUE)
        logger.info(f"氏名 '{NAME_VALUE}' を選択しました。")

        password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "_word")))
        password_input.send_keys(PASSWORD)
        logger.info("パスワードを入力しました。")

        login_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "login-btn")))
        login_button.click()
        logger.info("ログインボタンをクリックしました。")

        try:
            username_display = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "dn-h-username")))
            logger.info(f"ユーザー名表示要素 ('dn-h-username') を確認しました。")

            all_handles = driver.window_handles
            if len(all_handles) > 1:
                logger.warning(f"複数のウィンドウ/タブが検出されました: {all_handles}")
                for handle in all_handles:
                    if handle != main_window_handle:
                        try:
                            driver.switch_to.window(handle)
                            if "about:blank" in driver.current_url or "dneo.cgi?cmd=login" in driver.current_url:
                                logger.info(f"不要なウィンドウ '{handle}' ({driver.current_url}) を閉じます。")
                                driver.close()
                        except WebDriverException as switch_e:
                            logger.warning(f"ウィンドウ切り替えまたは閉じに失敗しました '{handle}': {switch_e}")
                driver.switch_to.window(main_window_handle)
                logger.info(f"メインウィンドウ '{main_window_handle}' に切り替えました。")
            else:
                logger.info("単一のウィンドウ/タブのみ検出されました。")

            logger.info(f"ログイン後のURL (現在のウィンドウ): {driver.current_url}")
            logger.info(f"ログイン後のページのタイトル (現在のウィンドウ): {driver.title}")
            logger.info("ログインに成功しました！")

            return driver

        except TimeoutException:
            logger.error("ログイン後の期待する要素が表示されませんでした（タイムアウト）。ログイン失敗の可能性あり。")
            logger.error(f"現在のURL: {driver.current_url}")
            logger.error(f"現在のページのタイトル: {driver.title}")
            logger.error("現在のページのHTMLソースの冒頭（デバッグ用）：")
            logger.error(driver.page_source[:2000])
            driver.quit()
            return None
        except Exception as e:
            logger.error(f"ログイン成功確認中に予期せぬエラーが発生しました: {e}", exc_info=True)
            if driver: driver.quit()
            return None

    except WebDriverException as e:
        logger.error(f"WebDriver関連のエラーが発生しました: {e}", exc_info=True)
        if driver: driver.quit()
        return None
    except Exception as e:
        logger.error(f"ログイン処理中に予期せぬエラーが発生しました: {e}", exc_info=True)
        if driver: driver.quit()
        return None

# このファイル単体で実行されたときのテスト用コード
if __name__ == "__main__":
    logger.info("--- login.py を単体でテスト実行します ---")
    # 単体実行時、引数なしで呼び出すとブラウザのデフォルトダウンロードディレクトリが使用される
    test_driver = login_and_get_driver() 
    if test_driver:
        input("ログイン後の状態を確認するため、ブラウザを閉じるにはEnterキーを押してください...")
        test_driver.quit()
        logger.info("ブラウザを閉じました。")
    else:
        logger.error("ログインテストに失敗しました。")
        print("\n" + "="*50)
        print("【原因を確認してください】")
        print("上に表示されている赤い 'ERROR' の内容を確認してください。")
        print("="*50)
        input("\nEnterキーを押すとウィンドウを閉じます...")