import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from db_config import DB_PATH
from notification_state import evaluate_notification_state
from recession_signal_history import update_recession_signal_history
from risk import calculate_economic_trend, detect_simultaneous_deterioration

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

JST = ZoneInfo("Asia/Tokyo")

# Discord Embed colors
COLOR_GREEN = 0x2ECC71
COLOR_YELLOW = 0xF1C40F
COLOR_ORANGE = 0xE67E22
COLOR_RED = 0xE74C3C
COLOR_GRAY = 0x95A5A6


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


def status_rank(status):
    text = str(status or "")

    if text.startswith("🔴"):
        return 3

    if text.startswith("🟠"):
        return 2

    if text.startswith("🟡"):
        return 1

    if text.startswith("🟢"):
        return 0

    return -1


def get_status_color(*statuses):
    highest = max(
        (
            status_rank(status)
            for status in statuses
        ),
        default=-1,
    )

    if highest >= 3:
        return COLOR_RED

    if highest == 2:
        return COLOR_ORANGE

    if highest == 1:
        return COLOR_YELLOW

    if highest == 0:
        return COLOR_GREEN

    return COLOR_GRAY


def risk_icon(value):
    if value is None:
        return "⚪"

    if value >= 60:
        return "🔴"

    if value >= 40:
        return "🟠"

    if value >= 25:
        return "🟡"

    return "🟢"


def format_risk(value):
    if value is None:
        return "データなし"

    return f"{float(value):.2f}"


def get_risk_items(current_risk):
    return [
        ("CPI", current_risk["cpi_risk"]),
        ("GDP", current_risk["gdp_risk"]),
        ("完全失業率", current_risk["unemployment_risk"]),
        ("実質賃金", current_risk["real_wage_risk"]),
        ("個人消費", current_risk["consumption_risk"]),
        ("日銀金利", current_risk["boj_rate_risk"]),
        ("ドル円", current_risk["usd_jpy_risk"]),
        ("鉱工業生産", current_risk["industrial_production_risk"]),
        ("機械受注", current_risk["machinery_orders_risk"]),
        ("CI一致指数", current_risk["coincident_index_risk"]),
    ]


def get_top_risks(current_risk, limit=3):
    items = [
        (name, value)
        for name, value in get_risk_items(
            current_risk
        )
        if value is not None
    ]

    items.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return items[:limit]


def build_top_risk_text(
    current_risk,
    limit=3,
):
    lines = []

    for index, (name, value) in enumerate(
        get_top_risks(
            current_risk,
            limit=limit,
        ),
        start=1,
    ):
        lines.append(
            f"`{index}.` {risk_icon(value)} "
            f"**{name}**  {format_risk(value)}"
        )

    return "\n".join(lines)


def build_all_risk_text(current_risk):
    lines = []

    for name, value in get_risk_items(
        current_risk
    ):
        lines.append(
            f"{risk_icon(value)} "
            f"**{name}**  {format_risk(value)}"
        )

    return "\n".join(lines)


def build_trend_detail_text(
    trend_details_data,
):
    return "\n".join(
        f"{label} **{name}** `{score:+.2f}`"
        for name, score, label
        in trend_details_data
    )


def build_change_summary(notification):
    if notification["is_first"]:
        return "🆕 初回状態登録"

    if notification["has_change"]:
        return "⚠️ 主要判定に変化あり"

    return "✅ 主要判定の変化なし"


def has_major_alert_state(
    current_risk,
    signal_current,
):
    """
    🟠 / 🔴 が継続しているときは
    毎日の定期通知も詳細版にする。

    🟡 は通常の短い通知に残し、
    状態が変わった瞬間は別の詳細警告で知らせる。
    """

    statuses = [
        current_risk["risk_status"],
        current_risk["anomaly_level"],
        signal_current["leading_warning"],
        signal_current["confirmation_status"],
        signal_current["final_status"],
    ]

    return any(
        status_rank(status) >= 2
        for status in statuses
    )


def build_compact_daily_embed(
    current_risk,
    simultaneous,
    trend_score,
    trend_status,
    trend_improving,
    trend_worsening,
    trend_mixed,
    signal_current,
    notification,
):
    now = datetime.now(JST)

    color = get_status_color(
        current_risk["risk_status"],
        current_risk["anomaly_level"],
        signal_current["final_status"],
    )

    return {
        "title": "📊 日本経済監視AI｜定期レポート",
        "description": (
            f"**{now:%Y年%m月%d日 %H:%M} JST**"
        ),
        "color": color,
        "fields": [
            {
                "name": "🧭 総合状況",
                "value": (
                    f"**総合リスク**　`{current_risk['total_risk']:.2f} / 100`\n"
                    f"**総合判定**　{current_risk['risk_status']}\n"
                    f"**10指標評価**　{current_risk['economic_condition']}\n"
                    f"**異常レベル**　{current_risk['anomaly_level']}"
                ),
                "inline": False,
            },
            {
                "name": "📉 景気後退 V2",
                "value": (
                    f"**最終判定**　{signal_current['final_status']}\n"
                    f"**先行警戒**　{signal_current['leading_warning']}\n"
                    f"**実体経済確認**　{signal_current['confirmation_status']}\n"
                    f"**40点以上** `{signal_current['deteriorated_count']} / "
                    f"{signal_current['available_count']}`　"
                    f"**60点以上** `{signal_current['severe_count']} / "
                    f"{signal_current['available_count']}`"
                ),
                "inline": False,
            },
            {
                "name": "🔥 リスク上位3",
                "value": (
                    build_top_risk_text(
                        current_risk,
                        limit=3,
                    )
                    or "データなし"
                ),
                "inline": False,
            },
            {
                "name": "📈 トレンド",
                "value": (
                    f"{trend_status}　`{trend_score:+.2f}`\n"
                    f"改善 `{trend_improving}` / "
                    f"悪化 `{trend_worsening}` / "
                    f"中立 `{trend_mixed}`\n"
                    f"同時悪化: {simultaneous}"
                ),
                "inline": False,
            },
            {
                "name": "🔄 前回比",
                "value": build_change_summary(
                    notification
                ),
                "inline": False,
            },
        ],
        "footer": {
            "text": (
                "Japan Economy Monitor | "
                "通常時はコンパクト表示"
            )
        },
        "timestamp": now.isoformat(),
    }


def build_detailed_daily_embed(
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
    now = datetime.now(JST)

    color = get_status_color(
        current_risk["risk_status"],
        current_risk["anomaly_level"],
        signal_current["final_status"],
        signal_current["leading_warning"],
        signal_current["confirmation_status"],
    )

    return {
        "title": "⚠️ 日本経済監視AI｜詳細レポート",
        "description": (
            f"**{now:%Y年%m月%d日 %H:%M} JST**\n"
            "🟠または🔴の警戒状態があるため、"
            "詳細表示に切り替えています。"
        ),
        "color": color,
        "fields": [
            {
                "name": "🧭 総合状況",
                "value": (
                    f"**総合リスク**　`{current_risk['total_risk']:.2f} / 100`\n"
                    f"**総合判定**　{current_risk['risk_status']}\n"
                    f"**10指標評価**　{current_risk['economic_condition']}\n"
                    f"**異常レベル**　{current_risk['anomaly_level']}\n"
                    f"**同時悪化**　{simultaneous}"
                ),
                "inline": False,
            },
            {
                "name": "📉 景気後退シグナル V2",
                "value": (
                    f"**最終判定**　{signal_current['final_status']}\n"
                    f"**先行警戒**　{signal_current['leading_warning']}\n"
                    f"**実体経済確認**　{signal_current['confirmation_status']}\n"
                    f"**確認スコア**　`{signal_current['confirmation_score']:.2f} / 100`\n"
                    f"**40点以上**　`{signal_current['deteriorated_count']} / "
                    f"{signal_current['available_count']}`\n"
                    f"**60点以上**　`{signal_current['severe_count']} / "
                    f"{signal_current['available_count']}`\n"
                    f"**データ信頼度**　{signal_current['data_confidence']}"
                ),
                "inline": False,
            },
            {
                "name": "📝 V2判断",
                "value": signal_current["final_message"],
                "inline": False,
            },
            {
                "name": "📊 10指標リスク",
                "value": build_all_risk_text(
                    current_risk
                ),
                "inline": False,
            },
            {
                "name": "📈 景気トレンド",
                "value": (
                    f"**判定**　{trend_status}\n"
                    f"**スコア**　`{trend_score:+.2f}`\n"
                    f"**内訳**　改善 `{trend_improving}` / "
                    f"悪化 `{trend_worsening}` / "
                    f"中立 `{trend_mixed}`"
                ),
                "inline": False,
            },
            {
                "name": "🔎 トレンド詳細",
                "value": (
                    build_trend_detail_text(
                        trend_details_data
                    )
                    or "データなし"
                ),
                "inline": False,
            },
            {
                "name": "🔄 前回比",
                "value": build_change_summary(
                    notification
                ),
                "inline": False,
            },
        ],
        "footer": {
            "text": (
                "Japan Economy Monitor | "
                "警戒時は詳細表示"
            )
        },
        "timestamp": now.isoformat(),
    }


def build_change_alert_embed(
    current_risk,
    simultaneous,
    trend_score,
    trend_status,
    trend_details_data,
    signal_current,
    notification,
):
    now = datetime.now(JST)

    change_text = "\n".join(
        f"• {change}"
        for change in notification["changes"]
    )

    color = get_status_color(
        current_risk["risk_status"],
        current_risk["anomaly_level"],
        signal_current["leading_warning"],
        signal_current["confirmation_status"],
        signal_current["final_status"],
    )

    if color == COLOR_GREEN:
        color = COLOR_YELLOW

    return {
        "title": "🚨 日本経済監視AI｜状態変化警告",
        "description": (
            "前回の自動実行から、"
            "**主要判定が変化しました。**\n"
            "変化した時だけ送られる詳細通知です。"
        ),
        "color": color,
        "fields": [
            {
                "name": "⚠️ 変化した項目",
                "value": (
                    change_text
                    or "変化内容を取得できませんでした。"
                ),
                "inline": False,
            },
            {
                "name": "🧭 現在の状態",
                "value": (
                    f"**総合リスク**　`{current_risk['total_risk']:.2f} / 100`\n"
                    f"**総合判定**　{current_risk['risk_status']}\n"
                    f"**10指標評価**　{current_risk['economic_condition']}\n"
                    f"**異常レベル**　{current_risk['anomaly_level']}\n"
                    f"**同時悪化**　{simultaneous}"
                ),
                "inline": False,
            },
            {
                "name": "📉 景気後退 V2",
                "value": (
                    f"**最終判定**　{signal_current['final_status']}\n"
                    f"**先行警戒**　{signal_current['leading_warning']}\n"
                    f"**実体経済確認**　{signal_current['confirmation_status']}\n"
                    f"**確認スコア**　`{signal_current['confirmation_score']:.2f} / 100`\n"
                    f"**40点以上**　`{signal_current['deteriorated_count']} / "
                    f"{signal_current['available_count']}`\n"
                    f"**60点以上**　`{signal_current['severe_count']} / "
                    f"{signal_current['available_count']}`"
                ),
                "inline": False,
            },
            {
                "name": "📝 V2判断",
                "value": signal_current["final_message"],
                "inline": False,
            },
            {
                "name": "🔥 リスク上位5",
                "value": (
                    build_top_risk_text(
                        current_risk,
                        limit=5,
                    )
                    or "データなし"
                ),
                "inline": False,
            },
            {
                "name": "📈 景気トレンド",
                "value": (
                    f"{trend_status}　`{trend_score:+.2f}`\n"
                    + (
                        build_trend_detail_text(
                            trend_details_data
                        )
                        or "データなし"
                    )
                ),
                "inline": False,
            },
        ],
        "footer": {
            "text": (
                "Japan Economy Monitor | "
                "主要判定の変化を検知"
            )
        },
        "timestamp": now.isoformat(),
    }


def send_discord(
    *,
    content=None,
    embed=None,
):
    if not DISCORD_WEBHOOK_URL:
        print(
            "DISCORD_WEBHOOK_URLが設定されていません。"
        )
        return False

    payload = {}

    if content:
        payload["content"] = content

    if embed:
        payload["embeds"] = [embed]

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
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
        "===== GitHub定期通知 + 状態変化監視 ====="
    )

    current_risk = get_latest_risk()

    if current_risk is None:
        print(
            "10指標版のリスクデータがありません。"
        )
        return

    simultaneous = (
        detect_simultaneous_deterioration(
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
    )

    (
        trend_score,
        trend_status,
        trend_details_data,
        trend_improving,
        trend_worsening,
        trend_mixed,
    ) = calculate_economic_trend()

    signal_history = (
        update_recession_signal_history()
    )

    if not signal_history.get("success"):
        print(
            "景気後退シグナルV2の履歴更新に失敗しました。"
        )
        print(
            signal_history.get(
                "reason",
                "不明なエラー",
            )
        )
        return

    signal_current = signal_history[
        "current"
    ]

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
        signal_current["leading_warning"],
    )
    print(
        "実体経済確認:",
        signal_current["confirmation_status"],
    )
    print(
        "景気後退最終判定:",
        signal_current["final_status"],
    )

    major_alert_state = (
        has_major_alert_state(
            current_risk,
            signal_current,
        )
    )

    # 状態変化がある場合は、
    # 定期レポートは短くして、
    # この後に詳細な変化警告を別送する。
    if (
        major_alert_state
        and not notification["has_change"]
    ):
        print()
        print(
            "⚠ 🟠/🔴の警戒状態が継続中のため、"
            "詳細定期レポートを送信します。"
        )

        daily_embed = (
            build_detailed_daily_embed(
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
        )

    else:
        print()
        print(
            "📊 通常のコンパクト定期レポートを"
            "送信します。"
        )

        daily_embed = (
            build_compact_daily_embed(
                current_risk,
                simultaneous,
                trend_score,
                trend_status,
                trend_improving,
                trend_worsening,
                trend_mixed,
                signal_current,
                notification,
            )
        )

    daily_sent = send_discord(
        embed=daily_embed
    )

    if not daily_sent:
        print(
            "定期レポートの送信に失敗しました。"
        )
        return

    if notification["is_first"]:
        print()
        print(
            "🆕 通知状態を初期登録しました。"
        )
        print(
            "初回のため追加警告は送りません。"
        )
        return

    if not notification["has_change"]:
        print()
        print(
            "🟢 主要判定に変化なし。"
        )
        print(
            "追加警告はありません。"
        )
        return

    print()
    print(
        "⚠ 主要判定に変化があります。"
    )

    for change in notification["changes"]:
        print(
            "  ・",
            change,
        )

    alert_embed = (
        build_change_alert_embed(
            current_risk,
            simultaneous,
            trend_score,
            trend_status,
            trend_details_data,
            signal_current,
            notification,
        )
    )

    print(
        "🚨 詳細な状態変化警告を"
        "追加送信します。"
    )

    send_discord(
        content=(
            "⚠️ **日本経済の主要判定が"
            "変化しました**"
        ),
        embed=alert_embed,
    )


if __name__ == "__main__":
    main()
