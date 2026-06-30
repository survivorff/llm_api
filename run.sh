#!/usr/bin/env bash
# 本地启动脚本
set -euo pipefail

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi

if [ ! -f config.yaml ]; then
  cp config.example.yaml config.yaml
  echo "已生成 config.yaml，请检查渠道配置。"
fi

# 从 .env 读取环境变量（如果存在）
if [ -f .env ]; then
  set -a; source .env; set +a
fi

exec .venv/bin/python -m uvicorn app.main:app_factory --factory \
  --host "${HOST:-127.0.0.1}" --port "${PORT:-8080}"
