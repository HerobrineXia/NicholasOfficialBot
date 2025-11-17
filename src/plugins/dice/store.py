from __future__ import annotations

from typing import Optional

from storage import connect, db_path

DB_FILE = db_path("dice.db")


def init_tables() -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dice_user_settings (
                scope TEXT NOT NULL CHECK(scope IN ('direct','group')),
                group_id TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL,
                default_sides INTEGER,
                nickname TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (scope, group_id, user_id)
            )
            """
        )


def _key(event_scope: str, group_id: str, user_id: str) -> tuple[str, str, str]:
    return (event_scope, group_id if event_scope == "group" else "", user_id)


def get_default_sides(scope: str, group_id: str, user_id: str) -> Optional[int]:
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            "SELECT default_sides FROM dice_user_settings WHERE scope=? AND group_id=? AND user_id=?",
            _key(scope, group_id, user_id),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None


def set_default_sides(scope: str, group_id: str, user_id: str, sides: int) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO dice_user_settings(scope, group_id, user_id, default_sides)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(scope, group_id, user_id) DO UPDATE SET default_sides=excluded.default_sides, updated_at=CURRENT_TIMESTAMP
            """,
            _key(scope, group_id, user_id) + (sides,),
        )


def get_nickname(scope: str, group_id: str, user_id: str) -> str:
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            "SELECT nickname FROM dice_user_settings WHERE scope=? AND group_id=? AND user_id=?",
            _key(scope, group_id, user_id),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else ""


def set_nickname(scope: str, group_id: str, user_id: str, nickname: str) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO dice_user_settings(scope, group_id, user_id, nickname)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(scope, group_id, user_id) DO UPDATE SET nickname=excluded.nickname, updated_at=CURRENT_TIMESTAMP
            """,
            _key(scope, group_id, user_id) + (nickname,),
        )


def clear_nickname(scope: str, group_id: str, user_id: str) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO dice_user_settings(scope, group_id, user_id, nickname)
            VALUES (?, ?, ?, NULL)
            ON CONFLICT(scope, group_id, user_id) DO UPDATE SET nickname=NULL, updated_at=CURRENT_TIMESTAMP
            """,
            _key(scope, group_id, user_id),
        )
