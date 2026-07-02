"""计费测试：定价、预扣冻结、结算、余额不足拒绝。"""
ADMIN = {"Authorization": "Bearer ADMINKEY"}


def _admin_user_id(gateway):
    return gateway.get("/admin/users", headers=ADMIN).json()["users"][0]["id"]


def test_pricing_charged_on_request(gateway):
    uid = _admin_user_id(gateway)
    # 设置 deepseek-chat 定价：输入/输出各 1000 credits/1K
    gateway.post("/admin/pricing", headers=ADMIN, json={
        "model": "deepseek-chat", "group": "default",
        "input_price": 1000, "output_price": 1000,
    })
    # 创建一个归属 admin 用户的令牌
    key = gateway.post("/admin/tokens", headers=ADMIN,
                       json={"name": "payer", "user_id": uid}).json()["key"]
    h = {"Authorization": f"Bearer {key}"}

    before = gateway.get("/admin/users", headers=ADMIN).json()["users"][0]["balance"]
    r = gateway.post("/v1/chat/completions", headers=h,
                     json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    after = gateway.get("/admin/users", headers=ADMIN).json()["users"][0]["balance"]
    # mock 返回 prompt=5, completion=3 → cost = (5/1000+3/1000)*1000 = 8 credits
    assert before - after == 8


def test_insufficient_balance_rejected(gateway):
    # 新建一个零余额用户 + 定价
    u = gateway.post("/admin/users", headers=ADMIN,
                     json={"username": "broke", "balance": 0}).json()
    gateway.post("/admin/pricing", headers=ADMIN, json={
        "model": "deepseek-chat", "group": "default",
        "input_price": 100000, "output_price": 100000,
    })
    key = gateway.post("/admin/tokens", headers=ADMIN,
                       json={"name": "broke-tok", "user_id": u["id"]}).json()["key"]
    r = gateway.post("/v1/chat/completions",
                     headers={"Authorization": f"Bearer {key}"},
                     json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}],
                           "max_tokens": 1000})
    assert r.status_code == 402


def test_ledger_records_consumption(gateway):
    uid = _admin_user_id(gateway)
    gateway.post("/admin/pricing", headers=ADMIN, json={
        "model": "deepseek-chat", "input_price": 1000, "output_price": 1000})
    key = gateway.post("/admin/tokens", headers=ADMIN,
                       json={"name": "ledger", "user_id": uid}).json()["key"]
    gateway.post("/v1/chat/completions", headers={"Authorization": f"Bearer {key}"},
                 json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]})
    # 用量报表里应有费用记录
    usage = gateway.get("/admin/usage", headers=ADMIN).json()
    total_cost = sum(r["cost"] for r in usage["by_token"])
    assert total_cost >= 8


def test_no_pricing_no_charge(gateway):
    # 未配价的模型不扣费（仅记录）
    uid = _admin_user_id(gateway)
    key = gateway.post("/admin/tokens", headers=ADMIN,
                       json={"name": "free", "user_id": uid}).json()["key"]
    before = gateway.get("/admin/users", headers=ADMIN).json()["users"][0]["balance"]
    r = gateway.post("/v1/chat/completions", headers={"Authorization": f"Bearer {key}"},
                     json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200
    after = gateway.get("/admin/users", headers=ADMIN).json()["users"][0]["balance"]
    assert before == after
