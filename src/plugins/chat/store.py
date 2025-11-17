from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, List

from storage import connect, db_path

DB_FILE = db_path("chat.db")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMP_IMG_DIR = PROJECT_ROOT / "data" / "temp_img"


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
                short_id TEXT NOT NULL UNIQUE,
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_conv_short ON chat_conversations(short_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_msg_conv ON chat_messages(conversation_id, id)")
        # 兼容旧数据，补齐 short_id
        cur = conn.execute("SELECT id FROM chat_conversations WHERE short_id IS NULL OR short_id=''")
        missing = [row[0] for row in cur.fetchall()]
        for cid in missing:
            sid = _new_sid(conn)
            conn.execute("UPDATE chat_conversations SET short_id=? WHERE id=?", (sid, cid))


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


def clear_presets_for_user(user_id: str) -> None:
    """清空指定用户的所有预设（包含群内/私聊的用户级配置）。"""
    with connect(DB_FILE) as conn:
        conn.execute("DELETE FROM chat_user_presets WHERE user_id=?", (user_id,))


def _new_sid(conn: sqlite3.Connection) -> str:
    while True:
        sid = uuid.uuid4().hex[:6]
        cur = conn.execute("SELECT 1 FROM chat_conversations WHERE short_id=?", (sid,))
        if cur.fetchone() is None:
            return sid


def _paths_from_payload(payload: Any) -> List[Path]:
    paths: List[Path] = []

    def add_path(url: str):
        if url.startswith("file://"):
            p = Path(url.replace("file://", ""))
            try:
                if p.resolve().is_relative_to(TEMP_IMG_DIR):
                    paths.append(p)
                    return
            except Exception:
                try:
                    if str(TEMP_IMG_DIR.resolve()) in str(p.resolve()):
                        paths.append(p)
                        return
                except Exception:
                    pass

    def walk(obj: Any):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "image_url" and isinstance(v, dict) and "url" in v:
                    add_path(str(v["url"]))
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, str):
            if "file://" in obj:
                add_path(obj)

    walk(payload)
    return paths


def create_conversation(scope: str, group_id: str, user_id: str, model: str, max_tokens: int) -> tuple[str, int]:
    with connect(DB_FILE) as conn:
        sid = _new_sid(conn)
        cur = conn.execute(
            """
            INSERT INTO chat_conversations(short_id, scope, group_id, user_id, model, max_tokens)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sid, scope, group_id, user_id, model, max_tokens),
        )
        return sid, int(cur.lastrowid)


def trim_conversations(scope: str, group_id: str, user_id: str, keep: int = 3) -> None:
    """仅保留最近 keep 条会话，并清理临时图片。"""
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
        if not old_ids:
            return
        placeholders = ",".join(["?"] * len(old_ids))
        mcur = conn.execute(
            f"SELECT content FROM chat_messages WHERE conversation_id IN ({placeholders})",
            old_ids,
        )
        for (content,) in mcur.fetchall():
            try:
                payload = json.loads(content)
            except Exception:
                payload = None
            if payload is None:
                continue
            for p in _paths_from_payload(payload):
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
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
            SELECT id, short_id, model, max_tokens FROM chat_conversations
            WHERE scope=? AND group_id=? AND user_id=?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (scope, group_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        conv_id, sid, model, max_tokens = row
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
        return {"id": conv_id, "short_id": sid, "model": model, "max_tokens": max_tokens, "messages": messages}


def list_conversations(scope: str, group_id: str, user_id: str) -> list[Dict[str, Any]]:
    """列出用户的所有会话（按时间倒序）。"""
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            """
            SELECT short_id, model, max_tokens, created_at FROM chat_conversations
            WHERE scope=? AND group_id=? AND user_id=?
            ORDER BY created_at DESC
            """,
            (scope, group_id, user_id),
        )
        return [
            {"short_id": sid, "model": model, "max_tokens": max_tokens, "created_at": created}
            for sid, model, max_tokens, created in cur.fetchall()
        ]


def get_conversation_messages(conversation_id: int) -> list[Dict[str, Any]]:
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            """
            SELECT role, content, token FROM chat_messages
            WHERE conversation_id=?
            ORDER BY id ASC
            """,
            (conversation_id,),
        )
        return [{"role": role, "content": json.loads(content), "token": token} for role, content, token in cur.fetchall()]


def get_conversation_by_short_id(short_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """按短ID获取会话，要求 owner 匹配。"""
    with connect(DB_FILE) as conn:
        cur = conn.execute(
            """
            SELECT id, short_id, scope, group_id, model, max_tokens FROM chat_conversations
            WHERE short_id=? AND user_id=?
            LIMIT 1
            """,
            (short_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        cid, sid, scope, group_id, model, max_tokens = row
        return {"id": cid, "short_id": sid, "scope": scope, "group_id": group_id, "model": model, "max_tokens": max_tokens}
