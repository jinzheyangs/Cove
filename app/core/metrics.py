from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "cove_http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "cove_http_request_duration_seconds",
    "HTTP 请求耗时",
    ["method", "path"],
)

AI_CALLS = Counter(
    "cove_ai_calls_total",
    "AI 调用结果",
    ["result"],
)

AI_CIRCUIT_OPEN = Gauge(
    "cove_ai_circuit_open",
    "AI 熔断器是否打开（1 = 打开）",
)

COIN_RECONCILE_MISMATCHES = Gauge(
    "cove_coin_reconcile_mismatches",
    "金币对账不一致的账户数",
)
