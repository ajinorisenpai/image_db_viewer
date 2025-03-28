import sys
import os

from src.utils.config_constant import AppSettings

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dearpygui.dearpygui as dpg  # dearpygui version 2.0.0
import sqlite3
from PIL import Image
import numpy as np
from src.utils.util import dpg_resolve_font

# クエリオプション用のグローバル変数
query_options = {
    "random": False,
    "size_type": True,
    "limit": 63,
    "artist": ""
}

# 一時的なオプション保存用
temp_query_options = query_options.copy()


# クエリを生成する関数
def generate_query():
    base_query = current_query
    conditions = []

    if query_options["size_type"]:
        conditions.append("size_type=1")

    if query_options["artist"]:
        conditions.append(f"artists LIKE '%{query_options['artist']}%'")

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    if query_options["random"]:
        base_query += " ORDER BY RANDOM()"

    return base_query


# クエリオプションウィンドウのコールバック
def update_temp_options(sender=None, app_data=None, user_data=None):
    global temp_query_options
    if sender == "random_checkbox":
        temp_query_options["random"] = app_data
    elif sender == "size_type_checkbox":
        temp_query_options["size_type"] = app_data
    elif sender == "artist_input":
        temp_query_options["artist"] = app_data
    elif sender == "limit_input":
        try:
            temp_query_options["limit"] = int(app_data)
        except ValueError:
            pass


def apply_query_options():
    global query_options, temp_query_options
    query_options = temp_query_options.copy()
    dpg.set_value("query_input", generate_query())
    execute_query()


# DearPyGuiの初期化
dpg.create_context()
# 日本語フォントを設定
dpg_resolve_font()
dpg.setup_dearpygui()
# ウィンドウサイズを1.5倍に拡大
dpg.create_viewport(title="SQLite画像ビューアー", width=1600, height=900)
dpg.show_viewport()

# テクスチャレジストリの作成
with dpg.texture_registry(show=False, tag="texture_registry"):
    pass


# SQLiteデータベースから画像パスを取得する関数
def query_images_from_db(query, limit=25, offset=0):
    conn = sqlite3.connect(AppSettings.DB_FILE)
    cursor = conn.cursor()
    # LIMITとOFFSETがクエリに含まれていない場合は追加
    if "LIMIT" not in query.upper():
        query += f" LIMIT {limit} OFFSET {offset}"
    cursor.execute(query)
    paths = [row[0] for row in cursor.fetchall()]
    conn.close()
    return paths


# 画像サムネイルを作成する関数
def create_thumbnail(image_path, max_size=(200, 200)):
    try:
        img = Image.open(image_path)
        img.thumbnail(max_size, Image.LANCZOS)

        # PIL画像をDPG用のnumpy配列に変換
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        return img.size[0], img.size[1], 4, np.array(img, dtype=np.float32).ravel() / 255.0
    except Exception as e:
        print(f"サムネイル作成エラー ({image_path}): {e}")
        # エラー時の赤い長方形プレースホルダー
        width, height = 100, 100
        placeholder = np.zeros((height, width, 4), dtype=np.float32)
        placeholder[:, :, 0] = 1.0  # 赤チャンネル
        placeholder[:, :, 3] = 1.0  # アルファチャンネル
        return width, height, 4, placeholder.ravel()


# ページネーション用グローバル変数
current_page = 0
total_images = 0
current_query = "SELECT image_path FROM image_relation_view"


# 画像をグリッドに表示する関数
def load_images_to_grid(paths):
    global total_images

    # 以前の項目とテクスチャをクリア
    if dpg.does_item_exist("grid_content"):
        dpg.delete_item("grid_content")
    for item in dpg.get_item_children("texture_registry", slot=1):
        dpg.delete_item(item)

    # グリッドの作成
    with dpg.group(parent="grid_container", tag="grid_content"):
        # グリッドレイアウトのパラメータ
        cols = 7
        grid_spacing = 5  # マージンを5に縮小
        thumbnail_width = 200  # サムネイル + マージンを1000に縮小

        # 画像をグリッドに配置
        for i, path in enumerate(paths):
            # グリッド位置を計算
            col = i % cols
            row = i // cols

            # 位置を計算（X座標とY座標）
            x_pos = col * thumbnail_width
            y_pos = row * 136  # 高さも220に縮小

            # 画像を表示するグループ
            with dpg.group(pos=[x_pos, y_pos]):
                if os.path.exists(path):
                    # 画像の読み込みとリサイズ
                    width, height, channels, data = create_thumbnail(path)

                    # テクスチャとして追加
                    texture_id = dpg.add_static_texture(width, height, data, parent="texture_registry")

                    # 画像の表示（ツールチップ付き）
                    img = dpg.add_image(texture_id, tag=f"image_{i}")
                    with dpg.tooltip(img):
                        dpg.add_text(path)
                else:
                    # 画像が見つからない場合のエラーメッセージ（ツールチップ付き）
                    error_text = f"画像が見つかりません: {os.path.basename(path)}"
                    error = dpg.add_text(error_text, tag=f"error_{i}")
                    with dpg.tooltip(error):
                        dpg.add_text(path)

    # ページネーション情報の更新
    total_images = get_total_images_count(current_query)
    max_pages = max(1, (total_images + query_options["limit"] - 1) // query_options["limit"])
    dpg.set_value("pagination_text", f"ページ {current_page + 1}/{max_pages} (合計: {total_images}枚)")


# 画像の総数を取得する関数
def get_total_images_count(query):
    try:
        # 元のクエリからWHERE句を抽出
        where_clause = ""
        if "WHERE" in query.upper():
            where_parts = query.upper().split("WHERE", 1)
            if len(where_parts) > 1:
                where_clause = where_parts[1]
                # ORDER BY、LIMIT、OFFSETがある場合は除去
                if "ORDER BY" in where_clause:
                    where_clause = where_clause.split("ORDER BY", 1)[0]
                if "LIMIT" in where_clause:
                    where_clause = where_clause.split("LIMIT", 1)[0]

        # カウントクエリの作成（テーブル名を統一）
        count_query = "SELECT COUNT(*) FROM image_relation_view"

        # WHERE句がある場合は含める
        if where_clause:
            count_query += f" WHERE {where_clause}"

        conn = sqlite3.connect(AppSettings.DB_FILE)  # 正しいDBパスを使用
        cursor = conn.cursor()
        cursor.execute(count_query)
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"カウント取得エラー: {e}")
        return 0


# クエリ実行のコールバック
def execute_query(sender=None, app_data=None, user_data=None):
    global current_page, current_query
    current_query = dpg.get_value("query_input")
    current_page = 0
    paths = query_images_from_db(current_query, query_options["limit"], current_page * query_options["limit"])
    load_images_to_grid(paths)


# キー押下時のコールバック
def on_key(sender, app_data, user_data):
    execute_query()


# ページネーションコールバック
def next_page():
    global current_page
    total_pages = max(1, (total_images + query_options["limit"] - 1) // query_options["limit"])
    if current_page < total_pages - 1:
        current_page += 1
        paths = query_images_from_db(current_query, query_options["limit"], current_page * query_options["limit"])
        load_images_to_grid(paths)


def prev_page():
    global current_page
    if current_page > 0:
        current_page -= 1
        paths = query_images_from_db(current_query, query_options["limit"], current_page * query_options["limit"])
        load_images_to_grid(paths)


# メインウィンドウの作成
with dpg.window(label="SQLite画像ビューアー", width=1600, height=900, tag="main_window"):
    dpg.set_primary_window("main_window", True)
    with dpg.group(horizontal=True):
        query_input = dpg.add_input_text(label="SQLクエリ", tag="query_input", width=600,
                                         default_value=generate_query(), callback=on_key, on_enter=True)
        dpg.add_button(label="クエリ実行", callback=execute_query)
        dpg.add_button(label="クエリオプション", callback=lambda: dpg.show_item("query_options_window"))

    # クエリオプションウィンドウ
    with dpg.window(label="クエリオプション", tag="query_options_window", show=False, width=300, height=200):
        dpg.add_checkbox(label="ランダム表示", tag="random_checkbox", default_value=query_options["random"],
                         callback=update_temp_options)
        dpg.add_checkbox(label="size_type=1のみ", tag="size_type_checkbox", default_value=query_options["size_type"],
                         callback=update_temp_options)
        dpg.add_text("アーティスト検索:")
        dpg.add_input_text(tag="artist_input", default_value=query_options["artist"], callback=update_temp_options)
        dpg.add_text("表示件数:")
        dpg.add_input_int(tag="limit_input", default_value=query_options["limit"], callback=update_temp_options,
                          min_value=1, max_value=1000)
        dpg.add_button(label="適用", callback=apply_query_options)

    # ページネーションコントロール
    with dpg.group(horizontal=True):
        dpg.add_button(label="前のページ", callback=prev_page)
        dpg.add_text("ページ 1/1 (合計: 0枚)", tag="pagination_text")
        dpg.add_button(label="次のページ", callback=next_page)

    # 画像用コンテナの作成
    dpg.add_child_window(width=-1, height=-1, tag="grid_container")

# DearPyGuiの起動
dpg.start_dearpygui()
dpg.destroy_context()
