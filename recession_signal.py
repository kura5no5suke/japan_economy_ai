from leading_warning import calculate_leading_warning

from risk import (
    GDP_INDICATOR,
    UNEMPLOYMENT_INDICATOR,
    REAL_WAGE_INDICATOR,
    CONSUMPTION_INDICATOR,
    INDUSTRIAL_PRODUCTION_INDICATOR,
    MACHINERY_ORDERS_INDICATOR,
    COINCIDENT_INDEX_INDICATOR,

    calculate_gdp_risk,
    calculate_unemployment_risk,
    calculate_real_wage_risk,
    calculate_consumption_risk,
    calculate_industrial_production_risk,
    calculate_machinery_orders_risk,
    calculate_coincident_index_risk,
    calculate_economic_trend,

    get_data,
    get_latest_data_date,
)


# ============================================================
# 実体経済の確認対象
# ============================================================

CONFIRMATION_SPECS = [
    (
        "GDP",
        GDP_INDICATOR,
        0.20,
        calculate_gdp_risk,
    ),
    (
        "完全失業率",
        UNEMPLOYMENT_INDICATOR,
        0.15,
        calculate_unemployment_risk,
    ),
    (
        "実質賃金",
        REAL_WAGE_INDICATOR,
        0.10,
        calculate_real_wage_risk,
    ),
    (
        "個人消費",
        CONSUMPTION_INDICATOR,
        0.15,
        calculate_consumption_risk,
    ),
    (
        "鉱工業生産",
        INDUSTRIAL_PRODUCTION_INDICATOR,
        0.15,
        calculate_industrial_production_risk,
    ),
    (
        "機械受注",
        MACHINERY_ORDERS_INDICATOR,
        0.10,
        calculate_machinery_orders_risk,
    ),
    (
        "CI一致指数",
        COINCIDENT_INDEX_INDICATOR,
        0.15,
        calculate_coincident_index_risk,
    ),
]


LEADING_RANK = {
    "⚪ 判定不能": -1,
    "🟢 低警戒": 0,
    "🟡 注意": 1,
    "🟠 警戒": 2,
    "🔴 強い警戒": 3,
}


CONFIRMATION_RANK = {
    "⚪ 未確認": 0,
    "🟡 一部悪化": 1,
    "🟠 複数悪化": 2,
    "🔴 広範囲悪化": 3,
}


# ============================================================
# 最終🔴判定の確認条件
#
# バックテスト:
# CI>=🟡 AND 40点以上>=2 AND 60点以上>=1
#
# 高カバレッジ期:
# Precision 100.0%
# Recall     66.7%
# F1         0.800
# TP=2 / FP=0 / FN=1
#
# 2014年の赤い空振りを除外しつつ、
# 2012年・2018年の赤判定を維持した条件。
# ============================================================

RED_MIN_DETERIORATED = 2
RED_MIN_SEVERE = 1


# ============================================================
# 共通
# ============================================================

def safe_first(value):
    if isinstance(value, tuple):
        return value[0]

    return value


def has_enough_data(indicator):
    rows = get_data(indicator)

    return len(rows) >= 12


def calculate_data_confidence(
    available_count,
):
    if available_count >= 6:
        return "🟢 高"

    if available_count >= 3:
        return "🟡 中"

    if available_count >= 1:
        return "🟠 低"

    return "⚪ 判定不能"


# ============================================================
# 実体経済確認
# ============================================================

def classify_confirmation(
    deteriorated_count,
):
    """
    実体経済確認の名称は、
    実際に40点以上になった指標数だけで決める。

    バックテスト結果より、
    トレンドや確認スコアだけで
    「複数悪化」に昇格させない。
    """

    if deteriorated_count >= 4:
        return "🔴 広範囲悪化"

    if deteriorated_count >= 2:
        return "🟠 複数悪化"

    if deteriorated_count >= 1:
        return "🟡 一部悪化"

    return "⚪ 未確認"


def calculate_confirmation():
    risks = {}
    dates = {}
    available_names = []

    weighted_sum = 0.0
    used_weight = 0.0

    for (
        name,
        indicator,
        weight,
        calculator,
    ) in CONFIRMATION_SPECS:

        dates[name] = get_latest_data_date(
            indicator
        )

        if not has_enough_data(
            indicator
        ):
            risks[name] = None
            continue

        result = calculator()

        indicator_risk = safe_first(
            result
        )

        risks[name] = indicator_risk

        available_names.append(name)

        weighted_sum += (
            indicator_risk
            * weight
        )

        used_weight += weight

    if used_weight > 0:
        confirmation_score = (
            weighted_sum
            / used_weight
        )
    else:
        confirmation_score = 0.0

    confirmation_score = round(
        confirmation_score,
        2,
    )

    available_risks = [
        risk_value
        for risk_value in risks.values()
        if risk_value is not None
    ]

    deteriorated_count = sum(
        risk_value >= 40
        for risk_value in available_risks
    )

    severe_count = sum(
        risk_value >= 60
        for risk_value in available_risks
    )

    (
        trend_score,
        trend_status,
        trend_details,
        trend_improving,
        trend_worsening,
        trend_mixed,
    ) = calculate_economic_trend()

    status = classify_confirmation(
        deteriorated_count
    )

    return {
        "risks": risks,
        "dates": dates,
        "available_names": (
            available_names
        ),
        "available_count": len(
            available_names
        ),
        "confirmation_score": (
            confirmation_score
        ),
        "deteriorated_count": (
            deteriorated_count
        ),
        "severe_count": severe_count,
        "status": status,
        "trend_score": trend_score,
        "trend_status": trend_status,
        "trend_details": trend_details,
        "trend_improving": (
            trend_improving
        ),
        "trend_worsening": (
            trend_worsening
        ),
        "trend_mixed": trend_mixed,
        "data_confidence": (
            calculate_data_confidence(
                len(available_names)
            )
        ),
    }


# ============================================================
# 最終判断
# ============================================================

def classify_final_signal(
    leading_warning,
    confirmation_status,
    deteriorated_count=None,
    severe_count=None,
):
    """
    先行警戒と実体経済確認を別軸のまま解釈する。

    最終🔴の必須条件:
    ・CI先行警戒が🟡以上
    ・40点以上の悪化指標が2個以上
    ・そのうち60点以上の重度悪化指標が1個以上

    2014年のように、
    「40点以上が2個あるが60点以上は0個」の月は
    🔴にしない。

    deteriorated_count / severe_count が省略された場合は、
    旧コードからの直接呼び出しとの互換性のため
    confirmation_status から保守的に補完する。
    本番計算では必ず実数を渡す。
    """

    leading_rank = LEADING_RANK.get(
        leading_warning,
        -1,
    )

    confirmation_rank = (
        CONFIRMATION_RANK.get(
            confirmation_status,
            0,
        )
    )

    # --------------------------------------------------------
    # 後方互換用
    # --------------------------------------------------------

    if deteriorated_count is None:
        deteriorated_count = {
            0: 0,
            1: 1,
            2: 2,
            3: 4,
        }.get(
            confirmation_rank,
            0,
        )

    if severe_count is None:
        # status だけでは60点以上の実数は復元できない。
        # 外部から旧2引数形式で呼ばれた場合に
        # 旧動作を壊しすぎないための互換用補完。
        severe_count = (
            1
            if confirmation_rank >= 2
            else 0
        )

    confirmed_red = (
        leading_rank >= 1
        and deteriorated_count
        >= RED_MIN_DETERIORATED
        and severe_count
        >= RED_MIN_SEVERE
    )

    # --------------------------------------------------------
    # 判定不能
    # --------------------------------------------------------

    if leading_rank < 0:
        return (
            "⚪ 判定不能",
            (
                "CI先行指数の判定に必要な"
                "データが不足しています。"
            ),
        )

    # --------------------------------------------------------
    # 確認済み高リスク
    #
    # CIが🟡以上で、
    # 40点以上が2指標以上、
    # かつ60点以上が1指標以上。
    # --------------------------------------------------------

    if confirmed_red:

        if deteriorated_count >= 4:
            return (
                "🔴 景気後退リスク非常に高い",
                (
                    "CI先行指数が警戒し、"
                    "実体経済でも4指標以上が"
                    "40点以上まで悪化し、"
                    "そのうち1指標以上が"
                    "60点以上の重度悪化です。"
                ),
            )

        return (
            "🔴 景気後退リスク高",
            (
                "CI先行指数の警戒に加え、"
                "実体経済でも2指標以上が"
                "40点以上まで悪化し、"
                "そのうち1指標以上が"
                "60点以上の重度悪化です。"
            ),
        )

    # --------------------------------------------------------
    # CI先行が低警戒
    # --------------------------------------------------------

    if leading_rank == 0:

        if confirmation_rank >= 3:
            return (
                "🟠 実体経済の広範囲悪化",
                (
                    "CI先行警戒は低い一方、"
                    "実体経済では4指標以上の"
                    "悪化が確認されています。"
                ),
            )

        if confirmation_rank == 2:
            return (
                "🟡 現在の景気減速",
                (
                    "CI先行の強い警戒はありませんが、"
                    "実体経済では複数指標の"
                    "悪化が確認されています。"
                ),
            )

        if confirmation_rank == 1:
            return (
                "🟡 一部弱含み",
                (
                    "景気後退の先行警戒は低い一方、"
                    "実体経済の1指標に"
                    "明確な弱さがあります。"
                ),
            )

        return (
            "🟢 景気後退リスク低",
            (
                "CI先行警戒が低く、"
                "実体経済でも40点以上の"
                "悪化指標は確認されていません。"
            ),
        )

    # --------------------------------------------------------
    # CI先行 🟡
    #
    # 実体経済が複数悪化でも、
    # 60点以上がなければ🔴にはしない。
    # --------------------------------------------------------

    if leading_rank == 1:

        if confirmation_rank >= 3:
            return (
                "🟠 早期警戒・広範囲悪化",
                (
                    "CI先行指数に減速兆候があり、"
                    "実体経済でも4指標以上が"
                    "悪化していますが、"
                    "60点以上の重度悪化条件は"
                    "まだ満たしていません。"
                ),
            )

        if confirmation_rank == 2:
            return (
                "🟠 早期警戒・複数悪化",
                (
                    "CI先行指数に減速兆候があり、"
                    "実体経済でも2指標以上が"
                    "悪化していますが、"
                    "60点以上の重度悪化条件は"
                    "まだ満たしていません。"
                ),
            )

        if confirmation_rank == 1:
            return (
                "🟠 早期警戒・一部確認",
                (
                    "CI先行指数が減速を示し、"
                    "実体経済にも1指標の"
                    "明確な悪化があります。"
                ),
            )

        return (
            "🟡 早期警戒・未確認",
            (
                "CI先行指数に減速兆候がありますが、"
                "実体経済では40点以上の"
                "悪化指標はまだありません。"
            ),
        )

    # --------------------------------------------------------
    # CI先行 🟠
    # --------------------------------------------------------

    if leading_rank == 2:

        if confirmation_rank >= 3:
            return (
                "🟠 強い先行警戒・広範囲悪化",
                (
                    "CI先行指数が強く警戒し、"
                    "実体経済でも4指標以上が"
                    "悪化していますが、"
                    "60点以上の重度悪化条件は"
                    "まだ満たしていません。"
                ),
            )

        if confirmation_rank == 2:
            return (
                "🟠 強い先行警戒・複数悪化",
                (
                    "CI先行指数の強い警戒と、"
                    "実体経済の複数悪化が"
                    "同時に出ていますが、"
                    "60点以上の重度悪化条件は"
                    "まだ満たしていません。"
                ),
            )

        if confirmation_rank == 1:
            return (
                "🟠 強い先行警戒・一部確認",
                (
                    "CI先行指数が強く警戒しており、"
                    "実体経済にも1指標の"
                    "明確な悪化があります。"
                ),
            )

        return (
            "🟠 強い先行警戒・未確認",
            (
                "CI先行指数は強く警戒していますが、"
                "実体経済では40点以上の"
                "悪化指標はまだありません。"
            ),
        )

    # --------------------------------------------------------
    # CI先行 🔴
    #
    # CI単独では最終🔴にしない。
    # --------------------------------------------------------

    if confirmation_rank >= 3:
        return (
            "🟠 強い先行警戒・広範囲悪化",
            (
                "CI先行指数は強く悪化し、"
                "実体経済でも4指標以上が"
                "悪化していますが、"
                "60点以上の重度悪化条件は"
                "まだ満たしていません。"
            ),
        )

    if confirmation_rank == 2:
        return (
            "🟠 強い先行警戒・複数悪化",
            (
                "CI先行指数は強く悪化し、"
                "実体経済でも2指標以上が"
                "悪化していますが、"
                "60点以上の重度悪化条件は"
                "まだ満たしていません。"
            ),
        )

    if confirmation_rank == 1:
        return (
            "🟠 強い先行警戒・一部確認",
            (
                "CI先行指数は強く悪化していますが、"
                "実体経済で明確に悪化しているのは"
                "現時点では1指標です。"
            ),
        )

    return (
        "🟠 強い先行警戒・未確認",
        (
            "CI先行指数は強い景気悪化を"
            "警告していますが、"
            "実体経済では40点以上の"
            "悪化指標はまだありません。"
        ),
    )


# ============================================================
# 旧参考スコア
# ============================================================

def calculate_reference_score(
    leading_warning,
    confirmation_score,
    trend_score,
):
    """
    旧45/35/20方式。
    比較用にだけ残し、最終判定には使わない。
    """

    leading_score_map = {
        "⚪ 判定不能": 0,
        "🟢 低警戒": 0,
        "🟡 注意": 35,
        "🟠 警戒": 70,
        "🔴 強い警戒": 100,
    }

    leading_score = (
        leading_score_map.get(
            leading_warning,
            0,
        )
    )

    trend_risk = max(
        0,
        min(
            -trend_score,
            100,
        ),
    )

    score = (
        leading_score * 0.45
        + confirmation_score * 0.35
        + trend_risk * 0.20
    )

    return round(
        max(
            0,
            min(score, 100),
        ),
        2,
    )


# ============================================================
# 理由
# ============================================================

def build_leading_reasons(
    leading,
):
    reasons = []

    if (
        leading[
            "three_month_change"
        ] < 0
    ):
        reasons.append(
            "CI先行指数の3か月変化率がマイナス"
        )

    if (
        leading[
            "six_month_change"
        ] < 0
    ):
        reasons.append(
            "CI先行指数の6か月変化率がマイナス"
        )

    if (
        leading[
            "momentum_deceleration"
        ] <= -1.5
    ):
        reasons.append(
            "上昇モメンタムが大きく減速"
        )

    if (
        leading[
            "consecutive_declines"
        ] >= 2
    ):
        reasons.append(
            (
                f"CI先行指数が"
                f"{leading['consecutive_declines']}"
                "か月連続低下"
            )
        )

    if not reasons:
        reasons.append(
            "CI先行指数に強い悪化シグナルなし"
        )

    return reasons


def build_confirmation_reasons(
    confirmation,
):
    reasons = []

    for (
        name,
        risk_value,
    ) in confirmation[
        "risks"
    ].items():

        if risk_value is None:
            continue

        if risk_value >= 60:
            reasons.append(
                (
                    f"{name}が強く悪化 "
                    f"({risk_value:.2f})"
                )
            )

        elif risk_value >= 40:
            reasons.append(
                (
                    f"{name}が悪化 "
                    f"({risk_value:.2f})"
                )
            )

    if not reasons:
        reasons.append(
            "40点以上の確認指標なし"
        )

    return reasons


# ============================================================
# 全体計算
# ============================================================

def calculate_recession_signal():
    leading = (
        calculate_leading_warning()
    )

    if leading is None:
        return None

    confirmation = (
        calculate_confirmation()
    )

    (
        final_status,
        final_message,
    ) = classify_final_signal(
        leading["warning_level"],
        confirmation["status"],
        deteriorated_count=confirmation[
            "deteriorated_count"
        ],
        severe_count=confirmation[
            "severe_count"
        ],
    )

    reference_score = (
        calculate_reference_score(
            leading["warning_level"],
            confirmation[
                "confirmation_score"
            ],
            confirmation[
                "trend_score"
            ],
        )
    )

    return {
        "leading": leading,
        "confirmation": confirmation,
        "final_status": (
            final_status
        ),
        "final_message": (
            final_message
        ),
        "reference_score": (
            reference_score
        ),
        "leading_reasons": (
            build_leading_reasons(
                leading
            )
        ),
        "confirmation_reasons": (
            build_confirmation_reasons(
                confirmation
            )
        ),
    }


# ============================================================
# 表示
# ============================================================

def main():
    result = (
        calculate_recession_signal()
    )

    print()
    print(
        "========================================"
    )
    print(
        "日本景気後退シグナル V2"
    )
    print(
        "========================================"
    )

    if result is None:
        print(
            "判定に必要なデータが不足しています"
        )
        return

    leading = result["leading"]

    confirmation = result[
        "confirmation"
    ]

    # --------------------------------------------------------
    # 1. CI先行警戒
    # --------------------------------------------------------

    print()
    print(
        "【1. CI先行警戒】"
    )

    print(
        "最新年月:",
        leading["latest_date"],
    )

    print(
        "CI先行指数:",
        leading["latest_value"],
    )

    print(
        "先行警戒:",
        leading["warning_level"],
    )

    print(
        "3か月方向:",
        (
            f"{leading['direction_score']:+.2f} "
            f"({leading['direction_label']})"
        ),
    )

    print(
        "連続低下:",
        leading[
            "consecutive_declines"
        ],
        "か月",
    )

    print(
        "3か月変化率:",
        (
            f"{leading['three_month_change']:+.2f}%"
        ),
    )

    print(
        "6か月変化率:",
        (
            f"{leading['six_month_change']:+.2f}%"
        ),
    )

    print(
        "モメンタム減速:",
        (
            f"{leading['momentum_deceleration']:+.2f}%"
        ),
    )

    print(
        "景気減速スコア:",
        leading["slowdown_score"],
    )

    print(
        "先行側の理由:"
    )

    for reason in result[
        "leading_reasons"
    ]:
        print(
            "  ・",
            reason,
        )

    # --------------------------------------------------------
    # 2. 実体経済確認
    # --------------------------------------------------------

    print()
    print(
        "【2. 実体経済確認】"
    )

    for (
        name,
        risk_value,
    ) in confirmation[
        "risks"
    ].items():

        date = confirmation[
            "dates"
        ].get(name)

        if risk_value is None:
            print(
                f"{name}: "
                f"データ不足 "
                f"(最新 {date})"
            )
        else:
            print(
                f"{name}: "
                f"{risk_value:.2f} / 100 "
                f"(最新 {date})"
            )

    print()

    print(
        "確認スコア:",
        confirmation[
            "confirmation_score"
        ],
        "/ 100",
    )

    print(
        "実体経済確認:",
        confirmation["status"],
    )

    print(
        "40点以上:",
        confirmation[
            "deteriorated_count"
        ],
        "/",
        confirmation[
            "available_count"
        ],
        "指標",
    )

    print(
        "60点以上:",
        confirmation[
            "severe_count"
        ],
        "/",
        confirmation[
            "available_count"
        ],
        "指標",
    )

    print(
        "データ信頼度:",
        confirmation[
            "data_confidence"
        ],
        (
            f"("
            f"{confirmation['available_count']}"
            f"/7指標)"
        ),
    )

    print(
        "確認側の理由:"
    )

    for reason in result[
        "confirmation_reasons"
    ]:
        print(
            "  ・",
            reason,
        )

    # --------------------------------------------------------
    # 3. 景気トレンド
    # --------------------------------------------------------

    print()
    print(
        "【3. 景気トレンド】"
    )

    print(
        "トレンドスコア:",
        confirmation[
            "trend_score"
        ],
    )

    print(
        "トレンド判定:",
        confirmation[
            "trend_status"
        ],
    )

    print(
        "改善:",
        confirmation[
            "trend_improving"
        ],
        "指標",
    )

    print(
        "悪化:",
        confirmation[
            "trend_worsening"
        ],
        "指標",
    )

    print(
        "中立:",
        confirmation[
            "trend_mixed"
        ],
        "指標",
    )

    for (
        name,
        score,
        label,
    ) in confirmation[
        "trend_details"
    ]:

        print(
            f"  {name}: "
            f"{label} "
            f"({score:+.2f})"
        )

    # --------------------------------------------------------
    # 4. 最終判断
    # --------------------------------------------------------

    print()
    print(
        "========================================"
    )

    print(
        "【4. 最終景気判断】"
    )

    print(
        "先行警戒:",
        leading["warning_level"],
    )

    print(
        "実体経済確認:",
        confirmation["status"],
    )

    print(
        "最終判定:",
        result["final_status"],
    )

    print(
        "判断:",
        result["final_message"],
    )

    print(
        "参考スコア:",
        result[
            "reference_score"
        ],
        "/ 100",
    )

    print(
        "========================================"
    )

    print()
    print(
        "※CI先行警戒は将来の減速兆候、"
        "実体経済確認は現在の悪化状況として"
        "別々に評価しています。"
    )

    print(
        "※「複数悪化」は40点以上の指標が"
        "実際に2個以上ある場合だけです。"
    )

    print(
        "※最終🔴は、CI先行警戒が🟡以上、"
        "40点以上が2指標以上、かつ"
        "60点以上が1指標以上の場合だけです。"
    )

    print(
        "※トレンドスコアは補足情報であり、"
        "それだけで「複数悪化」や🔴には昇格しません。"
    )

    print(
        "※参考スコアは旧加重平均方式で、"
        "最終判定には使用していません。"
    )

    print(
        "※この判定は景気後退確率そのものを"
        "表すものではありません。"
    )


if __name__ == "__main__":
    main()
