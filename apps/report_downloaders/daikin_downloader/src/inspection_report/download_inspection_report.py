"""
ダイキン工業のウェブサイトから検査レポートを自動でダウンロードするスクリプト。

このスクリプトは以下の主要なステップを実行します:
1.  Selenium WebDriverを使用して、指定されたダウンロードページにアクセスします。
2.  ユーザーIDとパスワードを用いてログイン認証を行います。
3.  メールアドレスを入力して認証コードを要求し、
    別途 `automation_tools.apps.report_downloaders.daikin_downloader.src.common.auth_code_fetcher` を呼び出してメールから認証コードを取得します。
4.  取得した認証コードを入力し、本サイトへのログインを完了します。
    認証失敗時にはリトライ処理を行います。
5.  ログイン後、レポートダウンロードページで「全てチェック」のチェックボックスをクリックし、
    「一括ダウンロード」ボタンをクリックして、ZIP形式で検査レポートをダウンロードします。
6.  ダウンロード完了後、同じディレクトリ内にダウンロードされたZIPファイルを検出し、
    `automation_tools.common_utils.file_processing.unzip_files` スクリプトを呼び出して、ZIPファイルを解凍し、
    内部の全てのファイルを抽出した後に元のZIPファイルを削除します。

前提条件:
-   `.env` ファイルに、DAIKIN_CHEM_TRANSPRINT_URL、DAIKIN_CHEM_TRANSPRINT_AUTH_PAGE_URL、
    DAIKIN_CHEM_TRANSPRINT_USER_ID、DAIKIN_CHEM_TRANSPRINT_PASSWORD、
    DESKNETS_EMAIL_ADDRESS、DAIKIN_INSPECTION_REPORT_DIR が適切に設定されていること。
-   `auth_code_fetcher.py` と `unzip_files.py` が
    適切なパスに配置されており、対応するパッケージに `__init__.py` が存在すること。
-   Chromeブラウザがインストールされており、`webdriver_manager` がChromeDriverを管理できること。

使用方法:
このスクリプトを直接実行してください。自動的にブラウザが起動し、指定された操作を実行します。
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
import sys
import logging

# ロギング設定
# アプリケーション全体でログレベルとフォーマットを統一します。
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- .envファイルのパス解決と読み込み ---
# このセクションは、スクリプトが「ソースコードとして直接実行される場合」と
# 「PyInstallerでパッケージ化された実行可能ファイルとして実行される場合」の
# 両方で、正しい.envファイルを見つけるように設計されています。

dotenv_path = None # .envファイルのパスを初期化

# sys.frozen 属性でPyInstallerによってフリーズ（パッケージ化）されたかどうかを判定します。
# hasattr(sys, '_MEIPASS') は --onefile モードでの追加チェックです。
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # シナリオ1: PyInstallerでパッケージ化された実行可能ファイルとして実行された場合
    # 実行可能ファイル（例: dist/download_inspection_report.exe）はdist/フォルダ内にあり、
    # .envファイルはその一つ上の階層（配布されたアプリケーションのルートディレクトリ）に
    # 配置されることを想定しています。
    # 例: C:\App\dist\download_inspection_report.exe が C:\App\.env を参照
    
    # 実行可能ファイルがあるディレクトリのパスを取得 (例: C:\App\dist\)
    executable_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    
    # そのディレクトリの親ディレクトリのパスを取得 (例: C:\App\)
    parent_dir = os.path.abspath(os.path.join(executable_dir, os.pardir))
    
    # 親ディレクトリにある .env ファイルの完全なパスを構築
    dotenv_path = os.path.join(parent_dir, '.env')
    logger.info(f"実行可能ファイルモード: .envファイルを '{parent_dir}' から探します。")
else:
    # シナリオ2: Pythonスクリプトとして直接実行された場合
    # .envファイルがプロジェクトルート (automation_tools/) に存在することを想定しています。
    # スクリプトの現在の場所からプロジェクトルートまでディレクトリツリーを遡ります。
    # download_inspection_report.py は、
    # automation_tools/apps/report_downloaders/daikin_downloader/src/inspection_report/
    # にあるため、5階層遡ることでプロジェクトルートを特定します。
    
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(os.path.join(current_script_dir, *([os.pardir] * 5)))
    
    # プロジェクトルートにある .env ファイルの完全なパスを構築
    dotenv_path = os.path.join(project_root, '.env')
    logger.info(f"スクリプト実行モード: .envファイルを '{project_root}' から探します。")

# --- .envファイルの読み込み実行 ---
# 特定されたパスに.envファイルが存在する場合のみ読み込みます。
# 存在しない場合、load_dotenvは警告をログに出力しますが、プログラムは継続します。
if dotenv_path and os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    logger.info(f".envファイルを '{dotenv_path}' から正常に読み込みました。")
else:
    logger.warning(f"警告: .envファイルが見つかりませんでした。指定されたパス: '{dotenv_path}'。環境変数が設定されていない可能性があります。")

# --- 他のカスタムモジュールのインポートのためのパス設定（開発環境向け） ---
# この部分は、.envファイルの解決とは異なり、Pythonがカスタムモジュール（例: auth_code_fetcher）を
# 適切にインポートできるようにするためのものです。PyInstallerはモジュールを自動的にバンドルするため、
# 実行可能ファイル環境では通常このsys.path操作は不要ですが、開発環境でのスクリプト直接実行をサポートします。
current_script_dir_for_src_run = os.path.dirname(os.path.abspath(__file__))
# プロジェクトルートへの相対パスを計算（上記.env解決ロジックの project_root と同じ計算）
project_root_for_modules = os.path.normpath(os.path.join(current_script_dir_for_src_run, *([os.pardir] * 5))) 

if project_root_for_modules not in sys.path:
    sys.path.insert(0, project_root_for_modules) # sys.pathの先頭に追加し、検索パスの優先度を上げます。
    logger.info(f"開発環境向け: '{project_root_for_modules}' をsys.pathに追加しました。")


# --- カスタムモジュールのインポート ---
# アプリケーションの他の部分で定義されたカスタムロジックをインポートします。
try:
    # 認証コード取得モジュールをインポート
    from apps.report_downloaders.daikin_downloader.src.common.auth_code_fetcher import fetch_auth_code 
    logger.info("モジュール 'auth_code_fetcher.py' から 'fetch_auth_code' を正常にインポートしました。")
except ImportError as e:
    logger.error(f"エラー: 'auth_code_fetcher' モジュールのインポートに失敗しました: {e}")
    logger.error("次の点を確認してください: 'auth_code_fetcher.py' の正しい配置、および親ディレクトリに '__init__.py' ファイルが存在すること。")
    sys.exit(1) # インポート失敗は致命的なエラーとしてプログラムを終了

try:
    # ZIPファイル解凍モジュールをインポート
    # common_utils/file_processing/unzip_files.py の中に 'unzip_and_delete_zips' 関数が存在することを想定しています。
    from common_utils.file_processing.unzip_files import unzip_and_delete_zips 
    logger.info("モジュール 'unzip_files.py' から 'unzip_and_delete_zips' を正常にインポートしました。")
except ImportError as e:
    logger.error(f"エラー: 'unzip_files' モジュールのインポートに失敗しました: {e}")
    logger.error("次の点を確認してください: 'unzip_files.py' の正しい配置、および親ディレクトリに '__init__.py' ファイルが存在すること。")
    sys.exit(1) # インポート失敗は致命的なエラーとしてプログラムを終了


# --- 環境変数から設定値を取得 ---
# `.env` ファイルに設定された各種URL、認証情報を取得します。
DOWNLOAD_PAGE_URL = os.getenv("DAIKIN_CHEM_TRANSPRINT_URL")
AUTH_PAGE_URL = os.getenv("DAIKIN_CHEM_TRANSPRINT_AUTH_PAGE_URL") 
USER_ID = os.getenv("DAIKIN_CHEM_TRANSPRINT_USER_ID")
PASSWORD = os.getenv("DAIKIN_CHEM_TRANSPRINT_PASSWORD")
DESKNETS_EMAIL_ADDRESS = os.getenv("DESKNETS_MY_EMAIL_ADDRESS") 

# 環境変数が設定されているか確認
if not all([DOWNLOAD_PAGE_URL, AUTH_PAGE_URL, USER_ID, PASSWORD, DESKNETS_EMAIL_ADDRESS]):
    logger.error("エラー: 必要な環境変数がすべて設定されていません。'.env' ファイルを確認してください。")
    sys.exit(1) # 必須環境変数がない場合は終了


def perform_auth_code_entry_and_submit(driver: webdriver.Chrome) -> bool:
    """
    ウェブサイトでの認証コード入力と送信処理を実行します。
    認証コードの取得から、入力、送信ボタンのクリック、およびその後のページ遷移（成功または失敗）を扱います。

    Args:
        driver (webdriver.Chrome): Selenium WebDriverインスタンス。

    Returns:
        bool: 認証成功時はTrue、失敗時はFalseを返します。
    """
    logger.info("\n--- 認証コード取得から入力処理を開始します ---")
    
    # 認証コードを外部モジュール (auth_code_fetcher.py) から取得
    logger.info("auth_code_fetcher の 'fetch_auth_code' を呼び出して認証コードを取得します。")
    auth_code = fetch_auth_code() 
    
    if not auth_code:
        logger.error("認証コードの取得に失敗しました。プログラムを続行できません。")
        return False # 認証コードが取得できなかった場合は失敗

    logger.info(f"認証コード [{auth_code}] を取得しました。")

    # 認証コード入力欄に取得したコードを貼り付け
    logger.info("認証コード入力欄を探しています...")
    try:
        auth_code_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='認証コード']"))
        )
        auth_code_input.send_keys(auth_code)
        logger.info(f"認証コードを入力しました。")
        logger.debug(f"入力フィールドの値: {auth_code_input.get_attribute('value')}")
    except TimeoutException:
        logger.error("エラー: 認証コード入力欄が時間内に見つかりませんでした。")
        return False

    # 認証コード送信ボタンをクリック
    logger.info("認証コード送信ボタンを探しています...")
    try:
        auth_send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '送信')]"))
        )
        auth_send_button.click()
        logger.info("認証コード送信ボタンをクリックしました。")
        logger.debug(f"認証コード送信後の現在のURL: {driver.current_url}")
    except TimeoutException:
        logger.error("エラー: 認証コード送信ボタンが時間内に見つからないか、クリックできませんでした。")
        return False

    # 認証コード送信後の結果を判定
    try:
        # ログイン成功後のダウンロードページの特定の要素が表示されるのを待機
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "download_list_select_all")) 
        )
        logger.info("認証コード認証に成功し、ダウンロードページに遷移しました。")
        return True # 成功

    except TimeoutException:
        # 認証失敗時のエラーメッセージやダイアログが出現するか確認
        try:
            # エラーダイアログのヘッダーやメッセージ要素を待機
            error_dialog_header = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'header') and text()='エラー']"))
            )
            error_message_text_elem = driver.find_element(By.XPATH, "//div[@id='messages_box']/div[contains(text(), '認証に失敗しました。')]")
            
            logger.error(f"エラー: 認証コードの入力に失敗しました。メッセージ: '{error_message_text_elem.text}'")

            # エラーダイアログのOKボタンをクリックして閉じる
            logger.info("エラーダイアログの「OK」ボタンをクリックします。")
            alert_ok_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "alert_dialog_ok_btn"))
            )
            alert_ok_button.click()
            logger.info("エラーダイアログの「OK」ボタンをクリックしました。")
            time.sleep(1) # ダイアログが閉じるのを待つ

            return False # 認証失敗

        except TimeoutException:
            logger.error("エラー: 認証失敗時のエラーダイアログが出現しませんでした（予期せぬタイムアウト）。")
            return False
        except Exception as e:
            logger.error(f"エラー: 認証失敗時のエラーメッセージ/ダイアログ処理中に予期せぬエラーが発生しました: {e}")
            return False
    
    except Exception as e:
        logger.error(f"エラー: 認証コード送信後のページ遷移確認中に予期せぬエラーが発生しました: {e}")
        return False

def daikin_download_inspection_report():
    """
    ダイキン工業のウェブサイトからの検査レポートダウンロードと、それに続くZIPファイル処理の
    メインフローを管理する関数です。
    """
    driver = None # WebDriverインスタンスの初期化

    try:
        logger.info("Selenium WebDriverを初期化しています。ChromeDriverManagerが自動で適切なChromeDriverをダウンロード・設定します。")
        
        # ダウンロードディレクトリのパスを取得し、存在しない場合は作成
        download_dir = os.getenv("DAIKIN_INSPECTION_REPORT_DIR")
        if not download_dir:
            logger.error("エラー: 環境変数 'DAIKIN_INSPECTION_REPORT_DIR' が設定されていません。")
            logger.error("ダウンロードファイルの保存先が不明なため、処理を中断します。")
            return
        
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            logger.info(f"ダウンロードディレクトリ '{download_dir}' を作成しました。")

        # Chrome WebDriverのオプション設定
        # ダウンロードパスの指定や、自動ダウンロードの有効化などを行います。
        options = webdriver.ChromeOptions()
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False, # ダウンロード確認ダイアログを表示しない
            "download.directory_upgrade": True,
            "safeBrowse.enabled": True # セーフブラウジングを有効にする（任意）
        }
        options.add_experimental_option("prefs", prefs)

        # WebDriverの初期化
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options) 
        driver.maximize_window() # ブラウザウィンドウを最大化
        logger.debug("WebDriverが初期化され、ダウンロード設定が適用されました。")

        # --- 認証コード入力とログインの繰り返し処理 ---
        max_retries = 3 # 認証リトライの最大回数を設定
        login_successful = False

        for attempt in range(max_retries):
            logger.info(f"\n--- ログイン試行: {attempt + 1}/{max_retries}回目 ---")
            
            # ブラウザを初期状態に戻すため、ログインページに再アクセス
            logger.info(f"ログインページ [{DOWNLOAD_PAGE_URL}] にアクセスしています...")
            driver.get(DOWNLOAD_PAGE_URL)
            logger.debug(f"現在のURL: {driver.current_url}")

            # ユーザーIDとパスワードの入力
            logger.info("ユーザーID入力欄を探しています...")
            user_id_input = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='ユーザーID']"))
            )
            user_id_input.send_keys(USER_ID)
            logger.info(f"ユーザーIDを入力しました。")

            logger.info("パスワード入力欄を探しています...")
            password_input = driver.find_element(By.XPATH, "//input[@placeholder='パスワード']")
            password_input.send_keys(PASSWORD)
            logger.info(f"パスワードを入力しました。")

            logger.info("ログインボタンを探しています...")
            login_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ログイン')]"))
            )
            login_button.click()
            logger.info("ログインボタンをクリックしました。")
            logger.debug(f"ログインボタンクリック後の現在のURL: {driver.current_url}")

            # メールアドレス送信フェーズ
            logger.info("メールアドレス入力欄を探しています...")
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='メールアドレス']"))
            )
            email_input.send_keys(DESKNETS_EMAIL_ADDRESS)
            logger.info(f"メールアドレスを入力しました。")

            logger.info("メール送信ボタンを探しています...")
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '送信')]"))
            )
            send_button.click()
            logger.info("メール送信ボタンをクリックしました。")
            logger.debug(f"メール送信ボタンクリック後の現在のURL: {driver.current_url}")

            # メッセージウィンドウのOKボタンが出現するのを待機し、クリック
            logger.info("メッセージウィンドウのOKボタンが出現するのを待っています...")
            ok_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "complete_dialog_ok_btn"))
            )
            ok_button.click()
            logger.info("OKボタンをクリックしました。")
            logger.debug(f"OKボタンクリック後の現在のURL: {driver.current_url}")
            time.sleep(2) # 画面遷移のための短い待機

            # 認証コード入力と送信の実行
            login_successful = perform_auth_code_entry_and_submit(driver)
            
            if login_successful:
                break # ログイン成功したらリトライループを抜ける
            else:
                logger.warning(f"認証コード入力またはログインに失敗しました。再試行します...")
                time.sleep(3) # 次の試行まで少し待つ

        if not login_successful:
            logger.error(f"エラー: 認証コード入力とログインに {max_retries}回試行しましたが、全て失敗しました。処理を終了します。")
            return # ログインに失敗した場合は、これ以上処理を続行せず終了

        logger.info("\n--- ログイン処理が完了しました！ ---")
        logger.info("最終ページへの遷移を確認するため、数秒間待機します。")
        time.sleep(5) # ページが完全に読み込まれるのを待つ

        # --- レポート選択とダウンロード処理 ---
        logger.info("レポートダウンロード処理を開始します。")

        # 「全てチェック」のチェックボックスをクリックして、全てのレポートを選択
        try:
            logger.info("「全てチェック」のチェックボックスを探しています...")
            select_all_checkbox = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "download_list_select_all"))
            )
            
            if not select_all_checkbox.is_selected(): # まだチェックされていない場合のみクリック
                select_all_checkbox.click()
                logger.info("「全てチェック」のチェックボックスをクリックしました。")
            else:
                logger.info("「全てチェック」のチェックボックスは既にチェックされています。")
            
            time.sleep(2) # UI反映のための短い待機
            logger.debug(f"「全てチェック」のチェックボックスの状態: {select_all_checkbox.is_selected()}")

        except TimeoutException:
            logger.error("エラー: 「全てチェック」のチェックボックスが時間内に見つからないか、クリックできませんでした。セレクタを確認してください。")
            return # エラー発生時は終了
        except Exception as e:
            logger.error(f"エラー: 「全てチェック」のチェックボックスのクリック中に予期せぬエラーが発生しました: {e}")
            return # エラー発生時は終了

        logger.info("全てのレポートのダウンロード準備ができました。")
        
        # 「一括ダウンロード」ボタンをクリック
        try:
            logger.info("「一括ダウンロード」ボタンを探しています...")
            download_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@id='buttonText' and text()='一括ダウンロード']"))
            )
            download_button.click()
            logger.info("「一括ダウンロード」ボタンをクリックしました。")
            
            # ダウンロード確認ダイアログの「OK」ボタンをクリック
            logger.info("ダウンロード確認ウィンドウの「OK」ボタンを探しています...")
            confirm_ok_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "confirm_dialog_ok_btn"))
            )
            confirm_ok_button.click()
            logger.info("ダウンロード確認ウィンドウの「OK」ボタンをクリックしました。")
            
            time.sleep(2) # ダイアログが閉じるのを待つ

        except TimeoutException as e: 
            logger.error(f"エラー: ダウンロードボタンまたは確認ウィンドウの「OK」ボタンが時間内に見つからないか、クリックできませんでした。詳細: {e}")
            logger.error("WebサイトのHTML構造が変更された可能性があります。セレクタを確認してください。")
            return # エラー発生時は終了
        except Exception as e: 
            logger.error(f"エラー: ダウンロードボタンまたは確認ウィンドウの「OK」ボタンのクリック中に予期せぬエラーが発生しました: {e}")
            return # エラー発生時は終了

        logger.info("ダウンロードが開始されました。指定されたディレクトリにファイルが保存されるのを待っています。")
        logger.info(f"ダウンロードディレクトリ '{download_dir}' 内でダウンロード完了を待機します...")
        time.sleep(10) # ダウンロードが完了するまで十分な時間を確保

        logger.info("ダウンロード処理が完了したか確認してください。")

        # --- ダウンロード後のファイル処理（ZIP解凍と削除）---
        logger.info("ダウンロードされたZIPファイルの解凍処理を開始します。")
        
        # DAIKIN_INSPECTION_REPORT_DIR 環境変数の値を取得 (既にdownload_dirで取得済みですが、念のため)
        target_download_dir = os.getenv("DAIKIN_INSPECTION_REPORT_DIR")

        if target_download_dir: # ディレクトリが設定されているか確認
            try:
                # 外部モジュール 'unzip_files.py' の 'unzip_and_delete_zips' 関数を直接呼び出し
                unzip_success = unzip_and_delete_zips(target_download_dir) 
                if unzip_success:
                    logger.info("ZIPファイル解凍処理が完了しました。")
                else:
                    logger.warning("ZIPファイル解凍処理中に問題が発生しました。詳細はログを確認してください。")
            except Exception as e:
                logger.error(f"エラー: ZIPファイル解凍処理の呼び出し中に予期せぬエラーが発生しました: {e}")
        else:
            logger.warning("環境変数 'DAIKIN_INSPECTION_REPORT_DIR' が設定されていないため、ZIPファイル処理をスキップします。")

    except Exception as e:
        # 予期せぬグローバルエラーのキャッチ
        logger.error(f"\n!!! グローバルエラーが発生しました: {e} !!!")
        logger.error("プログラムの実行中に予期せぬ問題が発生しました。エラーメッセージを確認してください。")
        if driver:
            # エラー発生時のデバッグ情報（スクリーンショットは任意で実装）
            # screenshot_path = os.path.join(os.getcwd(), f"error_screenshot_{time.time()}.png")
            # driver.save_screenshot(screenshot_path)
            # logger.error(f"エラー発生時のスクリーンショットを保存しました: {screenshot_path}")
            logger.error(f"エラー発生時のURL: {driver.current_url}")
            logger.error(f"エラー発生時のページのタイトル: {driver.title}")
            logger.debug(f"エラー発生時のHTMLソースの冒頭: \n{driver.page_source[:2000]}...")
    finally:
        # プログラム終了前にWebDriverを確実にクリーンアップ
        if driver:
            input("\n操作が完了しました。ブラウザを閉じるにはEnterキーを押してください...")
            driver.quit()
            logger.info("ブラウザを閉じました。")
        else:
            logger.warning("WebDriverが初期化されなかったため、ブラウザを閉じる操作はスキップされました。")

# スクリプトが直接実行された場合の処理
if __name__ == "__main__":
    daikin_download_inspection_report()