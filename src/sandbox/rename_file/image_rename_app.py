import argparse
import os
import time

from rename_logic import RenameLogic
from thread_manager import ThreadManager


class ImageRenameApplication:
    """画像リネームアプリケーションのメインクラス"""

    def __init__(self):
        """初期化"""
        self.args = self.parse_arguments()
        self.start_time = time.time()
        # クラスのインスタンス化
        self.rename_logic = RenameLogic()
        self.thread_manager = ThreadManager(max_workers=self.args.threads)

    def parse_arguments(self):
        """コマンドライン引数の解析"""
        parser = argparse.ArgumentParser(
            description='指定された階層のディレクトリ内の画像ファイルをマルチスレッドでリネームします。')
        parser.add_argument('--directory', default="D:/Dropbox/aphotos/autoFiles", help='処理するディレクトリのパス')
        parser.add_argument('--output', default="D:/Dropbox/aphotos/filesV4", help='出力先ディレクトリのパス')
        parser.add_argument('--depth', type=int, default=2, help='処理する階層の深さ（1 = 直下、2 = 2階層下、...）')
        parser.add_argument('--threads', type=int, default=10, help='使用するスレッド数')

        return parser.parse_args()

    def setup_directories(self):
        """基本ディレクトリ構造を作成"""
        os.makedirs(os.path.join(self.args.output, "character"), exist_ok=True)
        os.makedirs(os.path.join(self.args.output, "artist"), exist_ok=True)

    def get_time(self):
        return time.time() - self.start_time

    def run(self):
        """アプリケーションの実行"""
        # 引数の検証
        if self.args.depth < 1:
            print("エラー: 深さは1以上を指定してください。")
            return 1

        # 基本ディレクトリ構造を作成
        self.setup_directories()

        # 処理開始メッセージ
        print(f"処理を開始します... {self.get_time():.2f}秒")
        print(f"ソースディレクトリ: {self.args.directory}")
        print(f"出力ディレクトリ: {self.args.output}")
        print(f"探索する深さ: {self.args.depth}")
        print(f"使用するスレッド数: {self.args.threads}")

        # 処理するファイルのリストを収集
        print("画像ファイルを検索中...")
        image_files = self.thread_manager.collect_image_files(self.args.directory, self.args.depth)
        total_files = len(image_files)

        if total_files == 0:
            print(f"処理対象のPNGファイルが見つかりませんでした。 {self.get_time():.2f}秒")
            return 0

        print(f"合計 {total_files} 個のPNGファイルを処理します。 {self.get_time():.2f}秒")

        # マルチスレッド処理を実行
        processed_count, failed_count = self.thread_manager.process_files(
            image_files, self.rename_logic, self.args.output
        )

        # 処理結果の表示
        print("\n処理完了!")
        print(f"経過時間: {self.get_time():.2f}秒")
        print(f"合計: {total_files} ファイル")
        print(f"リネーム完了: {self.thread_manager.counter} ファイル")
        print(f"失敗または不要: {total_files - self.thread_manager.counter} ファイル")

        return 0

if __name__ == "__main__":
    app = ImageRenameApplication()
    exit_code = app.run()
    exit(exit_code)