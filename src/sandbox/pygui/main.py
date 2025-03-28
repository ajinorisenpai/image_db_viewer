import dearpygui.dearpygui as dpg
from src.utils.util import dpg_resolve_font
from src.create_db import create_character_table

# カウンター変数
count = 0

def main():
    # コンテキストの作成
    dpg.create_context()
    dpg_resolve_font()
    # ビューポートの作成
    dpg.create_viewport(title="create_db", width=400, height=200)

    # ウィンドウの作成
    with dpg.window(label="カウンターアプリ",tag="main window", width=400, height=200):
        dpg.set_primary_window("main window", True)
        # カウント増加用のボタン
        dpg.add_button(label="create_db", callback=OnClickCreateDB)
        dpg.add_button(label="CreateCharacterTable", callback=OnClickCreateCharacterTable)

    # セットアップと表示
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()

# ボタンクリックのコールバック関数
def OnClickCreateDB(sender, app_data, user_data):
    CreateDB.main()
# ボタンクリックのコールバック関数
def OnClickCreateCharacterTable(sender, app_data, user_data):
    CreateCharacterTable.main()

if __name__ == "__main__":
    main()