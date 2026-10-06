import statistics

from recession_risk_backtest_v2 import (
    OFFICIAL_PEAKS,
    run_backtest,
    month_number,
    is_recession_month,
    find_future_peak,
)


WARNING_RANK = {
    "⚪ 判定不能": -1,
    "🟢 低警戒": 0,
    "🟡 注意": 1,
    "🟠 警戒": 2,
    "🔴 強い警戒": 3,
}


FOLLOW_UP_MONTHS = 3


def safe_mean(values):
    if not values:
        return 0.0

    return statistics.mean(values)


def safe_median(values):
    if not values:
        return 0.0

    return statistics.median(values)


def get_warning_rank(result):
    return WARNING_RANK.get(
        result["leading_warning"],
        -1,
    )


def build_leading_warning_events(
    results,
    minimum_rank=1,
):
    """
    CI先行警戒が最低ランク以上になった
    連続期間を1イベントとしてまとめる。
    """

    events = []
    current = None

    for result in results:
        active = (
            get_warning_rank(result)
            >= minimum_rank
        )

        if active:
            if current is None:
                current = {
                    "start_date": result["date"],
                    "end_date": result["date"],
                    "max_warning_rank": (
                        get_warning_rank(result)
                    ),
                }
                continue

            previous_month = month_number(
                current["end_date"]
            )

            current_month = month_number(
                result["date"]
            )

            if (
                current_month
                - previous_month
                == 1
            ):
                current["end_date"] = (
                    result["date"]
                )

                current[
                    "max_warning_rank"
                ] = max(
                    current[
                        "max_warning_rank"
                    ],
                    get_warning_rank(
                        result
                    ),
                )

            else:
                events.append(current)

                current = {
                    "start_date": result["date"],
                    "end_date": result["date"],
                    "max_warning_rank": (
                        get_warning_rank(result)
                    ),
                }

        elif current is not None:
            events.append(current)
            current = None

    if current is not None:
        events.append(current)

    return events


def classify_warning_events(
    results,
    minimum_rank=1,
    prediction_months=12,
):
    events = build_leading_warning_events(
        results,
        minimum_rank=minimum_rank,
    )

    if not results:
        return []

    latest_date = results[-1]["date"]

    classified = []
    matched_peaks = set()

    for event in events:
        start_date = event[
            "start_date"
        ]

        recession, peak, _trough = (
            is_recession_month(
                start_date
            )
        )

        if recession:
            classification = "recession"

            classified.append(
                {
                    **event,
                    "classification": (
                        classification
                    ),
                    "peak": peak,
                    "months_before": None,
                }
            )

            continue

        if start_date in OFFICIAL_PEAKS:
            classified.append(
                {
                    **event,
                    "classification": (
                        "same_month"
                    ),
                    "peak": start_date,
                    "months_before": 0,
                }
            )

            continue

        (
            future_peak,
            lead,
        ) = find_future_peak(
            start_date,
            min_months=1,
            max_months=prediction_months,
        )

        if future_peak is not None:
            if future_peak in matched_peaks:
                classification = (
                    "duplicate"
                )
            else:
                classification = "hit"

                matched_peaks.add(
                    future_peak
                )

            classified.append(
                {
                    **event,
                    "classification": (
                        classification
                    ),
                    "peak": future_peak,
                    "months_before": lead,
                }
            )

            continue

        if (
            month_number(latest_date)
            - month_number(start_date)
            < prediction_months
        ):
            classified.append(
                {
                    **event,
                    "classification": (
                        "pending"
                    ),
                    "peak": None,
                    "months_before": None,
                }
            )

            continue

        classified.append(
            {
                **event,
                "classification": (
                    "false_alarm"
                ),
                "peak": None,
                "months_before": None,
            }
        )

    return classified


def find_result(
    results,
    date,
):
    for result in results:
        if result["date"] == date:
            return result

    return None


def get_follow_up_results(
    results,
    event,
    follow_up_months=3,
):
    """
    警戒開始月からfollow_up_monthsか月後までを見る。

    hitの場合は景気の山を越えないよう、
    山の前月までに制限する。
    """

    start_number = month_number(
        event["start_date"]
    )

    end_number = (
        start_number
        + follow_up_months
    )

    if (
        event["classification"]
        == "hit"
        and event["peak"]
        is not None
    ):
        peak_number = month_number(
            event["peak"]
        )

        end_number = min(
            end_number,
            peak_number - 1,
        )

    return [
        result
        for result in results
        if (
            start_number
            <= month_number(
                result["date"]
            )
            <= end_number
        )
    ]


def extract_event_features(
    results,
    event,
):
    start = find_result(
        results,
        event["start_date"],
    )

    if start is None:
        return None

    follow_up = get_follow_up_results(
        results,
        event,
        FOLLOW_UP_MONTHS,
    )

    if not follow_up:
        follow_up = [start]

    confirmation_values = [
        item["confirmation_score"]
        for item in follow_up
    ]

    trend_values = [
        item["trend_score"]
        for item in follow_up
    ]

    deteriorated_values = [
        item["deteriorated_count"]
        for item in follow_up
    ]

    severe_values = [
        item["severe_count"]
        for item in follow_up
    ]

    total_values = [
        item["total_score"]
        for item in follow_up
    ]

    available_values = [
        item["available_count"]
        for item in follow_up
    ]

    return {
        "classification": (
            event["classification"]
        ),
        "start_date": (
            event["start_date"]
        ),
        "end_date": event["end_date"],
        "peak": event["peak"],
        "months_before": (
            event["months_before"]
        ),

        "warning_rank": (
            get_warning_rank(start)
        ),
        "leading_score": (
            start["leading_score"]
        ),

        "start_confirmation": (
            start["confirmation_score"]
        ),
        "max_confirmation_3m": max(
            confirmation_values
        ),
        "mean_confirmation_3m": (
            safe_mean(
                confirmation_values
            )
        ),

        "start_trend": (
            start["trend_score"]
        ),
        "worst_trend_3m": min(
            trend_values
        ),
        "mean_trend_3m": safe_mean(
            trend_values
        ),

        "start_deteriorated": (
            start["deteriorated_count"]
        ),
        "max_deteriorated_3m": max(
            deteriorated_values
        ),

        "start_severe": (
            start["severe_count"]
        ),
        "max_severe_3m": max(
            severe_values
        ),

        "start_total": (
            start["total_score"]
        ),
        "max_total_3m": max(
            total_values
        ),

        "available_count": min(
            available_values
        ),

        "coverage": start["coverage"],
    }


def summarize_features(
    rows,
):
    if not rows:
        return None

    keys = [
        "start_confirmation",
        "max_confirmation_3m",
        "mean_confirmation_3m",
        "start_trend",
        "worst_trend_3m",
        "mean_trend_3m",
        "start_deteriorated",
        "max_deteriorated_3m",
        "start_severe",
        "max_severe_3m",
        "start_total",
        "max_total_3m",
        "available_count",
    ]

    summary = {
        "count": len(rows),
    }

    for key in keys:
        values = [
            row[key]
            for row in rows
        ]

        summary[key] = {
            "mean": safe_mean(values),
            "median": safe_median(
                values
            ),
            "min": min(values),
            "max": max(values),
        }

    return summary


def print_stat_line(
    label,
    stat,
):
    print(
        f"{label}: "
        f"平均={stat['mean']:.2f} "
        f"中央値={stat['median']:.2f} "
        f"最小={stat['min']:.2f} "
        f"最大={stat['max']:.2f}"
    )


def print_summary(
    title,
    summary,
):
    print()
    print(
        f"===== {title} ====="
    )

    if summary is None:
        print("対象なし")
        return

    print(
        f"イベント数: "
        f"{summary['count']}"
    )

    print_stat_line(
        "開始時 確認スコア",
        summary[
            "start_confirmation"
        ],
    )

    print_stat_line(
        "3か月内 最大確認スコア",
        summary[
            "max_confirmation_3m"
        ],
    )

    print_stat_line(
        "3か月内 平均確認スコア",
        summary[
            "mean_confirmation_3m"
        ],
    )

    print_stat_line(
        "開始時 トレンド",
        summary[
            "start_trend"
        ],
    )

    print_stat_line(
        "3か月内 最悪トレンド",
        summary[
            "worst_trend_3m"
        ],
    )

    print_stat_line(
        "3か月内 平均トレンド",
        summary[
            "mean_trend_3m"
        ],
    )

    print_stat_line(
        "開始時 40点以上指標数",
        summary[
            "start_deteriorated"
        ],
    )

    print_stat_line(
        "3か月内 最大40点以上指標数",
        summary[
            "max_deteriorated_3m"
        ],
    )

    print_stat_line(
        "開始時 60点以上指標数",
        summary[
            "start_severe"
        ],
    )

    print_stat_line(
        "3か月内 最大60点以上指標数",
        summary[
            "max_severe_3m"
        ],
    )

    print_stat_line(
        "開始時 総合スコア",
        summary[
            "start_total"
        ],
    )

    print_stat_line(
        "3か月内 最大総合スコア",
        summary[
            "max_total_3m"
        ],
    )

    print_stat_line(
        "利用可能確認指標数",
        summary[
            "available_count"
        ],
    )


def print_difference(
    hit_summary,
    false_summary,
):
    print()
    print(
        "===== 本物 - 空振り 差 ====="
    )

    if (
        hit_summary is None
        or false_summary is None
    ):
        print("比較対象不足")
        return

    labels = [
        (
            "開始時 確認スコア",
            "start_confirmation",
        ),
        (
            "3か月内 最大確認スコア",
            "max_confirmation_3m",
        ),
        (
            "3か月内 平均確認スコア",
            "mean_confirmation_3m",
        ),
        (
            "開始時 トレンド",
            "start_trend",
        ),
        (
            "3か月内 最悪トレンド",
            "worst_trend_3m",
        ),
        (
            "開始時 40点以上指標数",
            "start_deteriorated",
        ),
        (
            "3か月内 最大40点以上指標数",
            "max_deteriorated_3m",
        ),
        (
            "開始時 60点以上指標数",
            "start_severe",
        ),
        (
            "3か月内 最大60点以上指標数",
            "max_severe_3m",
        ),
        (
            "開始時 総合スコア",
            "start_total",
        ),
        (
            "3か月内 最大総合スコア",
            "max_total_3m",
        ),
    ]

    for label, key in labels:
        difference = (
            hit_summary[key]["mean"]
            - false_summary[key][
                "mean"
            ]
        )

        print(
            f"{label}: "
            f"{difference:+.2f}"
        )


def print_event_list(
    title,
    rows,
):
    print()
    print(
        f"===== {title} ====="
    )

    if not rows:
        print("対象なし")
        return

    for row in rows:
        peak_text = (
            row["peak"]
            if row["peak"]
            else "-"
        )

        lead_text = (
            f"{row['months_before']}か月前"
            if (
                row[
                    "months_before"
                ]
                is not None
            )
            else "-"
        )

        print(
            f"{row['start_date']} "
            f"先行={row['leading_score']:3d} "
            f"確認開始="
            f"{row['start_confirmation']:5.2f} "
            f"確認3M最大="
            f"{row['max_confirmation_3m']:5.2f} "
            f"トレンド3M最悪="
            f"{row['worst_trend_3m']:+6.2f} "
            f"悪化3M最大="
            f"{row['max_deteriorated_3m']} "
            f"重度3M最大="
            f"{row['max_severe_3m']} "
            f"確認数="
            f"{row['available_count']}/7 "
            f"山={peak_text} "
            f"{lead_text}"
        )


def rule_confirmation_score(
    row,
    threshold,
):
    return (
        row[
            "max_confirmation_3m"
        ]
        >= threshold
    )


def rule_deteriorated(
    row,
    count,
):
    return (
        row[
            "max_deteriorated_3m"
        ]
        >= count
    )


def rule_severe(
    row,
    count,
):
    return (
        row[
            "max_severe_3m"
        ]
        >= count
    )


def rule_trend(
    row,
    threshold,
):
    return (
        row[
            "worst_trend_3m"
        ]
        <= threshold
    )


def evaluate_rule(
    hits,
    false_alarms,
    rule_function,
):
    tp = sum(
        rule_function(row)
        for row in hits
    )

    fp = sum(
        rule_function(row)
        for row in false_alarms
    )

    fn = (
        len(hits)
        - tp
    )

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
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

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def print_rule_result(
    label,
    stats,
):
    print(
        f"{label:<34} "
        f"P="
        f"{stats['precision'] * 100:5.1f}% "
        f"R="
        f"{stats['recall'] * 100:5.1f}% "
        f"F1="
        f"{stats['f1']:.3f} "
        f"TP={stats['tp']} "
        f"FP={stats['fp']} "
        f"FN={stats['fn']}"
    )


def search_single_rules(
    hits,
    false_alarms,
):
    print()
    print(
        "===== 単独確認ルール比較 ====="
    )

    best = None

    for threshold in range(
        5,
        51,
        5,
    ):
        stats = evaluate_rule(
            hits,
            false_alarms,
            lambda row, t=threshold: (
                rule_confirmation_score(
                    row,
                    t,
                )
            ),
        )

        label = (
            f"確認スコア >= {threshold}"
        )

        print_rule_result(
            label,
            stats,
        )

        candidate = {
            "label": label,
            **stats,
        }

        if (
            best is None
            or candidate["f1"]
            > best["f1"]
        ):
            best = candidate

    for count in range(
        1,
        5,
    ):
        stats = evaluate_rule(
            hits,
            false_alarms,
            lambda row, c=count: (
                rule_deteriorated(
                    row,
                    c,
                )
            ),
        )

        label = (
            f"40点以上指標 >= {count}"
        )

        print_rule_result(
            label,
            stats,
        )

        candidate = {
            "label": label,
            **stats,
        }

        if (
            best is None
            or candidate["f1"]
            > best["f1"]
        ):
            best = candidate

    for count in range(
        1,
        4,
    ):
        stats = evaluate_rule(
            hits,
            false_alarms,
            lambda row, c=count: (
                rule_severe(
                    row,
                    c,
                )
            ),
        )

        label = (
            f"60点以上指標 >= {count}"
        )

        print_rule_result(
            label,
            stats,
        )

        candidate = {
            "label": label,
            **stats,
        }

        if (
            best is None
            or candidate["f1"]
            > best["f1"]
        ):
            best = candidate

    for threshold in [
        0,
        -20,
        -40,
        -60,
    ]:
        stats = evaluate_rule(
            hits,
            false_alarms,
            lambda row, t=threshold: (
                rule_trend(
                    row,
                    t,
                )
            ),
        )

        label = (
            f"トレンド <= {threshold}"
        )

        print_rule_result(
            label,
            stats,
        )

        candidate = {
            "label": label,
            **stats,
        }

        if (
            best is None
            or candidate["f1"]
            > best["f1"]
        ):
            best = candidate

    if best is not None:
        print()
        print(
            "単独ルール F1最大:"
        )

        print_rule_result(
            best["label"],
            best,
        )


def search_combined_rules(
    hits,
    false_alarms,
):
    print()
    print(
        "===== 複合確認ルール探索 ====="
    )

    candidates = []

    confirmation_thresholds = [
        10,
        15,
        20,
        25,
        30,
        35,
        40,
    ]

    deteriorated_counts = [
        1,
        2,
        3,
    ]

    trend_thresholds = [
        0,
        -20,
        -40,
    ]

    for confirmation in (
        confirmation_thresholds
    ):
        for deteriorated in (
            deteriorated_counts
        ):
            stats = evaluate_rule(
                hits,
                false_alarms,
                lambda row,
                c=confirmation,
                d=deteriorated: (
                    rule_confirmation_score(
                        row,
                        c,
                    )
                    and rule_deteriorated(
                        row,
                        d,
                    )
                ),
            )

            candidates.append(
                {
                    "label": (
                        f"確認>={confirmation} "
                        f"AND 悪化数>={deteriorated}"
                    ),
                    **stats,
                }
            )

    for confirmation in (
        confirmation_thresholds
    ):
        for trend in (
            trend_thresholds
        ):
            stats = evaluate_rule(
                hits,
                false_alarms,
                lambda row,
                c=confirmation,
                t=trend: (
                    rule_confirmation_score(
                        row,
                        c,
                    )
                    and rule_trend(
                        row,
                        t,
                    )
                ),
            )

            candidates.append(
                {
                    "label": (
                        f"確認>={confirmation} "
                        f"AND トレンド<={trend}"
                    ),
                    **stats,
                }
            )

    for deteriorated in (
        deteriorated_counts
    ):
        for trend in (
            trend_thresholds
        ):
            stats = evaluate_rule(
                hits,
                false_alarms,
                lambda row,
                d=deteriorated,
                t=trend: (
                    rule_deteriorated(
                        row,
                        d,
                    )
                    and rule_trend(
                        row,
                        t,
                    )
                ),
            )

            candidates.append(
                {
                    "label": (
                        f"悪化数>={deteriorated} "
                        f"AND トレンド<={trend}"
                    ),
                    **stats,
                }
            )

    candidates.sort(
        key=lambda item: (
            item["f1"],
            item["recall"],
            item["precision"],
            -item["fp"],
        ),
        reverse=True,
    )

    print(
        "上位15ルール:"
    )

    for candidate in candidates[:15]:
        print_rule_result(
            candidate["label"],
            candidate,
        )


def analyze_by_coverage(
    rows,
):
    print()
    print(
        "===== カバレッジ別 ====="
    )

    groups = [
        (
            "低 1～2指標",
            1,
            2,
        ),
        (
            "中 3～4指標",
            3,
            4,
        ),
        (
            "高 5～7指標",
            5,
            7,
        ),
    ]

    for (
        label,
        minimum,
        maximum,
    ) in groups:
        group = [
            row
            for row in rows
            if (
                minimum
                <= row[
                    "available_count"
                ]
                <= maximum
            )
        ]

        hits = [
            row
            for row in group
            if (
                row[
                    "classification"
                ]
                == "hit"
            )
        ]

        false_alarms = [
            row
            for row in group
            if (
                row[
                    "classification"
                ]
                == "false_alarm"
            )
        ]

        print()
        print(
            f"【{label}】"
        )

        print(
            f"本物={len(hits)} "
            f"空振り="
            f"{len(false_alarms)}"
        )

        if (
            hits
            and false_alarms
        ):
            print(
                "本物 3M最大確認: "
                f"{safe_mean([
                    row['max_confirmation_3m']
                    for row in hits
                ]):.2f}"
            )

            print(
                "空振り 3M最大確認: "
                f"{safe_mean([
                    row['max_confirmation_3m']
                    for row in false_alarms
                ]):.2f}"
            )

            print(
                "本物 3M最大悪化数: "
                f"{safe_mean([
                    row['max_deteriorated_3m']
                    for row in hits
                ]):.2f}"
            )

            print(
                "空振り 3M最大悪化数: "
                f"{safe_mean([
                    row['max_deteriorated_3m']
                    for row in false_alarms
                ]):.2f}"
            )


def main():
    results = run_backtest()

    events = classify_warning_events(
        results,
        minimum_rank=1,
        prediction_months=12,
    )

    feature_rows = []

    for event in events:
        features = extract_event_features(
            results,
            event,
        )

        if features is not None:
            feature_rows.append(
                features
            )

    hits = [
        row
        for row in feature_rows
        if (
            row["classification"]
            == "hit"
        )
    ]

    false_alarms = [
        row
        for row in feature_rows
        if (
            row["classification"]
            == "false_alarm"
        )
    ]

    duplicates = [
        row
        for row in feature_rows
        if (
            row["classification"]
            == "duplicate"
        )
    ]

    recession_events = [
        row
        for row in feature_rows
        if (
            row["classification"]
            == "recession"
        )
    ]

    pending = [
        row
        for row in feature_rows
        if (
            row["classification"]
            == "pending"
        )
    ]

    print(
        "===== 景気後退確認指標 "
        "オプティマイザー ====="
    )

    print()
    print(
        "対象: CI先行警戒 "
        "🟡以上のイベント"
    )

    print(
        "確認期間: "
        f"警戒開始から{FOLLOW_UP_MONTHS}か月"
    )

    print(
        "hitの場合は景気の山を"
        "越えない範囲のみ使用"
    )

    print()
    print(
        f"本物の事前警戒: "
        f"{len(hits)}"
    )

    print(
        f"空振り: "
        f"{len(false_alarms)}"
    )

    print(
        f"重複警戒: "
        f"{len(duplicates)}"
    )

    print(
        f"景気後退中: "
        f"{len(recession_events)}"
    )

    print(
        f"判定保留: "
        f"{len(pending)}"
    )

    hit_summary = summarize_features(
        hits
    )

    false_summary = summarize_features(
        false_alarms
    )

    print_summary(
        "本物の事前警戒",
        hit_summary,
    )

    print_summary(
        "空振り",
        false_summary,
    )

    print_difference(
        hit_summary,
        false_summary,
    )

    print_event_list(
        "本物の事前警戒一覧",
        hits,
    )

    print_event_list(
        "空振り一覧",
        false_alarms,
    )

    analyze_by_coverage(
        feature_rows
    )

    search_single_rules(
        hits,
        false_alarms,
    )

    search_combined_rules(
        hits,
        false_alarms,
    )


if __name__ == "__main__":
    main()
