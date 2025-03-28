import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dearpygui.dearpygui as dpg  # dearpygui version 2.0.0
from src.utils.util import dpg_resolve_font
from typing import List, Optional, Callable, Any, Dict, Union
from src.image_viewer.image_viewer_viewmodel import ImageViewerViewModel

# ===== View =====
class ImageViewerView:
    """ユーザーインターフェースを担当するビュークラス"""

    def __init__(self, view_model: ImageViewerViewModel) -> None:
        self.view_model: ImageViewerViewModel = view_model

        # DearPyGuiの初期化
        dpg.create_context()
        dpg_resolve_font()  # 日本語フォントを設定
        dpg.setup_dearpygui()
        dpg.create_viewport(title="SQLite画像ビューアー", width=1600, height=900)

        # テクスチャレジストリの作成
        with dpg.texture_registry(show=False, tag="texture_registry"):
            pass

        # ViewModelのイベントハンドラを登録
        self.view_model.on_images_changed = self.on_images_changed
        self.view_model.on_pagination_changed = self.on_pagination_changed
        self.view_model.on_query_changed = self.on_query_changed
        self.view_model.on_query_state_changed = self.on_query_state_changed

    def setup_ui(self) -> None:
        """UIの初期設定"""
        # メインウィンドウの作成
        with dpg.window(label="SQLite画像ビューアー", width=1600, height=900, tag="main_window"):
            dpg.set_primary_window("main_window", True)
            with dpg.group(horizontal=True):
                dpg.add_input_text(label="SQLクエリ", tag="query_input", width=600,
                                   default_value=self.view_model.generate_query(),
                                   callback=self.on_query_input_change, on_enter=True)
                dpg.add_button(label="クエリ実行", callback=self.on_execute_query, tag="execute_button")
                dpg.add_button(label="キャンセル", callback=self.on_cancel_query, tag="cancel_button", show=False)
                dpg.add_button(label="クエリオプション", callback=lambda: dpg.show_item("query_options_window"))
                # ローディングインジケータ用のテキスト
                dpg.add_text("", tag="loading_text", color=(255, 255, 0))

            # クエリオプションウィンドウ
            with dpg.window(label="クエリオプション", tag="query_options_window", show=False, width=300, height=200):
                dpg.add_checkbox(label="ランダム表示", tag="random_checkbox",
                                 default_value=self.view_model.query_options["random"],
                                 callback=lambda s, a: self.view_model.update_temp_options("random", a))
                dpg.add_checkbox(label="size_type=1のみ", tag="size_type_checkbox",
                                 default_value=self.view_model.query_options["size_type"],
                                 callback=lambda s, a: self.view_model.update_temp_options("size_type", a))
                dpg.add_text("アーティスト検索:")
                dpg.add_input_text(tag="artist_input", default_value=self.view_model.query_options["artist"],
                                   callback=lambda s, a: self.view_model.update_temp_options("artist", a))
                dpg.add_text("表示件数:")
                dpg.add_input_int(tag="limit_input", default_value=self.view_model.query_options["limit"],
                                  callback=lambda s, a: self.view_model.update_temp_options("limit", a),
                                  min_value=1, max_value=1000)
                dpg.add_button(label="適用", callback=self.on_apply_options)

            # ページネーションコントロール
            with dpg.group(horizontal=True):
                dpg.add_button(label="前のページ", callback=self.on_prev_page, tag="prev_button", enabled=False)
                dpg.add_text("ページ 1/1 (合計: 0枚)", tag="pagination_text")
                dpg.add_button(label="次のページ", callback=self.on_next_page, tag="next_button", enabled=False)

            # 画像用コンテナの作成
            dpg.add_child_window(width=-1, height=-1, tag="grid_container")

    def show(self) -> None:
        """ビューを表示"""
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

    def on_images_changed(self, paths: List[str]) -> None:
        """画像リストが変更されたときのコールバック"""
        # 以前の項目とテクスチャをクリア
        if dpg.does_item_exist("grid_content"):
            dpg.delete_item("grid_content")
        for item in dpg.get_item_children("texture_registry", slot=1):
            dpg.delete_item(item)

        # グリッドの作成
        with dpg.group(parent="grid_container", tag="grid_content"):
            # グリッドレイアウトのパラメータ
            cols: int = 7
            thumbnail_width: int = 200

            # 画像をグリッドに配置
            for i, path in enumerate(paths):
                # キャンセルフラグを定期的に確認
                if i % 5 == 0 and not self.view_model.is_query_running:
                    # キャンセルされた場合、残りの画像を表示しない
                    return
                
                # グリッド位置を計算
                col: int = i % cols
                row: int = i // cols

                # 位置を計算（X座標とY座標）
                x_pos: int = col * thumbnail_width
                y_pos: int = row * 136

                # 画像を表示するグループ
                with dpg.group(pos=[x_pos, y_pos]):
                    if os.path.exists(path):
                        # 画像の読み込みとリサイズ
                        thumbnail_data: Optional[tuple] = self.view_model.create_thumbnail(path)
                        if thumbnail_data is None:  # キャンセルされた場合
                            return  # キャンセルされた場合、残りの画像を表示しない

                        width, height, channels, data = thumbnail_data

                        # テクスチャとして追加
                        texture_id: int = dpg.add_static_texture(width, height, data, parent="texture_registry")

                        # 画像の表示（ツールチップ付き）
                        img: int = dpg.add_image(texture_id, tag=f"image_{i}")
                        with dpg.tooltip(img):
                            dpg.add_text(path)
                    else:
                        # 画像が見つからない場合のエラーメッセージ（ツールチップ付き）
                        error_text: str = f"画像が見つかりません: {os.path.basename(path)}"
                        error: int = dpg.add_text(error_text, tag=f"error_{i}")
                        with dpg.tooltip(error):
                            dpg.add_text(path)

    def on_pagination_changed(self, current_page: int, max_pages: int, total_images: int) -> None:
        """ページネーション情報が変更されたときのコールバック"""
        dpg.set_value("pagination_text", f"ページ {current_page + 1}/{max_pages} (合計: {total_images}枚)")
        
        # ページネーションボタンの有効/無効状態を更新
        dpg.configure_item("prev_button", enabled=current_page > 0)
        dpg.configure_item("next_button", enabled=current_page < max_pages - 1)

    def on_query_changed(self, query: str) -> None:
        """クエリが変更されたときのコールバック"""
        dpg.set_value("query_input", query)

    def on_query_state_changed(self, is_running: bool) -> None:
        """クエリ実行状態が変更されたときのコールバック"""
        dpg.configure_item("execute_button", enabled=not is_running)
        dpg.configure_item("cancel_button", show=is_running)
        dpg.configure_item("query_input", enabled=not is_running)
        
        # ローディングテキストの更新
        if is_running:
            dpg.set_value("loading_text", "クエリ実行中...")
        else:
            dpg.set_value("loading_text", "")
        
        # ページネーションボタンは常に有効（条件に合う場合）
        dpg.configure_item("prev_button", enabled=self.view_model.current_page > 0)
        dpg.configure_item("next_button", enabled=self.view_model.current_page < self.view_model.max_pages - 1)

    def on_cancel_query(self) -> None:
        """キャンセルボタンが押されたときのハンドラ"""
        self.view_model.cancel_query()

    # UIイベントハンドラ
    def on_query_input_change(self, sender: int, app_data: str, user_data: Any) -> None:
        """クエリ入力フィールドが変更されたときのハンドラ"""
        if app_data:  # Enterキーが押された場合
            self.on_execute_query()

    def on_execute_query(self) -> None:
        """クエリ実行ボタンが押されたときのハンドラ"""
        query: str = dpg.get_value("query_input")
        self.view_model.execute_query(query)

    def on_prev_page(self) -> None:
        """前のページボタンが押されたときのハンドラ"""
        self.view_model.prev_page()

    def on_next_page(self) -> None:
        """次のページボタンが押されたときのハンドラ"""
        self.view_model.next_page()

    def on_apply_options(self) -> None:
        """クエリオプション適用ボタンが押されたときのハンドラ"""
        self.view_model.apply_query_options()
