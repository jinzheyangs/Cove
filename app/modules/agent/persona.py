"""从聊天记录提炼说话风格。

产出三样东西，存在 persona_profiles：
- stats：可量化的习惯（长度、标点、表情率、高频开头/结尾）
- samples_json：代表性原话，直接作为 few-shot 示例
- style_summary：一段自然语言描述，进 system prompt

统计是纯规则计算，不花钱；style_summary 需要一次 LLM 调用，
没配置模型时自动跳过，不影响其余部分。
"""

import json
import re
from collections import Counter

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.agent.models import ChatMessage, PersonaProfile
from app.modules.ai import client as ai_client

logger = structlog.get_logger("persona")

# 常见 emoji 范围，够用即可，不追求完整 Unicode 分类
_EMOJI_RE = re.compile("[\U0001f300-\U0001faff☀-➿]")

_SUMMARY_SYSTEM = (
    "你是一个语言风格分析助手。根据给出的统计和原话，"
    "用一段简洁的中文描述这个人的说话方式。"
    "只描述风格，不要评价人品，不要编造内容。"
    "覆盖：句子长短、标点习惯、常用词、语气、称呼方式。"
)

# 太短或太长的样本对模仿帮助不大
_SAMPLE_MIN = 2
_SAMPLE_MAX = 200


def _top_affixes(texts: list[str], length: int, take: int, from_end: bool) -> list[list]:
    """统计最常见的开头/结尾片段。"""
    counter: Counter[str] = Counter()
    for text in texts:
        cleaned = text.strip().strip("，。！？~… ")
        if len(cleaned) < length:
            continue
        affix = cleaned[-length:] if from_end else cleaned[:length]
        counter[affix] += 1
    return [[value, count] for value, count in counter.most_common(take)]


def compute_stats(texts: list[str]) -> dict:
    """计算风格统计。全是数字，不含原文。"""
    if not texts:
        return {}

    count = len(texts)
    lengths = [len(text) for text in texts]

    def rate(predicate) -> float:
        return round(sum(1 for text in texts if predicate(text)) / count, 3)

    return {
        "messages": count,
        "avg_length": round(sum(lengths) / count, 1),
        "max_length": max(lengths),
        "period_rate": rate(lambda t: "。" in t),
        "question_rate": rate(lambda t: "？" in t or "?" in t),
        "exclamation_rate": rate(lambda t: "！" in t or "!" in t),
        "tilde_rate": rate(lambda t: "~" in t or "～" in t),
        "emoji_rate": rate(lambda t: bool(_EMOJI_RE.search(t))),
        "top_openers": _top_affixes(texts, 2, 10, from_end=False),
        "top_endings": _top_affixes(texts, 2, 10, from_end=True),
    }


def pick_samples(texts: list[str], size: int) -> list[str]:
    """均匀抽样，保持时间上的分布，不用随机。

    使用 dict.fromkeys 去重并保留首次出现顺序。
    """
    candidates = [
        text.strip()
        for text in dict.fromkeys(texts)
        if _SAMPLE_MIN <= len(text.strip()) <= _SAMPLE_MAX
    ]
    if len(candidates) <= size:
        return candidates

    step = len(candidates) / size
    return [candidates[int(i * step)] for i in range(size)]


async def _summarize(stats: dict, samples: list[str]) -> str | None:
    """让模型写一段风格描述。失败时返回 None，不阻断导入。"""
    if not settings.LLM_API_KEY:
        return None

    sample_text = "\n".join(f"- {sample}" for sample in samples[:30])
    prompt = (
        f"统计：{json.dumps(stats, ensure_ascii=False)}\n\n"
        f"原话示例：\n{sample_text}\n\n"
        "请写一段 100 字以内的说话风格描述。"
    )
    try:
        return await ai_client.complete(system=_SUMMARY_SYSTEM, user=prompt)
    except Exception as exc:  # noqa: BLE001 - 画像失败不影响导入
        logger.warning("persona.summary_failed", error=repr(exc))
        return None


async def build_profile(
    session: AsyncSession, couple_id: int, user_id: int
) -> PersonaProfile | None:
    """根据该用户已导入的聊天记录生成画像。

    没有文本消息时返回 None。
    """
    rows = list(
        await session.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.couple_id == couple_id,
                ChatMessage.sender_id == user_id,
                ChatMessage.msg_type == "text",
            )
            .order_by(ChatMessage.sent_at)
        )
    )
    texts = [row.content.strip() for row in rows if row.content.strip()]
    if not texts:
        return None

    stats = compute_stats(texts)
    samples = pick_samples(texts, settings.PERSONA_SAMPLE_SIZE)
    summary = await _summarize(stats, samples)

    profile = await session.scalar(
        select(PersonaProfile).where(
            PersonaProfile.couple_id == couple_id,
            PersonaProfile.user_id == user_id,
        )
    )
    if profile is None:
        profile = PersonaProfile(couple_id=couple_id, user_id=user_id)
        session.add(profile)

    profile.stats = stats
    profile.samples_json = json.dumps(samples, ensure_ascii=False)
    profile.style_summary = summary
    await session.commit()
    await session.refresh(profile)

    logger.info(
        "persona.built", couple_id=couple_id, user_id=user_id, messages=len(texts)
    )
    return profile
