# 变更记录

遵循语义化版本；每个版本对应一个可部署里程碑。

## [2.2.0] - v2.2 后台运营工具补全

### 新增
- 后台新增 5 个功能页并全部接后端：
  - **请求日志**：明细表 + 多维筛选（令牌/模型/渠道/状态/仅错误）+ 分页。
  - **兑换码管理**：批量生成、复制、CSV 导出、单张/按批次作废。
  - **订单管理**：列表 + 状态 + 手动补单（幂等入账，记审计）。
  - **系统设置**：公告/站点名/注册开关等热更新（无需重启）。
  - **审计日志**：管理操作留痕查看。
- 概览卡片升级：今日请求/成功率、今日消费、累计消费。
- 用户/渠道支持后台直接启停。
- 后端新增：`/admin/logs`（筛选分页）、`/admin/logs/stats`（概览）、
  `/admin/redemption/void`、`/admin/redemption/export`、`/admin/orders/{no}/mark-paid`。
- 新增《运营后台使用手册》`docs/运营手册.md`（含 9 个常见运营场景操作步骤）。

### 测试
- 新增后台工具用例 8 个。累计 73 个全部通过。

## [2.1.1] - v2.1.1 登录安全与动态站点

### 变更
- **默认关闭邮箱密码注册/登录**（`EMAIL_AUTH_ENABLED=false`），仅保留 OAuth 登录。
  原因：邮箱注册未接入验证，公开服务存在刷号/薅额度风险。OAuth 身份已验证、免密码、零额外依赖。
  可通过配置随时重新开启（未来接入 SMTP 邮箱验证后）。
- 站点对外地址改为动态：新增 `SITE_DOMAIN` 配置与 `/public/settings.base_url`，
  门户/文档/价格页的示例地址运行时注入，不再硬编码，便于他人自部署。

### 新增
- 控制台登录页在纯 OAuth 模式下自动隐藏邮箱表单，展示第三方登录引导。
- 测试：邮箱开关（默认关 → register/login 返回 403）、公开设置 base_url/email_auth 暴露。

## [2.1.0] - v2.1 门户网站与 UI 重设计

### 新增
- 全新门户网站，现代深色 SaaS 风格，统一设计系统（`app/web/shared.py`）：
  - 首页 `/`：Hero、核心能力、三步上手、CTA。
  - 文档中心 `/docs`：快速开始、认证、API 参考、客户端配置、流式、错误码、FAQ，带侧边锚点导航。
  - 套餐价格 `/pricing`：实时模型价目表（拉 `/public/pricing`）、计费说明、¥/$ 切换。
- 公开只读端点：`GET /public/models`、`GET /public/pricing`（只暴露模型名与价格，绝不含 key/base_url）。
- 用户控制台 `/portal` 视觉重构，套用统一设计系统，功能不变。

### 变更
- 根路径 `/` 从"登录框"改为品牌首页；登录/控制台迁移到 `/portal`。
- 关闭 FastAPI 默认 Swagger/OpenAPI（`/docs`、`/openapi.json`），`/docs` 让位给文档中心。

### 测试
- 新增门户与公开端点用例 7 个。累计 63 个全部通过。

## [2.0.0] - v2.0 开源就绪与运营

### 新增
- 运营设置热更新：DB 支持的 KV 配置（公告/站点名/注册开关等），后台改无需重启（带缓存）。
- 公开设置端点 `/public/settings`，供门户展示公告等。
- Prometheus 指标 `/metrics`（零依赖内置采集器）：请求数/错误/token/延迟直方图，转发层统一埋点。
- 审计日志：管理操作留痕 + `/admin/audit` 查询 + 保留策略后台清理任务。
- 一键部署：Dockerfile（非 root + entrypoint 自动迁移）、compose 健康检查与依赖顺序。
- CI：GitHub Actions（pytest + docker build）。
- MIT License + 合规声明（`docs/design/COMPLIANCE.md`）。

### 数据模型
- 新增 `audit_logs` 表。
- Alembic 迁移 `0002`：orders 扩展列 + redemption_codes + oauth_accounts + audit_logs。

### 测试
- 新增运营/指标/审计用例 8 个。累计 56 个全部通过。

## [1.3.0] - v1.3 用户体验与登录

### 新增
- 邮箱注册/登录 + HMAC 无状态会话令牌（不引入 JWT 依赖）。
- OAuth2 登录（GitHub / Google / LinuxDO，配置驱动，可插拔）。
- 用户自助：令牌自助管理、账单流水、充值订单查询。
- 用户门户页面 `/portal`（`/` 根路径），中/英双语 i18n。
- 充值端点身份统一：会话优先、回退 API 令牌（`get_user_id`）。

### 变更
- 密码哈希改用 `bcrypt`（移除 passlib，规避与 bcrypt 5.x 的兼容问题）；
  预处理 `base64(sha256(pw))` 规避 72 字节上限。

### 数据模型
- 新增 `oauth_accounts` 表（第三方身份绑定）。

### 测试
- 新增账户/会话/自助/门户用例 10 个。累计 48 个全部通过。

## [1.2.0] - v1.2 支付与充值

### 新增
- 可插拔支付 provider 架构（`app/payments`），核心不绑定任何一家支付。
- 兑换码充值：管理员批量生成，用户输入即时到账。
- 易支付（EPay）聚合适配器：覆盖微信/支付宝扫码，MD5 验签 + 异步回调。
- 加密货币（USDT-TRC20）充值：唯一金额匹配 + TronGrid 链上轮询对账，无需支付牌照。
- 订单服务（OrderService）：创建订单、幂等入账、订单过期、对账查询。
- 充值 API（`/pay/*`）：下单、查单、兑换、支付回调。
- 后台订单 / 兑换码管理端点。
- 支付对账后台 worker：轮询 pending 订单主动查询 provider 并过期陈旧订单。

### 数据模型
- `orders` 表扩展：内部订单号、支付 URL/地址、过期时间、第三方订单号等。
- 新增 `redemption_codes` 表。

### 测试
- 新增支付用例（兑换码、订单对账、验签、加密下单）共 8 个。累计 38 个全部通过。

## [1.1.0] - 协议与渠道增强

### 新增
- 协议适配器层（`app/adapters`）：把上游各家协议统一成 OpenAI Chat 表示，新增上游只需实现一个适配器。
  - `openai`：透传（DeepSeek/Qwen/Moonshot/OpenRouter 等）。
  - `claude`：Anthropic Messages ⇄ OpenAI 互转（含流式）。
  - `gemini`：Google Generative Language ⇄ OpenAI 互转（含流式）。
- 新增端点：`/v1/embeddings`、`/v1/images/generations`、`/v1/messages`（Anthropic 原生入口）。
- 渠道加权随机路由（按 weight 加权采样，priority 分层）。
- 渠道健康巡检：连续失败自动熔断（status=2），冷却后台任务自动半开恢复。
- 缓存命中计费：`prompt_tokens_details.cached_tokens` 按 `cache_price` 单独计价。

### 变更
- 转发层 `proxy` 重构为基于适配器的统一链路，支持多端点。
- 路由缓存在渠道健康状态变更时自动失效。

### 测试
- 新增适配器互转、多端点、熔断恢复用例，共 32 个，全部通过。

## [1.0.0] - v1 架构基线

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
