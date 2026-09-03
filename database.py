import sqlite3
import os

DB_PATH = "data/economy.db"


def create_database():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS economic_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            indicator TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL,
            unit TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

    print("データベースを作成しました")


def save_economic_data(source, indicator, date, value, unit):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id
        FROM economic_data
        WHERE source = ?
        AND indicator = ?
        AND date = ?
    """, (
        source,
        indicator,
        date
    ))

    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE economic_data
            SET value = ?, unit = ?
            WHERE id = ?
        """, (
            value,
            unit,
            existing[0]
        ))

        print("既存データを更新しました")

    else:
        cursor.execute("""
            INSERT INTO economic_data
            (source, indicator, date, value, unit)
            VALUES (?, ?, ?, ?, ?)
        """, (
            source,
            indicator,
            date,
            value,
            unit
        ))

        print("経済データを保存しました")

    conn.commit()
    conn.close()