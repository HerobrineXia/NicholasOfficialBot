from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from storage import connect, db_path

DB_FILE = db_path("chat.db")


def init_tables() -> None:
    """仅在 chat 插件加载时创建/迁移自身的表。"""
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_user_settings (
                scope TEXT NOT NULL CHECK(scope IN ('direct','group_default','group_user')),
                group_id TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL DEFAULT '',
                current_model TEXT NOT NULL DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (scope, group_id, user_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_user_presets (
                scope TEXT NOT NULL CHECK(scope IN ('direct','group_default','group_user')),
                group_id TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL,
                preset TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (scope, group_id, user_id, model),
                FOREIGN KEY (scope, group_id, user_id) REFERENCES chat_user_settings(scope, group_id, user_id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL CHECK(scope IN ('direct','group_default','group_user')),
                group_id TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL,
                max_tokens INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content TEXT NOT NULL,
                token INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_conv_user ON chat_conversations(scope, group_id, user_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_msg_conv ON chat_messages(conversation_id, id)")


def upsert_setting(scope: str, group_id: str, user_id: str, current_model: str) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO chat_user_settings(scope, group_id, user_id, current_model)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(scope, group_id, user_id) DO UPDATE SET current_model=excluded.current_model, updated_at=CURRENT_TIMESTAMP
            """,
            (scope, group_id, user_id, current_model),
        )


def upsert_preset(scope: str, group_id: str, user_id: str, model: str, preset: str) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO chat_user_settings(scope, group_id, user_id, current_model)
            VALUES (?, ?, ?, '')
            ON CONFLICT(scope, group_id, user_id) DO NOTHING
            """,
            (scope, group_id, user_id),
        )
        conn.execute(
            """
            INSERT INTO chat_user_presets(scope, group_id, user_id, model, preset)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(scope, group_id, user_id, model) DO UPDATE SET preset=excluded.preset, updated_at=CURRENT_TIMESTAMP
            """,
            (scope, group_id, user_id, model, preset),
        )


def get_setting(scope: str, group_id: str, user_id: str) -> Optional[str]:
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            "SELECT current_model FROM chat_user_settings WHERE scope=? AND group_id=? AND user_id=?",
            (scope, group_id, user_id),
        )
        row = cur.fetchone()
        return row[0] if row else None


def get_presets(scope: str, group_id: str, user_id: str) -> Dict[str, str]:
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            "SELECT model, preset FROM chat_user_presets WHERE scope=? AND group_id=? AND user_id=?",
            (scope, group_id, user_id),
        )
        return {model: preset for model, preset in cur.fetchall()}


def create_conversation(scope: str, group_id: str, user_id: str, model: str, max_tokens: int) -> int:
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            """
            INSERT INTO chat_conversations(scope, group_id, user_id, model, max_tokens)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scope, group_id, user_id, model, max_tokens),
        )
        return int(cur.lastrowid)


def trim_conversations(scope: str, group_id: str, user_id: str, keep: int = 3) -> None:
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            """
            SELECT id FROM chat_conversations
            WHERE scope=? AND group_id=? AND user_id=?
            ORDER BY created_at DESC
            LIMIT -1 OFFSET ?
            """,
            (scope, group_id, user_id, keep),
        )
        old_ids = [row[0] for row in cur.fetchall()]
        if old_ids:
            conn.executemany("DELETE FROM chat_conversations WHERE id=?", [(cid,) for cid in old_ids])


def append_message(conversation_id: int, role: str, content: Dict[str, Any], token: int) -> None:
    with connect(DB_FILE) as conn:
        conn.execute(
            """
            INSERT INTO chat_messages(conversation_id, role, content, token)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, json.dumps(content, ensure_ascii=False), token),
        )


def get_latest_conversation(scope: str, group_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            """
            SELECT id, model, max_tokens FROM chat_conversations
            WHERE scope=? AND group_id=? AND user_id=?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (scope, group_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        conv_id, model, max_tokens = row
        mcur = conn.execute(
            """
            SELECT role, content, token FROM chat_messages
            WHERE conversation_id=?
            ORDER BY id ASC
            """,
            (conv_id,),
        )
        messages = []
        for role, content, token in mcur.fetchall():
            messages.append({"role": role, "content": json.loads(content), "token": token})
        return {"id": conv_id, "model": model, "max_tokens": max_tokens, "messages": messages}
