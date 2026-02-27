import os
import zipfile
import glob
import logging
import sys

# ロギング設定: アプリケーション全体で一貫したログ出力を行う
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def unzip_and_delete_zips(target_directory: str) -> bool:
    """
    指定されたディレクトリ内のすべてのZIPファイルを解凍し、その内容を同じディレクトリに保存します。
    解凍後、元のZIPファイルは削除されます。

    この関数は、他のスクリプトからモジュールとしてインポートされることを想定しています。
    エラー発生時はFalseを返しますが、個々のZIPファイル処理のエラーはログに出力されます。

    Args:
        target_directory (str): 処理対象のディレクトリパス。

    Returns:
        bool: 全てのZIPファイルの処理が成功または処理すべきファイルがなかった場合はTrue、
              いずれかのZIPファイル処理で回復不能なエラーが発生した場合はFalse。
    """
    # ディレクトリパスのバリデーション
    if not target_directory:
        logger.error("エラー: 処理対象のディレクトリが指定されていません。")
        return False

    if not os.path.isdir(target_directory):
        logger.error(f"エラー: 指定されたパスはディレクトリではありません、または存在しません: '{target_directory}'")
        return False

    logger.info(f"ディレクトリ '{target_directory}' 内のZIPファイルを処理します。")

    # 指定されたディレクトリ内のZIPファイルをすべて検索
    zip_files = glob.glob(os.path.join(target_directory, "*.zip"))

    if not zip_files:
        logger.info(f"'{target_directory}' 内に処理すべきZIPファイルは見つかりませんでした。")
        return True # 処理すべきファイルがない場合も成功とみなす

    # 各ZIPファイルを順番に処理
    for zip_file_path in zip_files:
        try:
            logger.info(f"ZIPファイル '{os.path.basename(zip_file_path)}' を解凍します。")
            
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                # 全てのファイルを指定したディレクトリに抽出。
                # ZIPファイル内のディレクトリ構造を維持して解凍されます。
                # 例: ZIP内に 'folder/file.txt' があれば、'target_directory/folder/file.txt' として解凍。
                zip_ref.extractall(target_directory) 
                logger.info(f"'{os.path.basename(zip_file_path)}' の内容を '{target_directory}' に抽出しました。")

            # 解凍が成功したら元のZIPファイルを削除
            os.remove(zip_file_path)
            logger.info(f"ZIPファイル '{os.path.basename(zip_file_path)}' を削除しました。")

        except zipfile.BadZipFile:
            logger.error(f"エラー: '{os.path.basename(zip_file_path)}' は破損しているか、有効なZIPファイルではありません。このファイルはスキップされます。")
            # 破損したZIPファイルは削除されないまま残るが、他のZIPファイルの処理は続行
            # ここでFalseを返すと、他のZIPファイルの処理が中断されるため、個別のエラーとしてログに記録し続行する方が良い場合も
            # 今回は元の挙動に従い、エラー発生でFalseを返す
            return False 
        except FileNotFoundError:
            logger.error(f"エラー: ZIPファイル '{os.path.basename(zip_file_path)}' が見つかりませんでした。このファイルはスキップされます。")
            return False
        except Exception as e:
            logger.error(f"エラー: ZIPファイル '{os.path.basename(zip_file_path)}' の処理中に予期せぬエラーが発生しました: {e}")
            return False

    logger.info("全てのZIPファイルの処理が完了しました。")
    return True

if __name__ == "__main__":
    """
    このスクリプトが単独で実行された場合の処理。
    コマンドライン引数として解凍対象ディレクトリを受け取ります。
    メインアプリケーションからモジュールとしてインポートされる場合は、このブロックは実行されません。
    """
    from dotenv import load_dotenv # 単独実行時のみdotenvが必要なため、ここでインポート

    # 単独実行時の.envファイルのパス解決
    # common_utils/file_processing/unzip_files.py から '../..' で automation_tools/ へ
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.normpath(os.path.join(current_dir, '..', '..'))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path) # .envファイルを読み込む

    # コマンドライン引数のバリデーションと関数呼び出し
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
        logger.info(f"単独実行モード: 指定されたディレクトリ '{target_dir}' のZIPファイルを処理します。")
        success = unzip_and_delete_zips(target_dir) 
        if not success:
            sys.exit(1) # 処理失敗時は終了コード1で終了
    else:
        logger.error("エラー: 処理対象ディレクトリがコマンドライン引数で指定されていません。")
        logger.info("使用法: python automation_tools/common_utils/file_processing/unzip_files.py <対象ディレクトリパス>")
        sys.exit(1)