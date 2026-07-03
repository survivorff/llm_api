# llm_api · LLM 网关 / 中转平台

一个 OpenAI 兼容的大模型网关：统一端点接入多家模型（国产直连 + OpenRouter/OpenAI 等），
支持**多用户、余额计费、按量计价、多渠道路由与故障转移、后台管理**，面向"自用 + 朋友互助 + 开源自部署"。

> 架构：异步 FastAPI + SQLAlchemy(async) + 可选 Redis，Gateway 无状态、可水平扩展。
> 设计与路线图见 [docs/design/](docs/design/)，上手看 [docs/使用说明.md](docs/使用说明.md)。

## 能力
**核心（v1.0）**
- OpenAI 兼容 `POST /v1/chat/completions`（流式 + 非流式）、`GET /v1/models`、`GET /v1/me`
- 数据库驱动的多渠道：按模型名路由（精确 / 前缀 `claude-*` / 通配 `*`）+ 分组 + 加权
- 同渠道多 key 轮询 + 失败自动重试（429/5xx 换 key、换渠道）
- 用户体系 + 余额；模型倍率定价 + **预扣式结算**（冻结→按实际 usage 结算退差额），可对账
- 多租户令牌：配额、有效期、RPM 限速（分布式）、模型白名单
- 后台 `/admin`：用户/令牌/渠道/定价/用量；上游 key 加密存储；SQLite/PostgreSQL + Alembic

**协议与渠道（v1.1）**
- Claude `POST /v1/messages` 原生入口 + Claude/Gemini ⇄ OpenAI 协议互转（含流式）
- `POST /v1/embeddings`、`POST /v1/images/generations`
- 渠道健康巡检：连续失败自动熔断，冷却后半开恢复

**支付与充值（v1.2）**
- 可插拔支付：易支付（微信/支付宝）、加密货币（USDT-TRC20）、兑换码
- 充值订单 + 异步对账 worker，幂等入账

**用户体验（v1.3）**
- 邮箱 / OAuth（GitHub·Google·LinuxDO）登录，HMAC 会话
- 用户门户 `/`：自助令牌、账单、充值，中/英双语

**运营（v2.0）**
- 设置热更新 + 公告；Prometheus `/metrics`；审计日志 + 保留策略
- Docker 一键部署（自动迁移）+ 健康检查 + GitHub Actions CI

## 角色与密钥
| 角色 | 用什么 | 能做什么 |
|---|---|---|
| 管理员 | `ADMIN_KEY` | 进 `/admin`，管理用户/令牌/渠道/定价/设置，看用量与审计 |
| 用户 | 邮箱/OAuth 登录会话 | 进门户 `/`，自助管理令牌、充值、看账单 |
| 用户令牌 | `sk-...` | 调用网关，受启停 + 配额 + 余额 + 限速约束 |

## 快速开始（本地自用，仅需 SQLite）
```bash
cp .env.example .env          # 填 ADMIN_KEY / CRYPTO_SECRET 等
bash run.sh                   # 首次自动建 venv（优先用 uv）、装依赖、建库
```
默认监听 `http://127.0.0.1:8080`。健康检查：`curl localhost:8080/healthz`

启动后打开 `http://127.0.0.1:8080/admin`，输入 `ADMIN_KEY`：
1. **渠道**页新建上游（如 DeepSeek）：填 base_url + api_key + 支持的模型
2. **定价**页给模型配价（credits/1K tokens，1 USD = 1,000,000 credits）；不配价则不扣费
3. **用户**页给自己/朋友建用户并充值余额
4. **令牌**页为用户生成 `sk-...`，发出去即可用

## 在 Cursor / Cline / Aider 里使用
- Base URL: `http://127.0.0.1:8080/v1`
- API Key: 后台发的 `sk-...`
- Model: `deepseek-chat` 等

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Authorization: Bearer sk-xxx" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hello"}]}'
```

## 部署到服务器（生产，PostgreSQL + Redis）
```bash
cp .env.example .env && vi .env    # 设强随机 ADMIN_KEY / SESSION_SECRET / CRYPTO_SECRET
                                   # DATABASE_URL 指向 Postgres，REDIS_URL 指向 Redis
docker compose up -d --build
```
⚠️ **安全红线**：上服务器/给他人用**必须**设置强随机 `ADMIN_KEY` 与 `CRYPTO_SECRET`。
建议：Nginx/Caddy + HTTPS + 限流；`/admin` 加 IP 白名单。合规义务见 [docs/design/COMPLIANCE.md](docs/design/COMPLIANCE.md)。

## 文档
- [docs/使用说明.md](docs/使用说明.md) — 上手与部署指南
- [docs/design/ARCHITECTURE.md](docs/design/ARCHITECTURE.md) — 架构设计
- [docs/design/ROADMAP.md](docs/design/ROADMAP.md) — 版本路线图
- [docs/design/DATA_MODEL.md](docs/design/DATA_MODEL.md) — 数据模型
- 版本设计：[v1.1-PROTOCOLS](docs/design/v1.1-PROTOCOLS.md) · [v1.2-PAYMENTS](docs/design/v1.2-PAYMENTS.md) · [v1.3-ACCOUNTS](docs/design/v1.3-ACCOUNTS.md) · [v2.0-OPS](docs/design/v2.0-OPS.md)
- [docs/design/COMPLIANCE.md](docs/design/COMPLIANCE.md) — 合规说明（部署者必读）
- [CHANGELOG.md](CHANGELOG.md) — 变更记录

## 测试
```bash
.venv/bin/python -m pytest -q
```
内置假上游端到端验证（无需真实 key/网络），覆盖：路由、鉴权、流式、故障转移、多租户、**计费预扣与结算**。

## 迁移（生产）
```bash
.venv/bin/alembic upgrade head    # 应用数据库迁移
```
开发/单机模式下应用启动会自动建表，无需手动迁移。
