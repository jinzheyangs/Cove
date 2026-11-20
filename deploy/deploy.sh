#!/usr/bin/env bash
# Cove 生产部署脚本（Ubuntu 22.04 / 24.04）
#
# 用法：
#   1. 先把代码放到 /opt/cove（git clone 或 scp 上传）
#   2. .env 单独上传到 /opt/cove/.env（不在仓库里）
#   3. sudo bash /opt/cove/deploy/deploy.sh
#
# 脚本做的事：装 Docker → 建 swap（内存不足时）→ 配防火墙 → 起 compose → 等迁移 → 健康检查
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/cove}"
cd "$APP_DIR"

COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

log() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }

# ---------- 前置检查 ----------
log "检查前置条件"

if [ ! -f "$APP_DIR/.env" ]; then
  echo "缺少 $APP_DIR/.env。它不在 git 里，需要单独上传。"
  exit 1
fi

if [ ! -f "$APP_DIR/docker-compose.prod.yml" ]; then
  echo "缺少 docker-compose.prod.yml，请确认代码完整。"
  exit 1
fi

MEM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
echo "内存: ${MEM_MB} MB"

# ---------- 安装 Docker ----------
if ! command -v docker >/dev/null 2>&1; then
  log "安装 Docker"
  apt-get update
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
  echo "Docker 已安装: $(docker --version)"
fi

# ---------- 内存不足时加 swap ----------
if [ "$MEM_MB" -lt 1900 ]; then
  if [ ! -f /swapfile ]; then
    log "内存不足 2 GB，创建 2 GB swap"
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    # 降低换出倾向，尽量不把热数据丢到 swap
    sysctl -w vm.swappiness=10
  else
    echo "swap 已存在"
  fi
  echo "注意：1 GiB 机器建议在 .env 里设 RAG_ENABLED=false，并去掉 chroma 容器。"
fi

# ---------- 防火墙 ----------
if command -v ufw >/dev/null 2>&1; then
  log "配置防火墙（只放行 22 / 80 / 443）"
  ufw allow 22/tcp >/dev/null 2>&1 || true
  ufw allow 80/tcp >/dev/null 2>&1 || true
  ufw allow 443/tcp >/dev/null 2>&1 || true
  ufw --force enable >/dev/null 2>&1 || true
  ufw status | head -n 6
  echo "阿里云控制台的『防火墙』也要同步只开 22/80/443，两处都要放行。"
fi

# ---------- 起服务 ----------
log "构建并启动（首次会跑 migrate，然后起 api / agent / worker / caddy / pg / redis / chroma）"
mkdir -p "$APP_DIR/uploads" "$APP_DIR/logs"
$COMPOSE up -d --build

# ---------- 等迁移 ----------
log "等待数据库迁移完成"
for _ in $(seq 1 60); do
  state=$(docker inspect -f '{{.State.Status}}' cove-migrate-1 2>/dev/null || echo "missing")
  if [ "$state" = "exited" ]; then
    code=$(docker inspect -f '{{.State.ExitCode}}' cove-migrate-1 2>/dev/null || echo 1)
    if [ "$code" != "0" ]; then
      echo "迁移失败，退出码 $code："
      docker logs cove-migrate-1 --tail 40
      exit 1
    fi
    echo "迁移完成"
    break
  fi
  sleep 2
done

# ---------- 健康检查 ----------
log "健康检查"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1/health >/dev/null 2>&1; then
    echo "HTTP 健康检查通过"
    curl -s http://127.0.0.1/health
    echo
    break
  fi
  sleep 2
done

if ! curl -fsS http://127.0.0.1/health >/dev/null 2>&1; then
  echo "健康检查未通过，看一下日志："
  $COMPOSE ps
  echo "--- api 日志 ---"
  $COMPOSE logs api --tail 40
  exit 1
fi

log "容器状态"
$COMPOSE ps

cat <<'EOF'

部署完成。

后续：
  1. 域名解析到本机公网 IP，然后把 .env 的 DOMAIN 改成域名，重启 caddy 拿证书：
       docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d caddy
  2. 每日备份（加到 crontab）：
       0 3 * * * cd /opt/cove && BACKUP_PASSPHRASE=xxx bash scripts/backup_db.sh backup
  3. 更新版本：
       cd /opt/cove && git pull && bash deploy/deploy.sh
EOF
