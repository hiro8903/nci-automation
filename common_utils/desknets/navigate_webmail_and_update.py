# desknets/navigate_webmail_and_update.py

import time
import os
import sys

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException

# login.py から login_and_get_driver 関数をインポート
# プロジェクト内の絶対インポート形式を使用して、実行ファイル環境での安定性を高めます
from common_utils.desknets.login import login_and_get_driver

def navigate_to_webmail_and_update():
    """
    desknet's NEO にログインし、ウェブメール画面（MailList）に遷移後、メールリストを更新します。
    成功すれば、ウェブメールタブにフォーカスされたWebDriverインスタンスを返し、
    失敗すればNoneを返します。
    """
    print("--- ウェブメールナビゲーションと更新処理を開始します ---")
    driver = None
    
    try:
        # Step 1: ログインし、WebDriverオブジェクトを取得
        driver = login_and_get_driver()
        
        if driver is None:
            print("エラー: WebDriverの取得に失敗しました。ログイン処理を確認してください。")
            return None 

        wait = WebDriverWait(driver, 20) # 待機時間を20秒に設定

        print("\n--- ログイン成功。ウェブメールへの遷移を開始します ---")
        
        # ページ遷移前に現在のウィンドウハンドルと全てのウィンドウハンドルを記録
        original_window = driver.current_window_handle
        all_window_handles_before = driver.window_handles 

        # Step 2: 「ウェブメール(個人アカウント)」のリンクを探してクリック
        print("「ウェブメール(個人アカウント)」のリンクを探しています...")
        webmail_link = wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "ウェブメール(個人アカウント)"))
        )
        
        driver.execute_script("arguments[0].click();", webmail_link)
        print("「ウェブメール(個人アカウント)」のリンクをJavaScriptでクリックしました。")
        time.sleep(3) # 新しいタブが開くのを少し長めに待つ

        # Step 3: 新しいウェブメールタブへの切り替え
        print("新しいウェブメールタブへの切り替えを試みています...")
        try:
            wait.until(EC.number_of_windows_to_be(len(all_window_handles_before) + 1))
        except TimeoutException:
            print("エラー: 新しいタブが開くのを待機中にタイムアウトしました。")
            print(f"現在のURL: {driver.current_url}")
            print(f"現在のページのタイトル: {driver.title}")
            driver.save_screenshot("new_tab_open_timeout_navigate_update.png")
            return None 

        new_window_handle = None
        for window_handle in driver.window_handles:
            if window_handle != original_window:
                new_window_handle = window_handle
                break
        
        if new_window_handle:
            driver.switch_to.window(new_window_handle)
            print(f"新しいウェブメールタブに切り替えました。ハンドル: {new_window_handle}")
            print(f"切り替え後のURL: {driver.current_url}")
            print(f"切り替え後のページのタイトル: {driver.title}")
        else:
            print("エラー: 新しいウェブメールタブが見つかりませんでした。")
            return None 

        # Step 4: 新しいタブでURLに 'page=MailList' が含まれるまで待機
        print("新しいタブでURLに 'page=MailList' が含まれるか確認しています...")
        try:
            wait.until(EC.url_contains("page=MailList"))
            print(f"ウェブメールのページに正常に遷移しました。(URLに 'page=MailList' 確認済)")
        except TimeoutException:
            print("エラー: 新しいタブで 'page=MailList' を含むURLへの遷移がタイムアウトしました。")
            print(f"現在のURL: {driver.current_url}")
            print(f"現在のページのタイトル: {driver.title}")
            # driver.save_screenshot("webmail_url_timeout_navigate_update.png")
            return None

        # Step 5: メールリストの更新操作
        print("\n--- メールリストの更新操作を開始します ---")
        try:
            print("メールリストの更新ボタンを探しています...")
            # driver.save_screenshot("before_refresh_button_click_navigate_update.png")
            # print("スクリーンショット 'before_refresh_button_click_navigate_update.png' を保存しました。")

            refresh_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.toolbar-button.toolbar-button-top"))
            )
            print("DEBUG: 更新ボタン要素が正常に特定され、クリック可能になりました。")
            
            driver.execute_script("arguments[0].scrollIntoView(true);", refresh_button)
            time.sleep(3) 

            driver.execute_script("arguments[0].click();", refresh_button)
            print("JavaScript でメールリストの更新ボタンをクリックしました。")
            
            time.sleep(3) # ページの更新やメール受信に時間がかかる場合を考慮し、少し長めに待つ
            print("メールリストが最新の状態に更新されたことを期待します。")

        except TimeoutException:
            print("エラー: メールリスト更新ボタンが見つからないか、クリック可能になりませんでした（TimeoutException）。")
            # driver.save_screenshot("refresh_button_timeout_navigate_update.png")
            # 更新ボタンクリックが失敗しても、次のメール検索に進むためにここでは pass
            pass 
        except NoSuchElementException:
            print("エラー: 指定したCSSセレクタの更新ボタンが見つかりませんでした（NoSuchElementException）。HTML構造を確認してください。")
            # driver.save_screenshot("refresh_button_not_found_navigate_update.png")
            pass
        except ElementClickInterceptedException:
            print("エラー: メールリスト更新ボタンが他の要素に隠されてクリックできませんでした（ElementClickInterceptedException）。")
            # driver.save_screenshot("refresh_button_intercepted_navigate_update.png")
            pass
        except Exception as e:
            print(f"エラー: メールリスト更新中に予期せぬエラーが発生しました: {e}")
            # driver.save_screenshot("refresh_button_error_navigate_update.png")
            pass
        
        print("\n--- ウェブメールナビゲーションと更新処理を終了します。---")
        return driver # 後続の処理のためにWebDriverインスタンスを返す

    except Exception as e:
        print(f"ウェブメールナビゲーションと更新中に予期せぬエラーが発生しました: {e}")
        if driver:
            print(f"現在のURL: {driver.current_url}")
            print(f"現在のページのタイトル: {driver.title}")
            print("現在のページのHTMLソースの冒頭（デバッグ用）：")
            print(driver.page_source[:2000])
            # driver.save_screenshot("global_error_navigate_update.png")
        # エラー発生時はWebDriverをクローズする
        if driver:
            driver.quit() 
        return None

if __name__ == "__main__":
    # このファイル単体でテスト実行する場合
    driver_instance = navigate_to_webmail_and_update()
    # 修正箇所: if driver: を if driver_instance: に変更
    if driver_instance:
        print("\nウェブメールナビゲーションと更新に成功しました。ブラウザを閉じるにはEnterキーを押してください...")
        input()
        driver_instance.quit()
        print("ブラウザを閉じました。")
    else:
        print("\nウェブメールナビゲーションと更新に失敗しました。")