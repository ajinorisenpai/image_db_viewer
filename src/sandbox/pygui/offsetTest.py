import dearpygui.dearpygui as dpg
import numpy as np
from src.utils.util import dpg_resolve_font


def coordinate_hierarchy_debug():
    dpg.create_context()

    # 日本語フォント設定
    dpg_resolve_font()

    # デバッグログを出力する関数
    def __log_debug(message):
        print(f"[DEBUG] {message}")

    # 座標階層情報を収集する関数
    def collect_hierarchy_info(item_id, depth=0):
        try:
            if not dpg.does_item_exist(item_id):
                return None

            # 基本情報の取得
            item_type = dpg.get_item_type(item_id)

            # ラベル取得（try-exceptで囲む）
            try:
                item_label = dpg.get_item_label(item_id)
            except:
                item_label = ""

            local_pos = dpg.get_item_pos(item_id)

            # 親の情報を取得
            parent_id = dpg.get_item_parent(item_id)

            # 子要素のリストを取得
            children = []
            try:
                children = dpg.get_item_children(item_id)
                # リストが入れ子になっている場合は最初の要素を取得
                if children and isinstance(children, list) and len(children) > 0:
                    if isinstance(children[0], list):
                        children = children[0]
            except:
                children = []

            # 累積座標（親の座標を加算）
            cumulative_pos = list(local_pos)

            # 親のチェーンを取得
            parent_chain = []
            current_parent = parent_id
            while current_parent and current_parent != 0:
                parent_chain.append(current_parent)
                current_parent = dpg.get_item_parent(current_parent)

            # 親チェーンを逆順に処理して累積座標を計算
            for p_id in reversed(parent_chain):
                try:
                    p_pos = dpg.get_item_pos(p_id)
                    p_type = dpg.get_item_type(p_id)

                    # ウィンドウ要素の場合の処理
                    if "Window" in p_type:
                        cumulative_pos[0] += p_pos[0]
                        cumulative_pos[1] += p_pos[1]
                    else:
                        cumulative_pos[0] += p_pos[0]
                        cumulative_pos[1] += p_pos[1]
                except:
                    pass

            # 親チェーン情報を整形
            parent_chain_info = []
            for p_id in parent_chain:
                try:
                    p_type = dpg.get_item_type(p_id)

                    # ラベル取得（try-exceptで囲む）
                    try:
                        p_label = dpg.get_item_label(p_id)
                    except:
                        p_label = ""

                    p_pos = dpg.get_item_pos(p_id)
                    parent_chain_info.append({
                        "id": p_id,
                        "type": p_type,
                        "label": p_label,
                        "pos": p_pos
                    })
                except:
                    pass

            # 収集した情報をまとめる
            return {
                "id": item_id,
                "type": item_type,
                "label": item_label,
                "local_pos": local_pos,
                "cumulative_pos": cumulative_pos,
                "depth": depth,
                "parent_id": parent_id,
                "parent_chain": parent_chain_info,
                "children": children
            }
        except Exception as e:
            __log_debug(f"項目情報収集エラー ({item_id}): {e}")
            return None

    # マウスの座標情報を更新する関数
    def update_mouse_info():
        mouse_pos = dpg.get_mouse_pos()
        viewport_pos = dpg.get_viewport_pos()

        # ビューポートのサイズ取得（DearPyGUI 2.0に対応）
        viewport_width = dpg.get_viewport_width()
        viewport_height = dpg.get_viewport_height()
        viewport_size = [viewport_width, viewport_height]

        dpg.set_value("mouse_pos", f"マウス位置: X={mouse_pos[0]:.1f}, Y={mouse_pos[1]:.1f}")
        dpg.set_value("viewport_info",
                      f"ビューポート: 位置=({viewport_pos[0]:.1f}, {viewport_pos[1]:.1f}), サイズ=({viewport_size[0]:.1f}, {viewport_size[1]:.1f})")

    # UI要素の階層情報を更新する関数
    def update_hierarchy_info():
        # メインウィンドウから情報収集開始
        main_info = collect_hierarchy_info("main_window")
        if not main_info:
            return

        # 表示用テキストを作成
        info_text = f"[メインウィンドウ] ID: {main_info['id']}\n"
        info_text += f"  タイプ: {main_info['type']}\n"
        info_text += f"  ラベル: {main_info['label']}\n"
        info_text += f"  ローカル座標: ({main_info['local_pos'][0]:.1f}, {main_info['local_pos'][1]:.1f})\n"
        info_text += f"  累積座標: ({main_info['cumulative_pos'][0]:.1f}, {main_info['cumulative_pos'][1]:.1f})\n"

        # 親チェーン情報の表示
        info_text += "\n[親要素チェーン]（上位から下位へ）\n"
        for i, parent in enumerate(main_info['parent_chain']):
            info_text += f"  {i + 1}. ID: {parent['id']}, タイプ: {parent['type'][:30]}...\n"
            info_text += f"     ラベル: {parent['label']}, 位置: ({parent['pos'][0]:.1f}, {parent['pos'][1]:.1f})\n"

        # テスト用要素の情報
        test_items = ["test_item1", "test_item2", "test_item3"]
        info_text += "\n[テスト要素情報]\n"

        for item_id in test_items:
            if dpg.does_item_exist(item_id):
                item_info = collect_hierarchy_info(item_id)
                if item_info:
                    info_text += f"  [要素] ID: {item_id}\n"
                    info_text += f"    タイプ: {item_info['type']}\n"
                    info_text += f"    ローカル座標: ({item_info['local_pos'][0]:.1f}, {item_info['local_pos'][1]:.1f})\n"
                    info_text += f"    累積座標: ({item_info['cumulative_pos'][0]:.1f}, {item_info['cumulative_pos'][1]:.1f})\n"
                    info_text += f"    親要素: {item_info['parent_id']}\n"

                    # 重要: 期待される階層に基づく座標計算経路を表示
                    info_text += "    座標計算経路:\n"
                    for i, parent in enumerate(reversed(item_info['parent_chain'])):
                        info_text += f"      {i + 1}. {parent['id']} ({parent['pos'][0]:.1f}, {parent['pos'][1]:.1f})\n"

        # 画像アイテムの情報（ホバー検出用）
        info_text += "\n[画像要素情報]\n"
        for img_id in ["hover_red_blue", "hover_red_yellow", "hover_black_white"]:
            if dpg.does_item_exist(img_id):
                img_info = collect_hierarchy_info(img_id)
                if img_info:
                    info_text += f"  [画像] ID: {img_id}\n"
                    info_text += f"    ローカル座標: ({img_info['local_pos'][0]:.1f}, {img_info['local_pos'][1]:.1f})\n"
                    info_text += f"    累積座標: ({img_info['cumulative_pos'][0]:.1f}, {img_info['cumulative_pos'][1]:.1f})\n"

                    # ホバー領域計算
                    width, height = 100, 100  # 画像サイズ
                    hover_rect = [
                        img_info['cumulative_pos'][0],
                        img_info['cumulative_pos'][1],
                        img_info['cumulative_pos'][0] + width,
                        img_info['cumulative_pos'][1] + height
                    ]

                    # マウス位置と交差チェック
                    mouse_pos = dpg.get_mouse_pos()
                    is_hover = (hover_rect[0] <= mouse_pos[0] <= hover_rect[2] and
                                hover_rect[1] <= mouse_pos[1] <= hover_rect[3])

                    info_text += f"    ホバー領域: ({hover_rect[0]:.1f}, {hover_rect[1]:.1f})-({hover_rect[2]:.1f}, {hover_rect[3]:.1f})\n"
                    info_text += f"    マウスホバー: {is_hover}\n"

        # 情報を更新
        dpg.set_value("hierarchy_info", info_text)

    # マウス移動ハンドラ
    def mouse_move_callback(sender, app_data):
        update_mouse_info()
        update_hierarchy_info()

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

        # ホバー効果用のテクスチャ
        textures["red_blue_hover"] = add_color_to_texture(textures["red_texture"], 0, 0, 100)
        textures["red_yellow_hover"] = add_color_to_texture(textures["red_texture"], 0, 100, 0)
        textures["black_white_hover"] = add_color_to_texture(textures["black_texture"], 50, 50, 50)

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

    # メインウィンドウ
    with dpg.window(label="座標階層デバッグ", width=800, height=600, tag="main_window"):
        dpg.add_text("DearPyGUI 2.0.0 座標階層関係デバッグ")

        # 基本テクスチャを作成
        create_basic_textures()

        # テスト用要素
        with dpg.child_window(width=400, height=200, tag="child_window1"):
            dpg.add_text("子ウィンドウ1の内容", tag="test_item1")

        with dpg.group(horizontal=True):
            dpg.add_text("グループ内テスト要素:", tag="test_item2")

            # ホバーのテスト用画像
            with dpg.group():
                dpg.add_text("赤 + 青 (ホバー)")
                dpg.add_image("red_texture", tag="hover_red_blue")

            with dpg.group():
                dpg.add_text("赤 + 黄 (ホバー)")
                dpg.add_image("red_texture", tag="hover_red_yellow")

            with dpg.group():
                dpg.add_text("黒 + 白 (ホバー)")
                dpg.add_image("black_texture", tag="hover_black_white")

        dpg.add_text("階層の深い要素:", tag="test_item3")

        # 座標情報表示エリア
        dpg.add_text("マウス位置: ", tag="mouse_pos")
        dpg.add_text("ビューポート情報: ", tag="viewport_info")

        # 階層情報表示エリア（スクロール可能）
        with dpg.child_window(height=300, horizontal_scrollbar=True):
            dpg.add_text("階層情報:", tag="hierarchy_info", wrap=0)

    # デバッグウィンドウ
    with dpg.window(label="座標オフセット情報", pos=(400, 400), width=400, height=300, tag="debug_window"):
        # ウィンドウタイトルバー高さ表示
        dpg.add_text("ウィンドウオフセット計測")

        def measure_window_title_height():
            # メインウィンドウとデバッグウィンドウの情報を取得
            main_window_pos = dpg.get_item_pos("main_window")
            debug_window_pos = dpg.get_item_pos("debug_window")

            # 親子関係と座標の違いを調査
            main_window_info = collect_hierarchy_info("main_window")
            debug_window_info = collect_hierarchy_info("debug_window")

            # 情報を表示
            info_text = "ウィンドウオフセット測定結果:\n"
            info_text += f"メインウィンドウ位置: ({main_window_pos[0]}, {main_window_pos[1]})\n"
            info_text += f"デバッグウィンドウ位置: ({debug_window_pos[0]}, {debug_window_pos[1]})\n"

            if main_window_info and 'parent_chain' in main_window_info:
                info_text += f"メインウィンドウ親数: {len(main_window_info['parent_chain'])}\n"

            if debug_window_info and 'parent_chain' in debug_window_info:
                info_text += f"デバッグウィンドウ親数: {len(debug_window_info['parent_chain'])}\n"

            # ビューポート座標を考慮した計算
            viewport_pos = dpg.get_viewport_pos()
            info_text += f"ビューポート位置: ({viewport_pos[0]}, {viewport_pos[1]})\n"

            # 推定タイトルバー高さ
            est_title_height = 30  # 一般的な値
            info_text += f"推定タイトルバー高さ: {est_title_height}px\n"

            dpg.set_value("offset_info", info_text)

        dpg.add_button(label="オフセット測定", callback=measure_window_title_height)
        dpg.add_text("オフセット情報:", tag="offset_info")

    # グローバルマウス移動ハンドラを追加
    with dpg.handler_registry():
        dpg.add_mouse_move_handler(callback=mouse_move_callback)

    # ビューポート設定と表示
    dpg.create_viewport(title="座標階層デバッグ", width=1200, height=800)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    # 初期情報更新
    update_mouse_info()
    update_hierarchy_info()

    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    coordinate_hierarchy_debug()
