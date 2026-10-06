from statistics import mean, median

from leading_warning import (
    classify_warning,
    count_consecutive_declines,
    calculate_period_change,
    calculate_momentum_deceleration,
    calculate_recent_high_drawdown,
    calculate_moving_average_gap,
    calculate_slowdown_score,
    get_leading_index_data,
)


OFFICIAL_PEAKS = [
    "1985-06",
    "1991-02",
    "1997-05",
    "2000-11",
    "2008-02",
    "2012-03",
    "2018-10",
]


OFFICIAL_TROUGHS = [
    "1986-11",
    "1993-10",
    "1999-01",
    "2002-01",
    "2009-03",
    "2012-11",
    "2020-05",
]


WARNING_RANK = {
    "⚪ 判定不能": -1,
    "🟢 低警戒": 0,
    "🟡 注意": 1,
    "🟠 警戒": 2,
    "🔴 強い警戒": 3,
}


WARNING_THRESHOLDS = (
    "🟡 注意",
    "🟠 警戒",
    "🔴 強い警戒",
)


def month_number(date_string):
    year, month = map(int, date_string.split("-"))
    return year * 12 + month


def is_warning_at_least(warning_level, threshold):
    return (
        WARNING_RANK.get(warning_level, -1)
        >= WARNING_RANK.get(threshold, 999)
    )


def calculate_direction_from_rows(rows, periods=3):
    if len(rows) < periods + 1:
        return 0.0, "データ不足"

    values = [
        row[1]
        for row in rows[-(periods + 1):]
    ]

    changes = []

    for i in range(1, len(values)):
        previous = values[i - 1]
        current = values[i]

        if previous == 0:
            change = current - previous
        else:
            change = (
                (current - previous)
                / abs(previous)
                * 100
            )

        changes.append(change)

    positive = sum(
        change > 0
        for change in changes
    )

    negative = sum(
        change < 0
        for change in changes
    )

    score = (
        (positive - negative)
        / len(changes)
        * 100
    )

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


def run_backtest():
    rows = get_leading_index_data()
    results = []

    for i in range(6, len(rows)):
        historical_rows = rows[: i + 1]

        date, value = historical_rows[-1]

        direction_score, direction_label = (
            calculate_direction_from_rows(
                historical_rows,
                periods=3,
            )
        )

        consecutive_declines = (
            count_consecutive_declines(
                historical_rows
            )
        )

        three_month_change = (
            calculate_period_change(
                historical_rows,
                periods=3,
            )
        )

        six_month_change = (
            calculate_period_change(
                historical_rows,
                periods=6,
            )
        )

        momentum_deceleration = (
            calculate_momentum_deceleration(
                historical_rows,
                periods=3,
            )
        )

        recent_high_drawdown = (
            calculate_recent_high_drawdown(
                historical_rows,
                periods=6,
            )
        )

        moving_average_gap = (
            calculate_moving_average_gap(
                historical_rows,
                periods=6,
            )
        )

        slowdown_score = (
            calculate_slowdown_score(
                three_month_change,
                six_month_change,
                momentum_deceleration,
                recent_high_drawdown,
                moving_average_gap,
                direction_label,
            )
        )

        warning_level = classify_warning(
            consecutive_declines,
            three_month_change,
            direction_label,
            six_month_change,
            momentum_deceleration,
            recent_high_drawdown,
            moving_average_gap,
        )

        results.append(
            {
                "date": date,
                "value": value,
                "direction_score": direction_score,
                "direction_label": direction_label,
                "consecutive_declines": consecutive_declines,
                "three_month_change": three_month_change,
                "six_month_change": six_month_change,
                "momentum_deceleration": momentum_deceleration,
                "recent_high_drawdown": recent_high_drawdown,
                "moving_average_gap": moving_average_gap,
                "slowdown_score": slowdown_score,
                "warning_level": warning_level,
            }
        )

    return results


def is_recession_month(date_string):
    target = month_number(date_string)

    for peak, trough in zip(
        OFFICIAL_PEAKS,
        OFFICIAL_TROUGHS,
    ):
        peak_number = month_number(peak)
        trough_number = month_number(trough)

        if peak_number < target <= trough_number:
            return True, peak, trough

    return False, None, None


def has_full_pre_peak_history(
    results,
    peak,
    months=12,
):
    if not results:
        return False

    first_result_number = month_number(
        results[0]["date"]
    )

    peak_number = month_number(peak)

    return (
        peak_number
        - first_result_number
        >= months
    )


def find_threshold_warning_before_peak(
    results,
    peak,
    threshold,
    min_months_before=1,
    max_months_before=12,
):
    peak_number = month_number(peak)
    candidates = []

    for result in results:
        difference = (
            peak_number
            - month_number(result["date"])
        )

        if not (
            min_months_before
            <= difference
            <= max_months_before
        ):
            continue

        if not is_warning_at_least(
            result["warning_level"],
            threshold,
        ):
            continue

        candidates.append(
            (
                difference,
                result,
            )
        )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: item[0],
    )


def find_same_month_warning(
    results,
    peak,
    threshold,
):
    for result in results:

        if result["date"] != peak:
            continue

        if is_warning_at_least(
            result["warning_level"],
            threshold,
        ):
            return result

    return None


def calculate_peak_detection(
    results,
    threshold,
    months=12,
):
    evaluated_peaks = []
    detected_peaks = []
    missed_peaks = []
    same_month_peaks = []
    insufficient_history = []

    for peak in OFFICIAL_PEAKS:

        if not has_full_pre_peak_history(
            results,
            peak,
            months=months,
        ):
            insufficient_history.append(peak)
            continue

        evaluated_peaks.append(peak)

        found = (
            find_threshold_warning_before_peak(
                results,
                peak,
                threshold,
                min_months_before=1,
                max_months_before=months,
            )
        )

        if found is not None:
            months_before, result = found

            detected_peaks.append(
                {
                    "peak": peak,
                    "warning_date": result["date"],
                    "months_before": months_before,
                    "warning_level": result["warning_level"],
                }
            )

            continue

        same_month = find_same_month_warning(
            results,
            peak,
            threshold,
        )

        if same_month is not None:
            same_month_peaks.append(
                {
                    "peak": peak,
                    "warning_level": (
                        same_month["warning_level"]
                    ),
                }
            )

        missed_peaks.append(peak)

    detection_rate = (
        len(detected_peaks)
        / len(evaluated_peaks)
        * 100
        if evaluated_peaks
        else 0
    )

    lead_times = [
        item["months_before"]
        for item in detected_peaks
    ]

    return {
        "evaluated_peaks": evaluated_peaks,
        "detected_peaks": detected_peaks,
        "missed_peaks": missed_peaks,
        "same_month_peaks": same_month_peaks,
        "insufficient_history": insufficient_history,
        "detection_rate": detection_rate,
        "average_lead": (
            mean(lead_times)
            if lead_times
            else 0
        ),
        "median_lead": (
            median(lead_times)
            if lead_times
            else 0
        ),
    }


def build_threshold_events(
    results,
    threshold,
):
    events = []
    current_event = None

    for result in results:

        active = is_warning_at_least(
            result["warning_level"],
            threshold,
        )

        if active:

            if current_event is None:
                current_event = {
                    "start_date": result["date"],
                    "end_date": result["date"],
                    "months": 1,
                    "max_rank": WARNING_RANK[
                        result["warning_level"]
                    ],
                    "max_level": (
                        result["warning_level"]
                    ),
                }

            else:
                previous_number = month_number(
                    current_event["end_date"]
                )

                current_number = month_number(
                    result["date"]
                )

                if (
                    current_number
                    - previous_number
                    == 1
                ):
                    current_event[
                        "end_date"
                    ] = result["date"]

                    current_event[
                        "months"
                    ] += 1

                    rank = WARNING_RANK[
                        result["warning_level"]
                    ]

                    if (
                        rank
                        > current_event["max_rank"]
                    ):
                        current_event[
                            "max_rank"
                        ] = rank

                        current_event[
                            "max_level"
                        ] = (
                            result["warning_level"]
                        )

                else:
                    events.append(current_event)

                    current_event = {
                        "start_date": result["date"],
                        "end_date": result["date"],
                        "months": 1,
                        "max_rank": WARNING_RANK[
                            result["warning_level"]
                        ],
                        "max_level": (
                            result["warning_level"]
                        ),
                    }

        elif current_event is not None:
            events.append(current_event)
            current_event = None

    if current_event is not None:
        events.append(current_event)

    return events


def find_future_peak(
    warning_date,
    min_months=1,
    max_months=12,
):
    warning_number = month_number(
        warning_date
    )

    candidates = []

    for peak in OFFICIAL_PEAKS:
        difference = (
            month_number(peak)
            - warning_number
        )

        if (
            min_months
            <= difference
            <= max_months
        ):
            candidates.append(
                (
                    difference,
                    peak,
                )
            )

    if not candidates:
        return None, None

    difference, peak = min(
        candidates,
        key=lambda item: item[0],
    )

    return peak, difference


def has_full_followup(
    warning_date,
    latest_date,
    months=12,
):
    available_months = (
        month_number(latest_date)
        - month_number(warning_date)
    )

    return available_months >= months


def classify_prediction_events(
    results,
    threshold,
    months=12,
):
    events = build_threshold_events(
        results,
        threshold,
    )

    latest_date = results[-1]["date"]

    classified = []
    matched_peaks = set()

    for event in events:
        start_date = event["start_date"]

        recession, peak, trough = (
            is_recession_month(start_date)
        )

        if recession:
            classified.append(
                {
                    **event,
                    "classification": "recession",
                    "peak": peak,
                    "trough": trough,
                    "months_before": None,
                }
            )
            continue

        if start_date in OFFICIAL_PEAKS:
            classified.append(
                {
                    **event,
                    "classification": "same_month",
                    "peak": start_date,
                    "trough": None,
                    "months_before": 0,
                }
            )
            continue

        future_peak, lead = find_future_peak(
            start_date,
            min_months=1,
            max_months=months,
        )

        if future_peak is not None:

            if future_peak in matched_peaks:
                classification = "duplicate"
            else:
                classification = "hit"
                matched_peaks.add(future_peak)

            classified.append(
                {
                    **event,
                    "classification": classification,
                    "peak": future_peak,
                    "trough": None,
                    "months_before": lead,
                }
            )

            continue

        if not has_full_followup(
            start_date,
            latest_date,
            months=months,
        ):
            classified.append(
                {
                    **event,
                    "classification": "pending",
                    "peak": None,
                    "trough": None,
                    "months_before": None,
                }
            )

            continue

        classified.append(
            {
                **event,
                "classification": "false_alarm",
                "peak": None,
                "trough": None,
                "months_before": None,
            }
        )

    return classified


def calculate_model_metrics(
    results,
    threshold,
    months=12,
):
    classified = classify_prediction_events(
        results,
        threshold,
        months=months,
    )

    hits = [
        event
        for event in classified
        if event["classification"] == "hit"
    ]

    false_alarms = [
        event
        for event in classified
        if event["classification"]
        == "false_alarm"
    ]

    duplicates = [
        event
        for event in classified
        if event["classification"]
        == "duplicate"
    ]

    recession_events = [
        event
        for event in classified
        if event["classification"]
        == "recession"
    ]

    same_month_events = [
        event
        for event in classified
        if event["classification"]
        == "same_month"
    ]

    pending_events = [
        event
        for event in classified
        if event["classification"]
        == "pending"
    ]

    peak_stats = calculate_peak_detection(
        results,
        threshold,
        months=months,
    )

    true_positive = len(hits)
    false_positive = len(false_alarms)
    false_negative = len(
        peak_stats["missed_peaks"]
    )

    precision = (
        true_positive
        / (
            true_positive
            + false_positive
        )
        if (
            true_positive
            + false_positive
        )
        else 0
    )

    recall = (
        true_positive
        / (
            true_positive
            + false_negative
        )
        if (
            true_positive
            + false_negative
        )
        else 0
    )

    f1 = (
        2
        * precision
        * recall
        / (
            precision
            + recall
        )
        if (
            precision
            + recall
        )
        else 0
    )

    lead_times = [
        event["months_before"]
        for event in hits
    ]

    return {
        "hits": hits,
        "false_alarms": false_alarms,
        "duplicates": duplicates,
        "recession_events": recession_events,
        "same_month_events": same_month_events,
        "pending_events": pending_events,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "average_lead": (
            mean(lead_times)
            if lead_times
            else 0
        ),
        "median_lead": (
            median(lead_times)
            if lead_times
            else 0
        ),
    }


def print_recent_results(results):
    print()
    print("===== 直近12か月 =====")

    for result in results[-12:]:

        print(
            f"{result['date']} "
            f"CI={result['value']} "
            f"3M={result['three_month_change']:+.2f}% "
            f"6M={result['six_month_change']:+.2f}% "
            f"減速="
            f"{result['momentum_deceleration']:+.2f}% "
            f"高値乖離="
            f"{result['recent_high_drawdown']:+.2f}% "
            f"平均乖離="
            f"{result['moving_average_gap']:+.2f}% "
            f"減速スコア="
            f"{result['slowdown_score']} "
            f"{result['warning_level']}"
        )


def print_peak_detection_analysis(results):
    print()
    print(
        "===== 景気の山 事前検知率 ====="
    )

    for threshold in WARNING_THRESHOLDS:

        stats = calculate_peak_detection(
            results,
            threshold,
            months=12,
        )

        print()
        print(
            f"【{threshold}以上】"
        )

        print(
            f"検知率: "
            f"{len(stats['detected_peaks'])}/"
            f"{len(stats['evaluated_peaks'])} "
            f"({stats['detection_rate']:.1f}%)"
        )

        print(
            f"平均先行期間: "
            f"{stats['average_lead']:.2f}か月"
        )

        print(
            f"中央値: "
            f"{stats['median_lead']:.1f}か月"
        )

        if stats["detected_peaks"]:
            print("検知した山:")

            for item in stats["detected_peaks"]:
                print(
                    f"  山 {item['peak']} "
                    f"← {item['warning_date']} "
                    f"({item['months_before']}か月前, "
                    f"{item['warning_level']})"
                )

        if stats["missed_peaks"]:
            print(
                "見逃した山: "
                + ", ".join(
                    stats["missed_peaks"]
                )
            )


def print_model_metrics(results):
    print()
    print(
        "===== 新モデル 予測精度 ====="
    )

    for threshold in WARNING_THRESHOLDS:

        stats = calculate_model_metrics(
            results,
            threshold,
            months=12,
        )

        print()
        print(
            f"【{threshold}以上】"
        )

        print(
            f"True Positive: "
            f"{stats['true_positive']}"
        )

        print(
            f"False Positive: "
            f"{stats['false_positive']}"
        )

        print(
            f"False Negative: "
            f"{stats['false_negative']}"
        )

        print(
            f"Precision: "
            f"{stats['precision'] * 100:.1f}%"
        )

        print(
            f"Recall: "
            f"{stats['recall'] * 100:.1f}%"
        )

        print(
            f"F1 Score: "
            f"{stats['f1']:.3f}"
        )

        print(
            f"平均先行期間: "
            f"{stats['average_lead']:.2f}か月"
        )

        print(
            f"空振り: "
            f"{len(stats['false_alarms'])}"
        )


def print_2000_analysis(results):
    print()
    print(
        "===== 2000-11 再検証 ====="
    )

    peak = "2000-11"
    peak_number = month_number(peak)

    for result in results:

        months_before = (
            peak_number
            - month_number(result["date"])
        )

        if not (
            0 <= months_before <= 12
        ):
            continue

        if months_before == 0:
            timing = "山当月"
        else:
            timing = (
                f"{months_before}か月前"
            )

        print(
            f"{result['date']} "
            f"({timing}) "
            f"CI={result['value']} "
            f"3M="
            f"{result['three_month_change']:+.2f}% "
            f"6M="
            f"{result['six_month_change']:+.2f}% "
            f"減速="
            f"{result['momentum_deceleration']:+.2f}% "
            f"高値乖離="
            f"{result['recent_high_drawdown']:+.2f}% "
            f"平均乖離="
            f"{result['moving_average_gap']:+.2f}% "
            f"スコア="
            f"{result['slowdown_score']} "
            f"{result['warning_level']}"
        )


def main():
    results = run_backtest()

    if not results:
        print(
            "バックテストデータがありません"
        )
        return

    print(
        "===== 景気先行警戒 "
        "減速モデル バックテスト ====="
    )

    print(
        f"判定件数: "
        f"{len(results)}"
    )

    print(
        f"最新月: "
        f"{results[-1]['date']}"
    )

    print_recent_results(results)

    print_peak_detection_analysis(
        results
    )

    print_model_metrics(
        results
    )

    print_2000_analysis(
        results
    )


if __name__ == "__main__":
    main()