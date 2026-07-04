"""v2.4 运营分析与批量操作：概览/排行/趋势/告警 + 批量令牌/充值/发放。"""
AUTH = {"Authorization": "Bearer ADMINKEY"}


def _traffic(gateway, n=3):
    key = gateway.post("/admin/tokens", headers=AUTH, json={"name": "an"}).json()["key"]
    h = {"Authorization": f"Bearer {key}"}
    for _ in range(n):
        gateway.post("/v1/chat/completions", headers=h,
                     json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]})


def test_analytics_overview(gateway):
    _traffic(gateway)
    r = gateway.get("/admin/analytics/overview?days=30", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "revenue" in body and "usage" in body
    assert "net_income" in body["revenue"]


def test_analytics_ranking(gateway):
    _traffic(gateway)
    for by in ("model", "user", "channel"):
        r = gateway.get(f"/admin/analytics/ranking?by={by}&days=30", headers=AUTH)
        assert r.status_code == 200
        assert r.json()["by"] == by
        assert isinstance(r.json()["ranking"], list)
    # 非法 by
    assert gateway.get("/admin/analytics/ranking?by=bad", headers=AUTH).status_code == 400


def test_analytics_timeseries(gateway):
    _traffic(gateway)
    r = gateway.get("/admin/analytics/timeseries?days=7&metric=cost", headers=AUTH)
    assert r.status_code == 200
    series = r.json()["series"]
    assert len(series) == 7  # 补齐 7 天
    assert all("date" in s and "value" in s for s in series)
    assert gateway.get("/admin/analytics/timeseries?metric=bad", headers=AUTH).status_code == 400


def test_revenue_reflects_topup(gateway):
    # 给 admin 用户充值，收入报表应反映
    uid = gateway.get("/admin/users", headers=AUTH).json()["users"][0]["id"]
    gateway.post(f"/admin/users/{uid}/topup", headers=AUTH, json={"amount": 500000})
    r = gateway.get("/admin/analytics/overview?days=30", headers=AUTH)
    # topup 通过 admin topup 记为 adjust；grant 才是 topup。这里验证 adjust 计入
    rev = r.json()["revenue"]
    assert rev["by_type"].get("adjust", {}).get("amount", 0) >= 500000


def test_alerts(gateway):
    r = gateway.get("/admin/alerts?min_balance=1000000000", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert "circuit_open" in body and "low_balance" in body


def test_batch_tokens(gateway):
    ids = []
    for i in range(3):
        ids.append(gateway.post("/admin/tokens", headers=AUTH, json={"name": f"b{i}"}).json()["id"])
    # 批量停用
    r = gateway.post("/admin/tokens/batch", headers=AUTH, json={"ids": ids, "action": "disable"})
    assert r.status_code == 200 and r.json()["affected"] == 3
    tokens = {t["id"]: t for t in gateway.get("/admin/tokens", headers=AUTH).json()["tokens"]}
    assert all(tokens[i]["enabled"] == 0 for i in ids)
    # 批量启用
    gateway.post("/admin/tokens/batch", headers=AUTH, json={"ids": ids, "action": "enable"})
    tokens = {t["id"]: t for t in gateway.get("/admin/tokens", headers=AUTH).json()["tokens"]}
    assert all(tokens[i]["enabled"] == 1 for i in ids)
    # 批量删除
    r = gateway.post("/admin/tokens/batch", headers=AUTH, json={"ids": ids, "action": "delete"})
    assert r.json()["affected"] == 3
    remaining = {t["id"] for t in gateway.get("/admin/tokens", headers=AUTH).json()["tokens"]}
    assert not (set(ids) & remaining)


def test_batch_tokens_validation(gateway):
    assert gateway.post("/admin/tokens/batch", headers=AUTH, json={"ids": [], "action": "disable"}).status_code == 400
    assert gateway.post("/admin/tokens/batch", headers=AUTH, json={"ids": [1], "action": "bad"}).status_code == 400


def test_batch_topup(gateway):
    u1 = gateway.post("/admin/users", headers=AUTH, json={"username": "bt1"}).json()["id"]
    u2 = gateway.post("/admin/users", headers=AUTH, json={"username": "bt2"}).json()["id"]
    r = gateway.post("/admin/users/batch-topup", headers=AUTH,
                     json={"user_ids": [u1, u2], "amount": 100000})
    assert r.status_code == 200 and r.json()["affected"] == 2
    users = {u["id"]: u for u in gateway.get("/admin/users", headers=AUTH).json()["users"]}
    assert users[u1]["balance"] == 100000 and users[u2]["balance"] == 100000


def test_grant(gateway):
    uid = gateway.post("/admin/users", headers=AUTH, json={"username": "gr1"}).json()["id"]
    r = gateway.post("/admin/redemption/grant", headers=AUTH,
                     json={"user_id": uid, "amount": 250000, "note": "compensation"})
    assert r.status_code == 200 and r.json()["balance"] == 250000
    # 记为 topup，收入报表可见
    rev = gateway.get("/admin/analytics/overview?days=1", headers=AUTH).json()["revenue"]
    assert rev["topup"] >= 250000
