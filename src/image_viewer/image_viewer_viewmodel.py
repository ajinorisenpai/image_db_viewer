import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import List, Optional, Callable, Dict, Any, Union
from src.image_viewer.image_database_model import ImageDatabaseModel

# ===== ViewModel =====
class ImageViewerViewModel:
    """ModelとViewの間を仲介し、Viewに表示するデータを準備するViewModelクラス"""

    def __init__(self, model: ImageDatabaseModel) -> None:
        self.model: ImageDatabaseModel = model

        # 状態を保持するプロパティ
        self.current_page: int = 0
        self.total_images: int = 0
        self.current_query: str = "SELECT image_path FROM image_relation_view"
        self.image_paths: List[str] = []
        self.max_pages: int = 1
        self.is_query_running: bool = False  # クエリ実行状態

        # クエリオプション
        self.query_options: Dict[str, Union[bool, int, str]] = {
            "random": False,
            "size_type": True,
            "limit": 63,
            "artist": ""
        }

        # 一時的なオプション保存用
        self.temp_query_options: Dict[str, Union[bool, int, str]] = self.query_options.copy()

        # 変更通知のためのコールバック
        self.on_images_changed: Optional[Callable[[List[str]], None]] = None
        self.on_pagination_changed: Optional[Callable[[int, int, int], None]] = None
        self.on_query_changed: Optional[Callable[[str], None]] = None
        self.on_query_state_changed: Optional[Callable[[bool], None]] = None  # クエリ状態変更通知用

    def generate_query(self) -> str:
        """現在のオプションに基づいてSQLクエリを生成"""
        base_query: str = "SELECT image_path FROM image_relation_view"
        conditions: List[str] = []

        if self.query_options["size_type"]:
            conditions.append("size_type=1")

        if self.query_options["artist"]:
            conditions.append(f"artists LIKE '%{self.query_options['artist']}%'")

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        if self.query_options["random"]:
            base_query += " ORDER BY RANDOM()"

        return base_query

    def execute_query(self, query: Optional[str] = None) -> None:
        """クエリを実行し、結果を更新"""
        # 新しいクエリを設定
        if query is not None:
            self.current_query = query
            # クエリが変更された場合はページをリセット
            self.current_page = 0

        # 状態を更新
        self.is_query_running = True
        if self.on_query_state_changed:
            self.on_query_state_changed(True)

        try:
            # 画像パスの取得
            paths: List[str] = self.model.query_images(
                self.current_query,
                self.query_options["limit"],
                self.current_page * self.query_options["limit"]
            )

            # 総数とページ数を更新
            self.total_images = self.model.get_total_images_count(self.current_query)
            self.max_pages = max(1, (self.total_images + self.query_options["limit"] - 1) // self.query_options["limit"])

            # 結果を処理
            self.image_paths = paths

            # UI更新
            if self.on_images_changed:
                self.on_images_changed(self.image_paths)

            if self.on_pagination_changed:
                self.on_pagination_changed(self.current_page, self.max_pages, self.total_images)

        except Exception as e:
            print(f"エラーが発生しました: {e}")
        finally:
            # 状態を更新
            self.is_query_running = False
            if self.on_query_state_changed:
                self.on_query_state_changed(False)

    def cancel_query(self) -> None:
        """実行中のクエリをキャンセル"""
        if not self.is_query_running:
            return
            
        # モデルのクエリをキャンセル
        self.model.cancel_query()
        
        # 状態を更新
        self.is_query_running = False
        if self.on_query_state_changed:
            self.on_query_state_changed(False)

    def next_page(self) -> bool:
        """次のページに移動"""
        # 条件をチェック（最後のページではない）
        if self.current_page >= self.max_pages - 1:
            return False
            
        # ページを進める
        self.current_page += 1
        
        # 状態を更新
        self.is_query_running = True
        if self.on_query_state_changed:
            self.on_query_state_changed(True)

        try:
            # 画像パスの取得
            paths: List[str] = self.model.query_images(
                self.current_query,
                self.query_options["limit"],
                self.current_page * self.query_options["limit"]
            )

            # 結果を処理
            self.image_paths = paths

            # UI更新
            if self.on_images_changed:
                self.on_images_changed(self.image_paths)

            if self.on_pagination_changed:
                self.on_pagination_changed(self.current_page, self.max_pages, self.total_images)

        except Exception as e:
            print(f"エラーが発生しました: {e}")
        finally:
            # 状態を更新
            self.is_query_running = False
            if self.on_query_state_changed:
                self.on_query_state_changed(False)
        return True

    def prev_page(self) -> bool:
        """前のページに移動"""
        # 条件をチェック（最初のページではない）
        if self.current_page <= 0:
            return False
            
        # ページを戻す
        self.current_page -= 1
        
        # 状態を更新
        self.is_query_running = True
        if self.on_query_state_changed:
            self.on_query_state_changed(True)

        try:
            # 画像パスの取得
            paths: List[str] = self.model.query_images(
                self.current_query,
                self.query_options["limit"],
                self.current_page * self.query_options["limit"]
            )

            # 結果を処理
            self.image_paths = paths

            # UI更新
            if self.on_images_changed:
                self.on_images_changed(self.image_paths)

            if self.on_pagination_changed:
                self.on_pagination_changed(self.current_page, self.max_pages, self.total_images)

        except Exception as e:
            print(f"エラーが発生しました: {e}")
        finally:
            # 状態を更新
            self.is_query_running = False
            if self.on_query_state_changed:
                self.on_query_state_changed(False)
        return True

    def update_temp_options(self, key: str, value: Union[bool, int, str]) -> None:
        """一時的なクエリオプションを更新"""
        self.temp_query_options[key] = value

    def apply_query_options(self) -> None:
        """一時的なクエリオプションを適用"""
        self.query_options = self.temp_query_options.copy()
        new_query: str = self.generate_query()

        # クエリが変更された場合は通知
        if self.on_query_changed:
            self.on_query_changed(new_query)

        # 新しいクエリで画像を読み込む
        self.execute_query(new_query)

    def create_thumbnail(self, image_path: str) -> Optional[tuple]:
        """画像のサムネイルを作成"""
        return self.model.create_thumbnail(image_path)
