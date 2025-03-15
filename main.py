import dearpygui.dearpygui as dpg


def drag_window(sender, app_data, user_data):
    """ドラッグ量を直接使用する修正版関数"""
    drag_delta = app_data  # float型の単一値
    current_pos = dpg.get_item_pos(user_data)

    new_x = current_pos[0] + drag_delta
    new_y = current_pos[1] + drag_delta
    dpg.set_item_pos(user_data, [new_x, new_y])


dpg.create_context()

# ウィンドウ設定
with dpg.window(label="ドラッグ可能ウィンドウ", tag="main_window"):
    dpg.add_text("ウィンドウをドラッグできます")
    dpg.add_drag_float(
        label="",
        no_input=True,
        callback=drag_window,
        user_data="main_window",
        speed=0.1
    )

dpg.create_viewport(title="Custom Window", width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
