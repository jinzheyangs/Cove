#!/usr/bin/env bash
set -euo pipefail

# 用法：
#   BACKUP_PASSPHRASE=xxx bash scripts/backup_db.sh backup
#   BACKUP_PASSPHRASE=xxx bash scripts/backup_db.sh restore backups/cove-xxx.sql.gz.enc

: "${BACKUP_PASSPHRASE:?请设置 BACKUP_PASSPHRASE（备份加密口令）}"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
PG_USER="${POSTGRES_USER:-cove}"
PG_DB="${POSTGRES_DB:-cove}"

usage() {
  echo "用法: $0 backup | restore <file>"
  exit 1
}

backup() {
  mkdir -p "$BACKUP_DIR"
  local stamp file
  stamp="$(date +%Y%m%d-%H%M%S)"
  file="$BACKUP_DIR/cove-$stamp.sql.gz.enc"

  docker compose exec -T postgres pg_dump -U "$PG_USER" "$PG_DB" \
    | gzip -9 \
    | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BACKUP_PASSPHRASE -out "$file"

  find "$BACKUP_DIR" -name 'cove-*.sql.gz.enc' -mtime "+$RETENTION_DAYS" -delete
  echo "备份完成: $file"
}

restore() {
  local file="${1:-}"
  [ -n "$file" ] || usage
  [ -f "$file" ] || { echo "文件不存在: $file"; exit 1; }

  echo "即将恢复到数据库 $PG_DB，3 秒后开始（Ctrl-C 取消）..."
  sleep 3

  openssl enc -d -aes-256-cbc -pbkdf2 -pass env:BACKUP_PASSPHRASE -in "$file" \
    | gunzip \
    | docker compose exec -T postgres psql -U "$PG_USER" "$PG_DB"

  echo "恢复完成"
}

case "${1:-}" in
  backup) backup ;;
  restore) restore "${2:-}" ;;
  *) usage ;;
esac
