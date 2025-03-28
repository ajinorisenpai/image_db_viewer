import sqlite3
import logging
import time
import argparse  # コマンドライン引数処理用
from typing import List, Optional, Set, Tuple, Dict, Any
from src.utils.config_constant import AppSettings

# 定数定義
DB_FILE: str = AppSettings.DB_FILE

# 簡略化したロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('../../data/logs/relation_update.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def init_relation_tables(cursor: sqlite3.Cursor, recreate: bool = True) -> None:
    """関連付けテーブルの初期化

    Args:
        cursor: データベースカーソル
        recreate: Trueの場合テーブルを再作成、Falseの場合は既存テーブルを維持
    """
    # 必要なテーブルの存在確認
    for table in ['artist', 'character', 'images']:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            raise Exception(f"{table}テーブルが存在しません")

    if recreate:
        # 既存のテーブルとビューを削除
        cursor.execute("DROP VIEW IF EXISTS image_relation_view")
        for item in ['artist', 'character']:
            cursor.execute(f"DROP VIEW IF EXISTS image_{item}_view")
            cursor.execute(f"DROP TABLE IF EXISTS image_{item}_relation")

        # 関連テーブルの作成（アーティストとキャラクター）
        for item in ['artist', 'character']:
            cursor.execute(f"""
                CREATE TABLE image_{item}_relation (
                    image_id INTEGER,
                    {item}_id INTEGER,
                    PRIMARY KEY (image_id, {item}_id),
                    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
                    FOREIGN KEY ({item}_id) REFERENCES {item}(id) ON DELETE CASCADE
                )
            """)
            cursor.execute(f'CREATE INDEX idx_{item}_relation_image_id ON image_{item}_relation(image_id)')
            cursor.execute(f'CREATE INDEX idx_{item}_relation_{item}_id ON image_{item}_relation({item}_id)')
    else:
        # テーブルが存在するか確認し、存在しなければ作成
        for item in ['artist', 'character']:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='image_{item}_relation'")
            if not cursor.fetchone():
                cursor.execute(f"""
                    CREATE TABLE image_{item}_relation (
                        image_id INTEGER,
                        {item}_id INTEGER,
                        PRIMARY KEY (image_id, {item}_id),
                        FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
                        FOREIGN KEY ({item}_id) REFERENCES {item}(id) ON DELETE CASCADE
                    )
                """)
                cursor.execute(f'CREATE INDEX idx_{item}_relation_image_id ON image_{item}_relation(image_id)')
                cursor.execute(f'CREATE INDEX idx_{item}_relation_{item}_id ON image_{item}_relation({item}_id)')

    # ビューの再作成（常に最新の関連付けを反映するため）
    cursor.execute("DROP VIEW IF EXISTS image_relation_view")
    cursor.execute("""
        CREATE VIEW image_relation_view AS
        SELECT 
            i.id as image_id,
            i.path as image_path,
            GROUP_CONCAT(DISTINCT a.name) as artists,
            GROUP_CONCAT(DISTINCT c.name) as characters,
            i.description,
            i.detail,
            i.created_at,
            i.size_type
        FROM images i
        LEFT JOIN image_artist_relation ar ON i.id = ar.image_id
        LEFT JOIN artist a ON ar.artist_id = a.id
        LEFT JOIN image_character_relation cr ON i.id = cr.image_id
        LEFT JOIN character c ON cr.character_id = c.id
        GROUP BY i.id
    """)

    # 個別ビューも再作成
    for item, col_name in [('artist', 'artists'), ('character', 'characters')]:
        cursor.execute(f"DROP VIEW IF EXISTS image_{item}_view")
        cursor.execute(f"""
            CREATE VIEW image_{item}_view AS
            SELECT 
                i.id as image_id,
                i.path as image_path,
                GROUP_CONCAT(DISTINCT {item[0]}.name) as {col_name},
                i.description,
                i.detail,
                i.created_at,
                i.size_type
            FROM images i
            LEFT JOIN image_{item}_relation r ON i.id = r.image_id
            LEFT JOIN {item} {item[0]} ON r.{item}_id = {item[0]}.id
            GROUP BY i.id
        """)


def create_relations(cursor: sqlite3.Cursor, entity_type: str, update_mode: bool = False, target_images: Optional[List[int]] = None) -> int:
    """アーティストまたはキャラクターの関連付けを作成

    Args:
        cursor: データベースカーソル
        entity_type: 'artist'または'character'
        update_mode: Trueの場合は既存の関連付けを維持して更新
        target_images: 更新対象の画像IDリスト（Noneの場合はすべての画像）

    Returns:
        int: 作成された関連付けの数
    """
    if not update_mode:
        # 既存の関連付けをクリア（更新モードでない場合）
        cursor.execute(f"DELETE FROM image_{entity_type}_relation")
    elif target_images:
        # 特定の画像IDに関連する関連付けのみ削除（更新モード＋対象指定の場合）
        placeholders = ','.join(['?'] * len(target_images))
        cursor.execute(f"DELETE FROM image_{entity_type}_relation WHERE image_id IN ({placeholders})", target_images)

    # エンティティ情報の取得
    cursor.execute(f"SELECT id, name, parent FROM {entity_type}")
    entities: List[Tuple[int, str, Optional[str]]] = cursor.fetchall()

    # 有効な親エンティティ名のセットを作成
    valid_entity_names: Set[str] = {name for _, name, _ in entities}

    # 画像情報の取得（更新対象が指定されている場合は対象のみ）
    if target_images:
        placeholders = ','.join(['?'] * len(target_images))
        cursor.execute(f"SELECT id, lower(description) FROM images WHERE id IN ({placeholders})", target_images)
    else:
        cursor.execute("SELECT id, lower(description) FROM images")

    images: List[Tuple[int, str]] = cursor.fetchall()

    relations: Set[Tuple[int, int]] = set()  # 重複を避けるためにセットを使用
    total_images: int = len(images)

    for i, (image_id, description) in enumerate(images):
        description = description.lower().replace("_", " ")
        for entity_id, name, parent in entities:
            # 名前を小文字に変換（検索用）
            entity_name_lower: str = name.lower().replace("_", " ")

            if entity_name_lower in description:
                # 親エンティティがある場合は親のIDを使用（親が有効な場合のみ）
                if parent and parent in valid_entity_names:
                    cursor.execute(f"SELECT id FROM {entity_type} WHERE name = ?", (parent,))
                    parent_id: int = cursor.fetchone()[0]
                    relations.add((image_id, parent_id))
                else:
                    relations.add((image_id, entity_id))

        if (i + 1) % 1000 == 0:
            logger.info(f"{entity_type}進捗: {i + 1}/{total_images} 件処理 ({(i + 1) / total_images * 100:.1f}%)")

    # 関連付けの一括挿入
    relations_list: List[Tuple[int, int]] = list(relations)
    batch_size: int = 1000
    for i in range(0, len(relations_list), batch_size):
        batch: List[Tuple[int, int]] = relations_list[i:i + batch_size]
        cursor.executemany(f"""
            INSERT OR IGNORE INTO image_{entity_type}_relation (image_id, {entity_type}_id)
            VALUES (?, ?)
        """, batch)

    return len(relations)


def get_new_images(cursor: sqlite3.Cursor, days: int = 7) -> List[int]:
    """最近追加された画像のIDを取得

    Args:
        cursor: データベースカーソル
        days: 何日前までの画像を「新規」とみなすか

    Returns:
        List[int]: 新規画像IDのリスト
    """
    cursor.execute(f"""
        SELECT id FROM images 
        WHERE created_at >= datetime('now', '-{days} days')
    """)
    return [row[0] for row in cursor.fetchall()]


def main() -> None:
    """メイン処理"""
    # コマンドライン引数の解析
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description='画像関連付けテーブル作成・更新ツール')
    parser.add_argument('--update', action='store_true', help='既存のテーブルを更新モードで実行')
    parser.add_argument('--new-only', action='store_true', help='新規画像のみ更新（--updateと併用）')
    parser.add_argument('--days', type=int, default=7, help='新規とみなす日数（デフォルト: 7日）')
    args: argparse.Namespace = parser.parse_args()

    start_time: float = time.time()

    if args.update:
        logger.info("関連付けテーブル更新処理を開始します")
        if args.new_only:
            logger.info(f"過去{args.days}日間の新規画像のみを対象とします")
    else:
        logger.info("関連付けテーブル作成処理を開始します（テーブル再作成モード）")

    try:
        # データベース接続とトランザクション開始
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor: sqlite3.Cursor = conn.cursor()

            # 関連付けテーブルの初期化
            init_relation_tables(cursor, recreate=not args.update)

            # 更新対象の画像を決定
            target_images: Optional[List[int]] = None
            if args.update and args.new_only:
                target_images = get_new_images(cursor, args.days)
                if not target_images:
                    logger.info(f"過去{args.days}日間に追加された新規画像はありません。処理を終了します。")
                    return
                logger.info(f"更新対象: {len(target_images)}件の新規画像")

            # アーティストとキャラクターの関連付け作成
            relation_counts: Dict[str, int] = {}
            for entity_type in ['artist', 'character']:
                relation_counts[entity_type] = create_relations(
                    cursor,
                    entity_type,
                    update_mode=args.update,
                    target_images=target_images
                )

        elapsed_time: float = time.time() - start_time

        if args.update:
            if args.new_only:
                logger.info(f"更新完了！{len(target_images)}件の新規画像に対して、"
                            f"アーティスト関連付け: {relation_counts['artist']}件、"
                            f"キャラクター関連付け: {relation_counts['character']}件を作成しました")
            else:
                logger.info(f"更新完了！アーティスト関連付け: {relation_counts['artist']}件、"
                            f"キャラクター関連付け: {relation_counts['character']}件を作成しました")
        else:
            logger.info(f"作成完了！アーティスト関連付け: {relation_counts['artist']}件、"
                        f"キャラクター関連付け: {relation_counts['character']}件を作成しました")

        logger.info(f"処理時間: {elapsed_time:.1f}秒")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        raise


if __name__ == "__main__":
    main()
