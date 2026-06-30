ADMIN = {"Authorization": "Bearer ADMINKEY"}


def test_admin_requires_key(gateway):
    assert gateway.get("/admin/tokens").status_code in (401, 403)
    assert gateway.get("/admin/tokens", headers=ADMIN).status_code == 200


def test_admin_ui_served(gateway):
    r = gateway.get("/admin")
    assert r.status_code == 200
    assert "llm_api" in r.text


def test_create_and_use_token(gateway):
    # 管理员创建朋友令牌
    r = gateway.post("/admin/tokens", headers=ADMIN, json={"name": "alice"})
    assert r.status_code == 200
    key = r.json()["key"]
    assert key.startswith("sk-")

    # 用该令牌调用网关
    r2 = gateway.post("/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]})
    assert r2.status_code == 200
    assert r2.json()["choices"][0]["message"]["content"] == "echo:deepseek-chat"


def test_disabled_token_rejected(gateway):
    key = gateway.post("/admin/tokens", headers=ADMIN, json={"name": "bob"}).json()["key"]
    tid = gateway.get("/admin/tokens", headers=ADMIN).json()["tokens"][-1]["id"]
    gateway.patch(f"/admin/tokens/{tid}", headers=ADMIN, json={"enabled": False})
    r = gateway.post("/v1/chat/completions",
                     headers={"Authorization": f"Bearer {key}"},
                     json={"model": "deepseek-chat", "messages": []})
    assert r.status_code == 401


def test_quota_enforced(gateway):
    # mock 每次返回 total_tokens=8；配额设 5，第一次成功后累计超额，第二次应 429
    key = gateway.post("/admin/tokens", headers=ADMIN,
                       json={"name": "carol", "quota_tokens": 5}).json()["key"]
    h = {"Authorization": f"Bearer {key}"}
    body = {"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]}
    assert gateway.post("/v1/chat/completions", headers=h, json=body).status_code == 200
    assert gateway.post("/v1/chat/completions", headers=h, json=body).status_code == 429


def test_usage_reports_per_token(gateway):
    key = gateway.post("/admin/tokens", headers=ADMIN, json={"name": "dave"}).json()["key"]
    h = {"Authorization": f"Bearer {key}"}
    gateway.post("/v1/chat/completions", headers=h,
                 json={"model": "deepseek-chat", "messages": []})
    u = gateway.get("/admin/usage", headers=ADMIN).json()
    names = [row["token_name"] for row in u["by_token"]]
    assert "dave" in names


def test_delete_token(gateway):
    key = gateway.post("/admin/tokens", headers=ADMIN, json={"name": "erin"}).json()["key"]
    tid = gateway.get("/admin/tokens", headers=ADMIN).json()["tokens"][-1]["id"]
    assert gateway.delete(f"/admin/tokens/{tid}", headers=ADMIN).status_code == 200
    r = gateway.post("/v1/chat/completions",
                     headers={"Authorization": f"Bearer {key}"},
                     json={"model": "deepseek-chat", "messages": []})
    assert r.status_code == 401
