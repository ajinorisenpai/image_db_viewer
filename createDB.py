import os
import sqlite3
from PIL import Image

# 定数定義
DB_FILE = "file.db"
IMAGE_DIR = "D:/Dropbox/aphotos/filesV4/character"


# データベース初期化
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS images(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE,
        description TEXT,
        detail TEXT
    )''')
    return conn, cursor


# 画像メタデータをDBに保存
def save_image_data(cursor, conn, path, desc, detail):
    try:
        cursor.execute("""
            INSERT INTO images(path, description, detail) VALUES(?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                description = excluded.description,
                detail = excluded.detail
        """, (path, desc, detail))
        conn.commit()
    except sqlite3.Error as e:
        print(f"エラー: {e}")


# ディレクトリを再帰的に探索して画像を処理
def scan_images(dir_path, cursor, conn):
    for file in os.listdir(dir_path):
        file_path = dir_path + '/' + file
        print(file_path)

        if os.path.isfile(file_path) and file.lower().endswith('.png'):
            # 画像ファイルの処理
            try:
                with Image.open(file_path) as img:
                    if 'Description' in img.info:
                        desc = img.info.get('Description', '')
                        detail = img.info.get('Comment', '')
                        save_image_data(cursor, conn, file_path, desc, detail)
            except Exception as e:
                print(f"画像の読み込みエラー: {file_path} - {e}")
        elif os.path.isdir(file_path):
            # サブディレクトリを再帰的に処理
            scan_images(file_path, cursor, conn)


# メイン処理
def main():
    conn, cursor = init_db()
    try:
        scan_images(IMAGE_DIR, cursor, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()