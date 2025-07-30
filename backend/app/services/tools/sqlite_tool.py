# SQLite Tool 래퍼
import sqlite3
import os


class SQLiteTool:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.getenv("DB_PATH", "data/financial_data.db")

    def query(self, sql, params=None):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        conn.close()
        return [dict(zip(columns, row)) for row in rows]


# 사용 예시:
# tool = SQLiteTool()
# tool.query('SELECT * FROM table LIMIT 5')
