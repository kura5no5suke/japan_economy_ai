import sqlite3
import os
import requests
from dotenv import load_dotenv

DB_PATH = "data/economy.db"

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def create_alert_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS risk_spike_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_history_id INTEGER NOT NULL UNIQUE,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_latest_two_risks():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, total_risk, calculated_at
        FROM risk_history
        ORDER BY id DESC
        LIMIT 2
    """)

    rows = cur.fetchall()
    conn.close()

    return rows


def was_alert_sent(risk_history_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM risk_spike_alerts
        WHERE risk_history_id = ?
        LIMIT 1
    """, (risk_history_id,))

    row = cur.fetchone()
    conn.close()

    return row is not None


def mark_alert_sent(risk_history_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO risk_spike_alerts (risk_history_id)
        VALUES (?)
    """, (risk_history_id,))

    conn.commit()
    conn.close()


def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("Discord Webhook URLが設定されていません。")
        return False

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=30
        )

        print("Discord HTTPステータス:", response.status_code)

        if response.status_code in (200, 204):
            print("Discord送信成功")
            return True

        print("Discord送信失敗")
        print(response.text)
        return False

    except Exception as e:
        print("Discord送信エラー:", e)
        return False


def main():
    create_alert_table()

    rows = get_latest_two_risks()

    print("===== 総合リスク急上昇監視 =====")

    if len(rows) < 2:
        print("比較できるリスク履歴が2件未満です。")
        return

    current_id, current_risk, current_time = rows[0]
    previous_id, previous_risk, previous_time = rows[1]

    risk_change = round(current_risk - previous_risk, 2)

    print("前回:", previous_risk, "/ 100")
    print("今回:", current_risk, "/ 100")
    print("変化:", risk_change, "ポイント")

    if risk_change < 10:
        print("🟢 総合リスクの急上昇はありません。")
        return

    print("🔴 総合リスク急上昇を検知しました。")

    if was_alert_sent(current_id):
        print("この急上昇はすでにDiscord通知済みです。")
        return

    message = (
        "🚨 日本経済監視AI 警告\n\n"
        "⚠️ 総合リスク急上昇\n"
        f"前回リスク: {previous_risk} / 100\n"
        f"今回リスク: {current_risk} / 100\n"
        f"変化: +{risk_change}ポイント\n\n"
        f"前回計算: {previous_time}\n"
        f"今回計算: {current_time}"
    )

    if send_discord(message):
        mark_alert_sent(current_id)
        print("急上昇通知済みとして記録しました。")


if __name__ == "__main__":
    main()