# 部署与运维手册

生产环境用 Docker Compose 统一编排：**app + PostgreSQL + Redis + Caddy(自动 HTTPS)**。
本地验收用 SQLite（`bash run.sh`），代码完全一致，仅 `.env` 不同。

## 目录

- `docker-compose.prod.yml` — 生产编排
- `Caddyfile` — 反向代理 + 自动 HTTPS（Let's Encrypt）
- `deploy.sh` — 一键部署脚本（装 docker → 起服务）
- `.env.prod.example` — 环境变量模板（复制为 `.env` 填真实值，不进 git）

## 首次部署

```bash
# 1. 本地把代码同步到服务器（在项目根目录执行）
rsync -az --delete \
  --exclude '.venv/' --exclude '__pycache__/' --exclude '.git/' \
  --exclude 'data/' --exclude 'SECRETS.md' --exclude '*.db' \
  ./ us-server:/opt/llm_api/

# 2. 服务器上执行部署
ssh us-server 'cd /opt/llm_api/deploy && REPO_DIR=/opt/llm_api bash deploy.sh'
```

> 前置：DNS A 记录指向服务器 IP；云安全组放行 80/443。

## 发布新版本（更新代码）

```bash
# 本地同步 + 服务器重建 app（不动数据库/缓存）
rsync -az --delete --exclude '.venv/' --exclude '__pycache__/' --exclude '.git/' \
  --exclude 'data/' --exclude 'SECRETS.md' --exclude '*.db' ./ us-server:/opt/llm_api/
ssh us-server 'cd /opt/llm_api/deploy && docker compose -f docker-compose.prod.yml up -d --build app'
```

app 容器启动时自动跑 `alembic upgrade head` 迁移。

## 常用运维

```bash
# 查看状态
docker compose -f docker-compose.prod.yml ps

# 看日志
docker logs llm-api --tail 100 -f
docker logs llm-api-caddy --tail 50      # HTTPS 证书问题看这里

# 重启某服务
docker compose -f docker-compose.prod.yml restart app

# 全部停止 / 启动
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d

# 进 app 容器
docker exec -it llm-api sh

# 备份数据库
docker exec llm-api-db pg_dump -U llmapi llmapi > backup_$(date +%F).sql

# 恢复数据库
cat backup.sql | docker exec -i llm-api-db psql -U llmapi llmapi
```

## 修改配置

改 `deploy/.env` 后重建 app 生效：

```bash
docker compose -f docker-compose.prod.yml up -d app
```

- 加 OAuth：改 `OAUTH_PROVIDERS`
- 加支付：改 `PAYMENT_PROVIDERS`
- 部分运营设置（公告/注册开关）可在 `/admin` 后台热更新，无需重启。

## 健康检查

- 公网：`curl https://<域名>/healthz`
- 指标：`curl https://<域名>/metrics`
- 后台：`https://<域名>/admin`（用 ADMIN_KEY 登录）
- 门户：`https://<域名>/`

## 故障排查

| 现象 | 排查 |
|---|---|
| HTTPS 打不开 | `docker logs llm-api-caddy`；查 DNS 解析、云安全组 80/443 |
| 502 | app 未就绪，`docker logs llm-api`；查 DATABASE_URL/迁移 |
| 调用 401 | API key 错/停用；上游渠道 key 无效看用量日志 error |
| 内存告警 | 1.6G 机器偏紧，可减 WEB_CONCURRENCY 或 PG shared_buffers |
