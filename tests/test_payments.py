"""v1.2 支付与充值：兑换码、订单创建、对账入账（用假 provider，不触网）。"""
from app.db.base import get_sessionmaker
from app.payments.base import PaymentProvider, PaymentRequest, PaymentResult

AUTH = {"Authorization": "Bearer ADMINKEY"}


class FakeProvider(PaymentProvider):
    """测试用假 provider：下单成功；query_status 由 _paid 开关控制。"""
    name = "fake"
    supports_callback = True

    def __init__(self, config=None):
        super().__init__(config or {})
        self._paid = False

    async def create_payment(self, req: PaymentRequest) -> PaymentResult:
        return PaymentResult(ok=True, pay_url=f"https://pay.test/{req.order_no}",
                             provider_order="prov-" + req.order_no)

    async def query_status(self, order_no, provider_order) -> bool:
        return self._paid


def _make_token(gateway):
    """建一个绑定 admin 用户的令牌，用于用户身份的支付接口。"""
    r = gateway.post("/admin/tokens", headers=AUTH, json={"name": "payer"})
    assert r.status_code == 200, r.text
    return r.json()["key"]


def _inject_fake(gateway) -> FakeProvider:
    services = gateway.app.state.services
    prov = FakeProvider()
    services.payments["fake"] = prov
    services.orders.providers["fake"] = prov
    return prov


# ---------------- 兑换码 ----------------
def test_redemption_flow(gateway):
    # admin 生成兑换码
    r = gateway.post("/admin/redemption/generate", headers=AUTH,
                     json={"amount_credits": 500000, "count": 2})
    assert r.status_code == 200, r.text
    codes = r.json()["codes"]
    assert len(codes) == 2

    token = _make_token(gateway)
    uauth = {"Authorization": f"Bearer {token}"}

    # 兑换第一个码
    r = gateway.post("/pay/redeem", headers=uauth, json={"code": codes[0]})
    assert r.status_code == 200, r.text
    assert r.json()["credited"] == 500000

    # 同一码不能重复兑换
    r = gateway.post("/pay/redeem", headers=uauth, json={"code": codes[0]})
    assert r.status_code == 400

    # 无效码
    r = gateway.post("/pay/redeem", headers=uauth, json={"code": "nope"})
    assert r.status_code == 400


# ---------------- 订单 + 对账 ----------------
def test_order_create_and_reconcile(gateway):
    prov = _inject_fake(gateway)
    token = _make_token(gateway)
    uauth = {"Authorization": f"Bearer {token}"}

    # 创建订单（法币 100 元 = 10000 分）
    r = gateway.post("/pay/orders", headers=uauth,
                     json={"method": "fake", "amount_money": 10000})
    assert r.status_code == 200, r.text
    order = r.json()
    assert order["status"] == "pending"
    assert order["pay_url"].startswith("https://pay.test/")
    order_no = order["order_no"]

    # 查询：provider 未支付 → 仍 pending
    r = gateway.get(f"/pay/orders/{order_no}", headers=uauth)
    assert r.json()["status"] == "pending"

    # 模拟支付成功 → 查询触发对账入账
    prov._paid = True
    r = gateway.get(f"/pay/orders/{order_no}", headers=uauth)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paid"

    # 再查一次仍 paid（幂等，不重复入账）
    r = gateway.get(f"/pay/orders/{order_no}", headers=uauth)
    assert r.json()["status"] == "paid"


def test_order_unknown_method_rejected(gateway):
    token = _make_token(gateway)
    uauth = {"Authorization": f"Bearer {token}"}
    r = gateway.post("/pay/orders", headers=uauth,
                     json={"method": "no-such", "amount_money": 100})
    assert r.status_code == 400


def test_payment_methods_listing(gateway):
    _inject_fake(gateway)
    r = gateway.get("/pay/methods", headers=AUTH)
    assert r.status_code == 200
    assert "fake" in r.json()["methods"]


# ---------------- provider 单元测试 ----------------
def test_epay_sign_roundtrip():
    """易支付验签：用同一密钥签名的回调应通过校验。"""
    from app.payments.epay import EPayProvider, _md5_sign

    prov = EPayProvider({"api_url": "https://pay.x", "pid": "1000", "key": "SECRET"})
    form = {
        "pid": "1000", "out_trade_no": "ORDER123", "trade_no": "T999",
        "money": "1.00", "trade_status": "TRADE_SUCCESS",
    }
    form["sign"] = _md5_sign(form, "SECRET")
    form["sign_type"] = "MD5"
    result = prov.verify_callback({}, b"", form)
    assert result.ok
    assert result.order_no == "ORDER123"
    assert result.provider_order == "T999"

    # 篡改金额后验签失败
    form["money"] = "999.00"
    bad = prov.verify_callback({}, b"", form)
    assert not bad.ok


def test_crypto_create_payment():
    """加密货币下单：返回收款地址与金额。"""
    import asyncio

    from app.payments.crypto import CryptoProvider
    from app.payments.base import PaymentRequest

    prov = CryptoProvider({"address": "TXtest123"})
    req = PaymentRequest(order_no="O1", amount_money=5_000_000, currency="USDT")
    result = asyncio.run(prov.create_payment(req))
    assert result.ok
    assert result.pay_address == "TXtest123"
    assert "5.0" in result.extra["amount_usdt"]
