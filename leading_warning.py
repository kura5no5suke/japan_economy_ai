from statistics import mean

from risk import get_data


LEADING_INDEX_INDICATOR = "景気動向指数（CI先行指数）"


# ============================================================
# データ取得
# ============================================================

def get_leading_index_data():
    """CI先行指数を古い順に取得する。"""
    return get_data(LEADING_INDEX_INDICATOR)


# ============================================================
# 連続低下回数
# ============================================================

def count_consecutive_declines(rows):
    """
    最新月から遡って、
    何か月連続でCI先行指数が低下したかを数える。
    """
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


# ============================================================
# 指定期間の変化率
# ============================================================

def calculate_period_change(rows, periods=3):
    """
    最新値が指定期間前から何％変化したかを計算する。
    """
    if len(rows) < periods + 1:
        return None

    previous = rows[-(periods + 1)][1]
    latest = rows[-1][1]

    if previous == 0:
        return None

    change = (
        (latest - previous)
        / abs(previous)
        * 100
    )

    return round(change, 2)


# ============================================================
# モメンタム減速
# ============================================================

def calculate_momentum_deceleration(
    rows,
    periods=3,
):
    """
    景気の上昇・下降ペースが
    どれくらい変化したかを計算する。

    直近3か月変化率
    －
    その前の3か月変化率

    マイナスが大きいほど、
    上昇ペースの減速が強い。
    """
    if len(rows) < periods * 2 + 1:
        return None

    current_change = calculate_period_change(
        rows,
        periods=periods,
    )

    previous_rows = rows[:-periods]

    previous_change = calculate_period_change(
        previous_rows,
        periods=periods,
    )

    if (
        current_change is None
        or previous_change is None
    ):
        return None

    deceleration = (
        current_change
        - previous_change
    )

    return round(deceleration, 2)


# ============================================================
# 直近高値からの乖離
# ============================================================

def calculate_recent_high_drawdown(
    rows,
    periods=6,
):
    """
    直近高値から現在値が
    何％下落しているかを計算する。

    0%に近い
    → 高値圏

    マイナスが大きい
    → 高値から下落している
    """
    if not rows:
        return None

    recent_rows = rows[-(periods + 1):]

    values = [
        row[1]
        for row in recent_rows
    ]

    recent_high = max(values)
    latest = values[-1]

    if recent_high == 0:
        return None

    drawdown = (
        (latest - recent_high)
        / abs(recent_high)
        * 100
    )

    return round(drawdown, 2)


# ============================================================
# 6か月平均との差
# ============================================================

def calculate_moving_average_gap(
    rows,
    periods=6,
):
    """
    最新CIが直近平均より
    何％上か下かを計算する。
    """
    if len(rows) < periods:
        return None

    values = [
        row[1]
        for row in rows[-periods:]
    ]

    average = mean(values)
    latest = values[-1]

    if average == 0:
        return None

    gap = (
        (latest - average)
        / abs(average)
        * 100
    )

    return round(gap, 2)


# ============================================================
# 景気減速スコア
# ============================================================

def calculate_slowdown_score(
    three_month_change,
    six_month_change,
    momentum_deceleration,
    recent_high_drawdown,
    moving_average_gap,
    direction_label,
):
    """
    景気減速の兆候を点数化する。

    スコアが高いほど、
    景気の勢いが弱くなっている可能性が高い。
    """
    score = 0

    # --------------------------------------------------------
    # 3か月変化
    # --------------------------------------------------------

    if three_month_change is not None:

        if three_month_change < 0:
            score += 2

        elif three_month_change <= 0.75:
            score += 1

    # --------------------------------------------------------
    # 6か月変化
    # --------------------------------------------------------

    if six_month_change is not None:

        if six_month_change < 0:
            score += 1

    # --------------------------------------------------------
    # モメンタム減速
    # --------------------------------------------------------

    if momentum_deceleration is not None:

        if momentum_deceleration <= -2.0:
            score += 2

        elif momentum_deceleration <= -1.0:
            score += 1

    # --------------------------------------------------------
    # 高値からの下落
    # --------------------------------------------------------

    if recent_high_drawdown is not None:

        if recent_high_drawdown <= -2.0:
            score += 2

        elif recent_high_drawdown <= -1.0:
            score += 1

    # --------------------------------------------------------
    # 移動平均との差
    # --------------------------------------------------------

    if moving_average_gap is not None:

        if moving_average_gap < 0:
            score += 1

    # --------------------------------------------------------
    # 方向判定
    # --------------------------------------------------------

    if direction_label == "強い悪化":
        score += 2

    elif direction_label == "悪化":
        score += 1

    return score


# ============================================================
# 警戒レベル判定
# ============================================================

def classify_warning(
    consecutive_declines,
    three_month_change,
    direction_label,
    six_month_change=None,
    momentum_deceleration=None,
    recent_high_drawdown=None,
    moving_average_gap=None,
):
    """
    景気先行警戒レベルを判定する。

    基本方針

    🟢 低警戒
        景気悪化の明確な兆候なし

    🟡 注意
        景気上昇中でも減速兆候が見られる
        早期警戒段階

    🟠 警戒
        実際の低下・悪化が確認された状態

    🔴 強い警戒
        強い、または継続的な景気悪化
    """

    if three_month_change is None:
        return "⚪ 判定不能"

    slowdown_score = calculate_slowdown_score(
        three_month_change,
        six_month_change,
        momentum_deceleration,
        recent_high_drawdown,
        moving_average_gap,
        direction_label,
    )

    # ========================================================
    # 🔴 強い警戒
    # ========================================================

    # 3か月以上連続低下し、
    # 3か月変化率も大きくマイナス
    if (
        consecutive_declines >= 3
        and three_month_change <= -2.0
    ):
        return "🔴 強い警戒"

    # 4か月以上の長期連続低下
    if (
        consecutive_declines >= 4
        and three_month_change < 0
    ):
        return "🔴 強い警戒"

    # ========================================================
    # 🟠 警戒
    # ========================================================

    # 2か月以上連続低下
    if consecutive_declines >= 2:
        return "🟠 警戒"

    # 3か月で2%以上低下
    if three_month_change <= -2.0:
        return "🟠 警戒"

    # 強い悪化方向かつ
    # 実際に指数も低下
    if (
        direction_label == "強い悪化"
        and three_month_change < 0
    ):
        return "🟠 警戒"

    # ========================================================
    # 🟡 注意
    # ========================================================

    # 方向が悪化
    if direction_label in (
        "悪化",
        "強い悪化",
    ):
        return "🟡 注意"

    # 3か月変化がマイナス
    if three_month_change < 0:
        return "🟡 注意"

    # --------------------------------------------------------
    # 2000年型の景気ピーク検知
    #
    # CI自体はまだ上昇しているが、
    # 上昇ペースが急速に低下している状態。
    # --------------------------------------------------------

    if (
        three_month_change <= 0.75
        and momentum_deceleration is not None
        and momentum_deceleration <= -1.5
    ):
        return "🟡 注意"

    # 複数の減速兆候が重なっている場合
    if slowdown_score >= 3:
        return "🟡 注意"

    return "🟢 低警戒"


# ============================================================
# 景気先行警戒の計算
# ============================================================

def calculate_leading_warning():
    """
    CI先行指数から
    景気先行警戒情報を計算する。
    """
    from risk import calculate_direction_score

    rows = get_leading_index_data()

    if len(rows) < 7:
        return None

    latest_date, latest_value = rows[-1]

    # --------------------------------------------------------
    # 方向
    # --------------------------------------------------------

    direction_score, direction_label = (
        calculate_direction_score(
            LEADING_INDEX_INDICATOR,
            periods=3,
        )
    )

    # --------------------------------------------------------
    # 連続低下
    # --------------------------------------------------------

    consecutive_declines = (
        count_consecutive_declines(rows)
    )

    # --------------------------------------------------------
    # 3か月変化
    # --------------------------------------------------------

    three_month_change = (
        calculate_period_change(
            rows,
            periods=3,
        )
    )

    # --------------------------------------------------------
    # 6か月変化
    # --------------------------------------------------------

    six_month_change = (
        calculate_period_change(
            rows,
            periods=6,
        )
    )

    # --------------------------------------------------------
    # モメンタム減速
    # --------------------------------------------------------

    momentum_deceleration = (
        calculate_momentum_deceleration(
            rows,
            periods=3,
        )
    )

    # --------------------------------------------------------
    # 高値乖離
    # --------------------------------------------------------

    recent_high_drawdown = (
        calculate_recent_high_drawdown(
            rows,
            periods=6,
        )
    )

    # --------------------------------------------------------
    # 6か月平均との差
    # --------------------------------------------------------

    moving_average_gap = (
        calculate_moving_average_gap(
            rows,
            periods=6,
        )
    )

    # --------------------------------------------------------
    # 景気減速スコア
    # --------------------------------------------------------

    slowdown_score = calculate_slowdown_score(
        three_month_change,
        six_month_change,
        momentum_deceleration,
        recent_high_drawdown,
        moving_average_gap,
        direction_label,
    )

    # --------------------------------------------------------
    # 警戒レベル
    # --------------------------------------------------------

    warning_level = classify_warning(
        consecutive_declines,
        three_month_change,
        direction_label,
        six_month_change,
        momentum_deceleration,
        recent_high_drawdown,
        moving_average_gap,
    )

    return {
        "latest_date": latest_date,
        "latest_value": latest_value,
        "direction_score": direction_score,
        "direction_label": direction_label,
        "consecutive_declines": (
            consecutive_declines
        ),
        "three_month_change": (
            three_month_change
        ),
        "six_month_change": (
            six_month_change
        ),
        "momentum_deceleration": (
            momentum_deceleration
        ),
        "recent_high_drawdown": (
            recent_high_drawdown
        ),
        "moving_average_gap": (
            moving_average_gap
        ),
        "slowdown_score": (
            slowdown_score
        ),
        "warning_level": (
            warning_level
        ),
    }


# ============================================================
# 表示用
# ============================================================

def format_percent(value):
    if value is None:
        return "データ不足"

    return f"{value:+.2f}%"


# ============================================================
# メイン
# ============================================================

def main():
    result = calculate_leading_warning()

    print(
        "===== 景気先行警戒 ====="
    )

    if result is None:
        print(
            "判定に必要なデータが不足しています"
        )
        return

    print(
        f"最新年月: "
        f"{result['latest_date']}"
    )

    print(
        f"CI先行指数: "
        f"{result['latest_value']}"
    )

    print(
        f"3か月方向: "
        f"{result['direction_score']:+.2f} "
        f"({result['direction_label']})"
    )

    print(
        f"連続低下: "
        f"{result['consecutive_declines']}か月"
    )

    print(
        "3か月変化率: "
        + format_percent(
            result["three_month_change"]
        )
    )

    print(
        "6か月変化率: "
        + format_percent(
            result["six_month_change"]
        )
    )

    print(
        "モメンタム減速: "
        + format_percent(
            result["momentum_deceleration"]
        )
    )

    print(
        "直近高値からの乖離: "
        + format_percent(
            result["recent_high_drawdown"]
        )
    )

    print(
        "6か月平均との差: "
        + format_percent(
            result["moving_average_gap"]
        )
    )

    print(
        f"景気減速スコア: "
        f"{result['slowdown_score']}"
    )

    print(
        f"先行警戒: "
        f"{result['warning_level']}"
    )


if __name__ == "__main__":
    main()