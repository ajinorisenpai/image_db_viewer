import sqlite3

from src.utils.config_constant import AppSettings

# データベースに接続
conn = sqlite3.connect(AppSettings.DB_FILE)
cursor = conn.cursor()

# 必要なテーブルが存在するか確認し、存在しない場合は作成する
cursor.execute('''
CREATE TABLE IF NOT EXISTS words (
    word TEXT PRIMARY KEY,
    kind TEXT NOT NULL
)
''')

# wordsテーブルのデータを読み込む
try:
    cursor.execute('SELECT word, kind FROM words')
    words_data = cursor.fetchall()
except sqlite3.OperationalError:
    words_data = []  # テーブルが存在しない場合は空リストを設定

# artistテーブルのデータを読み込む
try:
    cursor.execute('SELECT name FROM artist')
    artist_data = cursor.fetchall()
except sqlite3.OperationalError:
    artist_data = []  # テーブルが存在しない場合は空リストを設定

# characterテーブルのデータを読み込む
try:
    cursor.execute('SELECT name FROM character')
    character_data = cursor.fetchall()
except sqlite3.OperationalError:
    character_data = []  # テーブルが存在しない場合は空リストを設定

# artistテーブルのnameにwordが存在する場合、wordsテーブルのkindを'artist'に更新
for word, kind in words_data:
    if (word,) in artist_data:
        cursor.execute('UPDATE words SET kind = ? WHERE word = ?', ('artist', word))

# characterテーブルのnameにwordが存在する場合、wordsテーブルのkindを'character'に更新
for word, kind in words_data:
    if (word,) in character_data:
        cursor.execute('UPDATE words SET kind = ? WHERE word = ?', ('character', word))

# 変更をコミットして接続を閉じる
conn.commit()
conn.close()

print("処理が完了しました。")
