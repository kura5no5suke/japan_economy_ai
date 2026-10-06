import os
import sqlite3

import requests
from dotenv import load_dotenv

from db_config import DB_PATH
from notification_state import (
    evaluate_notification_state,
)
from recession_signal_history import (
    update_recession_signal_history,
)
from risk import (
    calculate_economic_trend,
    detect_simultaneous_deterioration,
)


load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL"
)


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
        WHERE data_key
            LIKE '%COINCIDENT_INDEX=%'
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
            timeout=30,
        )

        print(
            "Discord HTTPステータス:",
            response.status_code,
        )

        if response.status_code in (
            200,
            204,
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
            e,
        )
        return False


def main():
    print(
        "===== GitHub自動通知判定 ====="
    )

    current_risk = get_latest_risk()

    if current_risk is None:
        print(
            "10指標版のリスクデータが"
            "ありません。"
        )
        return

    simultaneous = (
        detect_simultaneous_deterioration(
            current_risk["cpi_risk"],
            current_risk["gdp_risk"],
            current_risk[
                "unemployment_risk"
            ],
            current_risk[
                "real_wage_risk"
            ],
            current_risk[
                "consumption_risk"
            ],
            current_risk[
                "boj_rate_risk"
            ],
            current_risk[
                "usd_jpy_risk"
            ],
            current_risk[
                "industrial_production_risk"
            ],
            current_risk[
                "machinery_orders_risk"
            ],
            current_risk[
                "coincident_index_risk"
            ],
        )
    )

    (
        trend_score,
        trend_status,
        trend_details_data,
        trend_improving,
        trend_worsening,
        trend_mixed,
    ) = calculate_economic_trend()

    # --------------------------------------------------------
    # 景気後退シグナルV2を計算・履歴保存
    # --------------------------------------------------------

    signal_history = (
        update_recession_signal_history()
    )

    if not signal_history.get(
        "success"
    ):
        print(
            "景気後退シグナルV2の"
            "履歴更新に失敗しました。"
        )

        print(
            signal_history.get(
                "reason",
                "不明なエラー",
            )
        )

        # 欠損状態を通知履歴へ保存すると
        # 次回に誤通知する可能性があるため、
        # この実行では通知状態を更新しない。
        return

    signal_current = signal_history[
        "current"
    ]

    # --------------------------------------------------------
    # 前回GitHub Actions実行時の状態と比較
    # --------------------------------------------------------

    notification = (
        evaluate_notification_state(
            current_risk,
            signal_current,
        )
    )

    print(
        "10指標総合判定:",
        current_risk["risk_status"],
    )

    print(
        "異常レベル:",
        current_risk["anomaly_level"],
    )

    print(
        "CI先行警戒:",
        signal_current[
            "leading_warning"
        ],
    )

    print(
        "実体経済確認:",
        signal_current[
            "confirmation_status"
        ],
    )

    print(
        "景気後退最終判定:",
        signal_current[
            "final_status"
        ],
    )

    if notification["is_first"]:
        print()
        print(
            "🆕 GitHub自動通知状態を"
            "初期登録しました。"
        )
        print(
            "初回登録ではDiscord通知を"
            "送信しません。"
        )
        return

    if not notification[
        "has_change"
    ]:
        print()
        print(
            "🟢 前回のGitHub Actions実行時から"
            "主要判定に変化がないため、"
            "Discord通知はありません。"
        )
        return

    print()
    print(
        "⚠ 前回のGitHub Actions実行時から"
        "主要判定が変化しました。"
    )

    for change in notification[
        "changes"
    ]:
        print(
            "  ・",
            change,
        )

    change_text = "\n".join(
        f"・{change}"
        for change in notification[
            "changes"
        ]
    )

    trend_details = "\n".join(
        (
            f"- {name}: "
            f"{label} "
            f"({score:+.2f})"
        )
        for (
            name,
            score,
            label,
        ) in trend_details_data
    )

    message = (
        "🚨 日本経済監視AI 状態変化\n\n"
        "【前回自動実行からの変化】\n"
        f"{change_text}\n\n"

        "【10指標】\n"
        f"CPIリスク: "
        f"{current_risk['cpi_risk']} / 100\n"
        f"GDPリスク: "
        f"{current_risk['gdp_risk']} / 100\n"
        f"完全失業率リスク: "
        f"{current_risk['unemployment_risk']} / 100\n"
        f"実質賃金リスク: "
        f"{current_risk['real_wage_risk']} / 100\n"
        f"個人消費リスク: "
        f"{current_risk['consumption_risk']} / 100\n"
        f"日銀金利リスク: "
        f"{current_risk['boj_rate_risk']} / 100\n"
        f"ドル円リスク: "
        f"{current_risk['usd_jpy_risk']} / 100\n"
        f"鉱工業生産リスク: "
        f"{current_risk['industrial_production_risk']} / 100\n"
        f"機械受注リスク: "
        f"{current_risk['machinery_orders_risk']} / 100\n"
        f"CI一致指数リスク: "
        f"{current_risk['coincident_index_risk']} / 100\n\n"

        f"総合リスク: "
        f"{current_risk['total_risk']} / 100\n"
        f"総合判定: "
        f"{current_risk['risk_status']}\n"
        f"経済状態: "
        f"{current_risk['economic_condition']}\n"
        f"異常レベル: "
        f"{current_risk['anomaly_level']}\n"
        f"同時悪化: "
        f"{simultaneous}\n\n"

        "【景気トレンド】\n"
        f"トレンドスコア: "
        f"{trend_score:+.2f}\n"
        f"トレンド判定: "
        f"{trend_status}\n"
        f"改善: {trend_improving}指標 / "
        f"悪化: {trend_worsening}指標 / "
        f"中立: {trend_mixed}指標\n"
        f"{trend_details}\n\n"

        "【景気後退シグナル V2】\n"
        f"先行警戒: "
        f"{signal_current['leading_warning']}\n"
        f"実体経済確認: "
        f"{signal_current['confirmation_status']}\n"
        f"確認スコア: "
        f"{signal_current['confirmation_score']} / 100\n"
        f"40点以上: "
        f"{signal_current['deteriorated_count']} / "
        f"{signal_current['available_count']}指標\n"
        f"60点以上: "
        f"{signal_current['severe_count']} / "
        f"{signal_current['available_count']}指標\n"
        f"データ信頼度: "
        f"{signal_current['data_confidence']}\n"
        f"最終判定: "
        f"{signal_current['final_status']}\n"
        f"判断: "
        f"{signal_current['final_message']}"
    )

    send_discord(
        message
    )


if __name__ == "__main__":
    main()
