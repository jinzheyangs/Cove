"""结构化日志配置。

两条硬规则：
1. 生产环境输出 JSON，方便日志系统解析
2. 绝不记录请求体——这里的业务数据大多是隐私内容
"""

import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """配置 structlog 与标准库 logging。

    在 app/main.py 导入时调用一次；worker 也会单独调用。
    """
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # 这些 processor 在每个日志事件上按顺序执行：
    # merge_contextvars 把 request_id / user_id 合并进日志
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        # UTC ISO 时间，跨时区排查时不会混淆
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    # 开发环境给人看，生产环境给机器看
    renderer = (
        structlog.dev.ConsoleRenderer()
        if settings.ENV == "dev"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            *shared_processors,
            # 把异常堆栈格式化成字符串，而不是对象
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        # 首次使用时缓存绑定，减少重复配置开销
        cache_logger_on_first_use=True,
    )

    # 让 uvicorn 等标准库日志也走同一套输出
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
    # 这两个库默认很吵，会把业务日志淹掉
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
