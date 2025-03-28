import dearpygui.dearpygui as dpg
import os

def set_font():
    # 日本語フォント設定
    with dpg.font_registry():
        # 日本語フォントの読み込み（フォントファイルのパスを指定）
        with dpg.font("C:/Users/thund/AppData/Local/Microsoft/Windows/Fonts/x12y16pxMaruMonica.ttf", size=16) as default_font:
            # 日本語の文字範囲を追加
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)
            # ユニコード範囲を明示的に追加
            dpg.add_font_range(0x0800, 0xFFFF)

            # 特定の文字をリストで追加
            dpg.add_font_chars(list(range(0x0800, 0xFFFF)))
        # デフォルトフォントとして設定
        dpg.bind_font(default_font)

# ファイル操作用の関数
def open_file(sender, app_data):
    file_path = app_data["file_path_name"]
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
            dpg.set_value("text_editor", text)
            dpg.set_value("status", f"ファイルを開きました: {file_path}")
            global current_file
            current_file = file_path
    except Exception as e:
        dpg.set_value("status", f"ファイルを開く際にエラーが発生しました: {e}")


def save_file(sender, app_data=None, user_data=None):
    global current_file
    if current_file:
        # すでに開いているファイルに保存
        try:
            with open(current_file, "w", encoding="utf-8") as file:
                text = dpg.get_value("text_editor")
                file.write(text)
                dpg.set_value("status", f"ファイルを保存しました: {current_file}")
        except Exception as e:
            dpg.set_value("status", f"ファイル保存エラー: {e}")
    else:
        # 新規保存ダイアログを開く
        dpg.show_item("save_file_dialog")


def save_file_as(sender, app_data):
    file_path = app_data["file_path_name"]
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            text = dpg.get_value("text_editor")
            file.write(text)
            dpg.set_value("status", f"ファイルを保存しました: {file_path}")
            global current_file
            current_file = file_path
    except Exception as e:
        dpg.set_value("status", f"ファイル保存エラー: {e}")


def new_file(sender, app_data=None, user_data=None):
    dpg.set_value("text_editor", "")
    global current_file
    current_file = None
    dpg.set_value("status", "新規ファイルを作成しました")


# GUIの初期化
dpg.create_context()
set_font()
dpg.create_viewport(title="シンプルテキストエディタ", width=1260, height=800)

# グローバル変数
current_file = None

with dpg.window(tag="primary_window"):
    # メニューバー
    with dpg.menu_bar():
        with dpg.menu(label="ファイル"):
            dpg.add_menu_item(label="新規作成", callback=new_file)
            dpg.add_menu_item(label="開く", callback=lambda: dpg.show_item("open_file_dialog"))
            dpg.add_menu_item(label="保存", callback=save_file)
            dpg.add_menu_item(label="名前を付けて保存", callback=lambda: dpg.show_item("save_file_dialog"))
            dpg.add_menu_item(label="終了", callback=lambda: dpg.stop_dearpygui())

        with dpg.menu(label="編集"):
            dpg.add_menu_item(label="切り取り(未実装)")
            dpg.add_menu_item(label="コピー(未実装)")
            dpg.add_menu_item(label="貼り付け(未実装)")

    # テキストエディタ部分（伸縮するサイズ設定）
    dpg.add_input_text(tag="text_editor", multiline=True, width=-1, height=-35)

    # ステータスバー
    dpg.add_text("準備完了", tag="status")

# ファイルを開くダイアログ
with dpg.file_dialog(
        directory_selector=False, show=False, callback=open_file,
        tag="open_file_dialog", width=700, height=400
):
    dpg.add_file_extension(".txt", color=(0, 255, 0, 255))
    dpg.add_file_extension(".py", color=(0, 255, 255, 255))
    dpg.add_file_extension(".*")

# ファイル保存ダイアログ
with dpg.file_dialog(
        directory_selector=False, show=False, callback=save_file_as,
        tag="save_file_dialog", width=700, height=400
):
    dpg.add_file_extension(".txt", color=(0, 255, 0, 255))
    dpg.add_file_extension(".py", color=(0, 255, 255, 255))
    dpg.add_file_extension(".*")

# DearPyGUIの設定と実行
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_primary_window("primary_window", True)
dpg.start_dearpygui()
dpg.destroy_context()