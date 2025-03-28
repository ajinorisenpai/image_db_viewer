import sqlite3
import time

from src.utils.config_constant import AppSettings


def create_or_update_table(db_file: str, table_name: str, input_file: str) -> None:
    """
    指定されたテーブルを作成または更新する関数
    """
    # データベースに接続
    conn: sqlite3.Connection = sqlite3.connect(db_file)
    cursor: sqlite3.Cursor = conn.cursor()

    # テーブルの存在確認
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    table_exists = cursor.fetchone()

    if not table_exists:
        # 新規テーブル作成
        if table_name == 'artist':
            cursor.execute('''
            CREATE TABLE artist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                active INTEGER DEFAULT 0,
                created INTEGER DEFAULT (strftime('%s', 'now')),
                parent TEXT,
                description TEXT
            )
            ''')
        else:
            cursor.execute('''
            CREATE TABLE character (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                active INTEGER DEFAULT 0,
                created INTEGER DEFAULT (strftime('%s', 'now')),
                parent TEXT,
                description TEXT
            )
            ''')

    # 既存のデータを取得
    cursor.execute(f'SELECT id, name, active FROM {table_name}')
    existing_records = cursor.fetchall()
    existing_name_to_id = {name: id for id, name, _ in existing_records}

    # ファイルに存在するエンティティ名を格納するセット
    file_entities = set()

    # 現在のUNIXタイムスタンプを取得
    current_time = int(time.time())

    # ファイルからデータを読み込む
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            for line in file:
                # 空白を削除
                entity_name = line.strip().split(',')[0]

                # 空行はスキップ
                if not entity_name:
                    continue

                # activeの値を決定（行頭が'-'かどうかで判断）
                is_active = not entity_name.startswith('-')

                # 行頭が'-'の場合は、その文字を削除
                if not is_active:
                    entity_name = entity_name[1:].strip()

                # ファイルに存在するエンティティをセットに追加
                file_entities.add(entity_name)

                try:
                    if entity_name in existing_name_to_id:
                        # 既存のレコードを更新（activeが変更された場合のみ）
                        cursor.execute(f'SELECT active FROM {table_name} WHERE name = ?', (entity_name,))
                        current_active = cursor.fetchone()[0]
                        if current_active != is_active:
                            cursor.execute(f'UPDATE {table_name} SET active = ? WHERE name = ?',
                                           (is_active, entity_name))
                    else:
                        # 新しいレコードを追加
                        cursor.execute(
                            f'INSERT INTO {table_name} (name, active, created) VALUES (?, ?, ?)',
                            (entity_name, is_active, current_time))
                        print(f"{entity_name}が新規に追加されました。")
                except sqlite3.IntegrityError:
                    # ユニーク制約違反の場合は無視
                    pass

        # ファイルに存在しないレコードのactiveをfalseに設定
        for id, name, active in existing_records:
            if name not in file_entities and active:  # activeが既にfalseの場合は更新不要
                cursor.execute(f'UPDATE {table_name} SET active = 0 WHERE id = ?',
                               (id,))

        # 変更をコミット
        conn.commit()
        print(f"{table_name}データの更新が完了しました")

    except FileNotFoundError:
        print(f"{input_file}ファイルが見つかりません")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        conn.rollback()  # エラー時はロールバック
    finally:
        # 接続を閉じる
        conn.close()


def main(db_path):
    create_or_update_table(db_path, 'artist', 'D:/Dropbox/nai/files/artist.txt')
    create_or_update_table(db_path, 'character', 'D:/Dropbox/nai/files/character.txt')

if __name__ == "__main__":
    main(AppSettings.DB_FILE)
