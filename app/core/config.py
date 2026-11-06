"""应用配置。

所有配置都通过环境变量或 `.env` 注入，代码里不出现任何真实密钥。

优先级（pydantic-settings 的默认行为）：
    显式环境变量 > `.env` 文件 > 下面定义的默认值

因此容器里可以用环境变量覆盖 `.env`，例如 docker-compose 会把
`DATABASE_URL` 的 host 从 localhost 改成 postgres。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置对象。

    字段名即环境变量名，大小写敏感（全大写）。
    新增配置时记得同步更新 `.env.example`。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # .env 里可能存在历史遗留的键，忽略而不是启动失败
        extra="ignore",
    )

    # ---------------------------------------------------------------- 基础
    APP_NAME: str = "Cove"
    # 取值约定：dev / ci / prod。prod 会启用 HSTS、强制要求加密密钥
    ENV: str = "dev"
    # 打开后 SQLAlchemy 会打印所有 SQL，只适合本地调试
    DEBUG: bool = True

    # ---------------------------------------------------------------- 存储
    # 注意驱动必须是 asyncpg：postgresql+asyncpg://
    DATABASE_URL: str = "postgresql+asyncpg://cove:cove@postgres:5432/cove"
    REDIS_URL: str = "redis://redis:6379/0"

    # ---------------------------------------------------------------- 向量检索
    # 模拟TA 的 RAG：PG 是真相，Chroma 是可重建的索引
    RAG_ENABLED: bool = True
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "cove_persona"
    RAG_TOP_K: int = 5
    # 切片长度与重叠，按字符数（中文场景不按 token 切）
    RAG_CHUNK_SIZE: int = 400
    RAG_CHUNK_OVERLAP: int = 50
    # 每个用户最多索引多少个聊天窗口，控制 embedding 成本
    RAG_CHAT_MAX_WINDOWS: int = 5000

    # embedding 走 OpenAI 兼容接口，供应商可换：
    # 通义 / 智谱 / 硅基流动 / 本地 vLLM 都支持
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_MODEL: str = ""
    # 部分模型支持指定维度；0 表示用模型默认值
    EMBEDDING_DIMENSIONS: int = 0

    # ---------------------------------------------------------------- 认证
    # 生产环境必须换成随机值：openssl rand -hex 32
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    # access token 很短，泄露后的窗口小；过期后靠 refresh token 续期
    JWT_ACCESS_EXPIRE_MINUTES: int = 30
    # refresh token 存库、可吊销，有效期可以长一些
    JWT_REFRESH_EXPIRE_DAYS: int = 30

    # ---------------------------------------------------------------- 加密
    # 私密字段（秘密、日记等）的 AES-256-GCM 密钥
    # 生成：openssl rand -base64 32
    # 生产环境为空时应用会拒绝启动；更换会导致旧数据无法解密
    DATA_ENCRYPTION_KEY: str = ""

    # ---------------------------------------------------------------- AI
    # 为空时所有 AI 调用会返回“未配置”错误，而不是静默失败
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    # 连续失败多少次后打开熔断器
    AI_FAILURE_THRESHOLD: int = 5
    # 熔断打开多久后进入半开，放一个请求试探
    AI_RECOVERY_SECONDS: float = 60.0

    # ---------------------------------------------------------------- 日志
    LOG_LEVEL: str = "INFO"

    # ---------------------------------------------------------------- 安全
    # 逗号分隔的允许来源，例如 "https://a.com,https://b.com"
    # 手机 App 不发送 Origin，留空不影响；给 Web 端用
    CORS_ORIGINS: str = ""

    # 限流开关。测试环境会关掉，避免依赖 Redis
    RATE_LIMIT_ENABLED: bool = True
    # 每个 IP 在窗口内的总请求数
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    # 认证接口更严格，防止撞库
    AUTH_RATE_LIMIT_REQUESTS: int = 10
    # AI 接口单独一档，模型调用又慢又贵
    AI_RATE_LIMIT_REQUESTS: int = 30
    # 同一手机号连续登录失败多少次后锁定
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCK_SECONDS: int = 900

    # ---------------------------------------------------------------- Agent
    # 会话历史保留天数；每次有新消息会顺延
    AGENT_RETENTION_DAYS: int = 30
    # 每次请求最多带多少轮历史（1 轮 = 用户 + 分身各一条）
    AGENT_MAX_HISTORY_TURNS: int = 10
    # 一轮对话里最多允许几次工具调用
    AGENT_MAX_TOOL_ROUNDS: int = 5
    # 聊天记录导入上限
    CHAT_IMPORT_MAX_BYTES: int = 20 * 1024 * 1024
    CHAT_IMPORT_MAX_MESSAGES: int = 100_000
    # 每次生成画像抽样的条数
    PERSONA_SAMPLE_SIZE: int = 50

    # ---------------------------------------------------------------- 队列
    # 测试环境关掉，避免每个写操作都尝试连 Redis
    QUEUE_ENABLED: bool = True

    # ---------------------------------------------------------------- 业务
    # 每人每天最多赠送多少金币，防止一个人无限发币
    DAILY_GIFT_LIMIT: int = 500

    # ---------------------------------------------------------------- 可观测性
    # 不设置则 /metrics 不校验；建议只在内网暴露
    METRICS_TOKEN: str = ""

    # 链路追踪默认关闭，避免本地/测试依赖 Jaeger
    # ---------------------------------------------------------------- 存储
    # local：开发环境写本地目录；oss：阿里云对象存储
    STORAGE_BACKEND: str = "local"
    # local 后端的落盘目录，同时通过 /uploads 静态挂载
    UPLOAD_DIR: str = "./uploads"
    # 单张图片上限，默认 10MB
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024
    # 公共读桶 / CDN 的访问前缀，例如 https://cdn.example.com
    STORAGE_PUBLIC_BASE_URL: str = ""
    # 私有桶签名 URL 的有效期（秒）
    STORAGE_URL_EXPIRE_SECONDS: int = 3600

    # 阿里云 OSS。STORAGE_BACKEND=oss 时必填
    OSS_ENDPOINT: str = ""
    OSS_BUCKET: str = ""
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    # True 表示私有桶，读取时生成签名 URL
    OSS_PRIVATE: bool = True

    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "cove-api"
    # OTLP HTTP 端点；容器内是 http://jaeger:4318/v1/traces
    OTEL_EXPORTER_ENDPOINT: str = "http://localhost:4318/v1/traces"
    # 采样率。生产环境通常调低到 0.1 以下，避免追踪存储被打满
    OTEL_SAMPLE_RATIO: float = 1.0

    @property
    def cors_origins(self) -> list[str]:
        """把逗号分隔的字符串转成列表，顺手去掉空项和首尾空格。"""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


# 模块级单例。整个进程共享一份配置，导入时读取环境变量和 .env。
settings = Settings()
