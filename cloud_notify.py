import os
import sqlite3
import requests
from dotenv import load_dotenv
from risk import calculate_economic_trend, detect_simultaneous_deterioration
from leading_warning import calculate_leading_warning


from db_config import DB_PATH

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL"
)


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
            boj_rate_risk,
            usd_jpy_risk,
            industrial_production_risk,
            machinery_orders_risk,
            coincident_index_risk,
            total_risk,
            risk_status,
            economic_condition,
            anomaly_level
        FROM risk_history
        WHERE data_key
            LIKE '%COINCIDENT_INDEX=%'
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    conn.close()

    return row


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

        print(
            "Discord HTTPステータス:",
            response.status_code
        )

        if response.status_code in (
            200,
            204
        ):
            print(
                "Discord送信成功"
            )
            return True

        print(
            "Discord送信失敗"
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
    row = get_latest_risk()

    if row is None:
        print(
            "10指標版のリスクデータが"
            "ありません。"
        )
        return

    (
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        boj_rate_risk,
        usd_jpy_risk,
        industrial_production_risk,
        machinery_orders_risk,
        coincident_index_risk,
        total_risk,
        risk_status,
        economic_condition,
        anomaly_level
    ) = row

    simultaneous = detect_simultaneous_deterioration(
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        boj_rate_risk,
        usd_jpy_risk,
        industrial_production_risk,
        machinery_orders_risk,
        coincident_index_risk
    )

    (
        trend_score,
        trend_status,
        trend_details_data,
        trend_improving,
        trend_worsening,
        trend_mixed
    ) = calculate_economic_trend()

    trend_details = "\n".join(
        f"- {name}: {label} ({score:+.2f})"
        for name, score, label in trend_details_data
    )
    leading_warning = calculate_leading_warning()


    message = (
        "📊 日本経済監視AI\n\n"
        f"CPIリスク: {cpi_risk} / 100\n"
        f"GDPリスク: {gdp_risk} / 100\n"
        f"完全失業率リスク: "
        f"{unemployment_risk} / 100\n"
        f"実質賃金リスク: "
        f"{real_wage_risk} / 100\n"
        f"個人消費リスク: "
        f"{consumption_risk} / 100\n"
        f"日銀金利リスク: "
        f"{boj_rate_risk} / 100\n"
        f"ドル円リスク: "
        f"{usd_jpy_risk} / 100\n"
        f"鉱工業生産リスク: "
        f"{industrial_production_risk} / 100\n"
        f"機械受注リスク: "
        f"{machinery_orders_risk} / 100\n"
        f"CI一致指数リスク: "
        f"{coincident_index_risk} / 100\n\n"
        f"総合リスク: {total_risk} / 100\n"
        f"総合判定: {risk_status}\n"
        f"経済状態: {economic_condition}\n\n"
        "【景気トレンド判定】\n"
        f"トレンドスコア: {trend_score} / -100 ～ +100\n"
        f"トレンド判定: {trend_status}\n"
        f"改善: {trend_improving}指標 / "
        f"悪化: {trend_worsening}指標 / "
        f"中立: {trend_mixed}指標\n"
        f"{trend_details}\n\n"
        "【景気先行警戒】\n"
        f"最新年月: {leading_warning['latest_date']}\n"
        f"CI先行指数: {leading_warning['latest_value']} (2020年=100)\n"
        f"3か月方向: {leading_warning['direction_score']:+.2f} ({leading_warning['direction_label']})\n"
        f"連続低下: {leading_warning['consecutive_declines']}か月\n"
        f"3か月変化率: {leading_warning['three_month_change']:+.2f}%\n"
        f"先行警戒: {leading_warning['warning_level']}\n\n"
        "【異常検知】\n"
        f"同時悪化: {simultaneous}\n"
        f"異常レベル: {anomaly_level}"
    )

    send_discord(
        message
    )


if __name__ == "__main__":
    main()