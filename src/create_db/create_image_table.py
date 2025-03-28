import os
import sqlite3
from PIL import Image
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import List, Tuple, Dict, Optional, Any, Set, Union
from logger_config import LoggerConfig
from src.utils.config_constant import AppSettings
from src.utils.util import normalize_slash

# 定数定義
DB_FILE: str = AppSettings.DB_FILE
IMAGE_DIR: str = AppSettings.NEW_IMAGE_DIR  # 入力パスも正規化
BATCH_SIZE: int = 1000  # コミットのバッチサイズ
MAX_WORKERS: int = 4  # 並列処理のワーカー数
logger = LoggerConfig.get_default_logger('db_update.log')

# 型エイリアスの定義
UpdateTuple = Tuple[Optional[str], Optional[str], str, int, Optional[int]]
ActivateTuple = Tuple[int, str]
FullUpdateTuple = Tuple[str, str, int, str, Optional[int]]
NewRecordTuple = Tuple[str, str, int, int, str]
UpdateRecordTuple = Tuple[str, str, int, str]

# データベース初期化とマイグレーション
def init_db() -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    """データベースを初期化し、必要なテーブルを作成する

    Returns:
        Tuple[sqlite3.Connection, sqlite3.Cursor]: データベース接続とカーソル
    """
    conn: sqlite3.Connection = sqlite3.connect(DB_FILE)
    # 外部キー制約を有効化
    conn.execute("PRAGMA foreign_keys = ON")
    # WALモードを有効化（書き込み性能向上）
    conn.execute("PRAGMA journal_mode = WAL")
    cursor: sqlite3.Cursor = conn.cursor()

    # テーブルが存在するか確認
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='images'")
    table_exists: Optional[Tuple[str]] = cursor.fetchone()

    if not table_exists:
        # テーブルを新規作成
        cursor.execute('''CREATE TABLE images(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            description TEXT NOT NULL,
            detail TEXT,
            active INTEGER DEFAULT 1,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            size_type AS (
                CASE 
                    WHEN detail LIKE '%"height":832,"width":1216%' OR detail LIKE '%"height": 832, "width": 1216%' THEN 1
                    WHEN detail LIKE '%"height":1216,"width":832%' OR detail LIKE '%"height": 1216, "width": 832%' THEN 2
                    ELSE 3
                END
            ) STORED
        )''')
        # パスに対するインデックスを作成（検索を高速化）
        cursor.execute('CREATE INDEX idx_images_path ON images(path)')
    else:
        # テーブルが存在する場合、カラム追加が必要か確認
        cursor.execute("PRAGMA table_info(images)")
        columns: Dict[str, Tuple[Any, ...]] = {column[1]: column for column in cursor.fetchall()}

        if 'active' not in columns:
            cursor.execute("ALTER TABLE images ADD COLUMN active INTEGER DEFAULT 1")

        # last_modifiedからcreated_atへの移行
        if 'last_modified' in columns and 'created_at' not in columns:
            # created_atカラムを追加
            cursor.execute("ALTER TABLE images ADD COLUMN created_at INTEGER")
            # last_modifiedの値をcreated_atにコピー（既存データの初回生成時間として）
            cursor.execute("UPDATE images SET created_at = last_modified WHERE created_at IS NULL")
            # 値がNULLの場合は現在時刻を設定
            cursor.execute("UPDATE images SET created_at = strftime('%s', 'now') WHERE created_at IS NULL")
            logger.info("last_modifiedからcreated_atへの移行が完了しました")

        elif 'created_at' not in columns:
            # created_atカラムを追加（新規の場合）
            cursor.execute("ALTER TABLE images ADD COLUMN created_at INTEGER DEFAULT (strftime('%s', 'now'))")

        # 既存パスの正規化
        migrate_path_format(cursor, conn)

        # descriptionがNULLまたは空の行を削除
        delete_empty_description(cursor, conn)

    conn.commit()
    return conn, cursor


# descriptionが空またはNULLのレコードを削除
def delete_empty_description(cursor: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    """descriptionが空またはNULLのレコードを削除する

    Args:
        cursor: データベースカーソル
        conn: データベース接続
    """
    cursor.execute("DELETE FROM images WHERE description IS NULL OR description = ''")
    deleted_count: int = cursor.rowcount
    if deleted_count > 0:
        logger.info(f"{deleted_count}件のdescriptionが空のレコードを削除しました")
        conn.commit()


# 既存パスを'/'に統一する
def migrate_path_format(cursor: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    """既存のパスを'/'に統一する

    Args:
        cursor: データベースカーソル
        conn: データベース接続
    """
    cursor.execute("SELECT id, path FROM images")
    paths: List[Tuple[int, str]] = cursor.fetchall()

    updated_count: int = 0
    for id, path in paths:
        normalized_path: str = normalize_slash(path)
        if path != normalized_path:
            cursor.execute("UPDATE images SET path = ? WHERE id = ?", (normalized_path, id))
            updated_count += 1

    if updated_count > 0:
        logger.info(f"{updated_count}件のパスを'/'に統一しました")
        conn.commit()


# 既存の画像パスとその作成日時をロード
def load_existing_images(cursor: sqlite3.Cursor) -> Dict[str, int]:
    """既存の画像パスとその作成日時をロードする

    Args:
        cursor: データベースカーソル

    Returns:
        Dict[str, int]: パスをキー、作成日時を値とする辞書
    """
    cursor.execute("SELECT path, created_at FROM images")
    # すべてのパスを正規化して返す
    return {normalize_slash(row[0]): row[1] for row in cursor.fetchall()}


# 一括で非アクティブにマーク
def mark_all_inactive(cursor: sqlite3.Cursor) -> None:
    """すべてのレコードを非アクティブにマークする

    Args:
        cursor: データベースカーソル
    """
    cursor.execute("UPDATE images SET active = 0")


# 画像のメタデータを取得
@lru_cache(maxsize=100)  # メタデータ取得結果をキャッシュ
def get_image_metadata(file_path: str) -> Tuple[str, str]:
    """画像ファイルからメタデータを取得する

    Args:
        file_path: 画像ファイルのパス

    Returns:
        Tuple[str, str]: (description, detail)のタプル
    """
    try:
        with Image.open(file_path) as img:
            # Descriptionがなければ空文字を返す（後で処理をスキップするため）
            desc: str = img.info.get('Description', '')
            detail: str = img.info.get('Comment', '')
            return desc, detail
    except Exception as e:
        logger.error(f"メタデータ取得エラー: {file_path} - {e}")
        return '', ''


# 画像ファイルを処理し更新が必要か判断
def process_image_file(file_path: str, existing_images: Dict[str, int], updates_needed: List[UpdateTuple]) -> None:
    """画像ファイルを処理し、更新が必要か判断する

    Args:
        file_path: 画像ファイルのパス
        existing_images: 既存の画像パスと作成日時の辞書
        updates_needed: 更新が必要なファイルのリスト
    """
    # パスを正規化
    normalized_path: str = normalize_slash(file_path)

    try:
        # まず、メタデータを取得してdescriptionをチェック
        desc: str
        detail: str
        desc, detail = get_image_metadata(file_path)

        # descriptionが空の場合は処理をスキップ
        if not desc:
            return

        current_time: int = int(time.time())

        if normalized_path in existing_images:
            # すでに登録済みの場合、アクティブフラグのみ更新
            # created_atは変更しない（初回生成時間を保持）
            updates_needed.append((None, None, normalized_path, 1))
            return

        # 新規の場合のみ、現在時刻をcreated_atとして設定
        updates_needed.append((desc, detail, normalized_path, 1, current_time))

    except Exception as e:
        logger.error(f"ファイル処理エラー: {normalized_path} - {e}")


# ディレクトリを再帰的に探索して画像を収集
def collect_image_files(dir_path: str) -> List[str]:
    """ディレクトリを再帰的に探索して画像ファイルを収集する

    Args:
        dir_path: 探索対象のディレクトリパス

    Returns:
        List[str]: 収集した画像ファイルのパスリスト
    """
    image_files: List[str] = []

    for root, _, files in os.walk(dir_path):
        # rootのパスを正規化
        normalized_root: str = normalize_slash(root)

        for file in files:
            if file.lower().endswith('.png'):
                # パスを結合して正規化
                image_path: str = normalized_root + '/' + file
                image_files.append(image_path)

    return image_files


# データベース更新をバッチ処理
def update_database_in_batches(cursor: sqlite3.Cursor, updates_needed: List[UpdateTuple]) -> None:
    """データベースをバッチ処理で更新する

    Args:
        cursor: データベースカーソル
        updates_needed: 更新が必要なファイルのリスト
    """
    total_updates: int = len(updates_needed)
    processed: int = 0

    # アクティブフラグのみの更新（メタデータ変更なし）
    activate_batch: List[ActivateTuple] = []
    # 完全な更新または新規追加
    full_update_batch: List[FullUpdateTuple] = []

    for update in updates_needed:
        if update[0] is None:  # メタデータなし = アクティブフラグのみ更新
            activate_batch.append((update[3], update[2]))  # (active, path)
        elif update[0]:  # None以外かつ空文字列でない場合
            if len(update) >= 5:  # 新規追加（created_atあり）
                full_update_batch.append((
                    update[0],  # description
                    update[1],  # detail
                    update[3],  # active
                    update[4],  # created_at
                    update[2]   # path
                ))
            else:  # 更新（created_atなし - 既存レコードの値を維持）
                full_update_batch.append((
                    update[0],  # description
                    update[1],  # detail
                    update[3],  # active
                    update[2]   # path
                ))

        processed += 1

        # バッチサイズに達したらコミット
        if len(activate_batch) + len(full_update_batch) >= BATCH_SIZE:
            execute_batch_updates(cursor, activate_batch, full_update_batch)
            logger.info(f"進捗: {processed}/{total_updates} 件処理 ({processed / total_updates * 100:.1f}%)")
            activate_batch = []
            full_update_batch = []

    # 残りのバッチを処理
    if activate_batch or full_update_batch:
        execute_batch_updates(cursor, activate_batch, full_update_batch)
        logger.info(f"進捗: {processed}/{total_updates} 件処理 (100%)")


# バッチ更新を実行
def execute_batch_updates(cursor: sqlite3.Cursor, activate_batch: List[ActivateTuple], full_update_batch: List[FullUpdateTuple]) -> None:
    """バッチ更新を実行する

    Args:
        cursor: データベースカーソル
        activate_batch: アクティブフラグのみの更新バッチ
        full_update_batch: 完全な更新または新規追加のバッチ
    """
    if activate_batch:
        cursor.executemany(
            "UPDATE images SET active = ? WHERE path = ?",
            activate_batch
        )

    # created_atを含む完全な更新または新規追加
    new_records: List[NewRecordTuple] = [item for item in full_update_batch if len(item) >= 5]
    if new_records:
        cursor.executemany("""
            INSERT INTO images(description, detail, active, created_at, path) 
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                description = excluded.description,
                detail = excluded.detail,
                active = excluded.active
        """, new_records)

    # created_atを含まない更新（既存レコードのcreated_atを維持）
    update_records: List[UpdateRecordTuple] = [item for item in full_update_batch if len(item) < 5]
    if update_records:
        cursor.executemany("""
            INSERT INTO images(description, detail, active, path) 
            VALUES(?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                description = excluded.description,
                detail = excluded.detail,
                active = excluded.active
        """, update_records)


# 非アクティブなレコードを削除
def delete_inactive_records(cursor: sqlite3.Cursor) -> int:
    """非アクティブなレコードを削除する

    Args:
        cursor: データベースカーソル

    Returns:
        int: 削除されたレコード数
    """
    cursor.execute("DELETE FROM images WHERE active = 0")
    return cursor.rowcount


def main() -> None:
    """メイン処理"""
    start_time: float = time.time()
    logger.info("データベース更新処理を開始します")

    conn: Optional[sqlite3.Connection] = None
    cursor: Optional[sqlite3.Cursor] = None
    try:
        # データベース接続とテーブル初期化
        conn, cursor = init_db()

        # トランザクション開始
        conn.execute("BEGIN TRANSACTION")

        # 既存画像データをロード
        logger.info("既存の画像データをロード中...")
        existing_images: Dict[str, int] = load_existing_images(cursor)
        logger.info(f"{len(existing_images)}件の既存レコードをロードしました")

        # 全レコードを非アクティブにマーク
        mark_all_inactive(cursor)

        # 画像ファイルのパスを収集
        logger.info("画像ファイルをスキャン中...")
        image_files: List[str] = collect_image_files(normalize_slash(IMAGE_DIR))
        logger.info(f"{len(image_files)}件の画像ファイルを見つけました")

        # 更新が必要なファイルを特定
        logger.info("ファイルの変更を確認中...")
        updates_needed: List[UpdateTuple] = []

        # 並列処理で画像ファイルを処理
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures: List[Any] = []
            for file_path in image_files:
                future = executor.submit(process_image_file, file_path, existing_images, updates_needed)
                futures.append(future)

            # すべての処理が完了するのを待つ
            for future in futures:
                future.result()

        # 一括でデータベース更新
        logger.info("データベースを更新中...")
        update_database_in_batches(cursor, updates_needed)

        # 非アクティブレコードを削除
        deleted_count: int = delete_inactive_records(cursor)
        logger.info(f"{deleted_count}件の古いレコードを削除しました")

        # トランザクションをコミット
        conn.commit()

        elapsed_time: float = time.time() - start_time
        logger.info(f"処理完了！所要時間: {elapsed_time:.2f}秒")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        # エラー発生時はロールバック
        if conn:
            conn.rollback()
    finally:
        # 接続を閉じる
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
