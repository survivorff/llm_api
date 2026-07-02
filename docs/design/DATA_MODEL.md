# 数据模型设计 (DATA_MODEL)

> 版本: v1.0
> 数据库: PostgreSQL（生产）/ SQLite（开发）。所有变更走 Alembic 迁移。
> 金额单位约定：内部一律用**整数「点数/credits」**存储，避免浮点误差。
> 建议 1 credit = 0.000001 USD（即 1 USD = 1_000_000 credits），足够表达 token 单价精度。

## 实体关系

```
users 1───* tokens
users 1───* orders
users 1───* billing_ledger
channels 1───* usage_logs
tokens 1───* usage_logs
model_pricing (按 model+group 定价)
settings (KV 系统配置)
```

## users — 用户

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| username | text unique | 登录名 |
| email | text unique nullable | 邮箱 |
| password_hash | text nullable | 本地登录（OAuth 用户可空） |
| role | text | admin / user |
| group | text | 用户分组（影响定价倍率），默认 default |
| balance | bigint | 余额（credits），>=0 |
| frozen | bigint | 冻结中的额度（预扣） |
| status | int | 1 启用 / 0 禁用 |
| created_at | float | |

## tokens — API 令牌（归属用户）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| user_id | int FK | 归属用户 |
| key | text unique | `sk-...` |
| name | text | |
| enabled | int | 启停 |
| quota_tokens | bigint nullable | 令牌级 token 上限（可选，独立于用户余额） |
| used_tokens | bigint | 已用 |
| rpm_limit | int nullable | 每分钟请求数限制 |
| allowed_models | text nullable | 逗号分隔白名单 |
| allowed_groups | text nullable | 可用渠道分组 |
| expires_at | float nullable | 过期时间 |
| created_at | float | |
| note | text | |

## channels — 上游渠道

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| name | text | |
| type | text | openai / claude / gemini / deepseek / openrouter ... 决定适配器 |
| base_url | text | |
| api_keys | text | 加密存储的 key 池（JSON 数组） |
| models | text | 支持的模型（JSON，支持 `*`、前缀） |
| model_map | text | 别名→上游 slug（JSON） |
| headers | text | 附加头（JSON） |
| group | text | 渠道分组，默认 default |
| weight | int | 加权随机权重 |
| priority | int | 优先级（越小越先尝试） |
| status | int | 1 启用 / 0 禁用 / 2 自动熔断 |
| fail_count | int | 连续失败计数（巡检用） |
| created_at | float | |

## model_pricing — 模型定价

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| model | text | 对外模型名 |
| group | text | 适用分组（default 为通用） |
| input_price | bigint | 每 1K 输入 token 的 credits |
| output_price | bigint | 每 1K 输出 token 的 credits |
| cache_price | bigint nullable | 每 1K 缓存命中 token 的 credits |
| multiplier | float | 分组倍率，默认 1.0 |
| enabled | int | |

> 费用 = (prompt/1000 × input_price + completion/1000 × output_price + cached/1000 × cache_price) × multiplier

## usage_logs — 请求明细

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| ts | float | |
| user_id | int nullable | |
| token_id | int nullable | |
| token_name | text | |
| channel | text | |
| model | text | 对外模型 |
| upstream_model | text | 实际上游模型 |
| status | int | HTTP 状态 |
| latency_ms | int | |
| prompt_tokens | int | |
| completion_tokens | int | |
| cached_tokens | int nullable | |
| total_tokens | int | |
| cost | bigint | 实际扣费（credits） |
| stream | int | |
| error | text nullable | |

## billing_ledger — 账单流水（对账核心）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| ts | float | |
| user_id | int FK | |
| type | text | topup 充值 / consume 消费 / refund 退款 / adjust 调整 |
| amount | bigint | 有符号，正为入账负为出账（credits） |
| balance_after | bigint | 记账后余额（快照，便于审计） |
| ref | text nullable | 关联单号（order_id / usage_log_id / 备注） |

> 不变式：任意用户 balance == Σ(该用户 ledger.amount)。定期对账。

## orders — 充值订单

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| user_id | int FK | |
| amount_credits | bigint | 到账点数 |
| amount_money | bigint | 实付金额（最小货币单位，如分/聪） |
| currency | text | CNY / USDT / ... |
| method | text | crypto / wechat / alipay / redemption |
| status | text | pending / paid / expired / failed |
| provider | text | 支付适配器标识 |
| provider_order | text nullable | 第三方单号 |
| created_at / paid_at | float | |

## redemptions — 兑换码（可选）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int PK | |
| code | text unique | |
| amount_credits | bigint | |
| used_by | int nullable | 使用者 user_id |
| used_at | float nullable | |
| created_at | float | |

## settings — 系统配置（可热更新）

| 字段 | 类型 | 说明 |
|---|---|---|
| key | text PK | |
| value | text | JSON |

---

## 迁移策略

- 全部通过 Alembic 版本化。首版 `0001_init` 建上述表。
- 旧 `config.yaml` 的 channels 可通过导入命令写入 channels 表。
- 旧 `usage.db` 提供可选一次性迁移脚本。
