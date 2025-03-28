import os
import concurrent.futures
import threading
import re

class ThreadManager:
    """マルチスレッド処理を管理するクラス"""

    def __init__(self, max_workers=4):
        """初期化"""
        self.max_workers = max_workers
        self.counter = 0
        self.counter_lock = threading.Lock()

    def increment_counter(self):
        """スレッドセーフにカウンターを増やして値を返す"""
        with self.counter_lock:
            self.counter += 1
            return self.counter

    def collect_image_files(self, directory_path, target_depth, filter=r'\.png$'):
        """指定された深さのディレクトリから正規表現に一致する画像ファイルを収集"""
        image_files = []
        pattern = re.compile(filter, re.IGNORECASE)  # 大文字小文字を無視

        def _collect_at_depth(current_path, current_depth):
            if current_depth == target_depth:
                for file in os.listdir(current_path):
                    file_path = os.path.join(current_path, file)
                    if not os.path.isdir(file_path) and pattern.search(file):
                        image_files.append(file_path)
            elif current_depth < target_depth:
                for item in os.listdir(current_path):
                    item_path = os.path.join(current_path, item)
                    if os.path.isdir(item_path):
                        _collect_at_depth(item_path, current_depth + 1)

        _collect_at_depth(directory_path, 1)
        return image_files

    def process_files(self, files, rename_logic, output_directory):
        """ファイルリストをマルチスレッドで処理"""
        processed_count = 0
        failed_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # ファイル処理をスレッドプールに送信
            future_to_file = {
                executor.submit(
                    rename_logic.process_image_file,
                    file_path,
                    output_directory,
                    self.increment_counter
                ): file_path for file_path in files
            }

            # 結果を収集
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    if future.result():
                        processed_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"処理エラー: {str(e)}")
                    failed_count += 1

        return processed_count, failed_count