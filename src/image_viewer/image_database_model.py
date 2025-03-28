import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sqlite3
from PIL import Image
import numpy as np
from typing import List, Optional, Dict, Tuple, Union

# ===== Model =====
class ImageDatabaseModel:
    """データベースとの通信とデータ処理を担当するモデルクラス"""

    def __init__(self, db_file: str) -> None:
        self.db_file: str = db_file
        self._count_cache: Dict[str, int] = {}  # クエリごとのカウントをキャッシュ
        self._is_cancelled: bool = False  # キャンセルフラグ
        self._current_connection: Optional[sqlite3.Connection] = None  # 現在のデータベース接続
        self._current_image_paths: List[str] = []  # 現在処理中の画像パスリスト

    def cancel_query(self) -> None:
        """実行中のクエリをキャンセル"""
        self._is_cancelled = True
        if self._current_connection:
            try:
                self._current_connection.interrupt()  # SQLiteのクエリを中断
            except:
                pass
        self._current_image_paths.clear()  # 画像パスリストをクリア

    def query_images(self, query: str, limit: int = 25, offset: int = 0) -> List[str]:
        """指定されたクエリでデータベースから画像パスを取得"""
        self._is_cancelled = False  # キャンセルフラグをリセット
        self._current_connection = sqlite3.connect(self.db_file)
        cursor: sqlite3.Cursor = self._current_connection.cursor()

        try:
            # LIMITとOFFSETがクエリに含まれていない場合は追加
            if "LIMIT" not in query.upper():
                query += f" LIMIT {limit} OFFSET {offset}"
            cursor.execute(query)
            paths: List[str] = [row[0] for row in cursor.fetchall()]
            return paths
        finally:
            self._current_connection.close()
            self._current_connection = None

    def get_total_images_count(self, query: str) -> int:
        """指定されたクエリに一致する画像の総数を取得"""
        # キャッシュに存在する場合はそれを返す
        if query in self._count_cache:
            return self._count_cache[query]

        self._is_cancelled = False  # キャンセルフラグをリセット
        self._current_connection = sqlite3.connect(self.db_file)
        cursor: sqlite3.Cursor = self._current_connection.cursor()

        try:
            # 元のクエリからWHERE句を抽出
            where_clause: str = ""
            if "WHERE" in query.upper():
                where_parts: List[str] = query.upper().split("WHERE", 1)
                if len(where_parts) > 1:
                    where_clause = where_parts[1]
                    # ORDER BY、LIMIT、OFFSETがある場合は除去
                    if "ORDER BY" in where_clause:
                        where_clause = where_clause.split("ORDER BY", 1)[0]
                    if "LIMIT" in where_clause:
                        where_clause = where_clause.split("LIMIT", 1)[0]

            # カウントクエリの作成（テーブル名を統一）
            count_query: str = "SELECT COUNT(*) FROM image_relation_view"

            # WHERE句がある場合は含める
            if where_clause:
                count_query += f" WHERE {where_clause}"
            
            cursor.execute(count_query)
            count: int = cursor.fetchone()[0]

            # 結果をキャッシュに保存
            self._count_cache[query] = count
            return count
        except Exception as e:
            print(f"カウント取得エラー: {e}")
            return 0
        finally:
            self._current_connection.close()
            self._current_connection = None

    def create_thumbnail(self, image_path: str, max_size: Tuple[int, int] = (200, 200)) -> Optional[Tuple[int, int, int, np.ndarray]]:
        """画像からサムネイルを作成"""

        try:
            img: Image.Image = Image.open(image_path)
            img.thumbnail(max_size, Image.LANCZOS)  
            # PIL画像をDPG用のnumpy配列に変換
            if img.mode != "RGBA":
                img = img.convert("RGBA")        
            return img.size[0], img.size[1], 4, np.array(img, dtype=np.float32).ravel() / 255.0
        except Exception as e:
            print(f"サムネイル作成エラー ({image_path}): {e}")            
            # エラー時の赤い長方形プレースホルダー
            width: int = 100
            height: int = 100
            placeholder: np.ndarray = np.zeros((height, width, 4), dtype=np.float32)
            placeholder[:, :, 0] = 1.0  # 赤チャンネル
            placeholder[:, :, 3] = 1.0  # アルファチャンネル
            return width, height, 4, placeholder.ravel()