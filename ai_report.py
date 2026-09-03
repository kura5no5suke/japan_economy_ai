import os
import sqlite3
import requests
from datetime import datetime
from dotenv import load_dotenv

DB_PATH = "data/economy.db"
REPORT_DIR = "reports"

CPI_INDICATOR = "CPI_総合_前年同月比"
GDP_INDICATOR = "GDP_実質_前年同期比"
UNEMPLOYMENT_INDICATOR = "完全失業率"
REAL_WAGE_INDICATOR = "実質賃金_前年比"
CONSUMPTION_INDICATOR = "個人消費_前年同月比"

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"


def get_latest_values(indicator, limit=2):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT date, value, unit
        FROM economic_data
        WHERE indicator = ?
        ORDER BY date DESC
        LIMIT ?
    """, (indicator, limit))

    rows = cur.fetchall()
    conn.close()

    return rows


def get_latest_risk_history(limit=2):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            calculated_at,
            data_key,
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
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return rows


def get_real_wage_decline_streak():
    rows = get_latest_values(REAL_WAGE_INDICATOR, 60)

    if len(rows) < 2:
        return 0

    rows = sorted(rows, key=lambda x: x[0])

    streak = 0

    for i in range(len(rows) - 1, 0, -1):
        current_value = rows[i][1]
        previous_value = rows[i - 1][1]

        if current_value < previous_value:
            streak += 1
        else:
            break

    return streak


def build_fact_texts():
    cpi_rows = get_latest_values(CPI_INDICATOR, 2)
    gdp_rows = get_latest_values(GDP_INDICATOR, 2)
    unemployment_rows = get_latest_values(UNEMPLOYMENT_INDICATOR, 2)
    real_wage_rows = get_latest_values(REAL_WAGE_INDICATOR, 2)
    consumption_rows = get_latest_values(CONSUMPTION_INDICATOR, 2)

    if len(cpi_rows) < 2:
        raise RuntimeError("CPIの比較データが不足しています。")

    if len(gdp_rows) < 2:
        raise RuntimeError("GDPの比較データが不足しています。")

    if len(unemployment_rows) < 2:
        raise RuntimeError("完全失業率の比較データが不足しています。")

    if len(real_wage_rows) < 2:
        raise RuntimeError("実質賃金の比較データが不足しています。")

    if len(consumption_rows) < 2:
        raise RuntimeError("個人消費の比較データが不足しています。")

    cpi_latest_date, cpi_latest_value, _ = cpi_rows[0]
    cpi_previous_date, cpi_previous_value, _ = cpi_rows[1]

    gdp_latest_date, gdp_latest_value, _ = gdp_rows[0]
    gdp_previous_date, gdp_previous_value, _ = gdp_rows[1]

    unemployment_latest_date, unemployment_latest_value, _ = unemployment_rows[0]
    unemployment_previous_date, unemployment_previous_value, _ = unemployment_rows[1]

    real_wage_latest_date, real_wage_latest_value, _ = real_wage_rows[0]
    real_wage_previous_date, real_wage_previous_value, _ = real_wage_rows[1]

    consumption_latest_date, consumption_latest_value, _ = consumption_rows[0]
    consumption_previous_date, consumption_previous_value, _ = consumption_rows[1]

    if cpi_latest_value > cpi_previous_value:
        cpi_direction = "上昇した"
    elif cpi_latest_value < cpi_previous_value:
        cpi_direction = "低下した"
    else:
        cpi_direction = "変化していない"

    if gdp_latest_value > gdp_previous_value:
        gdp_direction = "上昇した"
    elif gdp_latest_value < gdp_previous_value:
        gdp_direction = "低下した"
    else:
        gdp_direction = "変化していない"

    if unemployment_latest_value < unemployment_previous_value:
        unemployment_direction = "低下した"
    elif unemployment_latest_value > unemployment_previous_value:
        unemployment_direction = "上昇した"
    else:
        unemployment_direction = "変化していない"

    if real_wage_latest_value > real_wage_previous_value:
        real_wage_direction = "上昇した"
    elif real_wage_latest_value < real_wage_previous_value:
        real_wage_direction = "低下した"
    else:
        real_wage_direction = "変化していない"

    if consumption_latest_value > consumption_previous_value:
        consumption_direction = "上昇した"
    elif consumption_latest_value < consumption_previous_value:
        consumption_direction = "低下した"
    else:
        consumption_direction = "変化していない"

    cpi_fact = (
        f"CPIの前年同月比は、前回の{cpi_previous_value}%から"
        f"最新の{cpi_latest_value}%へ{cpi_direction}。"
    )

    gdp_fact = (
        f"実質GDPの前年同期比は、前回の{gdp_previous_value}%から"
        f"最新の{gdp_latest_value}%へ{gdp_direction}。"
    )

    unemployment_fact = (
        f"完全失業率は、前月の{unemployment_previous_value}%から"
        f"最新の{unemployment_latest_value}%へ{unemployment_direction}。"
    )

    real_wage_fact = (
        f"実質賃金の前年同月比は、前回の{real_wage_previous_value}%から"
        f"最新の{real_wage_latest_value}%へ{real_wage_direction}。"
    )

    consumption_fact = (
        f"個人消費の前年同月比は、前回の{consumption_previous_value}%から"
        f"最新の{consumption_latest_value}%へ{consumption_direction}。"
    )

    decline_streak = get_real_wage_decline_streak()

    return {
        "cpi_latest_date": cpi_latest_date,
        "cpi_previous_date": cpi_previous_date,
        "cpi_latest_value": cpi_latest_value,
        "cpi_previous_value": cpi_previous_value,

        "gdp_latest_date": gdp_latest_date,
        "gdp_previous_date": gdp_previous_date,
        "gdp_latest_value": gdp_latest_value,
        "gdp_previous_value": gdp_previous_value,

        "unemployment_latest_date": unemployment_latest_date,
        "unemployment_previous_date": unemployment_previous_date,
        "unemployment_latest_value": unemployment_latest_value,
        "unemployment_previous_value": unemployment_previous_value,

        "real_wage_latest_date": real_wage_latest_date,
        "real_wage_previous_date": real_wage_previous_date,
        "real_wage_latest_value": real_wage_latest_value,
        "real_wage_previous_value": real_wage_previous_value,

        "consumption_latest_date": consumption_latest_date,
        "consumption_previous_date": consumption_previous_date,
        "consumption_latest_value": consumption_latest_value,
        "consumption_previous_value": consumption_previous_value,

        "cpi_fact": cpi_fact,
        "gdp_fact": gdp_fact,
        "unemployment_fact": unemployment_fact,
        "real_wage_fact": real_wage_fact,
        "consumption_fact": consumption_fact,
        "real_wage_decline_streak": decline_streak,
    }


def build_reason_text(facts, current_risk):
    return (
        f"{facts['cpi_fact']}\n"
        f"{facts['gdp_fact']}\n"
        f"{facts['unemployment_fact']}\n"
        f"{facts['real_wage_fact']}\n"
        f"連続低下は{facts['real_wage_decline_streak']}か月である。\n"
        f"{facts['consumption_fact']}\n"
        f"総合リスクは{current_risk['total_risk']} / 100で、"
        f"総合判定は{current_risk['risk_status']}。"
    )


def build_prompt(facts, current_risk, previous_risk, reason_text):
    previous_risk_text = "データなし"

    if previous_risk is not None:
        previous_risk_text = f"{previous_risk['total_risk']}"

    if previous_risk is None:
        risk_change_text = "比較なし"
        risk_change_status = "🟢 初回計算"
    else:
        change = round(
            current_risk["total_risk"] - previous_risk["total_risk"],
            2
        )

        if change >= 10:
            risk_change_status = "🔴 急上昇"
        elif change >= 5:
            risk_change_status = "🟠 上昇"
        elif change <= -10:
            risk_change_status = "🟢 大幅低下"
        elif change <= -5:
            risk_change_status = "🟢 低下"
        else:
            risk_change_status = "🟢 大きな変化なし"

        risk_change_text = f"{change}"

    prompt = f"""
あなたは日本経済監視AIです。

以下のPython生成済みデータだけを使用して、
日本経済監視レポートを作成してください。

【最重要ルール】
- 数値を変更しない。
- 日付を変更しない。
- 期間を変更しない。
- 新しい事実を追加しない。
- 原因を推測しない。
- 将来予測をしない。
- 「改善」「悪化」「回復」「減速」「加速」などの評価語を勝手に追加しない。
- 「前月比」は完全失業率にだけ使用する。
- CPIは必ず「前年同月比」と表現する。
- GDPは必ず「前年同期比」と表現する。
- 実質賃金は必ず「前年同月比」と表現する。
- 個人消費は必ず「前年同月比」と表現する。
- 判断理由はPython生成済みの文章をそのまま使用する。
- 判断理由の文章を書き換えない。
- 思考過程を出力しない。
- 完成したレポートだけを出力する。

【Python生成済み事実文】

■ 物価
{facts['cpi_fact']}

■ 景気
{facts['gdp_fact']}

■ 雇用
{facts['unemployment_fact']}

■ 実質賃金
{facts['real_wage_fact']}
連続低下は{facts['real_wage_decline_streak']}か月である。

■ 個人消費
{facts['consumption_fact']}

【判断理由】
{reason_text}

【リスク】
CPIリスク: {current_risk['cpi_risk']} / 100
GDPリスク: {current_risk['gdp_risk']} / 100
完全失業率リスク: {current_risk['unemployment_risk']} / 100
実質賃金リスク: {current_risk['real_wage_risk']} / 100
個人消費リスク: {current_risk['consumption_risk']} / 100
総合リスク: {current_risk['total_risk']} / 100
総合判定: {current_risk['risk_status']}

【リスク変化】
前回総合リスク: {previous_risk_text}
今回総合リスク: {current_risk['total_risk']}
変化量: {risk_change_text}ポイント
変化判定: {risk_change_status}

【異常検知】
同時悪化: {current_risk['economic_condition']}
異常レベル: {current_risk['anomaly_level']}

【出力形式】

【日本経済監視レポート】

■ 物価
{facts['cpi_fact']}

■ 景気
{facts['gdp_fact']}

■ 雇用
{facts['unemployment_fact']}

■ 実質賃金
{facts['real_wage_fact']}
連続低下は{facts['real_wage_decline_streak']}か月である

■ 個人消費
{facts['consumption_fact']}

■ リスク
CPIリスク: {current_risk['cpi_risk']} / 100
GDPリスク: {current_risk['gdp_risk']} / 100
完全失業率リスク: {current_risk['unemployment_risk']} / 100
実質賃金リスク: {current_risk['real_wage_risk']} / 100
個人消費リスク: {current_risk['consumption_risk']} / 100
総合リスク: {current_risk['total_risk']} / 100
総合判定: {current_risk['risk_status']}

■ リスク変化
前回総合リスク: {previous_risk_text}
今回総合リスク: {current_risk['total_risk']}
変化量: {risk_change_text}ポイント
変化判定: {risk_change_status}

■ 異常検知
同時悪化: {current_risk['economic_condition']}
異常レベル: {current_risk['anomaly_level']}

■ 総合評価
{current_risk['economic_condition']}

■ 判断理由
{reason_text}

■ 注意事項
この5指標だけでは日本経済全体を完全には判断できない。
"""

    return prompt


def call_ollama(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=300
        )

        print("Ollama HTTPステータス:", response.status_code)

        if response.status_code != 200:
            print("Ollama呼び出し失敗")
            print(response.text)
            return None

        data = response.json()
        result = data.get("response", "").strip()

        if not result:
            print("Ollamaから空の回答が返されました。")
            return None

        return result

    except Exception as e:
        print("Ollama呼び出しエラー:", e)
        return None


def save_report(text):
    os.makedirs(REPORT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_path = os.path.join(
        REPORT_DIR,
        f"report_{timestamp}.txt"
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("レポート保存:", file_path)

    return file_path


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


def get_current_risk():
    rows = get_latest_risk_history(1)

    if not rows:
        raise RuntimeError("risk_historyにデータがありません。")

    row = rows[0]

    return {
        "id": row[0],
        "calculated_at": row[1],
        "data_key": row[2],
        "cpi_risk": row[3],
        "gdp_risk": row[4],
        "unemployment_risk": row[5],
        "real_wage_risk": row[6],
        "consumption_risk": row[7],
        "total_risk": row[8],
        "risk_status": row[9],
        "economic_condition": row[10],
        "anomaly_level": row[11],
    }


def get_previous_risk():
    rows = get_latest_risk_history(2)

    if len(rows) < 2:
        return None

    row = rows[1]

    return {
        "id": row[0],
        "calculated_at": row[1],
        "data_key": row[2],
        "cpi_risk": row[3],
        "gdp_risk": row[4],
        "unemployment_risk": row[5],
        "real_wage_risk": row[6],
        "consumption_risk": row[7],
        "total_risk": row[8],
        "risk_status": row[9],
        "economic_condition": row[10],
        "anomaly_level": row[11],
    }


def main():
    print()
    print("========================================")
    print("      日本経済監視AI レポート生成")
    print("========================================")

    print()
    print("===== 経済データ読み込み =====")

    facts = build_fact_texts()

    print(
        "CPI:",
        facts["cpi_latest_date"],
        facts["cpi_latest_value"],
        "%"
    )

    print(
        "GDP:",
        facts["gdp_latest_date"],
        facts["gdp_latest_value"],
        "%"
    )

    print(
        "完全失業率:",
        facts["unemployment_latest_date"],
        facts["unemployment_latest_value"],
        "%"
    )

    print(
        "実質賃金:",
        facts["real_wage_latest_date"],
        facts["real_wage_latest_value"],
        "%"
    )

    print(
        "個人消費:",
        facts["consumption_latest_date"],
        facts["consumption_latest_value"],
        "%"
    )

    print(
        "実質賃金連続低下:",
        facts["real_wage_decline_streak"],
        "か月"
    )

    current_risk = get_current_risk()
    previous_risk = get_previous_risk()

    print()
    print("===== リスク情報 =====")
    print("CPIリスク:", current_risk["cpi_risk"])
    print("GDPリスク:", current_risk["gdp_risk"])
    print("完全失業率リスク:", current_risk["unemployment_risk"])
    print("実質賃金リスク:", current_risk["real_wage_risk"])
    print("個人消費リスク:", current_risk["consumption_risk"])
    print("総合リスク:", current_risk["total_risk"])
    print("総合判定:", current_risk["risk_status"])

    reason_text = build_reason_text(
        facts,
        current_risk
    )

    prompt = build_prompt(
        facts,
        current_risk,
        previous_risk,
        reason_text
    )

    print()
    print("===== Ollamaによるレポート生成 =====")

    report = call_ollama(prompt)

    if report is None:
        print("AIレポート生成に失敗しました。")
        return

    file_path = save_report(report)

    print()
    print("===== レポート =====")
    print(report)

    print()
    print("===== Discord通知判定 =====")

    if current_risk["anomaly_level"] != "🟢 通常":
        message = (
            "🚨 日本経済監視AI 異常検知\n\n"
            f"総合リスク: {current_risk['total_risk']} / 100\n"
            f"総合判定: {current_risk['risk_status']}\n"
            f"異常レベル: {current_risk['anomaly_level']}\n\n"
            f"レポート: {os.path.basename(file_path)}"
        )

        send_discord(message)
    else:
        print("通常状態のためDiscord通知はありません。")


if __name__ == "__main__":
    main()