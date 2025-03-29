import sqlite3
import os
import shutil
import concurrent.futures
import threading
import time

from src.rename.DataBaseManager import DatabaseManager
from src.utils.config_constant import AppSettings


# 進捗状況を管理するクラス
class ProgressTracker:
    def __init__(self):
        self.success_count = 0
        self.error_count = 0
        self.lock = threading.Lock()
        self.last_report_time = time.time()

    def increment_success(self):
        with self.lock:
            self.success_count += 1
            self._report_progress_if_needed()

    def increment_error(self):
        with self.lock:
            self.error_count += 1

    def _report_progress_if_needed(self):
        current_time = time.time()
        if current_time - self.last_report_time > 2 or self.success_count % 100 == 0:
            print(f"進捗状況: 成功={self.success_count}件, 失敗={self.error_count}件")
            self.last_report_time = current_time

    def get_counts(self):
        return self.success_count, self.error_count


def ensure_directory_exists(directory):
    """指定されたディレクトリが存在しない場合は作成する"""
    os.makedirs(directory, exist_ok=True)


def process_file(args):
    """個々のファイルを処理する関数（スレッドプールで実行）"""
    image_id, original_path, new_path, db_manager, progress_tracker = args

    try:
        # 新しいディレクトリが存在することを確認
        new_dir = os.path.dirname(new_path)
        ensure_directory_exists(new_dir)

        # 元のファイルが存在するか確認
        if not os.path.exists(original_path):
            print(f"元ファイルが見つかりません: {original_path}")
            progress_tracker.increment_error()
            return False

        # 移動先に同名ファイルがすでに存在するか確認
        if os.path.exists(new_path):
            # 同一ファイルでない場合のみ警告
            if os.path.samefile(original_path, new_path):
                print(f"元ファイルと移動先が同じです: {new_path}")
            else:
                print(f"移動先にファイルが既に存在します: {new_path}")
                # 既存ファイルを上書きする場合は以下のコメントを解除
                # os.remove(new_path)

        shutil.move(original_path, new_path)

        # imagesテーブルのpathを更新
        cursor = db_manager.get_cursor()
        cursor.execute('''
        UPDATE images 
        SET path = ? 
        WHERE id = ?
        ''', (new_path, image_id))

        # 定期的にコミット
        db_manager.commit()

        progress_tracker.increment_success()
        return True

    except Exception as e:
        print(f"エラー発生: {e} - ファイル: {original_path}")
        progress_tracker.increment_error()
        return False


def move_files_and_update_db(db_path,max_workers=8, batch_size=500):
    """マルチスレッドでファイルを移動し、DBを更新する関数"""

    # メインDB接続（読み取り専用）
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # スレッド用のDB接続マネージャーを作成
    db_manager = DatabaseManager(db_path)

    # 進捗トラッカーを初期化
    progress_tracker = ProgressTracker()

    try:
        # 総レコード数を取得
        cursor.execute('SELECT COUNT(*) FROM renamed_images')
        total_records = cursor.fetchone()[0]
        print(f"処理対象レコード数: {total_records}")

        # オフセットを使って一定数ずつ処理
        offset = 0

        while True:
            # バッチサイズ分のデータを取得
            cursor.execute('''
            SELECT image_id, image_path, renamed_path 
            FROM renamed_images
            LIMIT ? OFFSET ?
            ''', (batch_size, offset))

            rows = cursor.fetchall()
            if not rows:
                break  # データがなければ終了

            # スレッドプールで並列処理
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 各ファイルの処理をスレッドプールに投入
                futures = [
                    executor.submit(
                        process_file,
                        (image_id, original_path, new_path, db_manager, progress_tracker)
                    )
                    for image_id, original_path, new_path in rows
                ]

                # すべてのタスクが完了するのを待機
                concurrent.futures.wait(futures)

            # 次のバッチへ
            offset += batch_size
            print(f"バッチ処理完了: {offset}/{total_records}")

            # バッチごとにコミット
            db_manager.commit()

        # 最終コミット
        db_manager.commit()

        # 結果を表示
        success_count, error_count = progress_tracker.get_counts()
        print(f"処理完了: 成功={success_count}件, 失敗={error_count}件")

    except Exception as e:
        print(f"致命的なエラーが発生しました: {e}")

    finally:
        # 接続を閉じる
        conn.close()
        db_manager.close_all()


# 確認メッセージを表示してから実行
def main(db_file):
    move_files_and_update_db(db_file,max_workers=8)



if __name__ == "__main__":
    main(AppSettings.DB_FILE)