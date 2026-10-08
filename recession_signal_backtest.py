import statistics

import risk
import leading_warning
import recession_signal


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

LEADING_INDEX_INDICATOR = (
    "景気動向指数（CI先行指数）"
)

INDICATORS = [
    LEADING_INDEX_INDICATOR,
    risk.GDP_INDICATOR,
    risk.UNEMPLOYMENT_INDICATOR,
    risk.REAL_WAGE_INDICATOR,
    risk.CONSUMPTION_INDICATOR,
    risk.INDUSTRIAL_PRODUCTION_INDICATOR,
    risk.MACHINERY_ORDERS_INDICATOR,
    risk.COINCIDENT_INDEX_INDICATOR,
]


ORIGINAL_RISK_GET_DATA = risk.get_data
ORIGINAL_LEADING_GET_DATA = (
    leading_warning.get_data
)
ORIGINAL_SIGNAL_GET_DATA = (
    recession_signal.get_data
)


ALL_DATA = {
    indicator: ORIGINAL_RISK_GET_DATA(
        indicator
    )
    for indicator in INDICATORS
}


CURRENT_TARGET_MONTH = None


def month_number(date_string):
    text = str(date_string).strip()

    if "Q" in text:
        year_text, quarter_text = (
            text.split("Q", 1)
        )

        year = int(year_text)
        quarter = int(
            quarter_text[0]
        )

        month = quarter * 3

        return year * 12 + month

    year = int(text[0:4])
    month = int(text[5:7])

    return year * 12 + month


def normalize_month(date_string):
    text = str(date_string).strip()

    if "Q" in text:
        year_text, quarter_text = (
            text.split("Q", 1)
        )

        year = int(year_text)
        quarter = int(
            quarter_text[0]
        )

        return (
            f"{year:04d}-"
            f"{quarter * 3:02d}"
        )

    return text[:7]


def historical_get_data(indicator):
    rows = ALL_DATA.get(
        indicator,
        [],
    )

    if CURRENT_TARGET_MONTH is None:
        return rows

    return [
        row
        for row in rows
        if (
            month_number(row[0])
            <= CURRENT_TARGET_MONTH
        )
    ]


def status_rank(status):
    if status.startswith("🔴"):
        return 3

    if status.startswith("🟠"):
        return 2

    if status.startswith("🟡"):
        return 1

    if status.startswith("🟢"):
        return 0

    return -1


def rank_name(rank):
    names = {
        0: "🟢",
        1: "🟡",
        2: "🟠",
        3: "🔴",
    }

    return names.get(
        rank,
        "⚪",
    )


def calculate_historical_month(
    target_date,
):
    global CURRENT_TARGET_MONTH

    CURRENT_TARGET_MONTH = (
        month_number(target_date)
    )

    risk.get_data = (
        historical_get_data
    )

    leading_warning.get_data = (
        historical_get_data
    )

    recession_signal.get_data = (
        historical_get_data
    )

    try:
        result = (
            recession_signal
            .calculate_recession_signal()
        )

        if result is None:
            return None

        leading = result["leading"]
        confirmation = result[
            "confirmation"
        ]

        final_status = result[
            "final_status"
        ]

        return {
            "date": normalize_month(
                target_date
            ),

            "final_status": final_status,
            "final_rank": status_rank(
                final_status
            ),

            "final_message": result[
                "final_message"
            ],

            "leading_warning": (
                leading[
                    "warning_level"
                ]
            ),

            "confirmation_status": (
                confirmation["status"]
            ),

            "confirmation_score": (
                confirmation[
                    "confirmation_score"
                ]
            ),

            "deteriorated_count": (
                confirmation[
                    "deteriorated_count"
                ]
            ),

            "severe_count": (
                confirmation[
                    "severe_count"
                ]
            ),

            "available_count": (
                confirmation[
                    "available_count"
                ]
            ),

            "data_confidence": (
                confirmation[
                    "data_confidence"
                ]
            ),

            "trend_score": (
                confirmation[
                    "trend_score"
                ]
            ),

            "reference_score": (
                result[
                    "reference_score"
                ]
            ),

            "three_month_change": (
                leading[
                    "three_month_change"
                ]
            ),

            "six_month_change": (
                leading[
                    "six_month_change"
                ]
            ),

            "slowdown_score": (
                leading[
                    "slowdown_score"
                ]
            ),
        }

    finally:
        risk.get_data = (
            ORIGINAL_RISK_GET_DATA
        )

        leading_warning.get_data = (
            ORIGINAL_LEADING_GET_DATA
        )

        recession_signal.get_data = (
            ORIGINAL_SIGNAL_GET_DATA
        )


def run_backtest():
    results = []
    seen = set()

    for (
        date,
        _value,
    ) in ALL_DATA[
        LEADING_INDEX_INDICATOR
    ]:

        month = normalize_month(date)

        if month in seen:
            continue

        seen.add(month)

        result = (
            calculate_historical_month(
                month
            )
        )

        if result is not None:
            results.append(result)

    return results


def is_recession_month(date_string):
    target = month_number(
        date_string
    )

    for (
        peak,
        trough,
    ) in zip(
        OFFICIAL_PEAKS,
        OFFICIAL_TROUGHS,
    ):

        if (
            month_number(peak)
            < target
            <= month_number(trough)
        ):
            return (
                True,
                peak,
                trough,
            )

    return False, None, None


def find_future_peak(
    warning_date,
    min_months=1,
    max_months=12,
):
    warning_number = (
        month_number(
            warning_date
        )
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

    (
        difference,
        peak,
    ) = min(
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


def first_at_rank(
    rows,
    minimum_rank,
):
    matches = [
        row
        for row in rows
        if (
            row["final_rank"]
            >= minimum_rank
        )
    ]

    if not matches:
        return None

    return min(
        matches,
        key=lambda row: (
            month_number(
                row["date"]
            )
        ),
    )


def max_rank_result(rows):
    if not rows:
        return None

    return max(
        rows,
        key=lambda row: (
            row["final_rank"],
            row[
                "confirmation_score"
            ],
            row[
                "reference_score"
            ],
        ),
    )


def build_events(
    results,
    minimum_rank,
):
    events = []
    current = None

    for result in results:
        active = (
            result["final_rank"]
            >= minimum_rank
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
                    "max_rank": (
                        result[
                            "final_rank"
                        ]
                    ),
                    "max_status": (
                        result[
                            "final_status"
                        ]
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
                    "max_reference": (
                        result[
                            "reference_score"
                        ]
                    ),
                    "available_count": (
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

                if (
                    result[
                        "final_rank"
                    ]
                    > current[
                        "max_rank"
                    ]
                ):
                    current[
                        "max_rank"
                    ] = result[
                        "final_rank"
                    ]

                    current[
                        "max_status"
                    ] = result[
                        "final_status"
                    ]

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
                    "max_reference"
                ] = max(
                    current[
                        "max_reference"
                    ],
                    result[
                        "reference_score"
                    ],
                )

                current[
                    "available_count"
                ] = max(
                    current[
                        "available_count"
                    ],
                    result[
                        "available_count"
                    ],
                )

            else:
                events.append(
                    current
                )

                current = {
                    "start_date": (
                        result["date"]
                    ),
                    "end_date": (
                        result["date"]
                    ),
                    "max_rank": (
                        result[
                            "final_rank"
                        ]
                    ),
                    "max_status": (
                        result[
                            "final_status"
                        ]
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
                    "max_reference": (
                        result[
                            "reference_score"
                        ]
                    ),
                    "available_count": (
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
    minimum_rank,
    prediction_months=12,
):
    events = build_events(
        results,
        minimum_rank,
    )

    if not results:
        return []

    latest_date = results[-1][
        "date"
    ]

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
                    "months_before": (
                        None
                    ),
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
            max_months=(
                prediction_months
            ),
        )

        if future_peak is not None:
            if (
                future_peak
                in matched_peaks
            ):
                classification = (
                    "duplicate"
                )
            else:
                classification = (
                    "hit"
                )

                matched_peaks.add(
                    future_peak
                )

            classified.append(
                {
                    **event,
                    "classification": (
                        classification
                    ),
                    "peak": (
                        future_peak
                    ),
                    "months_before": (
                        lead
                    ),
                }
            )

            continue

        if (
            month_number(
                latest_date
            )
            - month_number(
                start_date
            )
            < prediction_months
        ):
            classified.append(
                {
                    **event,
                    "classification": (
                        "pending"
                    ),
                    "peak": None,
                    "months_before": (
                        None
                    ),
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
                "months_before": (
                    None
                ),
            }
        )

    return classified


def calculate_metrics(
    results,
    minimum_rank,
):
    events = classify_events(
        results,
        minimum_rank,
        prediction_months=12,
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

    evaluable_peaks = [
        peak
        for peak in OFFICIAL_PEAKS
        if get_peak_window(
            results,
            peak,
            months=12,
        )
    ]

    missed_peaks = [
        peak
        for peak in evaluable_peaks
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
        "evaluable_peaks": (
            evaluable_peaks
        ),
        "missed_peaks": (
            missed_peaks
        ),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "average_lead": (
            statistics.mean(
                lead_times
            )
            if lead_times
            else 0
        ),
        "median_lead": (
            statistics.median(
                lead_times
            )
            if lead_times
            else 0
        ),
    }


def print_recent(results):
    print()
    print(
        "===== 直近12か月 ====="
    )

    for result in results[-12:]:
        print(
            f"{result['date']} "
            f"先行="
            f"{result['leading_warning']} "
            f"確認="
            f"{result['confirmation_status']} "
            f"最終="
            f"{result['final_status']} "
            f"確認点="
            f"{result['confirmation_score']:.2f} "
            f"悪化="
            f"{result['deteriorated_count']} "
            f"確認数="
            f"{result['available_count']}/7"
        )


def print_peak_paths(results):
    print()
    print(
        "===== 景気の山の前12か月 ====="
    )

    for peak in OFFICIAL_PEAKS:
        rows = get_peak_window(
            results,
            peak,
            months=12,
        )

        if not rows:
            print(
                f"{peak}: "
                "評価可能データ不足"
            )
            continue

        highest = (
            max_rank_result(rows)
        )

        yellow = first_at_rank(
            rows,
            1,
        )

        orange = first_at_rank(
            rows,
            2,
        )

        red = first_at_rank(
            rows,
            3,
        )

        print()
        print(
            f"山 {peak}"
        )

        print(
            "  最高判定: "
            f"{highest['final_status']} "
            f"({highest['date']})"
        )

        if yellow is not None:
            lead = (
                month_number(peak)
                - month_number(
                    yellow["date"]
                )
            )

            print(
                "  🟡以上 最初: "
                f"{yellow['date']} "
                f"({lead}か月前) "
                f"{yellow['final_status']}"
            )
        else:
            print(
                "  🟡以上: なし"
            )

        if orange is not None:
            lead = (
                month_number(peak)
                - month_number(
                    orange["date"]
                )
            )

            print(
                "  🟠以上 最初: "
                f"{orange['date']} "
                f"({lead}か月前) "
                f"{orange['final_status']}"
            )
        else:
            print(
                "  🟠以上: なし"
            )

        if red is not None:
            lead = (
                month_number(peak)
                - month_number(
                    red["date"]
                )
            )

            print(
                "  🔴 最初: "
                f"{red['date']} "
                f"({lead}か月前) "
                f"{red['final_status']}"
            )
        else:
            print(
                "  🔴: なし"
            )

        print(
            "  最高月の中身: "
            f"先行="
            f"{highest['leading_warning']} / "
            f"確認="
            f"{highest['confirmation_status']} / "
            f"確認点="
            f"{highest['confirmation_score']:.2f} / "
            f"悪化="
            f"{highest['deteriorated_count']} / "
            f"確認数="
            f"{highest['available_count']}/7"
        )


def get_pre_peak_event_highest(
    results,
    event,
    minimum_rank,
):
    """
    検知イベントが景気の山をまたいで継続した場合でも、
    表示用の「最高判定」は山より前の月だけで計算する。

    TP/FP/FNなどのイベント分類ロジック自体は変更しない。
    """

    peak = event.get("peak")

    if not peak:
        return None

    start_number = month_number(
        event["start_date"]
    )

    peak_number = month_number(
        peak
    )

    rows = [
        result
        for result in results
        if (
            start_number
            <= month_number(
                result["date"]
            )
            < peak_number
            and result["final_rank"]
            >= minimum_rank
        )
    ]

    return max_rank_result(rows)


def print_metrics(
    results,
    minimum_rank,
    label,
):
    stats = calculate_metrics(
        results,
        minimum_rank,
    )

    print()
    print(
        f"===== {label} ====="
    )

    print(
        f"TP={stats['tp']} "
        f"FP={stats['fp']} "
        f"FN={stats['fn']}"
    )

    print(
        "Precision: "
        f"{stats['precision'] * 100:.1f}%"
    )

    print(
        "Recall: "
        f"{stats['recall'] * 100:.1f}%"
    )

    print(
        "F1: "
        f"{stats['f1']:.3f}"
    )

    print(
        "平均先行期間: "
        f"{stats['average_lead']:.2f}か月"
    )

    print(
        "中央値: "
        f"{stats['median_lead']:.1f}か月"
    )

    if stats[
        "missed_peaks"
    ]:
        print(
            "見逃した山: "
            + ", ".join(
                stats[
                    "missed_peaks"
                ]
            )
        )

    if stats["hits"]:
        print(
            "検知:"
        )

        for event in stats[
            "hits"
        ]:
            highest_before_peak = (
                get_pre_peak_event_highest(
                    results,
                    event,
                    minimum_rank,
                )
            )

            if highest_before_peak is None:
                highest_status = (
                    event["max_status"]
                )
                highest_date = None
            else:
                highest_status = (
                    highest_before_peak[
                        "final_status"
                    ]
                )
                highest_date = (
                    highest_before_peak[
                        "date"
                    ]
                )

            print(
                f"  {event['peak']} "
                f"← "
                f"{event['start_date']} "
                f"({event['months_before']}か月前) "
                f"最高(山の前)="
                f"{highest_status}"
                + (
                    f" ({highest_date})"
                    if highest_date
                    else ""
                )
            )

    return stats


def print_false_alarms(
    stats,
    label,
):
    print()
    print(
        f"===== {label} 空振り ====="
    )

    false_alarms = stats[
        "false_alarms"
    ]

    if not false_alarms:
        print("空振りなし")
        return

    for event in false_alarms:
        print(
            f"{event['start_date']}"
            f"～{event['end_date']} "
            f"最高="
            f"{event['max_status']} "
            f"確認最高="
            f"{event['max_confirmation']:.2f} "
            f"悪化最大="
            f"{event['max_deteriorated']} "
            f"重度最大="
            f"{event['max_severe']} "
            f"確認数最大="
            f"{event['available_count']}/7"
        )


def print_named_false_alarm_check(
    results,
):
    print()
    print(
        "===== 代表的な空振り期間 ====="
    )

    periods = [
        (
            "2014",
            "2014-01",
            "2014-12",
        ),
        (
            "2015-2016",
            "2015-01",
            "2016-12",
        ),
        (
            "2021-2022",
            "2021-01",
            "2022-12",
        ),
        (
            "2022-2023",
            "2022-01",
            "2023-12",
        ),
        (
            "2024",
            "2024-01",
            "2024-12",
        ),
        (
            "2025",
            "2025-01",
            "2025-12",
        ),
    ]

    for (
        label,
        start,
        end,
    ) in periods:

        rows = [
            result
            for result in results
            if (
                month_number(start)
                <= month_number(
                    result["date"]
                )
                <= month_number(end)
            )
        ]

        if not rows:
            continue

        highest = max_rank_result(
            rows
        )

        print(
            f"{label}: "
            f"最高="
            f"{highest['final_status']} "
            f"({highest['date']}) "
            f"先行="
            f"{highest['leading_warning']} "
            f"確認="
            f"{highest['confirmation_status']} "
            f"確認点="
            f"{highest['confirmation_score']:.2f} "
            f"悪化="
            f"{highest['deteriorated_count']}"
        )


def main():
    results = run_backtest()

    if not results:
        print(
            "バックテスト結果が"
            "ありません"
        )
        return

    print(
        "===== 日本景気後退シグナル "
        "2軸モデル バックテスト ====="
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
        "※現在DBに保存されている"
        "改定後データを過去時点まで"
        "切って再計算しています。"
    )

    print(
        "※厳密なリアルタイム・"
        "ヴィンテージバックテストではありません。"
    )

    print(
        "※1985-06はCI先行データ開始直後のため、"
        "12か月前評価はできません。"
    )

    print(
        "※検知一覧の「最高(山の前)」は、"
        "イベントが山をまたいでも"
        "山より前の月だけで集計します。"
    )

    print_recent(
        results
    )

    print_peak_paths(
        results
    )

    yellow_stats = print_metrics(
        results,
        minimum_rank=1,
        label="🟡以上",
    )

    orange_stats = print_metrics(
        results,
        minimum_rank=2,
        label="🟠以上",
    )

    red_stats = print_metrics(
        results,
        minimum_rank=3,
        label="🔴",
    )

    print_false_alarms(
        yellow_stats,
        "🟡以上",
    )

    print_false_alarms(
        orange_stats,
        "🟠以上",
    )

    print_false_alarms(
        red_stats,
        "🔴",
    )

    print_named_false_alarm_check(
        results
    )


if __name__ == "__main__":
    main()
