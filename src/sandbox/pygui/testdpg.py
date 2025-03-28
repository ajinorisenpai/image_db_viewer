import dearpygui.dearpygui as dpg
import numpy as np
from src.utils.util import dpg_resolve_font


def color_addition_test():
    dpg.create_context()

    # 日本語フォント設定
    dpg_resolve_font()

    def log_debug(message):
        print(f"[DEBUG] {message}")

    # 現在ホバー中の要素を追跡するための変数
    current_hover_item = None

    # 色加算処理を行う関数
    def add_color_to_texture(base_texture, add_r, add_g, add_b, add_a=0):
        """テクスチャデータに色を加算する関数"""
        # 元のテクスチャをコピー
        result = np.copy(base_texture)

        # 色を加算（0-1の範囲でクリップ）
        result[:, :, 0] = np.clip(result[:, :, 0] + add_r / 255.0, 0.0, 1.0)  # R
        result[:, :, 1] = np.clip(result[:, :, 1] + add_g / 255.0, 0.0, 1.0)  # G
        result[:, :, 2] = np.clip(result[:, :, 2] + add_b / 255.0, 0.0, 1.0)  # B

        if add_a > 0:
            result[:, :, 3] = np.clip(result[:, :, 3] + add_a / 255.0, 0.0, 1.0)  # A

        return result

    # 基本テクスチャの作成
    textures = {}

    def create_basic_textures():
        # (テクスチャ作成部分は変更なし)
        # 赤色テクスチャ
        red_texture = np.ones((100, 100, 4), dtype=np.float32)
        red_texture[:, :, 0] = 1.0  # R
        red_texture[:, :, 1] = 0.0  # G
        red_texture[:, :, 2] = 0.0  # B
        red_texture[:, :, 3] = 1.0  # A
        textures["red_texture"] = red_texture

        # 青色テクスチャ
        blue_texture = np.ones((100, 100, 4), dtype=np.float32)
        blue_texture[:, :, 0] = 0.0  # R
        blue_texture[:, :, 1] = 0.0  # G
        blue_texture[:, :, 2] = 1.0  # B
        blue_texture[:, :, 3] = 1.0  # A
        textures["blue_texture"] = blue_texture

        # 黒色テクスチャ
        black_texture = np.ones((100, 100, 4), dtype=np.float32)
        black_texture[:, :, 0] = 0.0  # R
        black_texture[:, :, 1] = 0.0  # G
        black_texture[:, :, 2] = 0.0  # B
        black_texture[:, :, 3] = 1.0  # A
        textures["black_texture"] = black_texture

        # 事前に加工したテクスチャも作成
        red_blue = add_color_to_texture(textures["red_texture"], 0, 0, 100)
        textures["red_blue_hover"] = red_blue

        red_yellow = add_color_to_texture(textures["red_texture"], 0, 100, 0)
        textures["red_yellow_hover"] = red_yellow

        black_white = add_color_to_texture(textures["black_texture"], 50, 50, 50)
        textures["black_white_hover"] = black_white

        # テクスチャレジストリに登録
        with dpg.texture_registry():
            for tag, texture in textures.items():
                height, width = texture.shape[:2]
                dpg.add_static_texture(
                    width=width,
                    height=height,
                    default_value=texture,
                    tag=tag
                )

    # ホバー可能なアイテムの情報
    hover_items = {}

    # 修正: ビューポートのY座標オフセットを追跡
    y_offset = 0

    def register_hover_item(item_id, normal_texture, hover_texture, width=100, height=100):
        """ホバー可能なアイテムを登録する関数"""
        # アイテムの情報を保存
        hover_items[item_id] = {
            "normal_texture": normal_texture,
            "hover_texture": hover_texture,
            "width": width,
            "height": height,
            "mouse_pos_adjustment": [0, 0]  # 座標調整用
        }

    # デバッグモードフラグ
    debug_mode = True
    last_detected_hover = None

    # ホバー判定用のマウス移動ハンドラ
    def mouse_move_callback(sender, app_data):
        nonlocal current_hover_item, last_detected_hover

        # マウス座標を取得
        mouse_pos = dpg.get_mouse_pos()
        mouse_pos_global = mouse_pos

        # デバッグモードでマウス位置を表示
        if debug_mode:
            dpg.set_value("mouse_pos", f"マウス位置: X={mouse_pos[0]:.1f}, Y={mouse_pos[1]:.1f}")

        # 新しいホバー要素を検出
        new_hover_item = None
        hover_debug_info = []

        # 各ホバー可能アイテムをチェック
        for item_id, item_info in hover_items.items():
            try:
                # アイテムが存在するか確認
                if not dpg.does_item_exist(item_id):
                    continue

                # アイテムが表示されているか確認
                if not dpg.is_item_visible(item_id):
                    continue

                # 修正: アイテムの実際の位置を取得
                item_pos = dpg.get_item_pos(item_id)

                # アイテムの親の位置も考慮
                parent_stack = []
                parent = dpg.get_item_parent(item_id)
                while parent and parent != 0:
                    parent_stack.append(parent)
                    parent = dpg.get_item_parent(parent)

                # 親の位置を加算（逆順で処理）
                parent_offset = [0, 0]
                for parent in reversed(parent_stack):
                    if dpg.get_item_type(parent) in ["mvAppItemType::mvWindowAppItem", "mvAppItemType::mvChildWindow"]:
                        parent_pos = dpg.get_item_pos(parent)
                        parent_offset[0] += parent_pos[0]
                        parent_offset[1] += parent_pos[1]

                # 最終的なアイテム位置の計算
                actual_item_pos = [
                    item_pos[0] + parent_offset[0],
                    item_pos[1] + parent_offset[1]
                ]

                # マウス位置の調整（カスタム調整があれば適用）
                adjusted_pos = [
                    mouse_pos[0] - item_info["mouse_pos_adjustment"][0],
                    mouse_pos[1] - item_info["mouse_pos_adjustment"][1]
                ]

                # ホバー判定用の矩形を計算
                rect = [
                    actual_item_pos[0],  # x1
                    actual_item_pos[1],  # y1
                    actual_item_pos[0] + item_info["width"],  # x2
                    actual_item_pos[1] + item_info["height"]  # y2
                ]

                # デバッグ情報を収集
                if debug_mode:
                    hover_debug_info.append({
                        "id": item_id,
                        "rect": rect,
                        "in_rect": (rect[0] <= mouse_pos[0] <= rect[2] and rect[1] <= mouse_pos[1] <= rect[3])
                    })

                # マウスがアイテム内にあるかチェック
                if (rect[0] <= mouse_pos[0] <= rect[2] and
                        rect[1] <= mouse_pos[1] <= rect[3]):
                    new_hover_item = item_id
                    break

            except Exception as e:
                log_debug(f"ホバーチェックエラー（{item_id}）: {e}")

        # デバッグ情報を更新
        if debug_mode and hover_debug_info:
            debug_text = "\n".join([
                f"アイテム: {info['id']}, 領域: ({info['rect'][0]:.1f},{info['rect'][1]:.1f})-({info['rect'][2]:.1f},{info['rect'][3]:.1f}), 内部: {info['in_rect']}"
                for info in hover_debug_info
            ])
            dpg.set_value("hover_debug", debug_text)

        # ホバー状態に変更があった場合の処理
        if new_hover_item != current_hover_item:
            # 以前のホバーアイテムからマウスが離れた場合
            if current_hover_item is not None and current_hover_item in hover_items:
                # 元のテクスチャに戻す
                item_info = hover_items[current_hover_item]
                dpg.configure_item(current_hover_item, texture_tag=item_info["normal_texture"])
                log_debug(f"ホバー終了: {current_hover_item}")
                dpg.set_value("status", "通常状態")

            # 新しいアイテムにホバーした場合
            if new_hover_item is not None:
                # ホバー効果を適用
                item_info = hover_items[new_hover_item]
                dpg.configure_item(new_hover_item, texture_tag=item_info["hover_texture"])
                log_debug(f"ホバー開始: {new_hover_item}")
                dpg.set_value("status", f"ホバー中: {new_hover_item}")

                # 最後に検出されたホバーアイテムを記録
                last_detected_hover = new_hover_item

            # 現在のホバーアイテムを更新
            current_hover_item = new_hover_item

    # メインウィンドウ
    with dpg.window(label="色加算テスト", width=800, height=600):
        dpg.add_text("画像に色を加算するテスト - Y座標修正版")

        # 基本テクスチャを作成
        create_basic_textures()

        # ホバーによる色加算テスト
        dpg.add_text("ホバーによる色加算テスト", bullet=True)

        with dpg.group(horizontal=True):
            # 赤に青を加算（ホバー時）
            with dpg.group():
                dpg.add_text("赤 + 青 (ホバー)")
                img1 = dpg.add_image("red_texture", tag="hover_red_blue")
                register_hover_item("hover_red_blue", "red_texture", "red_blue_hover")

                with dpg.tooltip(img1):
                    dpg.add_text("ホバーで青色を加算")

            # 赤に黄色を加算（ホバー時）
            with dpg.group():
                dpg.add_text("赤 + 黄 (ホバー)")
                img2 = dpg.add_image("red_texture", tag="hover_red_yellow")
                register_hover_item("hover_red_yellow", "red_texture", "red_yellow_hover")

                with dpg.tooltip(img2):
                    dpg.add_text("ホバーで黄色を加算")

            # 黒に明るさを加算（ホバー時）
            with dpg.group():
                dpg.add_text("黒 + 白 (ホバー)")
                img3 = dpg.add_image("black_texture", tag="hover_black_white")
                register_hover_item("hover_black_white", "black_texture", "black_white_hover")

                with dpg.tooltip(img3):
                    dpg.add_text("ホバーで明るくする")

        # ステータス表示とデバッグ情報
        dpg.add_text("通常状態", tag="status")
        dpg.add_text("マウス位置: ", tag="mouse_pos")
        dpg.add_text("ホバー領域情報:", tag="hover_debug")

        # 座標調整スライダー
        dpg.add_text("座標調整", bullet=True)

        def update_y_adjustment(sender, value):
            nonlocal y_offset
            y_offset = value
            for item_id in hover_items:
                hover_items[item_id]["mouse_pos_adjustment"][1] = value

            # デバッグ表示を更新
            dpg.set_value("y_adjustment", f"Y座標調整: {value}px")

        dpg.add_slider_int(
            label="Y座標調整",
            default_value=0,
            min_value=-50,
            max_value=50,
            callback=update_y_adjustment
        )
        dpg.add_text("Y座標調整: 0px", tag="y_adjustment")

        # デバッグモード切り替え
        def toggle_debug(sender, value):
            nonlocal debug_mode
            debug_mode = value

        dpg.add_checkbox(
            label="デバッグ情報表示",
            default_value=True,
            callback=toggle_debug
        )

    # グローバルマウス移動ハンドラを追加
    with dpg.handler_registry():
        dpg.add_mouse_move_handler(callback=mouse_move_callback)

    # ビューポート設定と表示
    dpg.create_viewport(title="座標調整テスト", width=800, height=800)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    color_addition_test()
