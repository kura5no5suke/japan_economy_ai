import sqlite3
import statistics
from datetime import datetime


DB_PATH = "data/economy.db"

CPI_INDICATOR = "CPI_総合_前年同月比"
GDP_INDICATOR = "GDP_実質_前年同期比"
UNEMPLOYMENT_INDICATOR = "完全失業率"
REAL_WAGE_INDICATOR = "実質賃金_前年比"
CONSUMPTION_INDICATOR = "個人消費_前年同月比"
BOJ_RATE_INDICATOR = "basic_loan_rate"


def create_risk_history_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS risk_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calculated_at TIMESTAMP NOT NULL,
            data_key TEXT NOT NULL UNIQUE,
            cpi_risk REAL NOT NULL,
            gdp_risk REAL NOT NULL,
            unemployment_risk REAL NOT NULL,
            real_wage_risk REAL NOT NULL,
            consumption_risk REAL NOT NULL DEFAULT 0,
            boj_rate_risk REAL NOT NULL DEFAULT 0,
            total_risk REAL NOT NULL,
            risk_status TEXT NOT NULL,
            economic_condition TEXT NOT NULL,
            anomaly_level TEXT NOT NULL
        )
    """)

    columns = [
        row[1]
        for row in cur.execute(
            "PRAGMA table_info(risk_history)"
        ).fetchall()
    ]

    if "consumption_risk" not in columns:
        cur.execute("""
            ALTER TABLE risk_history
            ADD COLUMN consumption_risk REAL NOT NULL DEFAULT 0
        """)

        print(
            "risk_historyに"
            "consumption_risk列を追加しました"
        )

    if "boj_rate_risk" not in columns:
        cur.execute("""
            ALTER TABLE risk_history
            ADD COLUMN boj_rate_risk REAL NOT NULL DEFAULT 0
        """)

        print(
            "risk_historyに"
            "boj_rate_risk列を追加しました"
        )

    conn.commit()
    conn.close()


def get_previous_total_risk():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT total_risk
        FROM risk_history
        WHERE data_key LIKE '%BOJ_RATE=%'
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return row[0]


def calculate_risk_change(previous_risk, current_risk):
    if previous_risk is None:
        return None, "🟢 初回計算"

    change = round(current_risk - previous_risk, 2)

    if change >= 10:
        status = "🔴 急上昇"
    elif change >= 5:
        status = "🟠 上昇"
    elif change <= -10:
        status = "🟢 大幅低下"
    elif change <= -5:
        status = "🟢 低下"
    else:
        status = "🟢 大きな変化なし"

    return change, status


def get_latest_data_date(indicator):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT date
        FROM economic_data
        WHERE indicator = ?
        ORDER BY date DESC
        LIMIT 1
    """, (indicator,))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return row[0]


def get_risk_data_key():
    cpi_date = get_latest_data_date(
        CPI_INDICATOR
    )

    gdp_date = get_latest_data_date(
        GDP_INDICATOR
    )

    unemployment_date = get_latest_data_date(
        UNEMPLOYMENT_INDICATOR
    )

    real_wage_date = get_latest_data_date(
        REAL_WAGE_INDICATOR
    )

    consumption_date = get_latest_data_date(
        CONSUMPTION_INDICATOR
    )

    boj_rate_date = get_latest_data_date(
        BOJ_RATE_INDICATOR
    )

    return (
        f"CPI={cpi_date}|"
        f"GDP={gdp_date}|"
        f"UNEMPLOYMENT={unemployment_date}|"
        f"REAL_WAGE={real_wage_date}|"
        f"CONSUMPTION={consumption_date}|"
        f"BOJ_RATE={boj_rate_date}"
    )


def save_risk_history(
    data_key,
    cpi_risk,
    gdp_risk,
    unemployment_risk,
    real_wage_risk,
    consumption_risk,
    boj_rate_risk,
    total_risk,
    risk_status,
    condition,
    anomaly
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id
        FROM risk_history
        WHERE data_key = ?
    """, (data_key,))

    existing = cur.fetchone()

    if existing:
        print(
            "同じ経済データのリスク履歴は"
            "すでに保存されています"
        )

        conn.close()
        return False

    cur.execute("""
        INSERT INTO risk_history (
            calculated_at,
            data_key,
            cpi_risk,
            gdp_risk,
            unemployment_risk,
            real_wage_risk,
            consumption_risk,
            boj_rate_risk,
            total_risk,
            risk_status,
            economic_condition,
            anomaly_level
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        data_key,
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        boj_rate_risk,
        total_risk,
        risk_status,
        condition,
        anomaly
    ))

    conn.commit()
    conn.close()

    print("リスク履歴を保存しました")
    return True


def get_data(indicator):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT date, value
        FROM economic_data
        WHERE indicator = ?
        ORDER BY date ASC
    """, (indicator,))

    rows = cur.fetchall()
    conn.close()

    return rows


def calculate_z_score(values):
    if len(values) < 3:
        return 0

    historical = values[:-1]

    mean = statistics.mean(historical)
    std = statistics.stdev(historical)

    if std == 0:
        return 0

    latest = values[-1]

    return (latest - mean) / std


def calculate_change_z_score(values):
    if len(values) < 4:
        return 0

    changes = []

    for i in range(1, len(values)):
        changes.append(
            values[i] - values[i - 1]
        )

    historical_changes = changes[:-1]

    if len(historical_changes) < 2:
        return 0

    mean = statistics.mean(
        historical_changes
    )

    std = statistics.stdev(
        historical_changes
    )

    if std == 0:
        return 0

    latest_change = changes[-1]

    return (
        latest_change - mean
    ) / std


def z_to_risk(z_score):
    risk = z_score / 3 * 100

    risk = max(
        0,
        min(risk, 100)
    )

    return risk


def calculate_cpi_risk():
    rows = get_data(CPI_INDICATOR)

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    recent = values[-60:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    level_risk = z_to_risk(
        level_z
    )

    change_risk = z_to_risk(
        change_z
    )

    risk = (
        level_risk * 0.50
        + change_risk * 0.50
    )

    return (
        round(risk, 2),
        round(level_z, 2),
        round(change_z, 2)
    )


def calculate_gdp_risk():
    rows = get_data(GDP_INDICATOR)

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    recent = values[-20:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    level_risk = z_to_risk(
        -level_z
    )

    change_risk = z_to_risk(
        -change_z
    )

    risk = (
        level_risk * 0.50
        + change_risk * 0.50
    )

    return (
        round(risk, 2),
        round(level_z, 2),
        round(change_z, 2)
    )


def calculate_unemployment_risk():
    rows = get_data(
        UNEMPLOYMENT_INDICATOR
    )

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    recent = values[-60:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    level_risk = z_to_risk(
        level_z
    )

    change_risk = z_to_risk(
        change_z
    )

    risk = (
        level_risk * 0.50
        + change_risk * 0.50
    )

    return (
        round(risk, 2),
        round(level_z, 2),
        round(change_z, 2)
    )


def calculate_real_wage_risk():
    rows = get_data(
        REAL_WAGE_INDICATOR
    )

    if len(rows) < 12:
        return 0, 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    recent = values[-60:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    level_risk = z_to_risk(
        -level_z
    )

    change_risk = z_to_risk(
        -change_z
    )

    decline_streak = 0

    for i in range(
        len(values) - 1,
        0,
        -1
    ):
        if values[i] < values[i - 1]:
            decline_streak += 1
        else:
            break

    if decline_streak >= 6:
        streak_risk = 100
    elif decline_streak >= 5:
        streak_risk = 80
    elif decline_streak >= 4:
        streak_risk = 60
    elif decline_streak >= 3:
        streak_risk = 40
    elif decline_streak >= 2:
        streak_risk = 20
    else:
        streak_risk = 0

    risk = (
        level_risk * 0.40
        + change_risk * 0.30
        + streak_risk * 0.30
    )

    return (
        round(risk, 2),
        round(level_z, 2),
        round(change_z, 2),
        decline_streak
    )


def calculate_consumption_risk():
    rows = get_data(
        CONSUMPTION_INDICATOR
    )

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    recent = values[-60:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    level_risk = z_to_risk(
        -level_z
    )

    change_risk = z_to_risk(
        -change_z
    )

    risk = (
        level_risk * 0.50
        + change_risk * 0.50
    )

    return (
        round(risk, 2),
        round(level_z, 2),
        round(change_z, 2)
    )


def calculate_boj_rate_risk():
    rows = get_data(
        BOJ_RATE_INDICATOR
    )

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    # 金利制度が大きく異なる古い時代を
    # 直接比較しすぎないよう直近10年を使用
    recent = values[-120:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    # 金利は「高いこと」だけで
    # 景気悪化とは判断しない。
    # 急上昇をより重視する。
    level_risk = z_to_risk(
        level_z
    )

    change_risk = z_to_risk(
        change_z
    )

    risk = (
        level_risk * 0.30
        + change_risk * 0.70
    )

    return (
        round(risk, 2),
        round(level_z, 2),
        round(change_z, 2)
    )


def risk_level(score):
    if score < 20:
        return "🟢 安全"
    elif score < 40:
        return "🟢 低リスク"
    elif score < 60:
        return "🟡 注意"
    elif score < 80:
        return "🟠 高リスク"
    else:
        return "🔴 非常に高い"


def detect_simultaneous_deterioration(
    cpi_risk,
    gdp_risk,
    unemployment_risk,
    real_wage_risk,
    consumption_risk,
    boj_rate_risk
):
    risks = [
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        boj_rate_risk
    ]

    deteriorated = sum(
        risk >= 40
        for risk in risks
    )

    if deteriorated >= 6:
        return "🔴 6指標が同時に悪化"

    if deteriorated == 5:
        return "🔴 5指標が同時に悪化"

    if deteriorated == 4:
        return "🔴 4指標が同時に悪化"

    if deteriorated == 3:
        return "🔴 3指標が同時に悪化"

    if deteriorated == 2:
        return "🟠 2指標が同時に悪化"

    if deteriorated == 1:
        return "🟡 1指標が悪化"

    return "🟢 複数指標の大きな悪化なし"


def anomaly_level(
    total_risk,
    cpi_risk,
    gdp_risk,
    unemployment_risk,
    real_wage_risk,
    consumption_risk,
    boj_rate_risk
):
    risks = [
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        boj_rate_risk
    ]

    deteriorated = sum(
        risk >= 40
        for risk in risks
    )

    if total_risk >= 80:
        return "🔴 危険"

    if total_risk >= 60:
        return "🟠 警戒"

    if total_risk >= 40:
        return "🟡 注意"

    if deteriorated >= 4:
        return "🔴 危険"

    if deteriorated >= 2:
        return "🟠 警戒"

    if deteriorated == 1:
        return "🟡 注意"

    return "🟢 通常"


def economic_condition(
    cpi_risk,
    gdp_risk,
    unemployment_risk,
    real_wage_risk,
    consumption_risk,
    boj_rate_risk
):
    if (
        gdp_risk >= 40
        and unemployment_risk >= 40
        and real_wage_risk >= 40
        and consumption_risk >= 40
    ):
        return (
            "🔴 景気後退・所得・"
            "消費悪化警戒"
        )

    if (
        cpi_risk >= 40
        and real_wage_risk >= 40
        and consumption_risk >= 40
    ):
        return (
            "🟠 インフレによる"
            "実質所得・消費悪化警戒"
        )

    if (
        cpi_risk >= 40
        and gdp_risk >= 40
        and consumption_risk >= 40
    ):
        return (
            "🟠 スタグフレーション・"
            "消費悪化警戒"
        )

    if (
        gdp_risk >= 40
        and unemployment_risk >= 40
        and consumption_risk >= 40
    ):
        return (
            "🟠 景気後退・"
            "消費悪化警戒"
        )

    if (
        boj_rate_risk >= 40
        and gdp_risk >= 40
    ):
        return (
            "🟠 金利上昇・"
            "景気減速警戒"
        )

    if (
        boj_rate_risk >= 40
        and consumption_risk >= 40
    ):
        return (
            "🟠 金利上昇・"
            "個人消費悪化警戒"
        )

    if (
        real_wage_risk >= 40
        and consumption_risk >= 40
    ):
        return (
            "🟠 実質所得・"
            "消費悪化警戒"
        )

    if consumption_risk >= 40:
        return "🟡 個人消費悪化警戒"

    if real_wage_risk >= 40:
        return "🟡 実質所得悪化警戒"

    if cpi_risk >= 40:
        return "🟡 インフレ警戒"

    if gdp_risk >= 40:
        return "🟡 景気減速警戒"

    if unemployment_risk >= 40:
        return "🟡 雇用悪化警戒"

    if boj_rate_risk >= 40:
        return "🟡 金利上昇警戒"

    return "🟢 大きな異常なし"


def main():
    create_risk_history_table()

    previous_risk = get_previous_total_risk()

    (
        cpi_risk,
        cpi_level_z,
        cpi_change_z
    ) = calculate_cpi_risk()

    (
        gdp_risk,
        gdp_level_z,
        gdp_change_z
    ) = calculate_gdp_risk()

    (
        unemployment_risk,
        unemployment_level_z,
        unemployment_change_z
    ) = calculate_unemployment_risk()

    (
        real_wage_risk,
        real_wage_level_z,
        real_wage_change_z,
        real_wage_decline_streak
    ) = calculate_real_wage_risk()

    (
        consumption_risk,
        consumption_level_z,
        consumption_change_z
    ) = calculate_consumption_risk()

    (
        boj_rate_risk,
        boj_rate_level_z,
        boj_rate_change_z
    ) = calculate_boj_rate_risk()

    # 6指標のウェイト
    # 合計100%
    cpi_weight = 0.18
    gdp_weight = 0.23
    unemployment_weight = 0.18
    real_wage_weight = 0.18
    consumption_weight = 0.13
    boj_rate_weight = 0.10

    total_risk = round(
        cpi_risk * cpi_weight
        + gdp_risk * gdp_weight
        + unemployment_risk
        * unemployment_weight
        + real_wage_risk
        * real_wage_weight
        + consumption_risk
        * consumption_weight
        + boj_rate_risk
        * boj_rate_weight,
        2
    )

    status = risk_level(
        total_risk
    )

    condition = economic_condition(
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        boj_rate_risk
    )

    simultaneous = (
        detect_simultaneous_deterioration(
            cpi_risk,
            gdp_risk,
            unemployment_risk,
            real_wage_risk,
            consumption_risk,
            boj_rate_risk
        )
    )

    anomaly = anomaly_level(
        total_risk,
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        boj_rate_risk
    )

    risk_change, risk_change_status = (
        calculate_risk_change(
            previous_risk,
            total_risk
        )
    )

    data_key = get_risk_data_key()

    saved = save_risk_history(
        data_key,
        cpi_risk,
        gdp_risk,
        unemployment_risk,
        real_wage_risk,
        consumption_risk,
        boj_rate_risk,
        total_risk,
        status,
        condition,
        anomaly
    )

    print()
    print(
        "===== 日本経済リスクスコア ====="
    )
    print()

    print("【CPI】")
    print(
        "水準Zスコア:",
        cpi_level_z
    )
    print(
        "変化Zスコア:",
        cpi_change_z
    )
    print(
        "リスク:",
        cpi_risk,
        "/ 100"
    )
    print()

    print("【GDP】")
    print(
        "水準Zスコア:",
        gdp_level_z
    )
    print(
        "変化Zスコア:",
        gdp_change_z
    )
    print(
        "リスク:",
        gdp_risk,
        "/ 100"
    )
    print()

    print("【完全失業率】")
    print(
        "水準Zスコア:",
        unemployment_level_z
    )
    print(
        "変化Zスコア:",
        unemployment_change_z
    )
    print(
        "リスク:",
        unemployment_risk,
        "/ 100"
    )
    print()

    print("【実質賃金】")
    print(
        "水準Zスコア:",
        real_wage_level_z
    )
    print(
        "変化Zスコア:",
        real_wage_change_z
    )
    print(
        "連続低下:",
        real_wage_decline_streak,
        "か月"
    )
    print(
        "リスク:",
        real_wage_risk,
        "/ 100"
    )
    print()

    print("【個人消費】")
    print(
        "水準Zスコア:",
        consumption_level_z
    )
    print(
        "変化Zスコア:",
        consumption_change_z
    )
    print(
        "リスク:",
        consumption_risk,
        "/ 100"
    )
    print()

    print("【日銀金利】")
    print(
        "水準Zスコア:",
        boj_rate_level_z
    )
    print(
        "変化Zスコア:",
        boj_rate_change_z
    )
    print(
        "リスク:",
        boj_rate_risk,
        "/ 100"
    )
    print()

    print("【総合】")
    print(
        "CPIウェイト:",
        cpi_weight * 100,
        "%"
    )
    print(
        "GDPウェイト:",
        gdp_weight * 100,
        "%"
    )
    print(
        "失業率ウェイト:",
        unemployment_weight * 100,
        "%"
    )
    print(
        "実質賃金ウェイト:",
        real_wage_weight * 100,
        "%"
    )
    print(
        "個人消費ウェイト:",
        consumption_weight * 100,
        "%"
    )
    print(
        "日銀金利ウェイト:",
        boj_rate_weight * 100,
        "%"
    )
    print()

    print(
        "総合リスク:",
        total_risk,
        "/ 100"
    )

    print(
        "総合判定:",
        status
    )
    print()

    print("【前回との比較】")

    if previous_risk is None:
        print(
            "前回リスク: "
            "6指標版データなし"
        )
    else:
        print(
            "前回総合リスク:",
            previous_risk,
            "/ 100"
        )

    print(
        "今回総合リスク:",
        total_risk,
        "/ 100"
    )

    if risk_change is None:
        print(
            "リスク変化: "
            "6指標版の初回計算のため比較なし"
        )
    else:
        print(
            "リスク変化:",
            risk_change,
            "ポイント"
        )

    print(
        "変化判定:",
        risk_change_status
    )
    print()

    print(
        "経済状態:",
        condition
    )
    print()

    print("【異常検知】")
    print(
        "同時悪化:",
        simultaneous
    )
    print(
        "異常レベル:",
        anomaly
    )

    if not saved:
        print()
        print(
            "今回の経済データは前回と同じため、"
            "履歴は追加保存していません"
        )


if __name__ == "__main__":
    main()