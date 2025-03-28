import os
from pathlib import Path

from PIL import Image
import re
import threading
import sqlite3
import time
import logging
import json

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='rename_update.log'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)
logger = logging.getLogger(__name__)


def add_relations_for_new_image(conn, image_id):
    """新しく追加された画像の関連付けを作成する関数"""
    cursor = conn.cursor()

    # 画像の説明文を取得
    cursor.execute("SELECT lower(description) FROM images WHERE id = ?", (image_id,))
    result = cursor.fetchone()
    if not result:
        logger.warning(f"画像ID {image_id} が見つかりません")
        return 0, 0

    description = result[0]
    relation_counts = {'artist': 0, 'character': 0}

    # アーティストとキャラクターの両方について処理
    for entity_type in ['artist', 'character']:
        cursor.execute(f"SELECT id, name, parent FROM {entity_type}")
        entities = cursor.fetchall()

        # 有効な親エンティティ名のセット
        valid_entity_names = {name for _, name, _ in entities}
        relations = set()

        for entity_id, name, parent in entities:
            # 名前を小文字に変換（検索用）
            entity_name_lower = name.lower().replace("_", " ")

            if entity_name_lower in description:
                # 親エンティティがある場合は親のIDを使用（親が有効な場合のみ）
                if parent and parent in valid_entity_names:
                    cursor.execute(f"SELECT id FROM {entity_type} WHERE name = ?", (parent,))
                    parent_id = cursor.fetchone()[0]
                    relations.add((image_id, parent_id))
                else:
                    relations.add((image_id, entity_id))

        # 関連付けの挿入
        for relation in relations:
            cursor.execute(f"""
                INSERT OR IGNORE INTO image_{entity_type}_relation (image_id, {entity_type}_id)
                VALUES (?, ?)
            """, relation)

        relation_counts[entity_type] = len(relations)

    conn.commit()
    return relation_counts['artist'], relation_counts['character']


def normalize_slash(path):
    """パスの区切り文字を'/'に統一する"""
    return path.replace('\\', '/')


class RenameLogic:
    """画像ファイルのリネームロジックを管理するクラス"""

    def __init__(self, db_path="C:/Users/thund/source/notebook/nai/create_db/file.db", preview_mode=False):
        """初期化"""
        self.db_path = normalize_slash(db_path)  # データベースファイルのパスを保持
        self.preview_mode = preview_mode  # プレビューモードのフラグ

        # ディレクトリ作成のための同期オブジェクト
        self.directory_creation_lock = threading.Lock()
        self.created_directories = set()

        # データベース接続のための同期オブジェクト
        self.db_lock = threading.Lock()

    def update_database(self, old_path, new_path, description, detail="", artist_tag="", character_tag=""):
        """データベースを更新する"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # 古いパスのレコードを更新
                cursor.execute("""
                    UPDATE images 
                    SET path = ?, 
                        description = ?,
                        detail = ?,
                        active = 1
                    WHERE path = ?
                """, (new_path, description, detail, old_path))

                if cursor.rowcount == 0:
                    # レコードが存在しない場合は新規作成
                    cursor.execute("""
                        INSERT INTO images (
                            path, description, detail, active
                        )
                        VALUES (?, ?, ?, 1)
                    """, (new_path, description, detail))

                conn.commit()
                conn.close()
                logger.info(f"データベースを更新しました: {old_path} -> {new_path}")

        except Exception as e:
            logger.error(f"データベース更新エラー: {e}")

    def rename(self, path):
        """画像ファイルのメタデータから新しいファイル名を決定する関数"""
        try:
            image = Image.open(path)
            match = re.search(r"s-[0-9]+.png", path)
            if not match:
                return [], [], match.group(0) if match else "s-"

            seed = match.group(0)
            discript = image.info.get("Description", "")
            discript = discript.lower().replace("_", " ")

            # データベース接続
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # アーティスト情報の処理
            cursor.execute("SELECT id, name, parent FROM artist WHERE active = 1")
            artist_list = cursor.fetchall()
            artist_tag = []

            for artist_id, artist, parent in artist_list:
                artist = artist.lower().replace("_", " ")
                match = artist if discript.find(artist) > -1 else None
                if match != None:
                    match = parent if parent else match
                    discript = discript.replace(match, "", 1)
                    artist_tag.append(match)

            artist_tag.sort()

            # キャラクター情報の処理
            cursor.execute("SELECT id, name, parent FROM character WHERE active = 1")
            character_list = cursor.fetchall()
            character_tag = []

            for character_id, character, parent in character_list:
                character = character.lower().replace("_", " ")
                match = character if discript.find(character) > -1 else None
                if match != None:
                    match = parent if parent else match
                    discript = discript.replace(match, "", 1)
                    character_tag.append(match)

            # データベース接続を閉じる
            conn.close()

            return artist_tag, character_tag, seed

        except Exception as e:
            logger.error(f"リネーム情報の取得中にエラーが発生しました: {e}")
            return [], [], "s-"

    def safe_create_directory(self, directory_path):
        """スレッドセーフなディレクトリ作成"""
        # プレビューモードの場合はディレクトリを作成しない
        if self.preview_mode:
            return

        with self.directory_creation_lock:
            if directory_path not in self.created_directories:
                os.makedirs(directory_path, exist_ok=True)
                self.created_directories.add(directory_path)

    def get_image_dimensions(self, file_path):
        """画像のサイズを取得する"""
        try:
            with Image.open(file_path) as img:
                return {"width": img.width, "height": img.height}
        except Exception as e:
            logger.error(f"画像サイズの取得エラー: {e}")
            return {"width": 0, "height": 0}

    def process_image_file(self, file_path, new_directory, counter_callback):
        """画像ファイルを処理し、リネームして移動する"""
        try:
            # パスを正規化
            file_path = normalize_slash(file_path)
            new_directory = normalize_slash(new_directory)

            # リネーム情報を取得
            artist_tag, character_tag, seed = self.rename(file_path)

            if len(artist_tag) + len(character_tag) > 0:
                # 出力先ディレクトリを決定
                if len(character_tag) > 0:
                    dd = os.path.join(new_directory, "character")
                    label_dir = os.path.join(dd, character_tag[0])
                elif len(artist_tag) == 1:
                    dd = os.path.join(new_directory, "artist")
                    label_dir = os.path.join(dd, artist_tag[0])

                # パスを正規化
                dd = normalize_slash(dd)
                label_dir = normalize_slash(label_dir)

                new_name = ",".join(artist_tag + character_tag)
                new_path = normalize_slash(os.path.join(label_dir, new_name + seed))

                # カウンターコールバックを呼び出す
                current_count = counter_callback()

                if self.preview_mode:
                    # プレビューモードの場合は、移動先の情報を表示するだけ
                    print(f"[{current_count}] プレビュー:")
                    print(f"  元のパス: {file_path}")
                    print(f"  移動先  : {new_path}")
                else:
                    # 実際のモードの場合
                    # ディレクトリが存在することを確認（スレッドセーフ）
                    self.safe_create_directory(label_dir)

                    # 元のパスと新しいパスが異なる場合のみリネーム
                    if Path(file_path).resolve() != Path(new_path).resolve():
                        os.rename(file_path, new_path)

                        # 画像のメタデータを取得
                        with Image.open(new_path) as img:
                            description = img.info.get('Description', '')
                            comment = img.info.get('Comment', '')

                        # 画像サイズ情報を取得してdetailに追加
                        dimensions = self.get_image_dimensions(new_path)

                        # detailフィールドを構築
                        detail_data = {}

                        # 既存のCommentがJSONの場合は解析
                        if comment:
                            try:
                                detail_data = json.loads(comment)
                            except json.JSONDecodeError:
                                detail_data = {"comment": comment}

                        # サイズ情報を追加
                        detail_data.update(dimensions)

                        # JSON文字列に変換
                        detail = json.dumps(detail_data)

                        # データベースを更新
                        self.update_database(
                            file_path, new_path, description, detail
                        )

                        # 処理進捗を表示
                        print(f"[{current_count}] {file_path}")
                        print(f" -> {new_path}")

                return True
            return False

        except Exception as e:
            logger.error(f"エラー: ファイル '{file_path}' の処理中に問題が発生しました: {e}")
            return False
