# ---- 前端构建 ----
FROM node:25-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 运行时 ----
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

# 从 PyPI 安装 uv，避免依赖 ghcr.io（部分网络环境拉不到）
# 走国内源：容器内解析 pypi.org 可能拿到 IPv6 地址导致 Network unreachable
RUN pip install --no-cache-dir uv==0.8.22

COPY pyproject.toml uv.lock ./
# 生产镜像默认带上 OSS 依赖；本地开发不需要
RUN uv sync --no-dev --extra oss

COPY . .
# 前端产物来自上一阶段，覆盖掉本地可能残留的 dist
COPY --from=web /web/dist ./frontend/dist

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
