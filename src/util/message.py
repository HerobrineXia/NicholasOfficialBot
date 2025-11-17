from __future__ import annotations

from nonebot.internal.matcher import Matcher

DEFAULT_MAX_BYTES = 3000


def chunk_text_by_bytes(text: str, limit: int = DEFAULT_MAX_BYTES) -> list[str]:
    """按 UTF-8 字节长度切分文本，确保每段不超过 limit 字节。"""
    chunks: list[str] = []
    current: list[str] = []
    current_bytes = 0
    for ch in text:
        b = len(ch.encode("utf-8"))
        if current and current_bytes + b > limit:
            chunks.append("".join(current))
            current = []
            current_bytes = 0
        current.append(ch)
        current_bytes += b
    if current:
        chunks.append("".join(current))
    if not chunks:
        chunks.append("")
    return chunks


async def send_text_in_chunks(matcher: Matcher, text: str, limit: int = DEFAULT_MAX_BYTES) -> None:
    """将文本按字节限制分段发送，最后一段使用 finish 结束匹配。"""
    chunks = chunk_text_by_bytes(text, limit)
    for i, part in enumerate(chunks):
        if i == len(chunks) - 1:
            await matcher.finish(part)
        else:
            await matcher.send(part)
