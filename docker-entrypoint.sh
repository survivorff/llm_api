#!/usr/bin/env sh
# 容器启动：非 SQLite 时先跑数据库迁移，再启动服务。
set -e

case "${DATABASE_URL:-}" in
  ""|sqlite*)
    echo "[entrypoint] SQLite/无 DATABASE_URL：启动时自动建表，跳过 alembic"
    ;;
  *)
    echo "[entrypoint] 运行数据库迁移 alembic upgrade head"
    alembic upgrade head || echo "[entrypoint] 迁移失败，将回退到启动期自动建表"
    ;;
esac

exec python -m uvicorn app.main:app_factory --factory \
  --host "${HOST:-0.0.0.0}" --port "${PORT:-8080}" \
  --workers "${WEB_CONCURRENCY:-1}"
