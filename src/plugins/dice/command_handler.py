from __future__ import annotations

import random
import re
from typing import List

from nonebot.adapters import Event, Message
from nonebot.params import CommandArg

from util import send_text_in_chunks
from util.commands import get_command
from .config import get_config, DiceConfig
from . import store

# 配置与命令
plugin_config: DiceConfig = get_config()
DEFAULT_SIDES = plugin_config.default_sides
MAX_SIDES = plugin_config.max_sides
MAX_REPEAT = plugin_config.max_repeat
MAX_COUNT_PER_TERM = plugin_config.max_count_per_term

command_list = get_command(plugin_config.commands)
dice_cmd = command_list.get("Dice")
dice_set_cmd = command_list.get("Dice.SetDefault")
dice_nick_cmd = command_list.get("Dice.Nickname")


def get_user_id(event: Event) -> str:
    return str(event.get_user_id())


def get_scope(event: Event) -> tuple[str, str]:
    """返回 (scope, group_id)。scope 为 direct/group。"""
    group_id = ""
    if hasattr(event, "group_id"):
        group_id = str(getattr(event, "group_id"))
    elif hasattr(event, "detail_type") and getattr(event, "detail_type") == "group":
        group_id = str(getattr(event, "group_id", ""))
    scope = "group" if group_id else "direct"
    return scope, group_id


def parse_repeat(expr: str) -> tuple[int, str]:
    if "#" not in expr:
        return 1, expr
    parts = expr.split("#", 1)
    try:
        repeat = int(parts[0])
    except ValueError:
        raise ValueError("重复次数需要是数字")
    if repeat <= 0 or repeat > MAX_REPEAT:
        raise ValueError(f"重复次数需在 1-{MAX_REPEAT} 之间")
    return repeat, parts[1]


def roll_dice(count: int, sides: int) -> List[int]:
    return [random.randint(1, sides) for _ in range(count)]


def build_term_result(count: int, sides: int, adv: str | None) -> tuple[int, str]:
    if adv in ("h", "l"):
        r1 = roll_dice(count, sides)
        r2 = roll_dice(count, sides)
        s1, s2 = sum(r1), sum(r2)
        chosen = max(s1, s2) if adv == "h" else min(s1, s2)
        detail = f"{'max' if adv=='h' else 'min'}({'+'.join(map(str,r1))},{'+'.join(map(str,r2))})"
        return chosen, detail
    else:
        rolls = roll_dice(count, sides)
        total = sum(rolls)
        detail = "+".join(map(str, rolls))
        return total, detail


def parse_and_roll(expr: str, default_sides: int) -> tuple[int, str]:
    token_re = re.compile(r"([+-]?)(\d*)d(\d*)([hl]?)|([+-]?\d+)")
    pos = 0
    total = 0
    parts_detail: List[str] = []
    display_tokens: List[str] = []
    for m in token_re.finditer(expr):
        if m.start() != pos:
            raise ValueError("公式格式错误")
        pos = m.end()
        sign = m.group(1)
        if m.group(5):  # 纯数字
            val = int(m.group(5))
            if sign == "-":
                val = -val
            total += val
            prefix = "-" if val < 0 else "+"
            if not display_tokens:
                prefix = "" if val >= 0 else "-"
            token_disp = f"{prefix}{abs(val)}" if prefix else str(val)
            display_tokens.append(token_disp)
            detail_token = token_disp
            parts_detail.append(detail_token)
            continue
        count = int(m.group(2)) if m.group(2) else 1
        sides = int(m.group(3)) if m.group(3) else default_sides
        adv = m.group(4) or None
        if sides <= 0 or sides > MAX_SIDES:
            raise ValueError(f"骰面需在 1-{MAX_SIDES} 之间")
        if count <= 0 or count > MAX_COUNT_PER_TERM:
            raise ValueError(f"每个骰子段的数量需在 1-{MAX_COUNT_PER_TERM} 之间")
        term_total, detail = build_term_result(count, sides, adv)
        is_negative = sign == "-"
        if is_negative:
            term_total = -term_total
            detail_token = f"-({detail})"
            token_disp = f"-{count}d{sides}{adv or ''}" if not display_tokens else f"-{count}d{sides}{adv or ''}"
        else:
            detail_token = detail
            if display_tokens:
                detail_token = f"+{detail_token}"
            token_disp = f"{'' if not display_tokens else '+'}{count}d{sides}{adv or ''}"
        display_tokens.append(token_disp)
        total += term_total
        parts_detail.append(detail_token)
    if pos != len(expr):
        raise ValueError("公式解析失败")
    display_expr = "".join(display_tokens)
    detail_expr = "".join(parts_detail).replace("+-", "-")
    return total, f"{display_expr}={detail_expr}"


if dice_cmd:
    @dice_cmd.handle()
    async def _(event: Event, args: Message = CommandArg()):
        user_id = get_user_id(event)
        store.init_tables()
        scope, group_id = get_scope(event)
        text = args.extract_plain_text().strip()
        if not text:
            text = "d"  # 默认掷一次默认骰面
        text = text.lower()

        default_sides = store.get_default_sides(scope, group_id, user_id) or DEFAULT_SIDES
        nickname = store.get_nickname(scope, group_id, user_id)

        try:
            repeat, expr = parse_repeat(text)
        except Exception as e:
            await dice_cmd.finish(str(e))

        results: List[str] = []
        for i in range(repeat):
            try:
                total, detail = parse_and_roll(expr, default_sides)
            except Exception as e:
                await dice_cmd.finish(str(e))
            prefix = f"Roll {i+1}: " if repeat > 1 else ""
            if nickname:
                msg = f"{prefix}{nickname}掷出了 {detail}={total}"
            else:
                msg = f"{prefix}掷出了 {detail}={total}"
            results.append(msg)

        output = "\n".join(results)
        await send_text_in_chunks(dice_cmd, output)


if dice_set_cmd:
    @dice_set_cmd.handle()
    async def _(event: Event, args: Message = CommandArg()):
        user_id = get_user_id(event)
        store.init_tables()
        scope, group_id = get_scope(event)
        text = args.extract_plain_text().strip().lower()
        try:
            sides = int(text)
        except ValueError:
            await dice_set_cmd.finish("请输入正整数骰面")
        if sides <= 0 or sides > MAX_SIDES:
            await dice_set_cmd.finish(f"骰面需在 1-{MAX_SIDES} 之间")
        store.set_default_sides(scope, group_id, user_id, sides)
        await dice_set_cmd.finish(f"已将默认骰面设置为 d{sides}")


if dice_nick_cmd:
    @dice_nick_cmd.handle()
    async def _(event: Event, args: Message = CommandArg()):
        user_id = get_user_id(event)
        store.init_tables()
        scope, group_id = get_scope(event)
        nickname = args.extract_plain_text().strip()
        if nickname:
            store.set_nickname(scope, group_id, user_id, nickname)
            await dice_nick_cmd.finish(f"已设置昵称为 {nickname}")
        else:
            store.clear_nickname(scope, group_id, user_id)
            await dice_nick_cmd.finish("已清空昵称")
