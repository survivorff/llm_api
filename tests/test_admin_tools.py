"""v2.2 后台运营工具：请求日志筛选/分页、统计、兑换码作废/导出、订单补单。"""
AUTH = {"Authorization": "Bearer ADMINKEY"}


def _make_token(gateway):
    return gateway.post("/admin/tokens", headers=AUTH, json={"name": "logtest"}).json()["key"]


def _make_traffic(gateway):
    """产生若干请求日志（deepseek-chat 有 mock 渠道）。"""
    key = _make_token(gateway)
    h = {"Authorization": f"Bearer {key}"}
    for _ in range(3):
        gateway.post("/v1/chat/completions", headers=h,
                     json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]})


def test_logs_pagination_and_filter(gateway):
    _make_traffic(gateway)
    r = gateway.get("/admin/logs?limit=2&offset=0", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "total" in body and "items" in body
    assert body["total"] >= 3
    assert len(body["items"]) <= 2
    # 按模型筛选
    r2 = gateway.get("/admin/logs?model=deepseek-chat", headers=AUTH)
    assert all(it["model"] == "deepseek-chat" for it in r2.json()["items"])
    # 按不存在的模型筛选
    r3 = gateway.get("/admin/logs?model=nope", headers=AUTH)
    assert r3.json()["total"] == 0


def test_logs_only_errors(gateway):
    _make_traffic(gateway)
    r = gateway.get("/admin/logs?only_errors=1", headers=AUTH)
    assert r.status_code == 200
    assert all(it["status"] >= 400 for it in r.json()["items"])


def test_logs_stats(gateway):
    _make_traffic(gateway)
    r = gateway.get("/admin/logs/stats?days=7", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    for k in ("total", "today", "window"):
        assert k in body
        assert "requests" in body[k] and "success_rate" in body[k]
    assert body["total"]["requests"] >= 3


def test_redemption_void(gateway):
    codes = gateway.post("/admin/redemption/generate", headers=AUTH,
                         json={"amount_credits": 1000, "count": 2, "batch": "b1"}).json()
    # 找到第一个码的 id
    rid = gateway.get("/admin/redemption", headers=AUTH).json()["codes"][0]["id"]
    r = gateway.post("/admin/redemption/void", headers=AUTH, json={"id": rid})
    assert r.status_code == 200 and r.json()["voided"] == 1
    # 按批次作废剩余
    r2 = gateway.post("/admin/redemption/void", headers=AUTH, json={"batch": "b1"})
    assert r2.status_code == 200


def test_redemption_export_csv(gateway):
    gateway.post("/admin/redemption/generate", headers=AUTH,
                 json={"amount_credits": 1000, "count": 2, "batch": "exp"})
    r = gateway.get("/admin/redemption/export?batch=exp", headers=AUTH)
    assert r.status_code == 200
    assert "code,amount_credits" in r.text
    assert len(r.text.strip().splitlines()) >= 3  # header + 2


def test_void_requires_target(gateway):
    r = gateway.post("/admin/redemption/void", headers=AUTH, json={})
    assert r.status_code == 400


def test_order_mark_paid(gateway):
    # 造一个 pending 订单：注册用户 + 用假 provider 下单
    from app.payments.base import PaymentProvider, PaymentResult

    class Fake(PaymentProvider):
        name = "fake"
        async def create_payment(self, req):
            return PaymentResult(ok=True, pay_url="http://x", provider_order="p1")

    services = gateway.app.state.services
    services.payments["fake"] = Fake({})
    services.orders.providers["fake"] = services.payments["fake"]

    sess = gateway.post("/auth/register", json={"email": "o@e.com", "password": "secret123"}).json()["session"]
    uh = {"Authorization": f"Bearer {sess}"}
    order = gateway.post("/pay/orders", headers=uh,
                         json={"method": "fake", "amount_money": 10000}).json()
    no = order["order_no"]
    # admin 手动补单
    r = gateway.post(f"/admin/orders/{no}/mark-paid", headers=AUTH)
    assert r.status_code == 200 and r.json()["ok"] is True
    # 订单变为 paid
    orders = gateway.get("/admin/orders", headers=AUTH).json()["orders"]
    assert any(o["order_no"] == no and o["status"] == "paid" for o in orders)


def test_mark_paid_unknown_order(gateway):
    r = gateway.post("/admin/orders/nonexistent/mark-paid", headers=AUTH)
    assert r.status_code == 404
