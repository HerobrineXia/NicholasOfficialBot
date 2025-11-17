from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from storage import connect, db_path

DB_FILE = db_path("dice.db")


def init_tables() -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dice_user_settings (
                user_id TEXT PRIMARY KEY,
                default_sides INTEGER,
                nickname TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def get_default_sides(user_id: str) -> Optional[int]:
    with connect(DB_FILE) as conn:
        cur = conn.execute("SELECT default_sides FROM dice_user_settings WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None


def set_default_sides(user_id: str, sides: int) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO dice_user_settings(user_id, default_sides)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET default_sides=excluded.default_sides, updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, sides),
        )


def get_nickname(user_id: str) -> str:
    with connect(DB_FILE) as conn:
        cur = conn.execute("SELECT nickname FROM dice_user_settings WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] else ""


def set_nickname(user_id: str, nickname: str) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO dice_user_settings(user_id, nickname)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET nickname=excluded.nickname, updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, nickname),
        )


def clear_nickname(user_id: str) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO dice_user_settings(user_id, nickname)
            VALUES (?, NULL)
            ON CONFLICT(user_id) DO UPDATE SET nickname=NULL, updated_at=CURRENT_TIMESTAMP
            """,
            (user_id,),
        )
