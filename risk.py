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
USD_JPY_INDICATOR = "usd_jpy"
INDUSTRIAL_PRODUCTION_INDICATOR = "鉱工業生産指数"
MACHINERY_ORDERS_INDICATOR = "機械受注（船舶・電力を除く民需）"
COINCIDENT_INDEX_INDICATOR = "景気動向指数（CI一致指数）"


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
            usd_jpy_risk REAL NOT NULL DEFAULT 0,
            industrial_production_risk REAL NOT NULL DEFAULT 0,
            machinery_orders_risk REAL NOT NULL DEFAULT 0,
            coincident_index_risk REAL NOT NULL DEFAULT 0,
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

    if "usd_jpy_risk" not in columns:
        cur.execute("""
            ALTER TABLE risk_history
            ADD COLUMN usd_jpy_risk REAL NOT NULL DEFAULT 0
        """)

        print(
            "risk_historyに"
            "usd_jpy_risk列を追加しました"
        )

    if "industrial_production_risk" not in columns:
        cur.execute("""
            ALTER TABLE risk_history
            ADD COLUMN industrial_production_risk REAL NOT NULL DEFAULT 0
        """)

        print(
            "risk_historyに"
            "industrial_production_risk列を追加しました"
        )

    if "machinery_orders_risk" not in columns:
        cur.execute("""
            ALTER TABLE risk_history
            ADD COLUMN machinery_orders_risk REAL NOT NULL DEFAULT 0
        """)

        print(
            "risk_historyに"
            "machinery_orders_risk列を追加しました"
        )

    if "coincident_index_risk" not in columns:
        cur.execute("""
            ALTER TABLE risk_history
            ADD COLUMN coincident_index_risk REAL NOT NULL DEFAULT 0
        """)

        print(
            "risk_historyに"
            "coincident_index_risk列を追加しました"
        )

    conn.commit()
    conn.close()


def get_previous_total_risk():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT total_risk
        FROM risk_history
        WHERE data_key LIKE '%COINCIDENT_INDEX=%'
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


def get_latest_data_signature(indicator):
    """
    最新データの「日付:値」を返す。

    統計の公表後改定で日付が同じまま値だけ変わった場合も、
    risk_history が新しい経済データとして認識できるようにする。
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT date, value
        FROM economic_data
        WHERE indicator = ?
        ORDER BY date DESC
        LIMIT 1
    """, (indicator,))

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    date, value = row
    return f"{date}:{repr(value)}"


def get_risk_data_key():
    cpi_data = get_latest_data_signature(CPI_INDICATOR)
    gdp_data = get_latest_data_signature(GDP_INDICATOR)
    unemployment_data = get_latest_data_signature(UNEMPLOYMENT_INDICATOR)
    real_wage_data = get_latest_data_signature(REAL_WAGE_INDICATOR)
    consumption_data = get_latest_data_signature(CONSUMPTION_INDICATOR)
    boj_rate_data = get_latest_data_signature(BOJ_RATE_INDICATOR)
    usd_jpy_data = get_latest_data_signature(USD_JPY_INDICATOR)
    industrial_production_data = get_latest_data_signature(
        INDUSTRIAL_PRODUCTION_INDICATOR
    )
    machinery_orders_data = get_latest_data_signature(
        MACHINERY_ORDERS_INDICATOR
    )
    coincident_index_data = get_latest_data_signature(
        COINCIDENT_INDEX_INDICATOR
    )

    return (
        f"CPI={cpi_data}|"
        f"GDP={gdp_data}|"
        f"UNEMPLOYMENT={unemployment_data}|"
        f"REAL_WAGE={real_wage_data}|"
        f"CONSUMPTION={consumption_data}|"
        f"BOJ_RATE={boj_rate_data}|"
        f"USD_JPY={usd_jpy_data}|"
        f"INDUSTRIAL_PRODUCTION={industrial_production_data}|"
        f"MACHINERY_ORDERS={machinery_orders_data}|"
        f"COINCIDENT_INDEX={coincident_index_data}"
    )

def save_risk_history(
    data_key,
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
            usd_jpy_risk,
            industrial_production_risk,
            machinery_orders_risk,
            coincident_index_risk,
            total_risk,
            risk_status,
            economic_condition,
            anomaly_level
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        usd_jpy_risk,
        industrial_production_risk,
        machinery_orders_risk,
        coincident_index_risk,
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



def calculate_usd_jpy_risk():
    rows = get_data(
        USD_JPY_INDICATOR
    )

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    # 為替制度や長期構造の違いを直接比較しすぎないよう
    # 直近10年（120か月）を基準にする。
    recent = values[-120:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    # 円安・円高の方向そのものを「悪い」と決めつけず、
    # 平常レンジからの乖離と急変の大きさをリスク化する。
    level_risk = z_to_risk(
        abs(level_z)
    )

    change_risk = z_to_risk(
        abs(change_z)
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


def calculate_industrial_production_risk():
    rows = get_data(
        INDUSTRIAL_PRODUCTION_INDICATOR
    )

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    # 2020年基準の系列なので、直近5年程度を基準にする。
    recent = values[-60:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    # 生産水準が平常より低い、または急低下している場合に
    # リスクが高くなるよう、符号を反転して評価する。
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


def calculate_machinery_orders_risk():
    rows = get_data(
        MACHINERY_ORDERS_INDICATOR
    )

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    # 機械受注は月ごとの振れが大きいため、
    # 金額の絶対水準より変化率を重視する。
    recent = values[-61:]

    monthly_changes = []

    for i in range(1, len(recent)):
        previous = recent[i - 1]
        current = recent[i]

        if previous == 0:
            continue

        change = (
            (current - previous)
            / abs(previous)
            * 100
        )

        monthly_changes.append(change)

    if len(monthly_changes) < 4:
        return 0, 0, 0

    historical_changes = monthly_changes[:-1]

    mean = statistics.mean(
        historical_changes
    )

    std = statistics.stdev(
        historical_changes
    )

    latest_change = monthly_changes[-1]

    if std == 0:
        change_z = 0
    else:
        change_z = (
            latest_change - mean
        ) / std

    recent_three = monthly_changes[-3:]

    three_month_average = statistics.mean(
        recent_three
    )

    # 急激な低下をリスクとして評価する。
    change_risk = z_to_risk(
        -change_z
    )

    # 3か月平均がマイナスの場合もリスク化する。
    # 平均 -10% 以下で最大100点。
    trend_risk = max(
        0,
        min(
            -three_month_average
            / 10
            * 100,
            100
        )
    )

    # 単月の急変を70%、3か月方向を30%。
    risk = (
        change_risk * 0.70
        + trend_risk * 0.30
    )

    return (
        round(risk, 2),
        round(change_z, 2),
        round(three_month_average, 2)
    )


def calculate_coincident_index_risk():
    rows = get_data(
        COINCIDENT_INDEX_INDICATOR
    )

    if len(rows) < 12:
        return 0, 0, 0

    values = [
        row[1]
        for row in rows
    ]

    # CI一致指数は景気の現状を表す指標。
    # 基準改定や長期構造変化の影響を抑えるため、
    # 直近5年程度を基準にする。
    recent = values[-60:]

    level_z = calculate_z_score(
        recent
    )

    change_z = calculate_change_z_score(
        recent
    )

    # 平常より低い水準、または急低下を
    # リスクとして評価する。
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



def calculate_direction_score(indicator, periods=3, inverse=False):
    """直近の方向性を -100 ～ +100 で評価する。"""
    rows = get_data(indicator)

    if len(rows) < periods + 1:
        return 0.0, "データ不足"

    values = [row[1] for row in rows[-(periods + 1):]]
    changes = []

    for i in range(1, len(values)):
        previous = values[i - 1]
        current = values[i]

        if previous == 0:
            change = current - previous
        else:
            change = (current - previous) / abs(previous) * 100

        if inverse:
            change = -change

        changes.append(change)

    positive = sum(change > 0 for change in changes)
    negative = sum(change < 0 for change in changes)
    score = (positive - negative) / len(changes) * 100

    # 3期間の方向性を5段階で表現する。
    # 小幅でも改善・悪化の広がりを取りこぼさない一方、
    # 方向が揃った場合は「強い」と区別する。
    if score >= 66:
        label = "強い改善"
    elif score >= 20:
        label = "改善"
    elif score <= -66:
        label = "強い悪化"
    elif score <= -20:
        label = "悪化"
    else:
        label = "中立"

    return round(score, 2), label


def calculate_economic_trend():
    """
    GDPは直近3四半期、月次系列は直近3か月の方向性を使う。
    失業率は低下を改善として扱う。
    """
    specs = [
        ("GDP", GDP_INDICATOR, 3, False, 0.20),
        ("完全失業率", UNEMPLOYMENT_INDICATOR, 3, True, 0.15),
        ("実質賃金", REAL_WAGE_INDICATOR, 3, False, 0.10),
        ("個人消費", CONSUMPTION_INDICATOR, 3, False, 0.15),
        ("鉱工業生産", INDUSTRIAL_PRODUCTION_INDICATOR, 3, False, 0.15),
        ("機械受注", MACHINERY_ORDERS_INDICATOR, 3, False, 0.10),
        ("CI一致指数", COINCIDENT_INDEX_INDICATOR, 3, False, 0.15),
    ]

    details = []
    weighted_score = 0.0
    total_weight = 0.0

    for name, indicator, periods, inverse, weight in specs:
        score, label = calculate_direction_score(
            indicator,
            periods=periods,
            inverse=inverse
        )

        if label == "データ不足":
            details.append((name, score, label))
            continue

        weighted_score += score * weight
        total_weight += weight
        details.append((name, score, label))

    if total_weight == 0:
        return 0.0, "⚪ 判定不能", details, 0, 0, 0

    trend_score = round(weighted_score / total_weight, 2)
    improving = sum(
        label in ("強い改善", "改善")
        for _, _, label in details
    )
    worsening = sum(
        label in ("強い悪化", "悪化")
        for _, _, label in details
    )
    mixed = sum(
        label == "中立"
        for _, _, label in details
    )

    if trend_score >= 60 and improving >= 5:
        status = "🟢 回復加速"
    elif trend_score >= 20 and improving >= 4:
        status = "🟢 回復"
    elif trend_score <= -60 and worsening >= 5:
        status = "🔴 後退警戒"
    elif trend_score <= -20 and worsening >= 4:
        status = "🟡 減速"
    else:
        status = "⚪ 横ばい"

    return trend_score, status, details, improving, worsening, mixed


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
    boj_rate_risk,
    usd_jpy_risk,
    industrial_production_risk,
    machinery_orders_risk,
    coincident_index_risk
):
    risks = [
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
    ]

    deteriorated = sum(
        risk >= 40
        for risk in risks
    )

    if deteriorated >= 10:
        return "🔴 10指標が同時に悪化"

    if deteriorated == 9:
        return "🔴 9指標が同時に悪化"

    if deteriorated == 8:
        return "🔴 8指標が同時に悪化"

    if deteriorated == 7:
        return "🔴 7指標が同時に悪化"

    if deteriorated == 6:
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
    boj_rate_risk,
    usd_jpy_risk,
    industrial_production_risk,
    machinery_orders_risk,
    coincident_index_risk
):
    risks = [
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
    boj_rate_risk,
    usd_jpy_risk,
    industrial_production_risk,
    machinery_orders_risk,
    coincident_index_risk
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

    if (
        usd_jpy_risk >= 40
        and cpi_risk >= 40
    ):
        return "🟠 為替急変・物価警戒"

    if (
        usd_jpy_risk >= 40
        and boj_rate_risk >= 40
    ):
        return "🟠 為替・金利変動警戒"

    if (
        industrial_production_risk >= 40
        and gdp_risk >= 40
    ):
        return "🟠 生産・景気減速警戒"

    if (
        industrial_production_risk >= 40
        and unemployment_risk >= 40
    ):
        return "🟠 生産・雇用悪化警戒"

    if (
        machinery_orders_risk >= 40
        and industrial_production_risk >= 40
    ):
        return "🟠 設備投資・生産減速警戒"

    if (
        machinery_orders_risk >= 40
        and gdp_risk >= 40
    ):
        return "🟠 設備投資・景気減速警戒"

    if (
        coincident_index_risk >= 40
        and gdp_risk >= 40
    ):
        return "🟠 景気動向・GDP減速警戒"

    if (
        coincident_index_risk >= 40
        and industrial_production_risk >= 40
    ):
        return "🟠 景気動向・生産活動低下警戒"

    if coincident_index_risk >= 40:
        return "🟡 景気動向悪化警戒"

    if machinery_orders_risk >= 40:
        return "🟡 設備投資需要低下警戒"

    if usd_jpy_risk >= 40:
        return "🟡 為替変動警戒"

    if industrial_production_risk >= 40:
        return "🟡 生産活動低下警戒"

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

    (
        usd_jpy_risk,
        usd_jpy_level_z,
        usd_jpy_change_z
    ) = calculate_usd_jpy_risk()

    (
        industrial_production_risk,
        industrial_production_level_z,
        industrial_production_change_z
    ) = calculate_industrial_production_risk()

    (
        machinery_orders_risk,
        machinery_orders_change_z,
        machinery_orders_three_month_average
    ) = calculate_machinery_orders_risk()

    (
        coincident_index_risk,
        coincident_index_level_z,
        coincident_index_change_z
    ) = calculate_coincident_index_risk()

    # 10指標のウェイト
    # 合計100%
    cpi_weight = 0.13
    gdp_weight = 0.17
    unemployment_weight = 0.13
    real_wage_weight = 0.13
    consumption_weight = 0.09
    boj_rate_weight = 0.08
    usd_jpy_weight = 0.07
    industrial_production_weight = 0.07
    machinery_orders_weight = 0.06
    coincident_index_weight = 0.07

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
        * boj_rate_weight
        + usd_jpy_risk
        * usd_jpy_weight
        + industrial_production_risk
        * industrial_production_weight
        + machinery_orders_risk
        * machinery_orders_weight
        + coincident_index_risk
        * coincident_index_weight,
        2
    )

    status = risk_level(
        total_risk
    )

    (
        trend_score,
        trend_status,
        trend_details,
        trend_improving,
        trend_worsening,
        trend_mixed
    ) = calculate_economic_trend()

    condition = economic_condition(
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

    simultaneous = (
        detect_simultaneous_deterioration(
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
    )

    anomaly = anomaly_level(
        total_risk,
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
        usd_jpy_risk,
        industrial_production_risk,
        machinery_orders_risk,
        coincident_index_risk,
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

    print("【ドル円】")
    print(
        "水準Zスコア:",
        usd_jpy_level_z
    )
    print(
        "変化Zスコア:",
        usd_jpy_change_z
    )
    print(
        "リスク:",
        usd_jpy_risk,
        "/ 100"
    )
    print()

    print("【鉱工業生産】")
    print(
        "水準Zスコア:",
        industrial_production_level_z
    )
    print(
        "変化Zスコア:",
        industrial_production_change_z
    )
    print(
        "リスク:",
        industrial_production_risk,
        "/ 100"
    )
    print()

    print("【機械受注】")
    print(
        "前月比Zスコア:",
        machinery_orders_change_z
    )
    print(
        "直近3か月平均前月比:",
        machinery_orders_three_month_average,
        "%"
    )
    print(
        "リスク:",
        machinery_orders_risk,
        "/ 100"
    )
    print()

    print("【景気動向指数（CI一致指数）】")
    print(
        "水準Zスコア:",
        coincident_index_level_z
    )
    print(
        "変化Zスコア:",
        coincident_index_change_z
    )
    print(
        "リスク:",
        coincident_index_risk,
        "/ 100"
    )
    print()

    print("【総合】")
    print(f"CPIウェイト: {cpi_weight * 100:.1f} %")
    print(f"GDPウェイト: {gdp_weight * 100:.1f} %")
    print(f"失業率ウェイト: {unemployment_weight * 100:.1f} %")
    print(f"実質賃金ウェイト: {real_wage_weight * 100:.1f} %")
    print(f"個人消費ウェイト: {consumption_weight * 100:.1f} %")
    print(f"日銀金利ウェイト: {boj_rate_weight * 100:.1f} %")
    print(f"ドル円ウェイト: {usd_jpy_weight * 100:.1f} %")
    print(
        f"鉱工業生産ウェイト: "
        f"{industrial_production_weight * 100:.1f} %"
    )
    print(
        f"機械受注ウェイト: "
        f"{machinery_orders_weight * 100:.1f} %"
    )
    print(
        f"CI一致指数ウェイト: "
        f"{coincident_index_weight * 100:.1f} %"
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
            "10指標版データなし"
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
            "10指標版の初回計算のため比較なし"
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

    print("【景気トレンド判定】")
    print("トレンドスコア:", trend_score, "/ -100 ～ +100")
    print("トレンド判定:", trend_status)
    print(
        "改善:",
        trend_improving,
        "指標 / 悪化:",
        trend_worsening,
        "指標 / 中立:",
        trend_mixed,
        "指標"
    )

    for trend_name, indicator_score, trend_label in trend_details:
        print(
            f"{trend_name}: "
            f"{trend_label} "
            f"({indicator_score:+.2f})"
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