#!/usr/bin/env bash
# 生产部署脚本（在服务器上执行）。幂等：可重复运行。
# 前置：已 clone 代码到服务器，deploy/.env 已填好。
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/llm_api}"
cd "$REPO_DIR/deploy"

echo "==> 1/4 检查 Docker"
if ! command -v docker >/dev/null 2>&1; then
  echo "    安装 Docker ..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
else
  echo "    Docker 已安装：$(docker --version)"
fi

echo "==> 2/4 校验 .env"
if [ ! -f .env ]; then
  echo "    ERROR: deploy/.env 不存在，请先创建（见 .env.prod.example）"
  exit 1
fi
for k in ADMIN_KEY SESSION_SECRET CRYPTO_SECRET POSTGRES_PASSWORD SITE_DOMAIN; do
  grep -q "^${k}=" .env || { echo "    ERROR: .env 缺少 $k"; exit 1; }
done

echo "==> 3/4 构建并启动容器"
docker compose -f docker-compose.prod.yml up -d --build

echo "==> 4/4 等待健康检查"
sleep 8
docker compose -f docker-compose.prod.yml ps

echo
echo "完成。访问：https://$(grep '^SITE_DOMAIN=' .env | cut -d= -f2)"
echo "首次访问 HTTPS 证书签发可能需要 10-30 秒。"
