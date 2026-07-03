# 迭代路线图 (ROADMAP)

> 按版本划分，每个版本是一个可交付、可运行、测试通过的里程碑。
> 原则：先跑通全流程 → 再逐层增强，任何阶段都保持"能部署、能用"。

---

## v0.x — 现状（朋友互助最小版，已存在）

已实现：OpenAI 兼容 chat、多 key 轮询、故障转移、令牌配额、内存限速、SQLite 用量、内嵌后台。
局限：单连接 SQLite、内存限速、仅 chat 端点、无余额计费、无支付、无多协议。

---

## v1.0 — 架构地基 + 可运行第一版（本阶段目标）★

**目标：把地基换成可扩展架构，跑通"用户→令牌→计费→转发→落账"全流程，本地一键起。**

- [ ] 引入 SQLAlchemy 2.0 async + Alembic，PostgreSQL/SQLite 双支持
- [ ] Redis 接入（限流/缓存/计数），无 Redis 自动回退内存（单机开发）
- [ ] Gateway 无状态化改造
- [ ] 数据模型：users / tokens / channels / model_pricing / usage_logs / billing_ledger / settings
- [ ] 用户体系（管理员初始化 + 令牌归属用户）
- [ ] 余额 + 模型倍率定价 + **预扣式按量计费**（解决超额漏洞）
- [ ] 分布式 RPM 限速（Redis，回退内存）
- [ ] OpenAI 兼容 chat（流式/非流式）+ models + 渠道路由 + 故障转移（复用并增强现有）
- [ ] 后台：用户/令牌/渠道/定价/用量管理（在现有单页 UI 上扩展）
- [ ] docker-compose（app + postgres + redis）+ 本地 SQLite 快速体验
- [ ] 测试全绿（迁移现有 21 个用例 + 计费用例）

交付物：**本地能起、能创建用户与令牌、能配渠道与价格、能真实转发并按量扣费、后台能看用量与余额。**

---

## v1.1 — 协议与渠道增强 ✅

- [x] Claude Messages `/v1/messages` 原生协议 ⇄ OpenAI 互转
- [x] Google Gemini 原生口 ⇄ OpenAI 互转
- [x] `/v1/embeddings`、`/v1/images/generations` 端点
- [x] 渠道分组 + 加权随机
- [x] 渠道健康巡检 + 连续失败自动熔断/恢复
- [x] 缓存命中计费（DeepSeek/Claude 等 cache 定价）

> 设计文档：`docs/design/v1.1-PROTOCOLS.md`

---

## v1.2 — 支付与充值 ✅

- [x] 充值订单系统（orders）+ 异步对账 worker
- [x] 加密货币充值适配器（USDT-TRC20 / 聚合网关）
- [x] 微信 / 支付宝扫码充值适配器（易支付聚合 + 官方商户可选）
- [x] 兑换码充值
- [x] 支付适配器接口标准化（可插拔，部署者自选）

> 设计文档：`docs/design/v1.2-PAYMENTS.md`

---

## v1.3 — 用户体验与登录 ✅

- [x] 邮箱注册/登录（会话令牌）
- [x] OAuth 登录（GitHub / Google / LinuxDO）
- [x] 用户自助：用量仪表盘、账单明细、令牌自助管理
- [x] 多语言（中/英）

> 设计文档：`docs/design/v1.3-ACCOUNTS.md`
> 备注：邮件验证与 Telegram 登录归入 P2 储备，按需再加。

---

## v2.0 — 开源就绪与运营 ✅

- [x] 系统设置热更新、公告（模型价格表已有后台 CRUD）
- [x] Prometheus 指标（`/metrics`，零依赖内置采集器）
- [x] 审计日志 + 日志保留策略
- [x] 一键部署（Docker 自动迁移 + compose 健康检查）+ CI/CD
- [x] License 与合规声明定稿
- [ ] 安装向导（首次启动引导初始化）→ 归入后续增强
- [ ] Grafana 面板样例 → 归入后续增强

> 设计文档：`docs/design/v2.0-OPS.md`、`docs/design/COMPLIANCE.md`

---

## v2.1 — 门户网站与 UI 重设计 ✅

- [x] 现代化门户首页 `/`（Hero + 特性 + 三步上手 + CTA）
- [x] 文档中心 `/docs`（快速开始/认证/API/客户端/流式/错误码/FAQ）
- [x] 套餐价格 `/pricing`（实时价目表 + ¥/$ 切换）
- [x] 统一设计系统（深色 SaaS 风，响应式，中英双语）
- [x] 公开只读端点 `/public/models`、`/public/pricing`
- [x] 用户控制台 `/portal` 视觉重构

> 设计文档：`docs/design/v2.1-PORTAL.md`

---

## v2.2 — 后台运营工具补全 ✅

- [x] 请求日志（明细 + 多维筛选 + 分页）
- [x] 兑换码管理（批量生成 / 导出 / 作废）
- [x] 订单管理（列表 + 手动补单）
- [x] 系统设置界面（公告 / 注册开关等热更新）
- [x] 审计日志界面
- [x] 概览统计增强（今日/累计 请求·消费·成功率）
- [x] 运营后台使用手册

> 设计文档：`docs/design/v2.2-ADMIN-TOOLS.md`；使用手册：`docs/运营手册.md`

---

## v2.3 — 渠道与账号池增强 ✅

- [x] API Key 池：单 key 用量/失败统计 + 启停（路由跳过禁用 key）
- [x] 渠道连通性测试 + 测速
- [x] 模型自动发现（上游 /models 一键导入）
- [x] 用户分组聚合视图
- [x] 上游 key 解密改用注入 secret（加固）

> 设计文档：`docs/design/v2.3-CHANNELS.md`

---

## 进阶储备（P2，按需）

- Rerank（Cohere/Jina）、Midjourney、Suno 等特殊上游
- OpenAI Responses / Realtime API
- 独立 React 控制台
- 多渠道分组策略、用户分组倍率
- 成本分析与账单导出

---

## 版本管理约定

- 每个 `vX.Y` 对应一个 milestone，合并前测试全绿。
- 主干 `main` 保持可部署；开发走 `feat/*` 分支。
- 每版更新 `CHANGELOG.md` 与相关文档。
- 数据库变更一律走 Alembic 迁移，不手改 schema。
