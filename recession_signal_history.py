import hashlib
import json
import sqlite3
from datetime import datetime

from recession_signal import calculate_recession_signal


DB_PATH = "data/economy.db"


# ============================================================
# テーブル作成
# ============================================================

def create_recession_signal_history_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS recession_signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calculated_at TEXT NOT NULL,
            data_key TEXT NOT NULL UNIQUE,

            leading_date TEXT,
            leading_warning TEXT,

            confirmation_status TEXT,
            confirmation_score REAL,
            deteriorated_count INTEGER,
            severe_count INTEGER,
            available_count INTEGER,
            data_confidence TEXT,

            trend_score REAL,
            trend_status TEXT,

            final_status TEXT,
            final_message TEXT,

            reference_score REAL
        )
        """
    )

    conn.commit()
    conn.close()


# ============================================================
# 現在シグナルの整理
# ============================================================

def build_signal_record(result):
    leading = result["leading"]
    confirmation = result["confirmation"]

    return {
        "leading_date": (
            leading["latest_date"]
        ),
        "leading_warning": (
            leading["warning_level"]
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
            confirmation["trend_score"]
        ),
        "trend_status": (
            confirmation["trend_status"]
        ),

        "final_status": (
            result["final_status"]
        ),
        "final_message": (
            result["final_message"]
        ),

        "reference_score": (
            result["reference_score"]
        ),
    }


# ============================================================
# 同じ結果を重複保存しないためのキー
# ============================================================

def build_data_key(record):
    """
    景気後退シグナルの主要結果から
    一意キーを作る。

    同じ判定内容で何度実行しても
    同じdata_keyになるため、
    重複保存されない。
    """

    key_source = {
        "leading_date": (
            record["leading_date"]
        ),
        "leading_warning": (
            record["leading_warning"]
        ),
        "confirmation_status": (
            record["confirmation_status"]
        ),
        "confirmation_score": (
            record["confirmation_score"]
        ),
        "deteriorated_count": (
            record["deteriorated_count"]
        ),
        "severe_count": (
            record["severe_count"]
        ),
        "available_count": (
            record["available_count"]
        ),
        "data_confidence": (
            record["data_confidence"]
        ),
        "trend_score": (
            record["trend_score"]
        ),
        "trend_status": (
            record["trend_status"]
        ),
        "final_status": (
            record["final_status"]
        ),
        "reference_score": (
            record["reference_score"]
        ),
    }

    text = json.dumps(
        key_source,
        ensure_ascii=False,
        sort_keys=True,
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


# ============================================================
# DB行 → dict
# ============================================================

def row_to_dict(row):
    if row is None:
        return None

    return {
        "id": row[0],
        "calculated_at": row[1],
        "data_key": row[2],

        "leading_date": row[3],
        "leading_warning": row[4],

        "confirmation_status": row[5],
        "confirmation_score": row[6],
        "deteriorated_count": row[7],
        "severe_count": row[8],
        "available_count": row[9],
        "data_confidence": row[10],

        "trend_score": row[11],
        "trend_status": row[12],

        "final_status": row[13],
        "final_message": row[14],

        "reference_score": row[15],
    }


# ============================================================
# 最新履歴
# ============================================================

def get_latest_history():
    create_recession_signal_history_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            calculated_at,
            data_key,

            leading_date,
            leading_warning,

            confirmation_status,
            confirmation_score,
            deteriorated_count,
            severe_count,
            available_count,
            data_confidence,

            trend_score,
            trend_status,

            final_status,
            final_message,

            reference_score
        FROM recession_signal_history
        ORDER BY id DESC
        LIMIT 1
        """
    )

    row = cur.fetchone()

    conn.close()

    return row_to_dict(row)


def get_latest_histories(limit=10):
    create_recession_signal_history_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            calculated_at,
            data_key,

            leading_date,
            leading_warning,

            confirmation_status,
            confirmation_score,
            deteriorated_count,
            severe_count,
            available_count,
            data_confidence,

            trend_score,
            trend_status,

            final_status,
            final_message,

            reference_score
        FROM recession_signal_history
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cur.fetchall()

    conn.close()

    return [
        row_to_dict(row)
        for row in rows
    ]


# ============================================================
# 変化判定
# ============================================================

def detect_signal_changes(
    previous,
    current,
):
    """
    Discord通知などで使うための
    主要な判定変化を返す。
    """

    if previous is None:
        return {
            "is_first": True,
            "has_change": True,

            "leading_changed": True,
            "confirmation_changed": True,
            "final_changed": True,

            "deteriorated_changed": True,
            "severe_changed": True,
            "trend_changed": True,

            "changes": [
                "景気後退シグナルの初回記録"
            ],
        }

    changes = []

    leading_changed = (
        previous["leading_warning"]
        != current["leading_warning"]
    )

    if leading_changed:
        changes.append(
            (
                "先行警戒: "
                f"{previous['leading_warning']}"
                " → "
                f"{current['leading_warning']}"
            )
        )

    confirmation_changed = (
        previous["confirmation_status"]
        != current["confirmation_status"]
    )

    if confirmation_changed:
        changes.append(
            (
                "実体経済確認: "
                f"{previous['confirmation_status']}"
                " → "
                f"{current['confirmation_status']}"
            )
        )

    final_changed = (
        previous["final_status"]
        != current["final_status"]
    )

    if final_changed:
        changes.append(
            (
                "最終判定: "
                f"{previous['final_status']}"
                " → "
                f"{current['final_status']}"
            )
        )

    deteriorated_changed = (
        previous["deteriorated_count"]
        != current["deteriorated_count"]
    )

    if deteriorated_changed:
        changes.append(
            (
                "40点以上の指標数: "
                f"{previous['deteriorated_count']}"
                " → "
                f"{current['deteriorated_count']}"
            )
        )

    severe_changed = (
        previous["severe_count"]
        != current["severe_count"]
    )

    if severe_changed:
        changes.append(
            (
                "60点以上の指標数: "
                f"{previous['severe_count']}"
                " → "
                f"{current['severe_count']}"
            )
        )

    trend_changed = (
        previous["trend_status"]
        != current["trend_status"]
    )

    if trend_changed:
        changes.append(
            (
                "景気トレンド: "
                f"{previous['trend_status']}"
                " → "
                f"{current['trend_status']}"
            )
        )

    return {
        "is_first": False,
        "has_change": bool(changes),

        "leading_changed": (
            leading_changed
        ),
        "confirmation_changed": (
            confirmation_changed
        ),
        "final_changed": (
            final_changed
        ),

        "deteriorated_changed": (
            deteriorated_changed
        ),
        "severe_changed": (
            severe_changed
        ),
        "trend_changed": (
            trend_changed
        ),

        "changes": changes,
    }


# ============================================================
# 保存
# ============================================================

def save_signal_record(record):
    create_recession_signal_history_table()

    data_key = build_data_key(record)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM recession_signal_history
        WHERE data_key = ?
        LIMIT 1
        """,
        (data_key,),
    )

    existing = cur.fetchone()

    if existing is not None:
        conn.close()

        return {
            "saved": False,
            "data_key": data_key,
            "existing_id": existing[0],
        }

    calculated_at = (
        datetime.now().isoformat(
            timespec="seconds"
        )
    )

    cur.execute(
        """
        INSERT INTO recession_signal_history (
            calculated_at,
            data_key,

            leading_date,
            leading_warning,

            confirmation_status,
            confirmation_score,
            deteriorated_count,
            severe_count,
            available_count,
            data_confidence,

            trend_score,
            trend_status,

            final_status,
            final_message,

            reference_score
        )
        VALUES (
            ?, ?,
            ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?,
            ?, ?,
            ?
        )
        """,
        (
            calculated_at,
            data_key,

            record["leading_date"],
            record["leading_warning"],

            record["confirmation_status"],
            record["confirmation_score"],
            record["deteriorated_count"],
            record["severe_count"],
            record["available_count"],
            record["data_confidence"],

            record["trend_score"],
            record["trend_status"],

            record["final_status"],
            record["final_message"],

            record["reference_score"],
        ),
    )

    new_id = cur.lastrowid

    conn.commit()
    conn.close()

    return {
        "saved": True,
        "data_key": data_key,
        "new_id": new_id,
        "calculated_at": calculated_at,
    }


# ============================================================
# 一括処理
# ============================================================

def update_recession_signal_history():
    """
    現在のV2シグナルを計算し、
    前回との変化を調べたうえで履歴保存する。

    戻り値はai_report.pyからも利用できる。
    """

    result = calculate_recession_signal()

    if result is None:
        return {
            "success": False,
            "reason": (
                "景気後退シグナルを"
                "計算できませんでした。"
            ),
        }

    current = build_signal_record(
        result
    )

    previous = get_latest_history()

    changes = detect_signal_changes(
        previous,
        current,
    )

    save_result = save_signal_record(
        current
    )

    return {
        "success": True,
        "result": result,
        "current": current,
        "previous": previous,
        "changes": changes,
        "save_result": save_result,
    }


# ============================================================
# 表示
# ============================================================

def main():
    print()
    print(
        "========================================"
    )
    print(
        "景気後退シグナル 履歴管理"
    )
    print(
        "========================================"
    )

    update = (
        update_recession_signal_history()
    )

    if not update["success"]:
        print(
            update["reason"]
        )
        return

    current = update["current"]
    previous = update["previous"]
    changes = update["changes"]
    save_result = update[
        "save_result"
    ]

    print()
    print(
        "【現在】"
    )

    print(
        "対象年月:",
        current["leading_date"],
    )

    print(
        "先行警戒:",
        current["leading_warning"],
    )

    print(
        "実体経済確認:",
        current[
            "confirmation_status"
        ],
    )

    print(
        "40点以上:",
        current[
            "deteriorated_count"
        ],
        "/",
        current["available_count"],
        "指標",
    )

    print(
        "60点以上:",
        current[
            "severe_count"
        ],
        "/",
        current["available_count"],
        "指標",
    )

    print(
        "景気トレンド:",
        current["trend_status"],
        (
            f"("
            f"{current['trend_score']:+.2f}"
            f")"
        ),
    )

    print(
        "最終判定:",
        current["final_status"],
    )

    print()

    if previous is None:
        print(
            "【前回】"
        )
        print(
            "履歴なし（初回記録）"
        )

    else:
        print(
            "【前回】"
        )

        print(
            "対象年月:",
            previous["leading_date"],
        )

        print(
            "先行警戒:",
            previous[
                "leading_warning"
            ],
        )

        print(
            "実体経済確認:",
            previous[
                "confirmation_status"
            ],
        )

        print(
            "最終判定:",
            previous[
                "final_status"
            ],
        )

    print()
    print(
        "【変化判定】"
    )

    if changes["is_first"]:
        print(
            "🆕 初回記録です"
        )

    elif changes["has_change"]:
        print(
            "⚠ 景気後退シグナルに"
            "変化があります"
        )

        for change in changes[
            "changes"
        ]:
            print(
                "  ・",
                change,
            )

    else:
        print(
            "🟢 前回から主要判定に"
            "変化はありません"
        )

    print()
    print(
        "【履歴保存】"
    )

    if save_result["saved"]:
        print(
            "保存しました"
        )

        print(
            "履歴ID:",
            save_result["new_id"],
        )

    else:
        print(
            "同じ判定内容がすでに"
            "保存されているため、"
            "重複保存しませんでした"
        )

        print(
            "既存履歴ID:",
            save_result[
                "existing_id"
            ],
        )

    print()
    print(
        "========================================"
    )


if __name__ == "__main__":
    main()
