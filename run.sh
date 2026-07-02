#!/usr/bin/env bash
# 本地启动脚本（v1 架构）
set -euo pipefail

# 优先用 uv（若已安装），否则用 python3
PY="${PYTHON:-python3}"

if [ ! -d .venv ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 .venv
    uv pip install -r requirements.txt
  else
    "$PY" -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
  fi
fi

# 从 .env 读取环境变量（如果存在）
if [ -f .env ]; then
  set -a; source .env; set +a
fi

mkdir -p data

exec .venv/bin/python -m uvicorn app.main:app_factory --factory \
  --host "${HOST:-127.0.0.1}" --port "${PORT:-8080}"
