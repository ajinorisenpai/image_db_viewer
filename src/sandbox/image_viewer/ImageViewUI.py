import dearpygui.dearpygui as dpg
import cv2
import threading
import queue
import time
import os
import json  # 設定ファイル用に追加


class ImageViewUI:
    """画像表示とUIを担当するクラス"""

    def __init__(self, image_loader):
        self.image_loader = image_loader
        self.loaded_count = 0
        self.last_folder_path = ""  # 最後に選択したフォルダパスを保持
        self.config_file = "image_viewer_config.json"  # 設定ファイルのパス

        # 設定ファイルからデフォルトパスを読み込み
        self.load_config()

        # タグ名の定義
        self.tags = {
            "main_window": "main_window",
            "status": "status",
            "progress_bar": "progress_bar",
            "total_images": "total_images",
            "loaded_images": "loaded_images",
            "loaded_count": "loaded_count",
            "thumbnails": "thumbnails",
            "image_view": "image_view",
            "file_dialog": "file_dialog",
            "path_text": "path_text"  # パス表示用のテキスト要素を追加
        }

    def load_config(self):
        """設定ファイルを読み込む"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.last_folder_path = config.get('last_folder_path', '')
        except Exception as e:
            print(f"設定ファイルの読み込みエラー: {e}")
            self.last_folder_path = ""

    def save_config(self):
        """設定ファイルを保存する"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'last_folder_path': self.last_folder_path}, f)
        except Exception as e:
            print(f"設定ファイルの保存エラー: {e}")

    def setup_ui(self, font_path=None):
        """UIの初期設定"""
        dpg.create_context()

        # 日本語フォントの読み込み（指定がある場合）
        if font_path and os.path.exists(font_path):
            with dpg.font_registry():
                with dpg.font(font_path, size=16) as default_font:
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)
                    dpg.add_font_range(0x0800, 0xFFFF)
                    dpg.add_font_chars(list(range(0x0800, 0xFFFF)))
                dpg.bind_font(default_font)

        dpg.create_viewport(title="画像ビューア", width=1200, height=800)

        # テクスチャレジストリ
        with dpg.texture_registry():
            pass

        # ファイルダイアログ - デフォルトパスを設定
        with dpg.file_dialog(
                directory_selector=True,
                show=False,
                callback=self._on_folder_selected,
                tag=self.tags["file_dialog"],
                default_path=self.last_folder_path  # デフォルトパスを設定
        ):
            dpg.add_file_extension(".*")

        # メインウィンドウ
        with dpg.window(tag=self.tags["main_window"], label="マルチスレッド画像ビューア", width=1180, height=780):
            with dpg.menu_bar():
                with dpg.menu(label="ファイル"):
                    dpg.add_menu_item(label="フォルダを開く", callback=lambda: dpg.show_item(self.tags["file_dialog"]))
                    dpg.add_menu_item(label="終了", callback=lambda: dpg.stop_dearpygui())

            # 現在のフォルダパス表示
            with dpg.group(horizontal=True):
                dpg.add_text("現在のフォルダ: ")
                dpg.add_text(self.last_folder_path if self.last_folder_path else "未選択", tag=self.tags["path_text"])

            # ステータスバー
            dpg.add_text("フォルダを選択してください", tag=self.tags["status"])
            dpg.add_progress_bar(default_value=0, width=-1, tag=self.tags["progress_bar"])

            # 画像カウント情報
            with dpg.group(horizontal=True):
                dpg.add_text("合計: 0枚", tag=self.tags["total_images"])
                dpg.add_text("読み込み済み: 0枚", tag=self.tags["loaded_images"])
                dpg.add_input_int(label="", default_value=0, tag=self.tags["loaded_count"], show=False, width=1,
                                  enabled=False)

            # メインコンテンツエリア（分割表示）
            with dpg.group(horizontal=True):
                # サムネイル一覧（左側）
                dpg.add_child_window(tag=self.tags["thumbnails"], width=250)
                # 画像表示エリア（右側）
                dpg.add_child_window(tag=self.tags["image_view"], horizontal_scrollbar=True)

        # 定期的なUI更新用のハンドラ
        with dpg.handler_registry():
            dpg.add_mouse_move_handler(callback=self._update_ui)

        # 前回のフォルダパスがあれば自動的に読み込み
        if self.last_folder_path and os.path.exists(self.last_folder_path):
            self._load_default_folder()

    def _load_default_folder(self):
        """デフォルトフォルダを読み込む"""
        if self.last_folder_path and os.path.exists(self.last_folder_path):
            dpg.set_value(self.tags["status"], f"フォルダ '{self.last_folder_path}' から読み込み中...")
            dpg.set_value(self.tags["path_text"], self.last_folder_path)

            # UI要素のリセット
            dpg.set_value(self.tags["progress_bar"], 0)
            dpg.set_value(self.tags["total_images"], "合計: 0枚")
            dpg.set_value(self.tags["loaded_images"], "読み込み済み: 0枚")
            dpg.set_value(self.tags["loaded_count"], 0)
            self.loaded_count = 0

            dpg.delete_item(self.tags["thumbnails"], children_only=True)
            dpg.delete_item(self.tags["image_view"], children_only=True)

            # 読み込み開始
            self.image_loader.load_folder(self.last_folder_path, self._status_callback)

    def _on_folder_selected(self, sender, app_data):
        """フォルダ選択時のコールバック"""
        folder_path = app_data['file_path_name']
        self.last_folder_path = folder_path  # 選択したパスを保存

        # 設定ファイルに保存
        self.save_config()

        # パス表示を更新
        dpg.set_value(self.tags["path_text"], folder_path)

        # UI要素のリセット
        dpg.set_value(self.tags["progress_bar"], 0)
        dpg.set_value(self.tags["status"], f"フォルダ '{folder_path}' から読み込み中...")
        dpg.set_value(self.tags["total_images"], "合計: 0枚")
        dpg.set_value(self.tags["loaded_images"], "読み込み済み: 0枚")
        dpg.set_value(self.tags["loaded_count"], 0)
        self.loaded_count = 0

        dpg.delete_item(self.tags["thumbnails"], children_only=True)
        dpg.delete_item(self.tags["image_view"], children_only=True)

        # 読み込み開始
        self.image_loader.load_folder(folder_path, self._status_callback)

    def _status_callback(self, status_type, data):
        """画像読み込みの状態コールバック"""
        if status_type == "total":
            dpg.set_value(self.tags["total_images"], f"合計: {data}枚")

        elif status_type == "progress":
            dpg.set_value(self.tags["progress_bar"], data['progress'])
            dpg.set_value(self.tags["status"], f"読み込み中... {data['current']}/{data['total']}")

        elif status_type == "complete":
            dpg.set_value(self.tags["status"], f"読み込み完了: {data}枚")

        elif status_type == "cancelled":
            dpg.set_value(self.tags["status"], "読み込みが中断されました")

        elif status_type == "error":
            dpg.set_value(self.tags["status"], f"エラー: {data}")

    def _update_ui(self):
        """UI更新コールバック"""
        # キューに画像があれば処理
        while not self.image_loader.image_queue.empty():
            data = self.image_loader.image_queue.get()

            # サムネイル用テクスチャを作成
            thumb = data['thumbnail']
            thumb_h, thumb_w = thumb.shape[:2]
            thumb_tag = f"thumb_{data['filename']}"

            with dpg.texture_registry():
                dpg.add_static_texture(
                    width=thumb_w,
                    height=thumb_h,
                    default_value=thumb / 255.0,
                    tag=thumb_tag
                )

            # サムネイルボタンを追加
            with dpg.group(horizontal=True, parent=self.tags["thumbnails"]):
                dpg.add_image(thumb_tag)
                dpg.add_button(
                    label=data['filename'],
                    callback=lambda s, a, u: self.show_full_image(u),
                    user_data=data,
                    width=150
                )

            # 読み込み済み画像数を更新
            self.loaded_count += 1
            dpg.set_value(self.tags["loaded_count"], self.loaded_count)
            dpg.set_value(self.tags["loaded_images"], f"読み込み済み: {self.loaded_count}枚")

    def show_full_image(self, data):
        """画像を表示する関数"""
        # 表示エリアをクリア
        dpg.delete_item(self.tags["image_view"], children_only=True)

        # 画像情報を表示
        dpg.add_text(f"ファイル: {data['filename']}", parent=self.tags["image_view"])
        dpg.add_text(f"サイズ: {data['width']}x{data['height']}ピクセル", parent=self.tags["image_view"])

        # 画像用テクスチャを作成
        img = data['image']
        h, w = img.shape[:2]
        img_tag = f"img_{data['filename']}"

        # テクスチャが存在しない場合のみ作成
        if not dpg.does_item_exist(img_tag):
            with dpg.texture_registry():
                dpg.add_static_texture(
                    width=w,
                    height=h,
                    default_value=img / 255.0,
                    tag=img_tag
                )

        # 画像を表示
        dpg.add_image(img_tag, parent=self.tags["image_view"])

    def run(self):
        """アプリケーションの実行"""
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window(self.tags["main_window"], True)
        dpg.start_dearpygui()
        dpg.destroy_context()