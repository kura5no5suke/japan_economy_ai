import os
import sqlite3

import requests
from dotenv import load_dotenv

from db_config import DB_PATH
from notification_state import evaluate_notification_state
from recession_signal_history import update_recession_signal_history
from risk import calculate_economic_trend, detect_simultaneous_deterioration

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def get_latest_risk():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
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
        WHERE data_key LIKE '%COINCIDENT_INDEX=%'
        ORDER BY id DESC
        LIMIT 1
        """
    )

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "cpi_risk": row[0],
        "gdp_risk": row[1],
        "unemployment_risk": row[2],
        "real_wage_risk": row[3],
        "consumption_risk": row[4],
        "boj_rate_risk": row[5],
        "usd_jpy_risk": row[6],
        "industrial_production_risk": row[7],
        "machinery_orders_risk": row[8],
        "coincident_index_risk": row[9],
        "total_risk": row[10],
        "risk_status": row[11],
        "economic_condition": row[12],
        "anomaly_level": row[13],
    }


def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URLが設定されていません。")
        return False

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=30,
        )

        print("Discord HTTPステータス:", response.status_code)

        if response.status_code in (200, 204):
            print("Discord送信成功")
            return True

        print("Discord送信失敗")
        print(response.text)
        return False

    except requests.RequestException as e:
        print("Discord通信エラー:", e)
        return False


def build_daily_message(
    current_risk,
    simultaneous,
    trend_score,
    trend_status,
    trend_details_data,
    trend_improving,
    trend_worsening,
    trend_mixed,
    signal_current,
    notification,
):
    trend_details = "\n".join(
        f"- {name}: {label} ({score:+.2f})"
        for name, score, label in trend_details_data
    )

    if notification["is_first"]:
        change_summary = "初回状態登録"
    elif notification["has_change"]:
        change_summary = "⚠ 主要判定に変化あり"
    else:
        change_summary = "🟢 主要判定の変化なし"

    return (
        "📊 日本経済監視AI 定期レポート\n\n"
        "【10指標】\n"
        f"CPIリスク: {current_risk['cpi_risk']} / 100\n"
        f"GDPリスク: {current_risk['gdp_risk']} / 100\n"
        f"完全失業率リスク: {current_risk['unemployment_risk']} / 100\n"
        f"実質賃金リスク: {current_risk['real_wage_risk']} / 100\n"
        f"個人消費リスク: {current_risk['consumption_risk']} / 100\n"
        f"日銀金利リスク: {current_risk['boj_rate_risk']} / 100\n"
        f"ドル円リスク: {current_risk['usd_jpy_risk']} / 100\n"
        f"鉱工業生産リスク: {current_risk['industrial_production_risk']} / 100\n"
        f"機械受注リスク: {current_risk['machinery_orders_risk']} / 100\n"
        f"CI一致指数リスク: {current_risk['coincident_index_risk']} / 100\n\n"
        f"総合リスク: {current_risk['total_risk']} / 100\n"
        f"総合判定: {current_risk['risk_status']}\n"
        f"経済状態: {current_risk['economic_condition']}\n"
        f"異常レベル: {current_risk['anomaly_level']}\n"
        f"同時悪化: {simultaneous}\n\n"
        "【景気トレンド】\n"
        f"トレンドスコア: {trend_score:+.2f}\n"
        f"トレンド判定: {trend_status}\n"
        f"改善: {trend_improving}指標 / 悪化: {trend_worsening}指標 / 中立: {trend_mixed}指標\n"
        f"{trend_details}\n\n"
        "【景気後退シグナル V2】\n"
        f"先行警戒: {signal_current['leading_warning']}\n"
        f"実体経済確認: {signal_current['confirmation_status']}\n"
        f"確認スコア: {signal_current['confirmation_score']} / 100\n"
        f"40点以上: {signal_current['deteriorated_count']} / {signal_current['available_count']}指標\n"
        f"60点以上: {signal_current['severe_count']} / {signal_current['available_count']}指標\n"
        f"データ信頼度: {signal_current['data_confidence']}\n"
        f"景気トレンド: {signal_current['trend_status']} ({signal_current['trend_score']:+.2f})\n"
        f"最終判定: {signal_current['final_status']}\n"
        f"判断: {signal_current['final_message']}\n\n"
        "【前回自動実行との比較】\n"
        f"{change_summary}"
    )


def build_change_alert(current_risk, signal_current, notification):
    change_text = "\n".join(
        f"・{change}"
        for change in notification["changes"]
    )

    return (
        "🚨 日本経済監視AI 状態変化警告\n\n"
        "前回の自動実行から主要判定が変化しました。\n\n"
        "【変化した項目】\n"
        f"{change_text}\n\n"
        "【現在の状態】\n"
        f"総合リスク: {current_risk['total_risk']} / 100\n"
        f"総合判定: {current_risk['risk_status']}\n"
        f"異常レベル: {current_risk['anomaly_level']}\n"
        f"CI先行警戒: {signal_current['leading_warning']}\n"
        f"実体経済確認: {signal_current['confirmation_status']}\n"
        f"景気後退最終判定: {signal_current['final_status']}\n"
        f"判断: {signal_current['final_message']}"
    )


def main():
    print("===== GitHub定期通知 + 状態変化監視 =====")

    current_risk = get_latest_risk()

    if current_risk is None:
        print("10指標版のリスクデータがありません。")
        return

    simultaneous = detect_simultaneous_deterioration(
        current_risk["cpi_risk"],
        current_risk["gdp_risk"],
        current_risk["unemployment_risk"],
        current_risk["real_wage_risk"],
        current_risk["consumption_risk"],
        current_risk["boj_rate_risk"],
        current_risk["usd_jpy_risk"],
        current_risk["industrial_production_risk"],
        current_risk["machinery_orders_risk"],
        current_risk["coincident_index_risk"],
    )

    (
        trend_score,
        trend_status,
        trend_details_data,
        trend_improving,
        trend_worsening,
        trend_mixed,
    ) = calculate_economic_trend()

    signal_history = update_recession_signal_history()

    if not signal_history.get("success"):
        print("景気後退シグナルV2の履歴更新に失敗しました。")
        print(signal_history.get("reason", "不明なエラー"))
        return

    signal_current = signal_history["current"]

    notification = evaluate_notification_state(
        current_risk,
        signal_current,
    )

    print("10指標総合判定:", current_risk["risk_status"])
    print("異常レベル:", current_risk["anomaly_level"])
    print("CI先行警戒:", signal_current["leading_warning"])
    print("実体経済確認:", signal_current["confirmation_status"])
    print("景気後退最終判定:", signal_current["final_status"])

    daily_message = build_daily_message(
        current_risk,
        simultaneous,
        trend_score,
        trend_status,
        trend_details_data,
        trend_improving,
        trend_worsening,
        trend_mixed,
        signal_current,
        notification,
    )

    print()
    print("📊 定期レポートをDiscordへ送信します。")

    daily_sent = send_discord(daily_message)

    if not daily_sent:
        print("定期レポートの送信に失敗しました。")
        return

    if notification["is_first"]:
        print()
        print("🆕 通知状態を初期登録しました。")
        print("初回のため追加警告は送りません。")
        return

    if not notification["has_change"]:
        print()
        print("🟢 主要判定に変化なし。")
        print("追加警告はありません。")
        return

    print()
    print("⚠ 主要判定に変化があります。")

    for change in notification["changes"]:
        print("  ・", change)

    alert_message = build_change_alert(
        current_risk,
        signal_current,
        notification,
    )

    print("🚨 状態変化警告を追加送信します。")
    send_discord(alert_message)


if __name__ == "__main__":
    main()
