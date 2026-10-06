import statistics

from recession_signal_backtest import (
    OFFICIAL_PEAKS,
    OFFICIAL_TROUGHS,
    run_backtest,
    month_number,
)


# ============================================================
# 基本設定
# ============================================================

PREDICTION_MONTHS = 12

LEADING_RANK = {
    "⚪ 判定不能": -1,
    "🟢 低警戒": 0,
    "🟡 注意": 1,
    "🟠 警戒": 2,
    "🔴 強い警戒": 3,
}


REPRESENTATIVE_FALSE_PERIODS = [
    ("2014", "2014-01", "2014-12"),
    ("2015-2016", "2015-01", "2016-12"),
    ("2021-2022", "2021-01", "2022-12"),
    ("2022-2023", "2022-01", "2023-12"),
    ("2024", "2024-01", "2024-12"),
    ("2025", "2025-01", "2025-12"),
]


# ============================================================
# 共通
# ============================================================

def leading_rank(result):
    return LEADING_RANK.get(
        result["leading_warning"],
        -1,
    )


def coverage_label(count):
    if count >= 5:
        return "高"

    if count >= 3:
        return "中"

    if count >= 1:
        return "低"

    return "なし"


def is_recession_month(date_string):
    target = month_number(
        date_string
    )

    for peak, trough in zip(
        OFFICIAL_PEAKS,
        OFFICIAL_TROUGHS,
    ):
        if (
            month_number(peak)
            < target
            <= month_number(trough)
        ):
            return True, peak, trough

    return False, None, None


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
                (difference, peak)
            )

    if not candidates:
        return None, None

    difference, peak = min(
        candidates,
        key=lambda item: item[0],
    )

    return peak, difference


def get_peak_window(
    results,
    peak,
    months=12,
):
    return [
        result
        for result in results
        if (
            1
            <= (
                month_number(peak)
                - month_number(
                    result["date"]
                )
            )
            <= months
        )
    ]


def safe_mean(values):
    if not values:
        return 0.0

    return statistics.mean(values)


def safe_median(values):
    if not values:
        return 0.0

    return statistics.median(values)


# ============================================================
# 先行警戒だけの基準
# ============================================================

def leading_rule(
    result,
    minimum_rank=1,
):
    return (
        leading_rank(result)
        >= minimum_rank
    )


# ============================================================
# 確認ルール候補
#
# 重要:
# 「確認済み」と呼ぶルールは
# 必ず実際の悪化指標数を条件に含める。
# トレンドだけで「複数悪化」にしない。
# ============================================================

def rule_leading_and_deteriorated(
    result,
    minimum_leading,
    minimum_deteriorated,
):
    return (
        leading_rank(result)
        >= minimum_leading
        and result[
            "deteriorated_count"
        ]
        >= minimum_deteriorated
    )


def rule_leading_deteriorated_score(
    result,
    minimum_leading,
    minimum_deteriorated,
    minimum_confirmation,
):
    return (
        leading_rank(result)
        >= minimum_leading
        and result[
            "deteriorated_count"
        ]
        >= minimum_deteriorated
        and result[
            "confirmation_score"
        ]
        >= minimum_confirmation
    )


def rule_leading_deteriorated_trend(
    result,
    minimum_leading,
    minimum_deteriorated,
    maximum_trend,
):
    return (
        leading_rank(result)
        >= minimum_leading
        and result[
            "deteriorated_count"
        ]
        >= minimum_deteriorated
        and result[
            "trend_score"
        ]
        <= maximum_trend
    )


def rule_leading_and_severe(
    result,
    minimum_leading,
    minimum_severe,
):
    return (
        leading_rank(result)
        >= minimum_leading
        and result[
            "severe_count"
        ]
        >= minimum_severe
    )


def rule_balanced_confirmed(
    result,
):
    """
    意味を優先した複合候補。

    1) CIが🔴で、実際に1指標以上悪化
    2) CIが🟠以上で、実際に2指標以上悪化
    3) CIが🟡以上で、2指標以上悪化かつ確認スコア20以上

    のどれかを満たしたら「確認済み高リスク」候補。
    """

    rank = leading_rank(result)

    deteriorated = result[
        "deteriorated_count"
    ]

    confirmation = result[
        "confirmation_score"
    ]

    return (
        (
            rank >= 3
            and deteriorated >= 1
        )
        or (
            rank >= 2
            and deteriorated >= 2
        )
        or (
            rank >= 1
            and deteriorated >= 2
            and confirmation >= 20
        )
    )


# ============================================================
# 連続イベント化
# ============================================================

def build_events(
    results,
    rule_function,
    minimum_coverage=1,
):
    events = []
    current = None

    for result in results:
        usable = (
            result[
                "available_count"
            ]
            >= minimum_coverage
        )

        active = (
            usable
            and rule_function(result)
        )

        if active:
            if current is None:
                current = {
                    "start_date": (
                        result["date"]
                    ),
                    "end_date": (
                        result["date"]
                    ),
                    "max_leading_rank": (
                        leading_rank(result)
                    ),
                    "max_confirmation": (
                        result[
                            "confirmation_score"
                        ]
                    ),
                    "max_deteriorated": (
                        result[
                            "deteriorated_count"
                        ]
                    ),
                    "max_severe": (
                        result[
                            "severe_count"
                        ]
                    ),
                    "worst_trend": (
                        result[
                            "trend_score"
                        ]
                    ),
                    "max_available": (
                        result[
                            "available_count"
                        ]
                    ),
                }

                continue

            previous_month = (
                month_number(
                    current[
                        "end_date"
                    ]
                )
            )

            current_month = (
                month_number(
                    result["date"]
                )
            )

            if (
                current_month
                - previous_month
                == 1
            ):
                current[
                    "end_date"
                ] = result["date"]

                current[
                    "max_leading_rank"
                ] = max(
                    current[
                        "max_leading_rank"
                    ],
                    leading_rank(result),
                )

                current[
                    "max_confirmation"
                ] = max(
                    current[
                        "max_confirmation"
                    ],
                    result[
                        "confirmation_score"
                    ],
                )

                current[
                    "max_deteriorated"
                ] = max(
                    current[
                        "max_deteriorated"
                    ],
                    result[
                        "deteriorated_count"
                    ],
                )

                current[
                    "max_severe"
                ] = max(
                    current[
                        "max_severe"
                    ],
                    result[
                        "severe_count"
                    ],
                )

                current[
                    "worst_trend"
                ] = min(
                    current[
                        "worst_trend"
                    ],
                    result[
                        "trend_score"
                    ],
                )

                current[
                    "max_available"
                ] = max(
                    current[
                        "max_available"
                    ],
                    result[
                        "available_count"
                    ],
                )

            else:
                events.append(current)

                current = {
                    "start_date": (
                        result["date"]
                    ),
                    "end_date": (
                        result["date"]
                    ),
                    "max_leading_rank": (
                        leading_rank(result)
                    ),
                    "max_confirmation": (
                        result[
                            "confirmation_score"
                        ]
                    ),
                    "max_deteriorated": (
                        result[
                            "deteriorated_count"
                        ]
                    ),
                    "max_severe": (
                        result[
                            "severe_count"
                        ]
                    ),
                    "worst_trend": (
                        result[
                            "trend_score"
                        ]
                    ),
                    "max_available": (
                        result[
                            "available_count"
                        ]
                    ),
                }

        elif current is not None:
            events.append(current)
            current = None

    if current is not None:
        events.append(current)

    return events


def classify_events(
    results,
    rule_function,
    minimum_coverage=1,
):
    events = build_events(
        results,
        rule_function,
        minimum_coverage=minimum_coverage,
    )

    usable_results = [
        result
        for result in results
        if (
            result[
                "available_count"
            ]
            >= minimum_coverage
        )
    ]

    if not usable_results:
        return []

    latest_date = usable_results[
        -1
    ]["date"]

    classified = []
    matched_peaks = set()

    for event in events:
        start_date = event[
            "start_date"
        ]

        (
            recession,
            peak,
            _trough,
        ) = is_recession_month(
            start_date
        )

        if recession:
            classified.append(
                {
                    **event,
                    "classification": (
                        "recession"
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
            max_months=PREDICTION_MONTHS,
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
            < PREDICTION_MONTHS
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


# ============================================================
# 評価
# ============================================================

def evaluable_peaks(
    results,
    minimum_coverage,
):
    peaks = []

    for peak in OFFICIAL_PEAKS:
        rows = get_peak_window(
            results,
            peak,
            months=PREDICTION_MONTHS,
        )

        usable = [
            row
            for row in rows
            if (
                row[
                    "available_count"
                ]
                >= minimum_coverage
            )
        ]

        if usable:
            peaks.append(peak)

    return peaks


def evaluate_rule(
    results,
    rule_function,
    minimum_coverage=1,
):
    events = classify_events(
        results,
        rule_function,
        minimum_coverage=minimum_coverage,
    )

    hits = [
        event
        for event in events
        if (
            event[
                "classification"
            ]
            == "hit"
        )
    ]

    false_alarms = [
        event
        for event in events
        if (
            event[
                "classification"
            ]
            == "false_alarm"
        )
    ]

    detected_peaks = {
        event["peak"]
        for event in hits
    }

    peaks = evaluable_peaks(
        results,
        minimum_coverage,
    )

    missed_peaks = [
        peak
        for peak in peaks
        if peak not in detected_peaks
    ]

    tp = len(hits)
    fp = len(false_alarms)
    fn = len(missed_peaks)

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

    lead_times = [
        event["months_before"]
        for event in hits
        if (
            event[
                "months_before"
            ]
            is not None
        )
    ]

    return {
        "events": events,
        "hits": hits,
        "false_alarms": (
            false_alarms
        ),
        "missed_peaks": (
            missed_peaks
        ),
        "evaluable_peaks": peaks,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "average_lead": (
            safe_mean(lead_times)
        ),
        "median_lead": (
            safe_median(lead_times)
        ),
    }


def print_rule_result(
    label,
    stats,
):
    print(
        f"{label:<48} "
        f"P="
        f"{stats['precision'] * 100:5.1f}% "
        f"R="
        f"{stats['recall'] * 100:5.1f}% "
        f"F1="
        f"{stats['f1']:.3f} "
        f"TP={stats['tp']} "
        f"FP={stats['fp']} "
        f"FN={stats['fn']} "
        f"先行="
        f"{stats['average_lead']:.2f}M"
    )


# ============================================================
# 先行警戒の確認
# ============================================================

def print_early_warning_baseline(
    results,
):
    print()
    print(
        "===== 先行警戒ベースライン ====="
    )

    for rank, label in [
        (1, "CI 🟡以上"),
        (2, "CI 🟠以上"),
        (3, "CI 🔴"),
    ]:
        stats = evaluate_rule(
            results,
            lambda row, r=rank: (
                leading_rule(
                    row,
                    minimum_rank=r,
                )
            ),
            minimum_coverage=1,
        )

        print_rule_result(
            label,
            stats,
        )


# ============================================================
# 景気の山ごとの生データ
# ============================================================

def print_peak_raw_features(
    results,
):
    print()
    print(
        "===== 景気の山の前12か月 "
        "生データ最高値 ====="
    )

    for peak in OFFICIAL_PEAKS:
        rows = get_peak_window(
            results,
            peak,
            months=PREDICTION_MONTHS,
        )

        if not rows:
            print(
                f"{peak}: "
                "評価可能データ不足"
            )
            continue

        max_deteriorated = max(
            row[
                "deteriorated_count"
            ]
            for row in rows
        )

        max_severe = max(
            row[
                "severe_count"
            ]
            for row in rows
        )

        max_confirmation = max(
            row[
                "confirmation_score"
            ]
            for row in rows
        )

        worst_trend = min(
            row["trend_score"]
            for row in rows
        )

        max_leading = max(
            leading_rank(row)
            for row in rows
        )

        max_available = max(
            row[
                "available_count"
            ]
            for row in rows
        )

        print(
            f"{peak}: "
            f"先行最大={max_leading} "
            f"確認最大={max_confirmation:.2f} "
            f"40点以上最大={max_deteriorated} "
            f"60点以上最大={max_severe} "
            f"トレンド最悪={worst_trend:+.2f} "
            f"確認数={max_available}/7 "
            f"({coverage_label(max_available)})"
        )


# ============================================================
# 候補ルール探索
# ============================================================

def build_candidate_rules():
    candidates = []

    # --------------------------------------------------------
    # 1. 先行 + 実際の悪化数
    # --------------------------------------------------------

    for minimum_leading in [
        1,
        2,
        3,
    ]:
        for minimum_deteriorated in [
            1,
            2,
            3,
        ]:
            label = (
                f"CI>={minimum_leading} "
                f"AND 40点以上>="
                f"{minimum_deteriorated}"
            )

            candidates.append(
                (
                    label,
                    lambda row,
                    l=minimum_leading,
                    d=minimum_deteriorated: (
                        rule_leading_and_deteriorated(
                            row,
                            l,
                            d,
                        )
                    ),
                )
            )

    # --------------------------------------------------------
    # 2. 先行 + 悪化数 + 確認スコア
    # --------------------------------------------------------

    for minimum_leading in [
        1,
        2,
        3,
    ]:
        for minimum_deteriorated in [
            1,
            2,
        ]:
            for minimum_confirmation in [
                5,
                10,
                15,
                20,
                25,
                30,
            ]:
                label = (
                    f"CI>={minimum_leading} "
                    f"AND 悪化>="
                    f"{minimum_deteriorated} "
                    f"AND 確認>="
                    f"{minimum_confirmation}"
                )

                candidates.append(
                    (
                        label,
                        lambda row,
                        l=minimum_leading,
                        d=minimum_deteriorated,
                        c=minimum_confirmation: (
                            rule_leading_deteriorated_score(
                                row,
                                l,
                                d,
                                c,
                            )
                        ),
                    )
                )

    # --------------------------------------------------------
    # 3. 先行 + 悪化数 + トレンド
    # --------------------------------------------------------

    for minimum_leading in [
        1,
        2,
        3,
    ]:
        for minimum_deteriorated in [
            1,
            2,
        ]:
            for maximum_trend in [
                20,
                0,
                -20,
            ]:
                label = (
                    f"CI>={minimum_leading} "
                    f"AND 悪化>="
                    f"{minimum_deteriorated} "
                    f"AND Trend<="
                    f"{maximum_trend}"
                )

                candidates.append(
                    (
                        label,
                        lambda row,
                        l=minimum_leading,
                        d=minimum_deteriorated,
                        t=maximum_trend: (
                            rule_leading_deteriorated_trend(
                                row,
                                l,
                                d,
                                t,
                            )
                        ),
                    )
                )

    # --------------------------------------------------------
    # 4. 先行 + 60点以上指標
    # --------------------------------------------------------

    for minimum_leading in [
        1,
        2,
        3,
    ]:
        for minimum_severe in [
            1,
            2,
        ]:
            label = (
                f"CI>={minimum_leading} "
                f"AND 60点以上>="
                f"{minimum_severe}"
            )

            candidates.append(
                (
                    label,
                    lambda row,
                    l=minimum_leading,
                    s=minimum_severe: (
                        rule_leading_and_severe(
                            row,
                            l,
                            s,
                        )
                    ),
                )
            )

    # --------------------------------------------------------
    # 5. 意味重視の複合候補
    # --------------------------------------------------------

    candidates.append(
        (
            "BALANCED: 赤+悪化1 OR 橙+悪化2 OR 黄+悪化2+確認20",
            rule_balanced_confirmed,
        )
    )

    return candidates


def rank_candidates(
    results,
    minimum_coverage,
):
    ranked = []

    for label, rule in (
        build_candidate_rules()
    ):
        stats = evaluate_rule(
            results,
            rule,
            minimum_coverage=minimum_coverage,
        )

        ranked.append(
            {
                "label": label,
                "rule": rule,
                **stats,
            }
        )

    ranked.sort(
        key=lambda item: (
            item["f1"],
            item["precision"],
            item["recall"],
            -item["fp"],
            item[
                "average_lead"
            ],
        ),
        reverse=True,
    )

    return ranked


def print_ranked_candidates(
    results,
    minimum_coverage,
    title,
    top_n=20,
):
    print()
    print(
        f"===== 確認済み高リスク候補 "
        f"{title} ====="
    )

    ranked = rank_candidates(
        results,
        minimum_coverage,
    )

    for candidate in ranked[
        :top_n
    ]:
        print_rule_result(
            candidate["label"],
            candidate,
        )

    return ranked


# ============================================================
# Precision重視候補
# ============================================================

def print_precision_candidates(
    ranked,
    minimum_recall=0.30,
):
    print()
    print(
        "===== Precision重視 "
        "（最低Recall条件あり） ====="
    )

    filtered = [
        item
        for item in ranked
        if (
            item["recall"]
            >= minimum_recall
            and item["tp"] > 0
        )
    ]

    filtered.sort(
        key=lambda item: (
            item["precision"],
            item["f1"],
            item["recall"],
            -item["fp"],
        ),
        reverse=True,
    )

    if not filtered:
        print(
            "条件を満たす候補なし"
        )
        return

    for candidate in filtered[:10]:
        print_rule_result(
            candidate["label"],
            candidate,
        )


# ============================================================
# 代表空振り期間
# ============================================================

def period_max_features(
    results,
    start_date,
    end_date,
):
    rows = [
        result
        for result in results
        if (
            month_number(start_date)
            <= month_number(
                result["date"]
            )
            <= month_number(end_date)
        )
    ]

    if not rows:
        return None

    return {
        "max_leading": max(
            leading_rank(row)
            for row in rows
        ),
        "max_confirmation": max(
            row[
                "confirmation_score"
            ]
            for row in rows
        ),
        "max_deteriorated": max(
            row[
                "deteriorated_count"
            ]
            for row in rows
        ),
        "max_severe": max(
            row[
                "severe_count"
            ]
            for row in rows
        ),
        "worst_trend": min(
            row["trend_score"]
            for row in rows
        ),
        "max_available": max(
            row[
                "available_count"
            ]
            for row in rows
        ),
    }


def print_false_period_features(
    results,
):
    print()
    print(
        "===== 代表的な空振り期間 "
        "生データ ====="
    )

    for (
        label,
        start_date,
        end_date,
    ) in REPRESENTATIVE_FALSE_PERIODS:
        features = (
            period_max_features(
                results,
                start_date,
                end_date,
            )
        )

        if features is None:
            continue

        print(
            f"{label}: "
            f"先行最大="
            f"{features['max_leading']} "
            f"確認最大="
            f"{features['max_confirmation']:.2f} "
            f"40点以上最大="
            f"{features['max_deteriorated']} "
            f"60点以上最大="
            f"{features['max_severe']} "
            f"トレンド最悪="
            f"{features['worst_trend']:+.2f} "
            f"確認数="
            f"{features['max_available']}/7"
        )


# ============================================================
# 推奨ルールの詳細
# ============================================================

def print_candidate_detail(
    results,
    candidate,
    minimum_coverage,
    title,
):
    print()
    print(
        f"===== {title} 詳細 ====="
    )

    print(
        "ルール:",
        candidate["label"],
    )

    print_rule_result(
        "成績",
        candidate,
    )

    if candidate[
        "missed_peaks"
    ]:
        print(
            "見逃した山:",
            ", ".join(
                candidate[
                    "missed_peaks"
                ]
            ),
        )

    if candidate["hits"]:
        print()
        print("検知:")

        for event in candidate[
            "hits"
        ]:
            print(
                f"  山 "
                f"{event['peak']} "
                f"← "
                f"{event['start_date']} "
                f"("
                f"{event['months_before']}"
                f"か月前) "
                f"悪化最大="
                f"{event['max_deteriorated']} "
                f"重度最大="
                f"{event['max_severe']} "
                f"確認最大="
                f"{event['max_confirmation']:.2f}"
            )

    if candidate[
        "false_alarms"
    ]:
        print()
        print("空振り:")

        for event in candidate[
            "false_alarms"
        ]:
            print(
                f"  "
                f"{event['start_date']}"
                f"～"
                f"{event['end_date']} "
                f"悪化最大="
                f"{event['max_deteriorated']} "
                f"重度最大="
                f"{event['max_severe']} "
                f"確認最大="
                f"{event['max_confirmation']:.2f} "
                f"確認数最大="
                f"{event['max_available']}/7"
            )


# ============================================================
# main
# ============================================================

def main():
    results = run_backtest()

    if not results:
        print(
            "バックテスト結果がありません"
        )
        return

    print(
        "===== 景気後退シグナル "
        "ルール・オプティマイザー ====="
    )

    print(
        f"期間: "
        f"{results[0]['date']} "
        f"～ "
        f"{results[-1]['date']}"
    )

    print(
        f"判定月数: "
        f"{len(results)}"
    )

    print()
    print(
        "目的:"
    )

    print(
        "1. CI先行警戒は早期警戒として残す"
    )

    print(
        "2. 「確認済み高リスク」は"
        "実際の悪化指標数を必須条件にする"
    )

    print(
        "3. トレンドだけで"
        "「複数悪化」に昇格させない"
    )

    print(
        "4. 低カバレッジ期と"
        "高カバレッジ期を分けて評価する"
    )

    print()
    print(
        "※現在DBの改定後データを使うため、"
        "厳密なリアルタイム・"
        "ヴィンテージ検証ではありません。"
    )

    print_early_warning_baseline(
        results
    )

    print_peak_raw_features(
        results
    )

    print_false_period_features(
        results
    )

    ranked_all = (
        print_ranked_candidates(
            results,
            minimum_coverage=1,
            title="確認1指標以上",
            top_n=20,
        )
    )

    ranked_high = (
        print_ranked_candidates(
            results,
            minimum_coverage=5,
            title="確認5指標以上",
            top_n=20,
        )
    )

    print_precision_candidates(
        ranked_high,
        minimum_recall=0.30,
    )

    if ranked_all:
        print_candidate_detail(
            results,
            ranked_all[0],
            minimum_coverage=1,
            title=(
                "全期間 F1最大候補"
            ),
        )

    if ranked_high:
        print_candidate_detail(
            results,
            ranked_high[0],
            minimum_coverage=5,
            title=(
                "高カバレッジ F1最大候補"
            ),
        )

    balanced = None

    for candidate in ranked_high:
        if candidate[
            "label"
        ].startswith(
            "BALANCED:"
        ):
            balanced = candidate
            break

    if balanced is not None:
        print_candidate_detail(
            results,
            balanced,
            minimum_coverage=5,
            title=(
                "意味重視 BALANCED候補"
            ),
        )


if __name__ == "__main__":
    main()
