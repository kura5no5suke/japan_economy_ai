from risk import get_data


LEADING_INDEX_INDICATOR = "景気動向指数（CI先行指数）"


def get_leading_index_data():
    """CI先行指数を古い順に取得する。"""
    return get_data(LEADING_INDEX_INDICATOR)


def count_consecutive_declines(rows):
    """最新月から遡って、何か月連続で低下したかを数える。"""
    if len(rows) < 2:
        return 0

    count = 0

    for i in range(len(rows) - 1, 0, -1):
        current = rows[i][1]
        previous = rows[i - 1][1]

        if current < previous:
            count += 1
        else:
            break

    return count


def calculate_period_change(rows, periods=3):
    """最新値が指定期間前から何％変化したかを計算する。"""
    if len(rows) < periods + 1:
        return None

    previous = rows[-(periods + 1)][1]
    latest = rows[-1][1]

    if previous == 0:
        return None

    change = (latest - previous) / abs(previous) * 100

    return round(change, 2)


def calculate_leading_warning():
    """CI先行指数から景気先行警戒の基礎情報を計算する。"""
    from risk import calculate_direction_score

    rows = get_leading_index_data()

    if len(rows) < 4:
        return None

    latest_date, latest_value = rows[-1]
    direction_score, direction_label = calculate_direction_score(
        LEADING_INDEX_INDICATOR,
        periods=3,
    )
    consecutive_declines = count_consecutive_declines(rows)
    three_month_change = calculate_period_change(rows, periods=3)
    warning_level = classify_warning(
        consecutive_declines,
        three_month_change,
        direction_label,
    )

    return {
        "latest_date": latest_date,
        "latest_value": latest_value,
        "direction_score": direction_score,
        "direction_label": direction_label,
        "consecutive_declines": consecutive_declines,
        "three_month_change": three_month_change,
        "warning_level": warning_level,
    }




def classify_warning(consecutive_declines, three_month_change, direction_label):
    """独自ルールで景気先行警戒レベルを判定する。"""
    if three_month_change is None:
        return "⚪ 判定不能"

    if consecutive_declines >= 3 and three_month_change <= -2.0:
        return "🔴 強い警戒"

    if consecutive_declines >= 2 or three_month_change <= -2.0:
        return "🟠 警戒"

    if direction_label in ("悪化", "強い悪化") or three_month_change < 0:
        return "🟡 注意"

    return "🟢 低警戒"


def main():
    result = calculate_leading_warning()

    print("===== 景気先行警戒 =====")

    if result is None:
        print("判定に必要なデータが不足しています")
        return

    print(f"最新年月: {result['latest_date']}")
    print(f"CI先行指数: {result['latest_value']}")
    print(
        f"3か月方向: {result['direction_score']:+.2f} "
        f"({result['direction_label']})"
    )
    print(f"連続低下: {result['consecutive_declines']}か月")
    print(f"3か月変化率: {result['three_month_change']:+.2f}%")
    print(f"先行警戒: {result['warning_level']}")


if __name__ == "__main__":
    main()
