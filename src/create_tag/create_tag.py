import sqlite3
import re

from src.utils.config_constant import AppSettings

# データベースに接続
conn = sqlite3.connect(AppSettings.DB_FILE)
cursor = conn.cursor()

# 1. wordsテーブルの作成（主キー:word、複キー:kind）
cursor.execute('''
CREATE TABLE IF NOT EXISTS words (
    word TEXT PRIMARY KEY,
    kind TEXT NOT NULL
)
''')

# 2. imagesテーブルからdescriptionを読み込む
try:
    cursor.execute('SELECT description FROM images')
    descriptions = cursor.fetchall()
except sqlite3.OperationalError:
    descriptions = []  # imagesテーブルが存在しない場合の処理

# 3-7. descriptionの処理と単語の抽出
for desc_tuple in descriptions:
    if desc_tuple and desc_tuple[0]:
        description = desc_tuple[0]

        # 3. {}記号を削除
        description = description.replace('{', '').replace('}', '')
        description = description.replace('[', '').replace(']', '')
        # 4. 大文字を小文字に変換
        description = description.lower()

        # 5. アンダーバーを半角スペースに変換
        description = description.replace('_', ' ')

        # 6. カンマ区切りの単語に分割
        words = [word.strip() for word in description.split(',')]

        # 7-8. 単語をデータベースに追加
        for word in words:
            kind = "general"  # デフォルトのkind

            # artist:で始まる単語の処理
            if word.startswith('artist:'):
                word = word[7:].strip()  # artist:を削除
                kind = "artist"

            # 空でない単語のみデータベースに追加
            if word:
                try:
                    cursor.execute('INSERT OR IGNORE INTO words (word, kind) VALUES (?, ?)', (word, kind))
                except sqlite3.IntegrityError:
                    pass  # 重複エラーを無視

# 変更をコミットして接続を閉じる
conn.commit()
conn.close()