FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY alembic.ini ./alembic.ini
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh && \
    adduser --disabled-password --gecos "" appuser && \
    mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# 密钥与数据库通过环境变量注入；SQLite 数据挂载到 /app/data
ENTRYPOINT ["./docker-entrypoint.sh"]
