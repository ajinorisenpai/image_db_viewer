import dearpygui.dearpygui as dpg
import cv2
import threading
import queue
import time
import os

# 画像読み込み用のキューとスレッド制御用の変数
image_queue = queue.Queue()
loading_complete = threading.Event()
stop_loading = threading.Event()


# 画像を読み込むワーカー関数
def image_loader(folder_path):
    # 画像ファイル拡張子
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']

    try:
        # フォルダ内の画像ファイルを取得
        image_files = [
            f for f in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, f)) and
               os.path.splitext(f.lower())[1] in image_extensions
        ]

        total_files = len(image_files)
        dpg.set_value("total_images", f"合計: {total_files}枚")

        for i, filename in enumerate(image_files):
            # 停止リクエストがあった場合は処理を中断
            if stop_loading.is_set():
                break

            try:
                file_path = os.path.join(folder_path, filename)
                img = cv2.imread(file_path)
                if img is None:
                    print(f"画像の読み込みに失敗しました: {file_path}")
                    continue

                # RGBA形式に変換
                img_rgba = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)

                # サムネイル用に画像をリサイズ
                height, width = img_rgba.shape[:2]
                max_thumb_size = 100
                if width > height:
                    thumb_width = max_thumb_size
                    thumb_height = int(height * max_thumb_size / width)
                else:
                    thumb_height = max_thumb_size
                    thumb_width = int(width * max_thumb_size / height)

                thumb = cv2.resize(img_rgba, (thumb_width, thumb_height))

                # キューに情報を追加
                image_queue.put({
                    'path': file_path,
                    'filename': filename,
                    'image': img_rgba,
                    'thumbnail': thumb,
                    'width': width,
                    'height': height
                })

                # 進捗状況を更新
                progress = (i + 1) / total_files
                dpg.set_value("progress_bar", progress)
                dpg.set_value("status", f"読み込み中... {i + 1}/{total_files}")

                # UIの応答性を維持するため少し待機
                time.sleep(0.01)

            except Exception as e:
                print(f"画像処理エラー: {e} - {filename}")

        # 読み込み完了
        loading_complete.set()
        if not stop_loading.is_set():
            dpg.set_value("status", f"読み込み完了: {total_files}枚")
        else:
            dpg.set_value("status", "読み込みが中断されました")

    except Exception as e:
        print(f"フォルダ読み込みエラー: {e}")
        dpg.set_value("status", f"エラー: {e}")
        loading_complete.set()


# UI更新コールバック
def update_ui():
    # キューに画像があれば処理
    while not image_queue.empty():
        data = image_queue.get()

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
        with dpg.group(horizontal=True, parent="thumbnails"):
            dpg.add_image(thumb_tag)
            dpg.add_button(
                label=data['filename'],
                callback=lambda s, a, u: show_full_image(u),
                user_data=data,
                width=150
            )

        # 読み込み済み画像数を更新
        loaded = int(dpg.get_value("loaded_count")) + 1  # 明示的に整数型に変換
        dpg.set_value("loaded_count", loaded)
        dpg.set_value("loaded_images", f"読み込み済み: {loaded}枚")


# 画像を表示する関数
def show_full_image(data):
    # 表示エリアをクリア
    dpg.delete_item("image_view", children_only=True)

    # 画像情報を表示
    dpg.add_text(f"ファイル: {data['filename']}", parent="image_view")
    dpg.add_text(f"サイズ: {data['width']}x{data['height']}ピクセル", parent="image_view")

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
    dpg.add_image(img_tag, parent="image_view")


# フォルダ選択コールバック
def select_folder(sender, app_data):
    folder_path = app_data['file_path_name']

    # 以前のスレッドがあれば停止リクエスト
    stop_loading.set()
    time.sleep(0.2)  # スレッドが停止するのを少し待つ

    # 状態のリセット
    stop_loading.clear()
    loading_complete.clear()

    # UI要素のリセット
    dpg.set_value("progress_bar", 0)
    dpg.set_value("status", f"フォルダ '{folder_path}' から読み込み中...")
    dpg.set_value("total_images", "合計: 0枚")
    dpg.set_value("loaded_images", "読み込み済み: 0枚")
    dpg.set_value("loaded_count", 0)  # 整数値を設定
    dpg.delete_item("thumbnails", children_only=True)
    dpg.delete_item("image_view", children_only=True)

    # 新しいワーカースレッドを開始
    worker_thread = threading.Thread(
        target=image_loader,
        args=(folder_path,),
        daemon=True
    )
    worker_thread.start()


# メイン関数
def main():
    # DearPyGUIのセットアップ
    dpg.create_context()
    # 日本語フォントの読み込み（フォントファイルのパスを指定）
    with dpg.font_registry():
        with dpg.font("C:/Users/thund/AppData/Local/Microsoft/Windows/Fonts/x12y16pxMaruMonica.ttf", size=16) as default_font:
            # 日本語の文字範囲を追加
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)
            # ユニコード範囲を明示的に追加
            dpg.add_font_range(0x0800, 0xFFFF)

            # 特定の文字をリストで追加
            dpg.add_font_chars(list(range(0x0800, 0xFFFF)))
        # デフォルトフォントとして設定
        dpg.bind_font(default_font)
    dpg.create_viewport(title="画像ビューア", width=1200, height=800)

    # テクスチャレジストリ
    with dpg.texture_registry():
        pass

    # ファイルダイアログ
    with dpg.file_dialog(
            directory_selector=True,
            show=False,
            callback=select_folder,
            tag="file_dialog"
    ):
        dpg.add_file_extension(".*")

    # メインウィンドウ
    with dpg.window(tag="main_window", label="マルチスレッド画像ビューア", width=1180, height=780):
        dpg.set_primary_window("main_window", True)
        with dpg.menu_bar():
            with dpg.menu(label="ファイル"):
                dpg.add_menu_item(label="フォルダを開く", callback=lambda: dpg.show_item("file_dialog"))
                dpg.add_menu_item(label="終了", callback=lambda: dpg.stop_dearpygui())

        # ステータスバー
        dpg.add_text("フォルダを選択してください", tag="status")
        dpg.add_progress_bar(default_value=0, width=-1, tag="progress_bar")

        # 画像カウント情報
        with dpg.group(horizontal=True):
            dpg.add_text("合計: 0枚", tag="total_images")
            dpg.add_text("読み込み済み: 0枚", tag="loaded_images")
            # 初期値を整数型(0)で設定
            dpg.add_input_int(label="", default_value=0, tag="loaded_count", show=False, width=1, enabled=False)

        # メインコンテンツエリア（分割表示）
        with dpg.group(horizontal=True):
            # サムネイル一覧（左側）
            dpg.add_child_window(tag="thumbnails", width=250)

            # 画像表示エリア（右側）
            dpg.add_child_window(tag="image_view", horizontal_scrollbar=True)

    # 定期的なUI更新用のハンドラ
    with dpg.handler_registry():
        dpg.add_mouse_move_handler(callback=update_ui)

    # DearPyGUIの実行
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
