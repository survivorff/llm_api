# 变更记录

遵循语义化版本；每个版本对应一个可部署里程碑。

## [1.0.0] - v1 架构基线（进行中）

### 架构
- 重构为异步分层架构：`api → domain → db/core`，domain 层不依赖 FastAPI。
- 引入 SQLAlchemy 2.0 (async) + Alembic 迁移，支持 SQLite（单机）与 PostgreSQL（生产）。
- 引入可选 Redis（限流/缓存），无 Redis 自动回退内存（单机开发）。
- Gateway 无状态化，可水平扩展。

### 新增
- 用户体系（users）+ 余额账户 + 令牌归属用户。
- 模型倍率定价（model_pricing）+ **预扣式按量计费**（freeze → settle），解决旧版事后扣费超额漏洞。
- 账单流水（billing_ledger），余额可对账。
- 上游 key 加密存储（Fernet / CRYPTO_SECRET）。
- 分布式 RPM 限速（Redis 滑动窗口，回退内存）。
- 后台管理扩展：用户 / 渠道 / 定价 的完整 CRUD + 充值。
- 渠道数据库化管理（替代纯 YAML），支持分组、权重、优先级、熔断状态位。
- 首次启动可从旧 `config.yaml` 导入渠道。

### 变更
- 渠道/令牌从内存配置迁移到数据库。
- 网关鉴权改为 admin key / 数据库令牌（移除 owner key 概念）。

### 测试
- 迁移原有端到端用例并新增计费用例，共 25 个，全部通过。

## [0.x] - 朋友互助最小版（历史）
- OpenAI 兼容 chat、多 key 轮询、故障转移、令牌配额、内存限速、SQLite 用量、内嵌后台。
