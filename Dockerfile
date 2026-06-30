FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# config.yaml 通过挂载提供；密钥通过环境变量注入
ENV CONFIG_PATH=/app/config.yaml

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8080"]
