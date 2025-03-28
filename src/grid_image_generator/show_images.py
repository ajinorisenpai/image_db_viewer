import math
import os
import sqlite3
from src.grid_image_generator import grid_generator
from src.grid_image_generator.file_utility import save_grid, load_images, get_unique_filename
from src.utils.config_constant import AppSettings

# 定数定義
DB_FILE = AppSettings.DB_FILE
IMAGE_DIR = "D:/Dropbox/aphotos/filesV4/character"
SQL_DIR = AppSettings.SQL_DIR  # SQLクエリファイルの保存ディレクトリ


def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    return conn, cursor


def get_query(query_file_path):
    """SQLファイルからクエリを読み込む関数"""
    with open(query_file_path, 'r', encoding='utf-8') as f:
        query = f.read()
    return query


def plot_images(cursor, query_file="random_artist_only.sql"):
    """指定されたSQLファイルを使用して画像を表示する関数"""
    query_file_path = os.path.join(SQL_DIR, query_file)
    query = get_query(query_file_path)

    size_type = 1

    cursor.execute(query,('character/',size_type))
    fetch_image = cursor.fetchall()
    count = 6*6

    num_batches = math.ceil(len(fetch_image) / count)
    for i in range(num_batches):
        result = fetch_image[i * count:min((i + 1) * count, len(fetch_image))]
        grid_generator = GridGenerator.GridGenerator()
        image_paths = [image[1] for image in result]
        images = load_images(image_paths)
        grid = grid_generator.create_grid(images, [image['folder_name']+'('+str(image["folder_image_count"])+')' for image in result] )

        # display_grid(grid)
        # save_grid(grid, get_unique_filename(os.path.dirname(os.path.dirname(image_paths[0]))+"/"+os.path.splitext(query_file)[0]+str(i) + ".png"))
        save_grid(grid, get_unique_filename("image0.png"))


def main():
    conn, cursor = init_db()
    try:
        plot_images(cursor)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
