from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# 数据目录与临时图片保持一致，位于项目根目录下的 data
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def db_path(name: str) -> Path:
    """返回 data 目录下的数据库路径，不创建文件。"""
    return DATA_DIR / name


def ensure_data_dir() -> None:
    """确保 data 目录存在。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def db_exists(path: str | Path) -> bool:
    """判断数据库文件是否存在。"""
    return Path(path).exists()


@contextmanager
def connect(path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    """获取 sqlite3 连接（不做表初始化），由调用方负责建表。"""
    ensure_data_dir()
    conn = sqlite3.connect(path)
    # 全局开启外键约束
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
