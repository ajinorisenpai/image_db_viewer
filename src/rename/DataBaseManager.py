import sqlite3
import threading


# スレッドセーフなSQLite接続を管理するクラス
class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.thread_local = threading.local()
        self.lock = threading.Lock()

    def get_connection(self):
        if not hasattr(self.thread_local, "connection"):
            self.thread_local.connection = sqlite3.connect(self.db_path)
        return self.thread_local.connection

    def get_cursor(self):
        return self.get_connection().cursor()

    def commit(self):
        if hasattr(self.thread_local, "connection"):
            with self.lock:
                self.thread_local.connection.commit()

    def close_all(self):
        if hasattr(self.thread_local, "connection"):
            self.thread_local.connection.close()
            delattr(self.thread_local, "connection")