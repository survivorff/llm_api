# 架构设计文档 (ARCHITECTURE)

> 版本: v2 架构基线
> 状态: 设计已定稿，随迭代更新
> 定位: 一个 OpenAI 兼容的 LLM 网关 / 中转平台，支持多用户、按量计费、多协议、多渠道、可充值，面向"自用 + 朋友互助 + 开源自部署"。

## 1. 设计目标

| 目标 | 说明 |
|---|---|
| 对标市场 | 功能对齐主流中转站（new-api / one-api）：多协议、渠道分组、计费、充值、用户体系 |
| 计费内核 | 余额账户 + 模型倍率定价 + 预扣式按量计费，账目可对账 |
| 高并发就绪 | Gateway 无状态，可水平扩展；共享状态放 Redis / PostgreSQL |
| 开源可复用 | 一键部署，SQLite 单机回退，安装向导，合规义务清晰甩给部署者 |
| 可插拔支付 | 加密货币 / 微信 / 支付宝 / 兑换码，作为适配器，部署者自选自担责 |

## 2. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 语言/框架 | Python 3.12 + FastAPI | LLM 网关是 I/O 密集型，asyncio 足够；复用现有代码与测试；开源门槛低 |
| Web 服务器 | uvicorn (+ gunicorn 多 worker) | 生产多 worker，开发单进程 |
| 数据库 | PostgreSQL（生产）/ SQLite（单机、开发回退） | 计费与并发需要事务；SQLite 便于一键体验 |
| ORM / 迁移 | SQLAlchemy 2.0 (async) + Alembic | 统一支持 PG/SQLite，版本化 schema |
| 缓存/限流/队列 | Redis（生产）/ 内存回退（开发） | 分布式限速、令牌缓存、异步计费；开发无 Redis 也能跑 |
| HTTP 客户端 | httpx (连接池复用) | 流式转发 |
| 配置 | pydantic-settings + YAML | 环境变量 + 文件，热更新部分走 DB settings 表 |
| 前端 | 内嵌单页后台（现有）→ 后期可拆独立控制台 | 先够用，后演进 |
| 可观测 | 结构化日志 + Prometheus /metrics | 运营与排障 |

**关键决策：不转 Go。** 瓶颈在上游与网络 I/O，不在语言；高并发靠架构（无状态 + Redis + PG）解决，而非换语言。市场已有 Go 版 new-api，差异化在功能与体验而非语言。

## 3. 系统架构

```
                      ┌─────────────────────────┐
   客户端/朋友 ──────▶ │  Nginx / Caddy (TLS,限流) │
   (Cursor/Cline)     └───────────┬─────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   Gateway 实例 (无状态, xN)  │
                    │  FastAPI + uvicorn workers   │
                    │  ┌────────────────────────┐  │
                    │  │ 鉴权 auth (Redis缓存)    │  │
                    │  │ 计费 billing (预扣/结算)  │  │
                    │  │ 路由 router (分组/权重)   │  │
                    │  │ 协议 adapters (多协议互转)│  │
                    │  │ 转发 proxy (流式故障转移) │  │
                    │  └────────────────────────┘  │
                    └───┬───────────┬──────────┬───┘
                        │           │          │
              ┌─────────▼──┐  ┌─────▼────┐  ┌──▼──────────┐
              │ PostgreSQL │  │  Redis   │  │  上游 LLM     │
              │ 用户/渠道/  │  │ 缓存/限流 │  │ DeepSeek/    │
              │ 账单/日志   │  │ 计费队列  │  │ OpenRouter/  │
              └────────────┘  └──────────┘  │ Claude/...   │
                    ▲                        └─────────────┘
              ┌─────┴──────┐
              │ Worker 进程 │  ← 异步落账、用量聚合、渠道健康巡检、支付对账
              └────────────┘
```

**核心原则：Gateway 实例无状态。** 所有会话/限流/计数落 Redis 或 PG，实例可随意增减。

## 4. 分层与目录结构

```
app/
├── main.py            # app factory + lifespan
├── config/            # pydantic settings + YAML 加载（兼容旧 config.yaml）
├── core/              # 基础设施：安全、Redis、日志、依赖注入
├── db/
│   ├── base.py        # engine / session / Base
│   ├── models/        # SQLAlchemy ORM 模型
│   └── migrations/    # Alembic
├── domain/            # 业务服务（不依赖 FastAPI）
│   ├── auth/          # 鉴权、principal 解析
│   ├── billing/       # 计费、余额、定价
│   ├── channels/      # 渠道管理、健康巡检
│   ├── routing/       # 模型→渠道路由、故障转移
│   └── usage/         # 用量记录与聚合
├── adapters/          # 协议适配：openai / claude / gemini 互转
├── api/
│   ├── v1/            # 网关端点（OpenAI 兼容 + Claude + Gemini）
│   └── admin/         # 后台管理端点
├── payments/          # 支付适配器（crypto / wechat / alipay / 兑换码）
└── web/               # 内嵌后台 UI
```

**依赖方向**：`api → domain → db/core`。domain 层不 import FastAPI，便于测试与复用。

## 5. 请求生命周期（chat/completions）

```
1. 鉴权    verify token（Redis 缓存命中→免查库），解析 principal（用户/角色/限制）
2. 限速    分布式 RPM/TPM（Redis 滑动窗口）
3. 准入    模型白名单、渠道分组权限校验
4. 预扣    按模型定价估算最大费用 → 冻结余额（不足则 402）
5. 路由    model→渠道（精确/前缀/通配 + 分组 + 加权），生成 attempt 列表
6. 协议    根据上游类型做请求格式转换（OpenAI/Claude/Gemini）
7. 转发    httpx 流式/非流式 + 故障转移（429/5xx 换 key/渠道）
8. 计量    解析 usage（含缓存命中）→ 计算实际费用
9. 结算    实际扣费，释放冻结差额，写 usage_logs + billing_ledger
10. 巡检   失败计数上报，触发渠道熔断（异步）
```

## 6. 计费模型（核心差异化）

- **余额制**：用户有余额（credits，内部以最小货币单位或 token 折算，建议以「美分」或「点数」为单位存整数，避免浮点）。
- **模型倍率定价**：每个模型有输入/输出/缓存单价 + 分组倍率。费用 = Σ(tokens × 单价 × 倍率)。
- **预扣式（解决现有超额漏洞）**：请求前按 `max_tokens` 或保守上限冻结额度；请求后按实际 usage 结算并退还差额。
- **对账**：`billing_ledger` 记录每一笔（充值/消费/退款/调整），任意时刻余额 = Σ流水，可审计。

## 7. 高并发策略

| 关注点 | 方案 |
|---|---|
| DB 瓶颈 | 单连接+全局锁 → async 连接池；用量日志异步批量落库 |
| 限速 | 内存 → Redis 滑动窗口，支持多实例 |
| 令牌校验 | 每请求查库 → Redis 缓存（写时失效） |
| 计费竞态 | 事后累加 → Redis 原子预扣 + DB 事务结算 |
| 水平扩展 | Gateway 无状态，多实例 + LB |
| 优雅降级 | 无 Redis 时回退内存（仅单机开发） |

## 8. 安全与合规

- 生产强制 `ADMIN_KEY` / `SESSION_SECRET`，禁用匿名回退（仅开发允许）。
- 上游密钥加密存储（`CRYPTO_SECRET`）。
- 后台 IP 白名单、登录失败限制、审计日志。
- **合规声明**：项目仅提供工具，部署者需自行完成备案、许可、内容安全、实名、日志留存、税务、上游授权等义务（详见 docs/COMPLIANCE.md）。
- 无 KYC 支付有资金冻结/合规风险，作为可插拔适配器，部署者自选自担责。

## 9. 与旧版本的兼容

- 旧 `config.yaml`（channels/model_map/api_keys）仍可导入，作为渠道初始化来源。
- 旧 SQLite `usage.db` 提供一次性迁移脚本（可选）。
- OpenAI 兼容端点行为保持不变，客户端无需改动。
