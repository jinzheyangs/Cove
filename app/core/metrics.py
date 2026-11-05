"""Prometheus 指标定义。

指标名一旦上线就不要再改，告警规则和看板都依赖它。
新增指标时同步更新 deploy/prometheus/alerts.yml。
"""

from prometheus_client import Counter, Gauge, Histogram

# 请求总量。path 用的是路由模板（如 /api/v1/secrets/{secret_id}），
# 否则每个资源 id 都会开一条时间序列，把 Prometheus 撑爆。
REQUEST_COUNT = Counter(
    "cove_http_requests_total",
    "HTTP 请求总数",
    ["method", "path", "status"],
)

# 请求耗时分布。Histogram 会自动生成 _bucket/_sum/_count，
# P95/P99 用 histogram_quantile 在 Prometheus 侧计算。
REQUEST_LATENCY = Histogram(
    "cove_http_request_duration_seconds",
    "HTTP 请求耗时",
    ["method", "path"],
)

# AI 调用结果：success / failure / circuit_open。
# circuit_open 表示请求根本没发出去，被熔断器拦下了。
AI_CALLS = Counter(
    "cove_ai_calls_total",
    "AI 调用结果",
    ["result"],
)

# 熔断器状态。1 = 打开（正在拒绝请求），0 = 关闭或半开。
# 由 ai/client.py 在状态变化时更新。
AI_CIRCUIT_OPEN = Gauge(
    "cove_ai_circuit_open",
    "AI 熔断器是否打开（1 = 打开）",
)

# 对账不一致的账户数。由 worker 每天跑完对账后写入。
# 大于 0 说明缓存余额和流水对不上，需要人工核对。
COIN_RECONCILE_MISMATCHES = Gauge(
    "cove_coin_reconcile_mismatches",
    "金币对账不一致的账户数",
)
