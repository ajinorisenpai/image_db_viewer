import sqlite3
import os
import re
from re import Pattern, Match
from typing import List, Tuple, Optional
from src.utils.config_constant import AppSettings


def main(db_file):
    # データベースに接続
    conn: sqlite3.connect = sqlite3.connect(db_file)
    cursor: sqlite3.Cursor = conn.cursor()

    # リネーム用テーブルを作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS renamed_images (
        image_id INTEGER PRIMARY KEY,
        image_path TEXT,
        renamed_path TEXT
    )
    ''')

    # image_relation_viewからデータを取得
    cursor.execute('''
    SELECT image_id, image_path, characters, artists
    FROM image_relation_view
    WHERE image_path LIKE '%D:/Dropbox/autoFiles/%'
    ''')

    rows: List[Tuple[int, str, Optional[str], Optional[str]]] = cursor.fetchall()

    # リネームルールに基づいてパスを生成
    for row in rows:
        image_id, image_path, characters, artists = row

        if artists is None and characters is None:
            continue

        # ファイル名からs-以降の数字部分を抽出（.pngで終わるもの）
        filename: str = os.path.basename(image_path)
        pattern: Pattern[str] = re.compile(r's-\d+\.png$')
        match: Match[str] | None = pattern.search(filename)
        if match:
            suffix = match.group(0)
        else:
            continue

        # フォルダ名とファイル名の生成
        folder_name = ""
        artist_count = 0

        def create_folder_name(input_string:str, prefix:str) -> str:
            if not input_string:
                return ""

            parts = input_string.split(',')
            first_name = parts[0].strip()
            return f"{prefix}/{first_name}"

        # characterを優先するためにcharactersで上書き
        if artists:
            folder_name = create_folder_name(artists, "artists")
        if characters:
            folder_name = create_folder_name(characters, "character")

        # 3. ファイル名の生成
        new_filename = ""
        if artists:
            new_filename += artists

        if characters:
            if new_filename:
                new_filename += ","
            new_filename += characters

        # 4. ファイル名にs-以降を追加
        if suffix:
            new_filename += f",{suffix}"

        # 5. 新しいパスの生成
        base_dir = "D:/Dropbox/aphotos/filesV4/"
        renamed_path = os.path.join(base_dir, folder_name, new_filename)
        renamed_path = renamed_path.replace('\\', '/')
        # 6 & 7. リネーム後のパスをテーブルに挿入（image_idが被った場合は上書き）
        cursor.execute('''
        INSERT OR REPLACE INTO renamed_images (image_id, image_path, renamed_path)
        VALUES (?, ?, ?)
        ''', (image_id, image_path, renamed_path))

    # 変更を保存
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()