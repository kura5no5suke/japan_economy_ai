from statistics import mean, median

from leading_warning_backtest import (
    run_backtest,
    classify_prediction_events,
    WARNING_THRESHOLDS,
)


def safe_mean(values):
    values = [
        value
        for value in values
        if value is not None
    ]

    if not values:
        return None

    return mean(values)


def safe_median(values):
    values = [
        value
        for value in values
        if value is not None
    ]

    if not values:
        return None

    return median(values)


def find_result_by_date(results, date):
    for result in results:
        if result["date"] == date:
            return result

    return None


def extract_event_features(
    results,
    events,
):
    extracted = []

    for event in events:
        result = find_result_by_date(
            results,
            event["start_date"],
        )

        if result is None:
            continue

        extracted.append(
            {
                "start_date": event["start_date"],
                "end_date": event["end_date"],
                "classification": (
                    event["classification"]
                ),
                "peak": event.get("peak"),
                "months_before": (
                    event.get("months_before")
                ),
                "warning_level": (
                    result["warning_level"]
                ),
                "direction_score": (
                    result["direction_score"]
                ),
                "direction_label": (
                    result["direction_label"]
                ),
                "consecutive_declines": (
                    result[
                        "consecutive_declines"
                    ]
                ),
                "three_month_change": (
                    result[
                        "three_month_change"
                    ]
                ),
                "six_month_change": (
                    result[
                        "six_month_change"
                    ]
                ),
                "momentum_deceleration": (
                    result[
                        "momentum_deceleration"
                    ]
                ),
                "recent_high_drawdown": (
                    result[
                        "recent_high_drawdown"
                    ]
                ),
                "moving_average_gap": (
                    result[
                        "moving_average_gap"
                    ]
                ),
                "slowdown_score": (
                    result[
                        "slowdown_score"
                    ]
                ),
            }
        )

    return extracted


def summarize_features(events):
    if not events:
        return None

    return {
        "count": len(events),

        "direction_score_mean": safe_mean(
            [
                event["direction_score"]
                for event in events
            ]
        ),

        "consecutive_declines_mean": safe_mean(
            [
                event["consecutive_declines"]
                for event in events
            ]
        ),

        "three_month_change_mean": safe_mean(
            [
                event["three_month_change"]
                for event in events
            ]
        ),

        "three_month_change_median": safe_median(
            [
                event["three_month_change"]
                for event in events
            ]
        ),

        "six_month_change_mean": safe_mean(
            [
                event["six_month_change"]
                for event in events
            ]
        ),

        "six_month_change_median": safe_median(
            [
                event["six_month_change"]
                for event in events
            ]
        ),

        "momentum_deceleration_mean": safe_mean(
            [
                event[
                    "momentum_deceleration"
                ]
                for event in events
            ]
        ),

        "momentum_deceleration_median": (
            safe_median(
                [
                    event[
                        "momentum_deceleration"
                    ]
                    for event in events
                ]
            )
        ),

        "recent_high_drawdown_mean": safe_mean(
            [
                event[
                    "recent_high_drawdown"
                ]
                for event in events
            ]
        ),

        "moving_average_gap_mean": safe_mean(
            [
                event[
                    "moving_average_gap"
                ]
                for event in events
            ]
        ),

        "slowdown_score_mean": safe_mean(
            [
                event["slowdown_score"]
                for event in events
            ]
        ),

        "slowdown_score_median": safe_median(
            [
                event["slowdown_score"]
                for event in events
            ]
        ),
    }


def format_number(
    value,
    decimals=2,
):
    if value is None:
        return "N/A"

    return f"{value:.{decimals}f}"


def print_summary(
    title,
    summary,
):
    print()
    print(title)

    if summary is None:
        print("データなし")
        return

    print(
        f"件数: "
        f"{summary['count']}"
    )

    print(
        "平均方向スコア: "
        + format_number(
            summary[
                "direction_score_mean"
            ]
        )
    )

    print(
        "平均連続低下回数: "
        + format_number(
            summary[
                "consecutive_declines_mean"
            ]
        )
    )

    print(
        "3か月変化率 平均: "
        + format_number(
            summary[
                "three_month_change_mean"
            ]
        )
        + "%"
    )

    print(
        "3か月変化率 中央値: "
        + format_number(
            summary[
                "three_month_change_median"
            ]
        )
        + "%"
    )

    print(
        "6か月変化率 平均: "
        + format_number(
            summary[
                "six_month_change_mean"
            ]
        )
        + "%"
    )

    print(
        "6か月変化率 中央値: "
        + format_number(
            summary[
                "six_month_change_median"
            ]
        )
        + "%"
    )

    print(
        "モメンタム減速 平均: "
        + format_number(
            summary[
                "momentum_deceleration_mean"
            ]
        )
        + "%"
    )

    print(
        "モメンタム減速 中央値: "
        + format_number(
            summary[
                "momentum_deceleration_median"
            ]
        )
        + "%"
    )

    print(
        "高値乖離 平均: "
        + format_number(
            summary[
                "recent_high_drawdown_mean"
            ]
        )
        + "%"
    )

    print(
        "6か月平均との差 平均: "
        + format_number(
            summary[
                "moving_average_gap_mean"
            ]
        )
        + "%"
    )

    print(
        "減速スコア 平均: "
        + format_number(
            summary[
                "slowdown_score_mean"
            ]
        )
    )

    print(
        "減速スコア 中央値: "
        + format_number(
            summary[
                "slowdown_score_median"
            ]
        )
    )


def print_difference(
    hit_summary,
    false_summary,
):
    print()
    print(
        "===== 的中 vs 空振り 差分 ====="
    )

    if (
        hit_summary is None
        or false_summary is None
    ):
        print(
            "比較データが不足しています"
        )
        return

    comparisons = [
        (
            "3か月変化率",
            "three_month_change_mean",
        ),
        (
            "6か月変化率",
            "six_month_change_mean",
        ),
        (
            "モメンタム減速",
            "momentum_deceleration_mean",
        ),
        (
            "高値乖離",
            "recent_high_drawdown_mean",
        ),
        (
            "6か月平均との差",
            "moving_average_gap_mean",
        ),
        (
            "減速スコア",
            "slowdown_score_mean",
        ),
        (
            "連続低下回数",
            "consecutive_declines_mean",
        ),
    ]

    for label, key in comparisons:
        hit_value = hit_summary[key]
        false_value = false_summary[key]

        if (
            hit_value is None
            or false_value is None
        ):
            continue

        difference = (
            hit_value
            - false_value
        )

        print(
            f"{label}: "
            f"的中={hit_value:.2f} "
            f"空振り={false_value:.2f} "
            f"差={difference:+.2f}"
        )


def print_event_list(
    title,
    events,
):
    print()
    print(title)

    if not events:
        print("なし")
        return

    for event in events:
        peak_text = ""

        if event["peak"] is not None:
            peak_text = (
                f" → 山 {event['peak']}"
            )

        lead_text = ""

        if event["months_before"] is not None:
            lead_text = (
                f" "
                f"({event['months_before']}"
                f"か月前)"
            )

        print(
            f"{event['start_date']} "
            f"{event['warning_level']} "
            f"3M="
            f"{event['three_month_change']:+.2f}% "
            f"6M="
            f"{event['six_month_change']:+.2f}% "
            f"減速="
            f"{event['momentum_deceleration']:+.2f}% "
            f"高値乖離="
            f"{event['recent_high_drawdown']:+.2f}% "
            f"平均乖離="
            f"{event['moving_average_gap']:+.2f}% "
            f"スコア="
            f"{event['slowdown_score']}"
            f"{peak_text}"
            f"{lead_text}"
        )


def analyze_threshold(
    results,
    threshold,
):
    classified = (
        classify_prediction_events(
            results,
            threshold,
            months=12,
        )
    )

    hit_events = [
        event
        for event in classified
        if event["classification"]
        == "hit"
    ]

    false_events = [
        event
        for event in classified
        if event["classification"]
        == "false_alarm"
    ]

    hit_features = extract_event_features(
        results,
        hit_events,
    )

    false_features = (
        extract_event_features(
            results,
            false_events,
        )
    )

    hit_summary = summarize_features(
        hit_features
    )

    false_summary = summarize_features(
        false_features
    )

    print()
    print(
        "========================================"
    )

    print(
        f"【{threshold}以上】"
    )

    print(
        "========================================"
    )

    print_summary(
        "===== 的中イベント =====",
        hit_summary,
    )

    print_summary(
        "===== 空振りイベント =====",
        false_summary,
    )

    print_difference(
        hit_summary,
        false_summary,
    )

    print_event_list(
        "===== 的中イベント詳細 =====",
        hit_features,
    )

    print_event_list(
        "===== 空振りイベント詳細 =====",
        false_features,
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
        "特徴量比較 ====="
    )

    print(
        f"分析期間: "
        f"{results[0]['date']} "
        f"～ "
        f"{results[-1]['date']}"
    )

    print(
        f"月数: "
        f"{len(results)}"
    )

    for threshold in WARNING_THRESHOLDS:
        analyze_threshold(
            results,
            threshold,
        )


if __name__ == "__main__":
    main()