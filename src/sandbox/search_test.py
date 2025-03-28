import dearpygui.dearpygui as dpg
from src.utils.util import dpg_resolve_font

open_path = "/files/artist.txt"

def load_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    except Exception as e:
        return [f"エラー: {str(e)}"]


def fuzzy_search(lines, query):
    if not query:
        return lines

    results = []
    query_terms = query.lower().split()

    for line in lines:
        line_lower = line.lower()
        if all(term in line_lower for term in query_terms):
            results.append(line)

    return results


def create_gui():
    dpg.create_context()
    dpg_resolve_font()
    # 状態変数
    state = {
        "file_lines": [],
        "search_results": [],
        "selected_index": -1
    }

    def update_search_results():
        """検索結果を更新"""
        query = dpg.get_value("search_input")
        state["search_results"] = fuzzy_search(state["file_lines"], query)

        # 検索結果表示を更新
        dpg.delete_item("search_results", children_only=True)
        for i, line in enumerate(state["search_results"]):
            # 行番号と内容を表示
            with dpg.group(parent="search_results", horizontal=True):
                dpg.add_text(f"{i + 1}:")
                dpg.add_text(line.strip())

    def on_search_input(sender, app_data):
        """検索テキスト入力時のコールバック"""
        update_search_results()

    def on_load_file(sender):
        """ファイル読み込みボタン押下時のコールバック"""
        file_path = open_path
        if file_path:
            state["file_lines"] = load_text_file(file_path)
            update_search_results()

    # メインウィンドウ
    with dpg.window(label="fzf風テキスト検索", width=800, height=600):
        # ファイルパス入力
        with dpg.group(horizontal=True):
            dpg.add_button(label="読み込み", callback=on_load_file)

        # 検索入力
        dpg.add_text("検索:")
        dpg.add_input_text(tag="search_input", callback=on_search_input, width=700)

        # 検索結果表示エリア
        dpg.add_text("検索結果:")
        with dpg.child_window(tag="search_results", width=700, height=400):
            pass

    # ビューポートの設定と表示
    dpg.create_viewport(title="fzf風テキスト検索", width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    create_gui()
