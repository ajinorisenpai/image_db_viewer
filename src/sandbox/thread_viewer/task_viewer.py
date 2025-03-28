import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import dearpygui.dearpygui as dpg #dearpygui version 2.0.0
from src.utils.util import dpg_resolve_font
dpg.create_context()
dpg_resolve_font()

def dummy_callback(sender, app_data, user_data):
    print(f"{user_data}: {app_data}")


# テーマの設定
with dpg.theme() as global_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (70, 70, 80), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_Button, (80, 80, 90), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (100, 100, 120), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (90, 90, 110), category=dpg.mvThemeCat_Core)

with dpg.theme() as timeline_clip_theme:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 120, 180), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 140, 200), category=dpg.mvThemeCat_Core)

with dpg.theme() as audio_clip_theme:
    with dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 120, 60), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (200, 140, 80), category=dpg.mvThemeCat_Core)

# メインウィンドウ
with dpg.window(label="タイムラインエディタ Pro", width=1200, height=800, no_resize=True):
    # メニューバー
    with dpg.menu_bar():
        with dpg.menu(label="ファイル"):
            dpg.add_menu_item(label="新規プロジェクト", callback=dummy_callback, user_data="新規プロジェクト")
            dpg.add_menu_item(label="開く", callback=dummy_callback, user_data="開く")
            dpg.add_menu_item(label="保存", callback=dummy_callback, user_data="保存")
            dpg.add_menu_item(label="名前を付けて保存", callback=dummy_callback, user_data="名前を付けて保存")
            dpg.add_separator()
            dpg.add_menu_item(label="書き出し", callback=dummy_callback, user_data="書き出し")
            dpg.add_separator()
            dpg.add_menu_item(label="終了", callback=dummy_callback, user_data="終了")

        with dpg.menu(label="編集"):
            dpg.add_menu_item(label="元に戻す", callback=dummy_callback, user_data="元に戻す")
            dpg.add_menu_item(label="やり直し", callback=dummy_callback, user_data="やり直し")
            dpg.add_separator()
            dpg.add_menu_item(label="切り取り", callback=dummy_callback, user_data="切り取り")
            dpg.add_menu_item(label="コピー", callback=dummy_callback, user_data="コピー")
            dpg.add_menu_item(label="貼り付け", callback=dummy_callback, user_data="貼り付け")
            dpg.add_separator()
            dpg.add_menu_item(label="クリップを分割", callback=dummy_callback, user_data="クリップを分割")
            dpg.add_menu_item(label="クリップを結合", callback=dummy_callback, user_data="クリップを結合")

        with dpg.menu(label="表示"):
            dpg.add_menu_item(label="ズームイン", callback=dummy_callback, user_data="ズームイン")
            dpg.add_menu_item(label="ズームアウト", callback=dummy_callback, user_data="ズームアウト")
            dpg.add_menu_item(label="全体を表示", callback=dummy_callback, user_data="全体を表示")
            dpg.add_separator()
            dpg.add_menu_item(label="波形表示", callback=dummy_callback, user_data="波形表示")
            dpg.add_menu_item(label="グリッド表示", callback=dummy_callback, user_data="グリッド表示")

    # メインレイアウト（上下分割）
    with dpg.group(horizontal=False):

        # プレビューとコントロールエリア
        with dpg.child_window(width=-1, height=300, border=False):
            with dpg.group(horizontal=True):
                # プレビューエリア
                with dpg.child_window(width=640, height=280, label="プレビュー"):
                    dpg.add_text("プレビュー表示エリア", pos=(270, 130))

                # 右側のパネル
                with dpg.child_window(width=-1, height=280):
                    # エフェクトとプロパティタブ
                    with dpg.tab_bar():
                        with dpg.tab(label="プロパティ"):
                            with dpg.group(horizontal=False):
                                dpg.add_input_text(label="クリップ名", default_value="選択したクリップ", width=300)
                                dpg.add_slider_float(label="開始時間", default_value=0.0, min_value=0.0, max_value=60.0,
                                                     width=300)
                                dpg.add_slider_float(label="長さ", default_value=5.0, min_value=0.1, max_value=60.0,
                                                     width=300)
                                dpg.add_slider_float(label="音量", default_value=1.0, min_value=0.0, max_value=2.0,
                                                     width=300)
                                dpg.add_combo(label="トランジション",
                                              items=["なし", "フェード", "クロスフェード", "ディゾルブ", "ワイプ"],
                                              width=300)

                        with dpg.tab(label="エフェクト"):
                            with dpg.group(horizontal=False):
                                dpg.add_button(label="エフェクトを追加", width=150)
                                dpg.add_separator()
                                with dpg.tree_node(label="色調補正"):
                                    dpg.add_slider_float(label="明るさ", default_value=0.0, min_value=-1.0,
                                                         max_value=1.0, width=300)
                                    dpg.add_slider_float(label="コントラスト", default_value=1.0, min_value=0.0,
                                                         max_value=2.0, width=300)
                                    dpg.add_slider_float(label="彩度", default_value=1.0, min_value=0.0, max_value=2.0,
                                                         width=300)
                                with dpg.tree_node(label="変形"):
                                    dpg.add_slider_float(label="スケール", default_value=1.0, min_value=0.1,
                                                         max_value=5.0, width=300)
                                    dpg.add_slider_float(label="回転", default_value=0.0, min_value=0.0,
                                                         max_value=360.0, width=300)

                        with dpg.tab(label="メディア"):
                            with dpg.group(horizontal=False):
                                with dpg.group(horizontal=True):
                                    dpg.add_button(label="メディアを追加", width=120)
                                    dpg.add_button(label="フォルダを開く", width=120)

                                with dpg.child_window(height=200, width=-1):
                                    for i in range(8):
                                        with dpg.group(horizontal=True):
                                            dpg.add_text(f"メディア{i + 1}.mp4")
                                            dpg.add_button(label="追加", width=50, callback=dummy_callback,
                                                           user_data=f"メディア{i + 1}を追加")

        # タイムラインコントロール
        with dpg.group(horizontal=True):
            dpg.add_button(label="再生", width=60, height=25, callback=dummy_callback, user_data="再生")
            dpg.add_button(label="停止", width=60, height=25, callback=dummy_callback, user_data="停止")
            dpg.add_button(label="◀◀", width=40, height=25, callback=dummy_callback, user_data="先頭へ")
            dpg.add_button(label="◀", width=40, height=25, callback=dummy_callback, user_data="前のフレーム")
            dpg.add_button(label="▶", width=40, height=25, callback=dummy_callback, user_data="次のフレーム")
            dpg.add_button(label="▶▶", width=40, height=25, callback=dummy_callback, user_data="末尾へ")
            dpg.add_text("00:00:00.000")
            dpg.add_slider_float(label="", default_value=1.0, min_value=0.25, max_value=4.0, width=150,
                                 callback=dummy_callback, user_data="ズーム")
            dpg.add_text("ズーム:")

            # 右寄せのボタン
            dpg.add_spacer(width=200)
            dpg.add_button(label="マーカー追加", width=100, height=25, callback=dummy_callback,
                           user_data="マーカー追加")
            dpg.add_button(label="クリップ分割", width=100, height=25, callback=dummy_callback,
                           user_data="クリップ分割")

        # タイムラインエリア
        with dpg.child_window(width=-1, height=-1, label="タイムライン"):
            with dpg.group(horizontal=True):
                # トラック名エリア
                with dpg.child_window(width=150, height=-1, border=False):
                    dpg.add_spacer(height=20)  # ルーラーの高さ分の余白

                    # トラック名
                    for i in range(8):
                        track_type = "ビデオ" if i < 4 else "オーディオ"
                        track_num = i + 1 if i < 4 else i - 3
                        with dpg.group(horizontal=True):
                            dpg.add_text(f"{track_type} {track_num}", indent=5)
                            dpg.add_button(label="M", width=20, height=20, indent=80, callback=dummy_callback,
                                           user_data=f"ミュート {track_type}{track_num}")
                            dpg.add_button(label="S", width=20, height=20, callback=dummy_callback,
                                           user_data=f"ソロ {track_type}{track_num}")
                        dpg.add_spacer(height=5)

                # タイムラインコンテンツエリア
                with dpg.child_window(width=-1, height=-1, border=False):
                    # タイムルーラー
                    with dpg.group(horizontal=False):
                        # ルーラー
                        with dpg.drawlist(width=2000, height=20):
                            # 目盛りを描画
                            for i in range(21):
                                dpg.draw_line((i * 100, 0), (i * 100, 10), color=(200, 200, 200), thickness=1)
                                dpg.draw_text((i * 100 + 5, 10), f"{i * 5}s", color=(200, 200, 200), size=12)

                        # グリッドと背景を描画する描画リスト
                        with dpg.drawlist(width=2000, height=600):
                            # グリッド線
                            for i in range(21):
                                dpg.draw_line((i * 100, 0), (i * 100, 600), color=(60, 60, 60), thickness=1)

                            # トラック背景
                            for i in range(8):
                                y_pos = i * 50 + 10
                                dpg.draw_rectangle((0, y_pos), (2000, y_pos + 40), fill=(50, 50, 55))
                            
                            # 現在位置マーカー
                            dpg.draw_line((350, 0), (350, 600), color=(255, 50, 50), thickness=2)

                    # クリップボタンを重ねて表示
                    with dpg.group(horizontal=False):
                        # ビデオトラック1のクリップ
                        y_pos_0 = 0 * 50 + 10 + 5
                        clip1 = dpg.add_button(label="オープニング", width=150, height=30, pos=(50, y_pos_0))
                        dpg.bind_item_theme(clip1, timeline_clip_theme)

                        clip2 = dpg.add_button(label="メインシーン", width=300, height=30, pos=(250, y_pos_0))
                        dpg.bind_item_theme(clip2, timeline_clip_theme)

                        clip3 = dpg.add_button(label="エンディング", width=200, height=30, pos=(600, y_pos_0))
                        dpg.bind_item_theme(clip3, timeline_clip_theme)

                        # ビデオトラック2のクリップ
                        y_pos_1 = 1 * 50 + 10 + 5
                        clip4 = dpg.add_button(label="オーバーレイ", width=180, height=30, pos=(300, y_pos_1))
                        dpg.bind_item_theme(clip4, timeline_clip_theme)

                        # ビデオトラック3のクリップ
                        y_pos_2 = 2 * 50 + 10 + 5
                        clip5 = dpg.add_button(label="テキストタイトル", width=250, height=30, pos=(100, y_pos_2))
                        dpg.bind_item_theme(clip5, timeline_clip_theme)

                        # オーディオトラック1のクリップ
                        y_pos_4 = 4 * 50 + 10 + 5
                        clip6 = dpg.add_button(label="BGM", width=500, height=30, pos=(50, y_pos_4))
                        dpg.bind_item_theme(clip6, audio_clip_theme)

                        # オーディオトラック2のクリップ
                        y_pos_5 = 5 * 50 + 10 + 5
                        clip7 = dpg.add_button(label="ナレーション", width=200, height=30, pos=(300, y_pos_5))
                        dpg.bind_item_theme(clip7, audio_clip_theme)

                        clip8 = dpg.add_button(label="効果音", width=100, height=30, pos=(550, y_pos_5))
                        dpg.bind_item_theme(clip8, audio_clip_theme)

# グローバルテーマを適用
dpg.bind_theme(global_theme)

# ビューポート設定
dpg.create_viewport(title="タイムラインエディタ Pro", width=1200, height=800)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
