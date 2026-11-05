from prometheus_client import Counter, Histogram

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
