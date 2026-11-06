"""聊天记录导入解析。

支持两种格式：
- jsonl：每行一个 JSON 对象（推荐，适合大文件）
- json：一个数组，或 {"messages": [...]}

每种消息至少需要：
    sender    发送人名字
    sent_at   时间
    content   内容

type 可选，默认 text。非 text 的消息会存下来，但不参与索引。
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")

_FIELD_ALIASES = {
    "sender": ("sender", "from", "name", "nickname", "发送人"),
    "sent_at": ("sent_at", "time", "timestamp", "date", "时间"),
    "content": ("content", "text", "msg", "message", "内容"),
    "type": ("type", "msg_type", "类型"),
}


@dataclass
class ParsedMessage:
    sender: str
    sent_at: datetime
    content: str
    msg_type: str


@dataclass
class ParseResult:
    messages: list[ParsedMessage]
    skipped: int


def parse_timestamp(value: object) -> datetime:
    """把各种时间表示统一成带时区的 datetime。

    支持：
    - ISO 8601（带不带 Z / 偏移都行）
    - 常见日期格式，按北京时间理解
    - Unix 秒 / 毫秒
    """
    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 1_000_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=UTC)

    text = str(value).strip()
    if not text:
        raise ValueError("空时间")

    # ISO 8601
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=TZ)
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=TZ)
        except ValueError:
            continue

    raise ValueError(f"无法解析时间: {text}")


def _pick(row: dict, field: str) -> object | None:
    for key in _FIELD_ALIASES[field]:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _to_message(row: dict) -> ParsedMessage:
    sender = _pick(row, "sender")
    sent_at = _pick(row, "sent_at")
    content = _pick(row, "content")
    if sender is None or sent_at is None or content is None:
        raise ValueError("缺少必填字段")
    return ParsedMessage(
        sender=str(sender).strip(),
        sent_at=parse_timestamp(sent_at),
        content=str(content),
        msg_type=str(_pick(row, "type") or "text"),
    )


def parse_messages(text: str, fmt: str) -> ParseResult:
    """解析聊天记录。

    单行解析失败会被跳过并累计到 skipped，不会让整个导入失败。
    """
    rows: list[dict] = []

    if fmt == "jsonl":
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({})  # 交给下面统一计为 skipped
    elif fmt == "json":
        data = json.loads(text)
        rows = data.get("messages", []) if isinstance(data, dict) else data
    else:
        raise ValueError(f"不支持的格式: {fmt}")

    messages: list[ParsedMessage] = []
    skipped = 0
    for row in rows:
        try:
            messages.append(_to_message(row))
        except (ValueError, TypeError, KeyError):
            skipped += 1

    # 按时间排序，保证窗口索引和画像的连贯性
    messages.sort(key=lambda m: m.sent_at)
    return ParseResult(messages=messages, skipped=skipped)


def detect_format(filename: str) -> str:
    """按扩展名猜格式，默认 jsonl。"""
    lower = filename.lower()
    if lower.endswith(".json"):
        return "json"
    return "jsonl"
