
import sqlite3
from datetime import datetime


DB_PATH = "data/economy.db"


def create_notification_state_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS notification_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            updated_at TEXT NOT NULL,
            risk_status TEXT,
            anomaly_level TEXT,
            leading_warning TEXT,
            confirmation_status TEXT,
            final_status TEXT
        )
        '''
    )

    conn.commit()
    conn.close()


def get_notification_state():
    create_notification_state_table()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT
            updated_at,
            risk_status,
            anomaly_level,
            leading_warning,
            confirmation_status,
            final_status
        FROM notification_state
        WHERE id = 1
        '''
    )

    row = cur.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "updated_at": row[0],
        "risk_status": row[1],
        "anomaly_level": row[2],
        "leading_warning": row[3],
        "confirmation_status": row[4],
        "final_status": row[5],
    }


def build_current_notification_state(
    current_risk,
    signal_current,
):
    return {
        "risk_status": current_risk["risk_status"],
        "anomaly_level": current_risk["anomaly_level"],
        "leading_warning": (
            signal_current["leading_warning"]
            if signal_current is not None
            else None
        ),
        "confirmation_status": (
            signal_current["confirmation_status"]
            if signal_current is not None
            else None
        ),
        "final_status": (
            signal_current["final_status"]
            if signal_current is not None
            else None
        ),
    }


def compare_notification_state(
    previous,
    current,
):
    if previous is None:
        return {
            "is_first": True,
            "has_change": False,
            "changes": [],
        }

    fields = [
        ("risk_status", "10指標総合判定"),
        ("anomaly_level", "異常レベル"),
        ("leading_warning", "CI先行警戒"),
        ("confirmation_status", "実体経済確認"),
        ("final_status", "最終景気判断"),
    ]

    changes = []

    for key, label in fields:
        old_value = previous.get(key)
        new_value = current.get(key)

        if old_value != new_value:
            changes.append(
                f"{label}: {old_value} → {new_value}"
            )

    return {
        "is_first": False,
        "has_change": bool(changes),
        "changes": changes,
    }


def save_notification_state(current):
    create_notification_state_table()

    updated_at = datetime.now().isoformat(
        timespec="seconds"
    )

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        '''
        INSERT INTO notification_state (
            id,
            updated_at,
            risk_status,
            anomaly_level,
            leading_warning,
            confirmation_status,
            final_status
        )
        VALUES (
            1, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(id) DO UPDATE SET
            updated_at = excluded.updated_at,
            risk_status = excluded.risk_status,
            anomaly_level = excluded.anomaly_level,
            leading_warning = excluded.leading_warning,
            confirmation_status = excluded.confirmation_status,
            final_status = excluded.final_status
        ''',
        (
            updated_at,
            current["risk_status"],
            current["anomaly_level"],
            current["leading_warning"],
            current["confirmation_status"],
            current["final_status"],
        ),
    )

    conn.commit()
    conn.close()


def evaluate_notification_state(
    current_risk,
    signal_current,
):
    previous = get_notification_state()

    current = build_current_notification_state(
        current_risk,
        signal_current,
    )

    comparison = compare_notification_state(
        previous,
        current,
    )

    save_notification_state(current)

    return {
        "previous": previous,
        "current": current,
        **comparison,
    }
