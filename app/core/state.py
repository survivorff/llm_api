"""应用级共享服务容器（挂在 app.state 上）。"""
import httpx

from ..config import Settings
from ..domain.accounts import AccountService
from ..domain.auth import AuthService
from ..domain.billing import BillingService
from ..domain.health import HealthService
from ..domain.oauth import build_oauth_providers
from ..domain.orders import OrderService
from ..domain.pricing import PricingService
from ..domain.routing import Router
from ..domain.usage import UsageService
from ..payments import build_providers
from .ratelimit import MemoryRateLimiter, RateLimiter, RedisRateLimiter


class AppServices:
    def __init__(self, settings: Settings, http: httpx.AsyncClient, redis, limiter: RateLimiter):
        self.settings = settings
        self.http = http
        self.redis = redis
        self.limiter = limiter
        self.auth = AuthService(settings.admin_key)
        self.billing = BillingService()
        self.pricing = PricingService()
        self.usage = UsageService()
        self.router = Router()
        self.health = HealthService(
            fail_threshold=settings.channel_fail_threshold,
            cooldown=settings.channel_cooldown_seconds,
        )
        # 健康状态变更后让路由缓存失效，避免熔断/恢复延迟
        self.health.on_change = self.router.invalidate
        # 支付 provider（可插拔）+ 订单服务
        self.payments = build_providers(settings.payment_config)
        self.orders = OrderService(self.billing, self.payments, settings)
        # 账户 / 会话 / OAuth（v1.3）
        self.accounts = AccountService(
            settings.session_secret, session_ttl=settings.session_ttl_seconds,
            allow_registration=settings.allow_registration,
        )
        self.oauth = build_oauth_providers(settings.oauth_config)

    @classmethod
    def build(cls, settings: Settings, http, redis) -> "AppServices":
        limiter: RateLimiter = RedisRateLimiter(redis) if redis else MemoryRateLimiter()
        return cls(settings, http, redis, limiter)
