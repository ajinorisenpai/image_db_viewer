import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import sqlite3
from PIL import Image
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import List, Tuple, Set, Optional, Any
from logger_config import LoggerConfig
from src.utils.config_constant import AppSettings
from src.utils.util import normalize_slash
import threading


class UpdateImageTable:
    def __init__(self, db_file: str, image_dir: str, batch_size: int = 1000, max_workers: int = 4) -> None:
        """
        初期化メソッド

        Args:
            db_file: データベースファイルのパス
            image_dir: 新しい画像フォルダのパス
            batch_size: コミットのバッチサイズ
            max_workers: 並列処理のワーカー数
        """
        self.db_file: str = db_file
        self.image_dir: str = normalize_slash(image_dir)
        self.batch_size: int = batch_size
        self.max_workers: int = max_workers
        self.logger: Any = LoggerConfig.get_default_logger('db_add_new_images.log')
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.existing_images: Set[str] = set()
        self.new_images: List[Tuple[str, str, int, int, str]] = []
        self._lock: Optional[threading.Lock] = None

    def connect_db(self) -> bool:
        """データベースに接続する

        Returns:
            bool: 接続が成功したかどうか
        """
        self.conn = sqlite3.connect(self.db_file)
        # 外部キー制約を有効化
        self.conn.execute("PRAGMA foreign_keys = ON")
        # WALモードを有効化（書き込み性能向上）
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.cursor = self.conn.cursor()

        # テーブルが存在するか確認
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='images'")
        table_exists: Optional[Tuple[str]] = self.cursor.fetchone()

        if not table_exists:
            self.logger.error("imagesテーブルが存在しません。先に初期化スクリプトを実行してください。")
            self.close_connection()
            return False

        return True

    def load_existing_images(self) -> None:
        """既存の画像パスをロード"""
        self.cursor.execute("SELECT path FROM images")
        # すべてのパスを正規化して設定
        self.existing_images = {normalize_slash(row[0]) for row in self.cursor.fetchall()}
        self.logger.info(f"{len(self.existing_images)}件の既存レコードをロードしました")

    @lru_cache(maxsize=100)
    def get_image_metadata(self, file_path: str) -> Tuple[str, str]:
        """画像のメタデータを取得

        Args:
            file_path: 画像ファイルのパス

        Returns:
            Tuple[str, str]: (description, detail)のタプル
        """
        try:
            with Image.open(file_path) as img:
                # Descriptionがなければ空文字を返す
                desc: str = img.info.get('Description', '')
                detail: str = img.info.get('Comment', '')
                return desc, detail
        except Exception as e:
            self.logger.error(f"メタデータ取得エラー: {file_path} - {e}")
            return '', ''

    def collect_image_files(self) -> List[str]:
        """ディレクトリを再帰的に探索して画像を収集

        Returns:
            List[str]: 収集した画像ファイルのパスリスト
        """
        image_files: List[str] = []

        for root, _, files in os.walk(self.image_dir):
            # rootのパスを正規化
            normalized_root: str = normalize_slash(root)

            for file in files:
                if file.lower().endswith('.png'):
                    # パスを結合して正規化
                    image_path: str = normalized_root + '/' + file
                    image_files.append(image_path)

        self.logger.info(f"{len(image_files)}件の画像ファイルを見つけました")
        return image_files

    def process_image_file(self, file_path: str) -> None:
        """画像ファイルを処理し新規追加が必要か判断

        Args:
            file_path: 画像ファイルのパス
        """
        # パスを正規化
        normalized_path: str = normalize_slash(file_path)

        # 既に登録済みの場合はスキップ
        if normalized_path in self.existing_images:
            return

        try:
            # メタデータを取得
            desc: str
            detail: str
            desc, detail = self.get_image_metadata(file_path)

            # descriptionが空の場合は処理をスキップ
            if not desc:
                self.logger.warning(f"説明がないためスキップ: {normalized_path}")
                return

            current_time: int = int(time.time())

            # 新規追加用のデータを準備
            with self._lock:  # スレッドセーフな操作のためのロック
                self.new_images.append((desc, detail, 1, current_time, normalized_path))

        except Exception as e:
            self.logger.error(f"ファイル処理エラー: {normalized_path} - {e}")

    def update_database_in_batches(self) -> None:
        """データベース更新をバッチ処理"""
        total_updates: int = len(self.new_images)
        processed: int = 0
        batch: List[Tuple[str, str, int, int, str]] = []

        for image_data in self.new_images:
            batch.append(image_data)
            processed += 1

            # バッチサイズに達したらコミット
            if len(batch) >= self.batch_size:
                self.execute_batch_insert(batch)
                self.logger.info(f"進捗: {processed}/{total_updates} 件処理 ({processed / total_updates * 100:.1f}%)")
                batch = []

        # 残りのバッチを処理
        if batch:
            self.execute_batch_insert(batch)
            self.logger.info(f"進捗: {processed}/{total_updates} 件処理 (100%)")

    def execute_batch_insert(self, batch: List[Tuple[str, str, int, int, str]]) -> None:
        """バッチ挿入を実行

        Args:
            batch: 挿入するデータのバッチ
        """
        if batch:
            self.cursor.executemany("""
                INSERT INTO images(description, detail, active, created_at, path) 
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(path) DO NOTHING
            """, batch)

    def close_connection(self) -> None:
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def run(self) -> bool:
        """メイン処理を実行

        Returns:
            bool: 処理が成功したかどうか
        """
        start_time: float = time.time()
        self.logger.info("新規画像データの追加処理を開始します")

        try:
            # データベース接続
            if not self.connect_db():
                return False

            # トランザクション開始
            self.conn.execute("BEGIN TRANSACTION")

            # 既存画像データをロード
            self.logger.info("既存の画像データをロード中...")
            self.load_existing_images()

            # 新しい画像ファイルのパスを収集
            self.logger.info("新規画像ファイルをスキャン中...")
            image_files: List[str] = self.collect_image_files()

            # 追加が必要なファイルを特定
            self.logger.info("新規追加ファイルを確認中...")
            self.new_images = []
            self._lock = threading.Lock()  # スレッドセーフな操作のためのロック

            # 並列処理で画像ファイルを処理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                executor.map(self.process_image_file, image_files)

            # 一括でデータベース更新
            self.logger.info(f"{len(self.new_images)}件の新規画像データを追加中...")
            self.update_database_in_batches()

            # トランザクションをコミット
            self.conn.commit()

            elapsed_time: float = time.time() - start_time
            self.logger.info(
                f"処理完了！{len(self.new_images)}件の新規データを追加しました。所要時間: {elapsed_time:.2f}秒")
            return True

        except Exception as e:
            self.logger.error(f"エラーが発生しました: {e}")
            # エラー発生時はロールバック
            if self.conn:
                self.conn.rollback()
            return False

        finally:
            # 接続を閉じる
            self.close_connection()


if __name__ == "__main__":
    updater = UpdateImageTable(
        db_file=AppSettings.DB_FILE,
        image_dir=AppSettings.NEW_IMAGE_DIR,
        batch_size=1000,
        max_workers=4
    )
    updater.run()
