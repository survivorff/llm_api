FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8080

# 密钥与数据库通过环境变量注入；SQLite 数据挂载到 /app/data
CMD ["python", "-m", "uvicorn", "app.main:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8080"]
