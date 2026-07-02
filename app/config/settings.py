"""应用配置：环境变量 + .env（pydantic-settings）。

生产用环境变量注入；本地开发有合理默认值，无需 Redis/Postgres 也能起。
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- 基础 ----
    app_name: str = "llm_api gateway"
    host: str = "127.0.0.1"
    port: int = 8080
    debug: bool = False

    # ---- 数据库 ----
    # 默认 SQLite（开发/单机）。生产设 DATABASE_URL 为 postgresql+asyncpg://...
    database_url: str = "sqlite+aiosqlite:///./data/llm_api.db"

    # ---- Redis（可选，缺省回退内存） ----
    redis_url: str | None = None

    # ---- 安全 ----
    admin_key: str | None = None          # 后台管理密钥
    session_secret: str = "dev-session-secret-change-me"
    crypto_secret: str = "dev-crypto-secret-change-me-32byte"  # 上游 key 加密

    # ---- 计费 ----
    # 1 USD = 1_000_000 credits（微美元精度）
    credits_per_usd: int = 1_000_000
    # 预扣保守上限：无 max_tokens 时按此估算冻结
    default_prefreeze_tokens: int = 8192

    # ---- 渠道健康巡检（熔断/恢复）----
    channel_fail_threshold: int = 5        # 连续失败达到即熔断
    channel_cooldown_seconds: float = 60.0  # 熔断后冷却时长，过后半开重试
    channel_health_interval: float = 30.0   # 后台巡检周期（秒）

    # ---- 充值与支付 ----
    # 支付渠道配置（JSON 字符串）。示例：
    #   {"epay":{"api_url":"https://pay.x.com","pid":"1000","key":"xxx",
    #            "notify_url":"https://host/pay/notify/epay"},
    #    "crypto":{"address":"TXXXX","api_key":"trongrid-key"}}
    payment_providers: str = "{}"
    usd_cny_rate: float = 7.2          # 人民币→USD 换算（credits 以 USD 计价）
    order_ttl_seconds: float = 1800.0  # 订单有效期（秒）
    reconcile_interval: float = 30.0   # 对账 worker 轮询周期（秒）

    # ---- 旧配置兼容：首次启动可从 config.yaml 导入渠道 ----
    legacy_config_path: str | None = "config.yaml"

    # ---- HTTP 客户端是否信任系统代理（生产按需；本地测试常设 False 绕过本机代理）----
    http_trust_env: bool = True

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def payment_config(self) -> dict:
        import json
        try:
            return json.loads(self.payment_providers or "{}")
        except Exception:
            return {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
