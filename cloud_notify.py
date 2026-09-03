import os
import sqlite3
import requests
from dotenv import load_dotenv

DB_PATH = "data/economy.db"

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_latest_risk():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            cpi_risk,
            gdp_risk,
            unemployment_risk,
            real_wage_risk,
            consumption_risk,
            total_risk,
            risk_status,
            economic_condition,
            anomaly_level
        FROM risk_history
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    return row


def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URLが設定されていません。")
        return False

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


def main():
    row = get_latest_risk()

    if row is None:
        print("リスクデータがありません。")
        return

    (
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        total_risk,
        risk_status,
        economic_condition,
        anomaly_level
    ) = row

    message = (
        "📊 日本経済監視AI\n\n"
        f"CPIリスク: {cpi_risk} / 100\n"
        f"GDPリスク: {gdp_risk} / 100\n"
        f"完全失業率リスク: {unemployment_risk} / 100\n"
        f"実質賃金リスク: {real_wage_risk} / 100\n"
        f"個人消費リスク: {consumption_risk} / 100\n\n"
        f"総合リスク: {total_risk} / 100\n"
        f"総合判定: {risk_status}\n"
        f"経済状態: {economic_condition}\n"
        f"異常レベル: {anomaly_level}"
    )

    send_discord(message)


if __name__ == "__main__":
    main()