import dearpygui.dearpygui as dpg
import os
from PIL import Image
import numpy as np


def simple_image_viewer_with_zoom():
    # コンテキスト作成
    dpg.create_context()
    dpg.create_viewport(title="Image Viewer with Zoom", width=1200, height=800)

    # テクスチャIDを管理するためのカウンター
    texture_counter = 0

    # 状態変数
    state = {
        "is_zoomed": False,  # ズーム状態
        "original_image": None,  # 元の画像データ (PIL Image形式)
        "original_image_np": None,  # 元の画像データ (NumPy配列形式)
        "zoom_factor": 2.0,  # ズーム倍率
        "width": 0,  # 元画像の幅
        "height": 0,  # 元画像の高さ
        "display_width": 0,  # 表示サイズの幅
        "display_height": 0  # 表示サイズの高さ
    }

    # クリックイベントハンドラ
    def on_image_click(sender, app_data):
        # クリック位置取得
        mouse_pos = dpg.get_mouse_pos()
        image_pos = dpg.get_item_pos("image_display")

        # 画像内の相対座標
        x = int(mouse_pos[0] - image_pos[0])
        y = int(mouse_pos[1] - image_pos[1])

        width = state["width"]
        height = state["height"]
        display_width = state["display_width"]
        display_height = state["display_height"]

        # 表示サイズから元画像サイズへの変換
        orig_x = int(x * width / display_width)
        orig_y = int(y * height / display_height)

        # 画像範囲内かチェック
        if 0 <= x < display_width and 0 <= y < display_height:
            if state["is_zoomed"]:
                # ズーム解除 - 元の画像に戻す
                state["is_zoomed"] = False
                dpg.set_value("status_text", "通常表示")

                # 元のサイズで表示
                img_data = np.array(state["original_image"]).astype(np.float32).flatten() / 255.0
                update_texture(width, height, img_data, width, height)
            else:
                # ズーム実行 - クリック位置を中心に拡大
                state["is_zoomed"] = True

                # 元の画像サイズでのズーム範囲の計算
                zoom_width = int(width / state["zoom_factor"])
                zoom_height = int(height / state["zoom_factor"])

                # クリック位置を中心とした領域
                x1 = max(0, orig_x - zoom_width // 2)
                y1 = max(0, orig_y - zoom_height // 2)

                # 右下が画像をはみ出さないよう調整
                x2 = min(width, x1 + zoom_width)
                y2 = min(height, y1 + zoom_height)

                # 左上を再調整（右下が合うように）
                if x2 == width:
                    x1 = max(0, width - zoom_width)
                if y2 == height:
                    y1 = max(0, height - zoom_height)

                # 領域を切り出し - PIL Imageを使用して切り出しと拡大を一括処理
                zoomed_img = state["original_image"].crop((x1, y1, x2, y2))

                # 切り出した画像を元の表示サイズに拡大
                zoomed_img = zoomed_img.resize((display_width, display_height), Image.LANCZOS)

                # 表示用のデータに変換
                zoomed_data = np.array(zoomed_img).astype(np.float32).flatten() / 255.0

                dpg.set_value("status_text", f"拡大表示中: 位置({x1},{y1}) - {zoom_width}x{zoom_height}から拡大")

                # テクスチャ更新（拡大表示）
                update_texture(display_width, display_height, zoomed_data, display_width, display_height)

    # テクスチャ更新関数 - ユニークなタグを使用
    def update_texture(width, height, img_data, display_width, display_height):
        nonlocal texture_counter
        texture_counter += 1
        new_tag = f"texture_id_{texture_counter}"

        # デバッグ情報
        print(f"テクスチャ更新: {width}x{height}, 表示サイズ: {display_width}x{display_height}")

        # 新しいテクスチャを作成
        with dpg.texture_registry():
            dpg.add_static_texture(width, height, img_data, tag=new_tag)

        # 画像表示を更新
        dpg.configure_item("image_display", texture_tag=new_tag, width=display_width, height=display_height)

        # 古いテクスチャを削除（メモリリークを防ぐため）
        if texture_counter > 1:
            old_tag = f"texture_id_{texture_counter - 1}"
            if dpg.does_item_exist(old_tag):
                try:
                    dpg.delete_item(old_tag)
                except:
                    print(f"テクスチャ削除失敗: {old_tag}")

    # 画像ファイルの存在確認
    if not os.path.exists("../create_db/grid.png"):
        print("エラー: grid.png が見つかりません")
        with dpg.window(label="Error", width=400, height=200):
            dpg.add_text("画像ファイル grid.png が見つかりません")
            dpg.add_button(label="閉じる", callback=lambda: dpg.stop_dearpygui())
    else:
        # 画像の読み込み
        print("画像を読み込み中...")
        img = Image.open("../create_db/grid.png")
        img = img.convert("RGBA")  # アルファチャンネルを含む形式に変換

        # 画像サイズ取得とstate更新
        width, height = img.size
        state["width"] = width
        state["height"] = height

        # 表示サイズ（初期値は元のサイズと同じ）
        display_width = width
        display_height = height

        # 画面に収まるようにサイズ調整
        max_size = 1000
        if max(width, height) > max_size:
            scale = max_size / max(width, height)
            display_width = int(width * scale)
            display_height = int(height * scale)
            # 表示用に画像リサイズ
            img_display = img.resize((display_width, display_height), Image.LANCZOS)
        else:
            img_display = img

        state["display_width"] = display_width
        state["display_height"] = display_height

        print(f"画像サイズ: {width}x{height}, 表示サイズ: {display_width}x{display_height}")

        # 元画像を保存
        state["original_image"] = img
        state["original_image_np"] = np.array(img)

        # 表示用画像データを一次元配列に変換し正規化
        img_data = np.array(img_display).astype(np.float32).flatten() / 255.0

        # DearPyGuiのウィンドウ設定
        with dpg.window(label="Image Viewer", width=display_width + 50, height=display_height + 100):
            dpg.add_text("画像をクリックでズームイン/アウト", tag="status_text")

            # 初期テクスチャの作成
            texture_counter += 1
            first_tag = f"texture_id_{texture_counter}"
            with dpg.texture_registry():
                dpg.add_static_texture(display_width, display_height, img_data, tag=first_tag)

            # 画像の表示
            dpg.add_image(first_tag, tag="image_display", width=display_width, height=display_height)

            # クリックイベントの登録
            with dpg.item_handler_registry(tag="click_handler"):
                dpg.add_item_clicked_handler(callback=on_image_click)
            dpg.bind_item_handler_registry("image_display", "click_handler")

            dpg.add_text(f"元画像サイズ: {width}x{height} ピクセル")

    # DearPyGUIのセットアップと表示
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # メインループ開始
    dpg.start_dearpygui()

    # 後片付け
    dpg.destroy_context()


if __name__ == "__main__":
    simple_image_viewer_with_zoom()
