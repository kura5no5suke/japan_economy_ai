import sqlite3

DB_PATH = "data/economy.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
    DELETE FROM economic_data
    WHERE indicator = 'CPI_総合_前年同月比'
""")

deleted = cur.rowcount

conn.commit()

print("削除したCPIデータ:", deleted, "件")

cur.execute("""
    SELECT COUNT(*)
    FROM economic_data
    WHERE indicator = 'CPI_総合_前年同月比'
""")

remaining = cur.fetchone()[0]

print("残っているCPIデータ:", remaining, "件")

conn.close()