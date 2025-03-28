import dearpygui.dearpygui as dpg

from src.utils.config_constant import AppSettings


def dpg_resolve_font():
    with dpg.font_registry():
        with dpg.font(AppSettings.FONT_PATH,size=16) as default_font:
            # 日本語の文字範囲を追加
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Japanese)
            # ユニコード範囲を明示的に追加
            dpg.add_font_range(0x0800, 0xFFFF)
            # 特定の文字をリストで追加
            dpg.add_font_chars(list(range(0x0800, 0xFFFF)))
        dpg.bind_font(default_font)

def normalize_slash(path):
    return path.replace('\\', '/')