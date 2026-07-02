"""SQLAlchemy ORM 模型（对应 docs/design/DATA_MODEL.md）。

金额单位：credits（整数），1 USD = settings.credits_per_usd。
时间：统一用 float epoch 秒，跨 SQLite/PG 一致、无时区歧义。
"""
import time

from sqlalchemy import BigInteger, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _now() -> float:
    return time.time()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(16), default="user")  # admin / user
    group: Mapped[str] = mapped_column(String(32), default="default")
    balance: Mapped[int] = mapped_column(BigInteger, default=0)      # 可用余额 credits
    frozen: Mapped[int] = mapped_column(BigInteger, default=0)       # 冻结中 credits
    status: Mapped[int] = mapped_column(Integer, default=1)          # 1 启用 / 0 禁用
    created_at: Mapped[float] = mapped_column(Float, default=_now)


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="token")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    quota_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    used_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    rpm_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_models: Mapped[str | None] = mapped_column(Text, nullable=True)   # 逗号分隔
    allowed_groups: Mapped[str | None] = mapped_column(Text, nullable=True)   # 逗号分隔
    expires_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_now)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(32), default="openai")  # 决定适配器
    base_url: Mapped[str] = mapped_column(Text)
    api_keys: Mapped[str] = mapped_column(Text, default="[]")        # 加密后的 JSON 数组
    models: Mapped[str] = mapped_column(Text, default="[]")          # JSON 数组
    model_map: Mapped[str] = mapped_column(Text, default="{}")       # JSON 对象
    headers: Mapped[str] = mapped_column(Text, default="{}")         # JSON 对象
    group: Mapped[str] = mapped_column(String(32), default="default")
    weight: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(Integer, default=1)          # 1启用/0禁用/2熔断
    fail_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=_now)


class ModelPricing(Base):
    __tablename__ = "model_pricing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(128), index=True)
    group: Mapped[str] = mapped_column(String(32), default="default")
    input_price: Mapped[int] = mapped_column(BigInteger, default=0)   # per 1K tokens, credits
    output_price: Mapped[int] = mapped_column(BigInteger, default=0)
    cache_price: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[float] = mapped_column(Float, default=_now, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    token_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    upstream_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[int] = mapped_column(BigInteger, default=0)          # 实际扣费 credits
    stream: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class BillingLedger(Base):
    __tablename__ = "billing_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[float] = mapped_column(Float, default=_now, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    type: Mapped[str] = mapped_column(String(16))   # topup/consume/refund/adjust
    amount: Mapped[int] = mapped_column(BigInteger)  # 有符号 credits
    balance_after: Mapped[int] = mapped_column(BigInteger, default=0)
    ref: Mapped[str | None] = mapped_column(Text, nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    amount_credits: Mapped[int] = mapped_column(BigInteger)
    amount_money: Mapped[int] = mapped_column(BigInteger)   # 最小货币单位
    currency: Mapped[str] = mapped_column(String(16), default="CNY")
    method: Mapped[str] = mapped_column(String(32))         # crypto/wechat/alipay/redemption
    status: Mapped[str] = mapped_column(String(16), default="pending")
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_order: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_now)
    paid_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
