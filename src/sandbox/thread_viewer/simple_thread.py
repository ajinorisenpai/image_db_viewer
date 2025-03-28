import dearpygui.dearpygui as dpg
from src.utils.util import dpg_resolve_font

def save_callback():
    print("Save Clicked")

dpg.create_context()
dpg_resolve_font()
dpg.window(label="Simple Thread")
dpg.create_viewport()
dpg.setup_dearpygui()

dpg.show_documentation()


dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()