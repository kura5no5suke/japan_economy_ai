import sqlite3
from db_config import DB_PATH

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
    SELECT indicator, COUNT(*), COUNT(DISTINCT date)
    FROM economic_data
    GROUP BY indicator
    ORDER BY COUNT(*) DESC
""")

rows = cur.fetchall()

print("===== データベースの中身 =====")

for row in rows:
    print(
        "指標:", row[0],
        "| 件数:", row[1],
        "| ユニーク年月:", row[2]
    )

conn.close()
