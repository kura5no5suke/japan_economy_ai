import sqlite3
import statistics

DB_PATH = "data/economy.db"

INDICATOR = "CPI_総合_前年同月比"


def get_cpi_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT date, value
        FROM economic_data
        WHERE indicator = ?
        ORDER BY date ASC
    """, (INDICATOR,))

    rows = cur.fetchall()

    conn.close()

    return rows


def analyze_cpi():
    rows = get_cpi_data()

    if len(rows) < 12:
        print("CPIデータが少なすぎます")
        return

    values = [row[1] for row in rows]

    changes = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        changes.append(change)

    latest_date = rows[-1][0]
    previous_date = rows[-2][0]

    latest_value = rows[-1][1]
    previous_value = rows[-2][1]

    latest_change = latest_value - previous_value

    historical_changes = changes[:-1]

    mean_change = statistics.mean(historical_changes)
    std_change = statistics.stdev(historical_changes)

    if std_change == 0:
        z_score = 0
    else:
        z_score = (latest_change - mean_change) / std_change

    print()
    print("===== CPI統計的異常検知 =====")

    print("現在:", latest_date, latest_value, "%")
    print("前回:", previous_date, previous_value, "%")

    print("今回の変化:", round(latest_change, 2), "ポイント")
    print("過去の平均変化:", round(mean_change, 2), "ポイント")
    print("過去の標準偏差:", round(std_change, 2))

    print("Zスコア:", round(z_score, 2))

    if abs(z_score) >= 3:
        print("判定: 🔴 非常に異常")
    elif abs(z_score) >= 2:
        print("判定: 🟠 異常")
    elif abs(z_score) >= 1.5:
        print("判定: 🟡 注意")
    else:
        print("判定: 🟢 通常")


if __name__ == "__main__":
    analyze_cpi()