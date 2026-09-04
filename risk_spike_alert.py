import os
import sqlite3
import requests
from dotenv import load_dotenv


DB_PATH = "data/economy.db"
SPIKE_THRESHOLD = 10.0

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_latest_two_risks():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # risk_history の列を確認
    cursor.execute("PRAGMA table_info(risk_history)")
    columns = [row[1] for row in cursor.fetchall()]

    # 6指標版では data_key に BOJ_RATE= が入っている
    if "data_key" in columns:
        cursor.execute("""
            SELECT total_risk
            FROM risk_history
            WHERE data_key LIKE '%BOJ_RATE=%'
            ORDER BY id DESC
            LIMIT 2
        """)
    else:
        # 古いDB形式の場合
        cursor.execute("""
            SELECT total_risk
            FROM risk_history
            ORDER BY id DESC
            LIMIT 2
        """)

    rows = cursor.fetchall()

    conn.close()

    if len(rows) < 2:
        return None

    current_risk = float(rows[0][0])
    previous_risk = float(rows[1][0])

    return previous_risk, current_risk


def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print(
            "DISCORD_WEBHOOK_URLが"
            "設定されていません。"
        )
        return False

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={
                "content": message
            },
            timeout=30
        )

        if response.status_code in (200, 204):
            print(
                "Discord警告を送信しました。"
            )
            return True

        print(
            "Discord送信失敗:",
            response.status_code
        )

        print(
            response.text
        )

        return False

    except requests.RequestException as e:
        print(
            "Discord通信エラー:",
            e
        )

        return False


def main():
    result = get_latest_two_risks()

    print(
        "===== 総合リスク急上昇監視 ====="
    )

    if result is None:
        print(
            "比較できる6指標版の"
            "リスク履歴が2件ありません。"
        )

        print(
            "次回以降、履歴が増えると"
            "自動比較されます。"
        )

        return

    previous_risk, current_risk = result

    change = round(
        current_risk - previous_risk,
        2
    )

    print(
        f"前回: {previous_risk:.2f} / 100"
    )

    print(
        f"今回: {current_risk:.2f} / 100"
    )

    print(
        f"変化: {change:.2f} ポイント"
    )

    if change >= SPIKE_THRESHOLD:
        print(
            "🔴 総合リスクが急上昇しています"
        )

        message = (
            "🚨 日本経済監視AI 緊急警告\n\n"
            "総合リスクが急上昇しました。\n\n"
            f"前回: "
            f"{previous_risk:.2f} / 100\n"
            f"今回: "
            f"{current_risk:.2f} / 100\n"
            f"上昇幅: "
            f"+{change:.2f} ポイント\n\n"
            f"警告基準: "
            f"+{SPIKE_THRESHOLD:.0f}"
            "ポイント以上"
        )

        send_discord(message)

    else:
        print(
            "🟢 総合リスクの"
            "急上昇はありません"
        )


if __name__ == "__main__":
    main()