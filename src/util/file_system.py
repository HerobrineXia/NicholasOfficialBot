import base64
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request

from nonebot import logger

# 默认存储路径：项目根下 data/files，使用绝对路径避免 chdir 影响。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FILES_DIR = PROJECT_ROOT / "data" / "files"


def read_file(file_path: str | Path) -> Optional[bytes]:
    """读取文件内容并返回字节数据。"""
    try:
        return Path(file_path).read_bytes()
    except FileNotFoundError:
        logger.error("文件未找到！")
        return None
    except IOError:
        logger.error("读取文件时出错！")
        return None


def read_file_as_base64(file_path: str | Path) -> Optional[str]:
    """读取文件并转为 Base64 编码字符串。"""
    data = read_file(file_path)
    if data is None:
        return None
    return base64.b64encode(data).decode("utf-8")


def save_file(url: str, storage_dir: Path | None = None) -> str:
    """
    从 URL 下载文件并保存到指定目录，返回文件的绝对路径。
    默认目录为项目根下 data/files，避免依赖当前工作目录。
    """
    storage_root = storage_dir if storage_dir is not None else FILES_DIR
    storage_root = Path(storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    file_name = f"{timestamp}_{unique_id}.jpg"  # 默认写成 .jpg，可按需扩展
    file_path = storage_root / file_name

    try:
        with urllib.request.urlopen(url) as resp, file_path.open("wb") as output:
            output.write(resp.read())
            logger.info(f"Write file at: {file_path}")
    except Exception as e:
        logger.error(f"下载文件时出错：{e}")
        return ""
    return str(file_path.resolve())


def remove_file(file_path: str | Path) -> None:
    """删除指定路径的文件。"""
    try:
        path = Path(file_path)
        path.unlink()
        logger.info(f"Remove file at: {path}")
    except FileNotFoundError:
        logger.error("文件未找到！")
    except IOError:
        logger.error("删除文件时出错！")
