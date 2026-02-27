import time
import re
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# WebDriver関連のインポートはnavigate_webmail_and_update.pyで処理されているため、
# ここでは不要な場合があるが、明示的に残しても問題なし
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains

# プロジェクトのルートディレクトリを特定し、sys.path に追加します
if getattr(sys, 'frozen', False):
    # PyInstaller実行環境 (EXE内)
    project_root = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.argv[0])))
else:
    # 通常実行環境
    # auth_code_fetcher.py (common/) -> src/ -> daikin_downloader/ -> report_downloaders/ -> apps/ -> automation_tools/
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(os.path.join(current_script_dir, *([os.pardir] * 5)))

# プロジェクトルート自体を追加
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# common_utils/desknets を追加 (既存のインポート形式を維持するため)
desknets_module_path = os.path.join(project_root, 'common_utils', 'desknets')
if desknets_module_path not in sys.path:
    sys.path.append(desknets_module_path)

# navigate_webmail_and_update から navigate_to_webmail_and_update 関数をインポート
# プロジェクトルートが登録されているため、絶対パス形式でも相対形式でも解決可能です
try:
    from navigate_webmail_and_update import navigate_to_webmail_and_update
except ImportError:
    from common_utils.desknets.navigate_webmail_and_update import navigate_to_webmail_and_update

# .env ファイルをロード
load_dotenv()

def fetch_auth_code():
    """
    更新されたウェブメールリストから、特定の差出人名と件名キーワードに合致するメールのうち、
    最も新しい日時の認証コードを取得します。
    """
    print("--- 認証コード取得処理を開始します ---")

    driver = None
    auth_code = None
    new_mail_body_window_handle = None

    try:
        # navigate_to_webmail_and_update() がメールリストタブにフォーカスしたドライバーを返す
        # このdriverはウェブメール専用の新しいブラウザインスタンスであると想定
        driver = navigate_to_webmail_and_update()

        if driver is None:
            print("エラー: ウェブメールナビゲーションまたは更新に失敗したため、認証コードの取得を中断します。\n")
            return None

        wait = WebDriverWait(driver, 20) # 全体の待機時間

        print(f"DEBUG: 初期メールリストタブのURL: {driver.current_url}")
        print(f"DEBUG: 初期メールリストタブのタイトル: {driver.title}\n")

        print("--- 新着メールからの認証コード取得を開始します ---\n")

        sender_name = os.getenv("DAIKIN_AUTH_CODE_SENDER_NAME")
        subject_keyword = os.getenv("DAIKIN_AUTH_CODE_SUBJECT_KEYWORD")
        
        if not sender_name or not subject_keyword:
            print("エラー: .envファイルにDAIKIN_AUTH_CODE_SENDER_NAMEまたはDAIKIN_AUTH_CODE_SUBJECT_KEYWORDが設定されていません。\n")
            return None

        try:
            print(f"差出人: '{sender_name}', 件名キーワード: '{subject_keyword}' のメールを検索しています...\n")

            mail_rows_xpath = (
                f"//tr["
                f".//td[contains(@class, 'mail-table-cell-from')]//div[normalize-space(.)='{sender_name}'] and " 
                f".//td[contains(@class, 'mail-table-cell-subject')]//div[normalize-space(.)='{subject_keyword}'] and " 
                f".//td[contains(@class, 'mail-table-cell-datetime')]//div[contains(@class, 'com_table-box') and contains(@style, 'width:130px')]" 
                f"]"
            )
            
            # メールリストが正しくロードされるまで待機（現在のタブ/ウィンドウで）
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.com_table-table tbody tr")))
            
            matching_mail_rows = driver.find_elements(By.XPATH, mail_rows_xpath)
            
            if not matching_mail_rows:
                print(f"エラー: 差出人 '{sender_name}' かつ件名に '{subject_keyword}' を含むメールが見つかりませんでした。\n")
                print("現在のページのHTMLソースの冒頭（デバッグ用）：")
                if driver:
                    print(driver.page_source[:2000])
                    driver.save_screenshot("email_search_no_match.png")
                return None

            latest_mail_row = None
            latest_mail_datetime = None

            print("--- 該当メールの時刻解析を開始します ---\n")
            for i, row in enumerate(matching_mail_rows):
                try:
                    date_time_div = row.find_element(By.XPATH, 
                        ".//td[contains(@class, 'mail-table-cell-datetime')]//div[contains(@class, 'com_table-box') and contains(@style, 'width:130px')]")
                    date_time_text = date_time_div.text.strip()
                    
                    current_year = datetime.now().year
                    full_date_time_str = f"{current_year}/{date_time_text}"
                    
                    mail_datetime = datetime.strptime(full_date_time_str, "%Y/%m/%d %H:%M")

                    if latest_mail_datetime is None or mail_datetime > latest_mail_datetime:
                        latest_mail_datetime = mail_datetime
                        latest_mail_row = row 
                        print(f"DEBUG: 最新メール候補更新: Index {i}, Time: {mail_datetime}")
                except StaleElementReferenceException:
                    print("WARN: StaleElementReferenceExceptionが発生しました。次の要素に進みます.\n")
                    continue 
                except NoSuchElementException:
                    print(f"WARN: 日時要素が見つかりませんでした (row index: {i})。HTMLを確認してください.\n")
                    continue
                except ValueError as ve:
                    print(f"WARN: 日時フォーマットエラー: '{date_time_text}' を解析できませんでした (row index: {i}, error: {ve}).\n")
                    continue
                except Exception as e:
                    print(f"WARN: メールの日時解析中に予期せぬエラーが発生しました: {e} for row index: {i}.\n")
                    continue 
            print("\n--- 該当メールの時刻解析を完了しました ---\n")


            if latest_mail_row:
                print(f"最も新しい日時 ({latest_mail_datetime.strftime('%m/%d %H:%M')}) のメールを特定しました。クリックを試みます.\n")
                
                target_click_element_xpath = (
                    f".//td[contains(@class, 'mail-table-cell-subject')]//div[normalize-space(.)='{subject_keyword}']"
                )

                try:
                    target_email_subject_div = wait.until(
                        lambda d: latest_mail_row.find_element(By.XPATH, target_click_element_xpath)
                    )
                    wait.until(EC.element_to_be_clickable(target_email_subject_div)) 

                    # ★追加デバッグ情報★ クリック前のウィンドウハンドルリスト
                    print(f"DEBUG: ダブルクリック前のウィンドウハンドルリスト: {driver.window_handles}\n")
                    all_handles_before_click = driver.window_handles

                    actions = ActionChains(driver)
                    actions.double_click(target_email_subject_div).perform()
                    print("最新の認証コードメールをダブルクリックしました.\n")
                    
                    # ダブルクリック後に少し待機して、新しいウィンドウが開くのを待つ
                    time.sleep(3) # 少し長めに待つ

                    # 新しいウィンドウに切り替える処理
                    new_mail_body_window_handle = None
                    
                    # ★切り替えロジックとデバッグ情報★
                    print(f"DEBUG: ダブルクリック後のウィンドウハンドルリスト: {driver.window_handles}\n")
                    
                    print("--- 新しいウィンドウの特定と切り替えを開始します (確認ロジックなし) ---\n")
                    # 新しいウィンドウが出現するまで最大15秒待機 (0.5秒ごとにチェック、合計30回)
                    for attempt in range(30):
                        current_handles = driver.window_handles
                        print(f"DEBUG: 切り替え試行 {attempt+1}/{30}: 現在のハンドル数: {len(current_handles)}")
                        
                        if len(current_handles) > len(all_handles_before_click): # 新しいウィンドウが開いたか
                            for handle in current_handles:
                                if handle not in all_handles_before_click: # クリック前に存在しなかったハンドルが新しいタブ
                                    # 最初の新しいハンドルを目的のウィンドウとして設定し、すぐに切り替えてループを抜ける
                                    new_mail_body_window_handle = handle
                                    print(f"INFO: 新しいウィンドウを特定しました。ハンドル: {new_mail_body_window_handle}\n")
                                    try:
                                        driver.switch_to.window(new_mail_body_window_handle)
                                        print(f"DEBUG: 特定された新しいウィンドウのURL: {driver.current_url}")
                                        print(f"DEBUG: 特定された新しいウィンドウのタイトル: {driver.title}\n")
                                    except Exception as e:
                                        print(f"WARN: 特定したウィンドウ {new_mail_body_window_handle} の切り替えまたは情報取得中にエラー: {e}\n")
                                    break # 目的のウィンドウが見つかったので内側のループを抜ける
                        
                        if new_mail_body_window_handle: # 新しいハンドルが見つかったら、外側のループも抜ける
                            break
                        
                        time.sleep(0.5) # まだ見つかっていなければ待機

                    print("--- 新しいウィンドウの特定と切り替えを完了しました ---\n")

                    if new_mail_body_window_handle:
                        # 確実に目的のウィンドウにフォーカスを当てる
                        driver.switch_to.window(new_mail_body_window_handle)
                        print(f"INFO: 最終的に新しいウィンドウ '{new_mail_body_window_handle}' に切り替えました.\n")
                        print(f"新しく開いたウィンドウのURL: {driver.current_url}")
                        print(f"新しく開いたウィンドウのタイトル: {driver.title}\n")
                        
                        # --- ここからメール本文取得の強化ロジック ---
                        email_text = None
                        try:
                            # 1. まずiframeの存在をチェックし、存在すればiframeに切り替える
                            try:
                                print("DEBUG: iframeが存在するか確認しています...\n")
                                iframe = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                                )
                                driver.switch_to.frame(iframe)
                                print("DEBUG: iframeに切り替えました.\n")
                                mail_body_element = WebDriverWait(driver, 10).until(
                                    EC.visibility_of_element_located((By.TAG_NAME, "body")) 
                                )
                                email_text = mail_body_element.text
                                print("DEBUG: iframe内のメール本文を取得しました.\n")
                            except TimeoutException:
                                print("DEBUG: iframeが見つからないか、iframe内のbodyタグのロードに時間がかかっています。直接bodyタグから取得を試みます.\n")
                                driver.switch_to.default_content() # もし以前にiframeに切り替わっていた場合、親フレームに戻る
                                mail_body_element = WebDriverWait(driver, 10).until(
                                    EC.visibility_of_element_located((By.TAG_NAME, "body")) 
                                )
                                email_text = mail_body_element.text
                                print("DEBUG: iframeなしで直接bodyタグからメール本文を取得しました.\n")
                            
                            # 2. 取得したメール本文が空でないことを確認
                            if not email_text or email_text.strip() == "":
                                print("WARN: 取得したメール本文が空、または空白のみです。表示されるまでさらに待機を試みます.\n")
                                time.sleep(5) 
                                email_text = driver.find_element(By.TAG_NAME, "body").text # 再度取得を試みる
                                if not email_text or email_text.strip() == "":
                                    print("WARN: 待機後もメール本文が取得できませんでした.\n")
                                    email_text = None # 取得失敗として扱う

                        except TimeoutException:
                            print("エラー: メール本文要素（bodyタグまたはiframe内）が新しいウィンドウで表示されませんでした（タイムアウト）。HTML構造を確認してください.\n")
                            if driver:
                                driver.save_screenshot("mail_body_timeout_new_window.png")
                            return None # メール本文が取得できない場合は処理中断
                        except Exception as e:
                            print(f"メール本文の取得中に予期せぬエラーが発生しました: {e}\n")
                            if driver:
                                driver.save_screenshot("mail_body_acquisition_error.png")
                            return None # メール本文が取得できない場合は処理中断


                        # --- 認証コード抽出ロジック ---
                        if email_text:
                            print("メール本文を取得しました.\n")
                            
                            print(f"DEBUG: 取得したメール本文の冒頭（最大1000文字）: \n{email_text[:1000]}...\n") 

                            auth_code_match = re.search(r'認証コードのお知らせ.*?(\d{6})', email_text, re.DOTALL)

                            if auth_code_match:
                                auth_code = auth_code_match.group(1) 
                                print(f"--- 認証コードを取得しました: {auth_code} ---\n")
                            else:
                                print("メール本文から認証コードのパターンが見つかりませんでした.\n")
                                if driver:
                                    driver.save_screenshot("auth_code_pattern_not_found.png")
                        else:
                            print("エラー: メール本文が空のため、認証コードを抽出できませんでした.\n")
                            return None

                except TimeoutException:
                    print(f"エラー: 最新のメールの件名要素がクリックできませんでした (TimeoutException).\n")
                    if driver:
                        driver.save_screenshot("latest_email_click_timeout.png")
                    return None
                except Exception as e:
                    print(f"エラー: 最新のメールクリック中に予期せぬエラーが発生しました: {e}\n")
                    if driver:
                        driver.save_screenshot("latest_email_click_error.png")
                    return None
            else:
                print("エラー: 最新のメールを特定できませんでした。解析可能なメールがなかったか、リストが空でした.\n")
                return None

        except TimeoutException:
            print(f"エラー: 目的のメールを検索するための要素（メールリスト自体）が見つからないか、タイムアウトしました.\n")
            print("現在のページのHTMLソースの冒頭（デバッグ用）：")
            if driver:
                print(driver.page_source[:2000])
                driver.save_screenshot("email_list_initial_load_timeout.png")
            return None
        except NoSuchElementException:
            print("エラー: 指定したXPathのメール行要素が見つかりませんでした。HTML構造と.envの設定を確認してください.\n")
            if driver:
                print(driver.page_source[:2000]) # エラー時のHTMLも保存
                driver.save_screenshot("email_rows_not_found.png")
            return None
        except Exception as e:
            print(f"メールリストからのメール選択中に予期せぬエラーが発生しました: {e}\n")
            if driver:
                print(driver.page_source[:2000]) # エラー時のHTMLも保存
                driver.save_screenshot("email_selection_general_error.png")
            return None
        
        return auth_code 

    except Exception as e:
        print(f"認証コード取得処理中に予期せぬエラーが発生しました: {e}\n")
        if driver:
            print(f"現在のURL: {driver.current_url}")
            print(f"現在のページのタイトル: {driver.title}")
            print("現在のページのHTMLソースの冒頭（デバッグ用）：")
            print(driver.page_source[:2000])
            driver.save_screenshot("auth_code_fetch_global_error.png")
        return None
    finally:
        # 認証コード取得後、このウェブメール専用のブラウザを自動的に閉じる
        if driver:
            # New: 新しいメール本文ウィンドウが開いている場合、それを閉じてからメインのウェブメールウィンドウを閉じる
            if new_mail_body_window_handle and new_mail_body_window_handle != driver.current_window_handle:
                try:
                    driver.switch_to.window(new_mail_body_window_handle)
                    driver.close() # 新しいウィンドウを閉じる
                    print(f"INFO: 新しいメール本文ウィンドウ {new_mail_body_window_handle} を閉じました.\n")
                    # 元のウェブメールリストのウィンドウに戻る（これは navigate_to_webmail_and_update で開かれたメインのウィンドウ）
                    # driver.switch_to.window(driver.window_handles[0]) # 複数ウィンドウがある場合、最初のウィンドウに切り替える
                except Exception as e:
                    print(f"WARN: 新しいメール本文ウィンドウを閉じる際にエラーが発生しました: {e}\n")
            
            # 元々 navigate_to_webmail_and_update で開かれたウェブメールのブラウザを閉じる
            # ここでは navigate_to_webmail_and_update が新しいWebDriverインスタンスを返すことを前提
            # なので、そのインスタンスを quit() する
            driver.quit() 
            print("ウェブメールのブラウザを閉じました.\n")
        else:
            print("WebDriverが初期化されなかったため、ブラウザを閉じる操作はスキップされました.\n")

# if __name__ == "__main__": ブロックは単体テスト用なので変更なし
if __name__ == "__main__":
    final_auth_code = fetch_auth_code()
    if final_auth_code:
        print(f"\n実行結果: 認証コード '{final_auth_code}' を取得しました.\n")
    else:
        print("\n実行結果: 認証コードの取得に失敗しました.\n")